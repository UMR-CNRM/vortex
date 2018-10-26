#!/usr/bin/env python
# -*- coding:Utf-8 -*-
# pylint: disable=unused-argument

from __future__ import print_function, absolute_import, unicode_literals, division

import ast
import collections
import copy
import hashlib
import re
import six

import footprints
from vortex.data.stores import Store, ArchiveStore, MultiStore, CacheStore,\
    ConfigurableArchiveStore
from vortex.util.config import GenericConfigParser
from gco.syntax.stdattrs import UgetId

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)

GGET_DEFAULT_CONFIGFILE = '@gget-key-specific-conf.ini'


class GcoStoreConfig(GenericConfigParser):
    """Configuration handler for the GcoStores."""

    def __init__(self, *kargs, **kwargs):
        self.__dict__['_config_defaults'] = dict()
        self.__dict__['_config_re_cache'] = collections.defaultdict(dict)
        self.__dict__['_search_cache'] = dict()
        super(GcoStoreConfig, self).__init__(*kargs, **kwargs)

    def _decoder(self, value):
        """Try to evaluate the configuration file values."""
        try:
            return ast.literal_eval(value)
        except (SyntaxError, ValueError):
            return value

    def setfile(self, inifile, encoding=None):
        """Read the specified ``inifile`` as new configuration."""
        super(GcoStoreConfig, self).setfile(inifile, encoding=None)
        # Create a regex cache for later use in key_properties
        for section in self.sections():
            k_re = re.compile(section)
            self._config_re_cache[k_re] = {k: self._decoder(v)
                                           for k, v in self.items(section)}
        self._config_defaults = {k: self._decoder(v)
                                 for k, v in six.iteritems(self.defaults())}

    def key_properties(self, ggetkey):
        """See if a given *ggetkey* matches one of the sections of the configuration file.

        If the *ggetkey* matches one of the sections, a dictionary of the keys
        defined in this section is returned. Otherwise, the default values are
        returned.
        """
        if ggetkey not in self._search_cache:
            if self.file is None:
                raise RuntimeError("A configuration file must be setup first")
            myconf = self._config_defaults
            for section_re, section_conf in six.iteritems(self._config_re_cache):
                if section_re.match(ggetkey):
                    myconf = section_conf
                    break
            self._search_cache[ggetkey] = myconf
        return self._search_cache[ggetkey]

    def key_untar_properties(self, ggetkey):
        """Filtered version of **key_properties** with only untar related data."""
        return {k: v for k, v in six.iteritems(self.key_properties(ggetkey))
                if k in ['uniquelevel_ignore']}


class GcoCentralStore(Store):
    """
    GCO central storage class.

    Extended footprint:

    * scheme (in values: ``gget``)
    * netloc (in values: ``gco.meteo.fr``)
    """

    _footprint = dict(
        info = 'GCO Central Store',
        attr = dict(
            scheme = dict(
                values   = ['gget'],
            ),
            netloc = dict(
                values   = ['gco.meteo.fr'],
            ),
            ggetcmd = dict(
                optional = True,
                default  = None
            ),
            ggetpath = dict(
                optional = True,
                default  = None
            ),
            ggetroot = dict(
                optional = True,
                default  = None
            ),
            ggetarchive = dict(
                optional = True,
                default  = None
            ),
            ggetconfig = dict(
                type = GcoStoreConfig,
                optional = True,
                default = GcoStoreConfig(GGET_DEFAULT_CONFIGFILE),
            )
        )
    )

    def __init__(self, *args, **kw):
        """Proxy init abstract method. Logging only for the time being."""
        logger.debug('Gco store init %s', self.__class__)
        super(GcoCentralStore, self).__init__(*args, **kw)

    @property
    def realkind(self):
        """Default realkind is ``gstore``."""
        return 'gstore'

    def _actualgget(self, rpath):
        """Return actual (gtool, garchive, tampon, gname)."""
        tg = self.system.default_target

        lpath = rpath.lstrip('/').split('/')
        gname = lpath.pop()

        if 'GGET_TAMPON' in self.system.env:
            tampon = self.system.env.GGET_TAMPON
        else:
            rootdir = self.ggetroot
            if rootdir is None:
                rootdir = tg.get('gco:rootdir', '')
            tampon = rootdir + '/' + '/'.join(lpath)

        gcmd = self.ggetcmd
        if gcmd is None:
            gcmd = tg.get('gco:ggetcmd', 'gget')

        gpath = self.ggetpath
        if gpath is None:
            if 'GGET_PATH' in self.system.env:
                gpath = self.system.env.GGET_PATH
            else:
                gpath = tg.get('gco:ggetpath', '')

        garchive = self.ggetarchive
        if garchive is None:
            garchive = tg.get('gco:ggetarchive', 'hendrix')

        return (self.system.path.join(gpath, gcmd), garchive, tampon, gname)

    def ggetcheck(self, remote, options):
        """Verify disponibility in GCO's tampon using ``gget`` external tool."""
        gloc = self.ggetlocate(remote, options)
        if gloc:
            return self.system.size(gloc)
        else:
            return False

    def ggetlocate(self, remote, options):
        """Get location in GCO's tampon using ``gget`` external tool."""
        (gtool, archive, tampon, gname) = self._actualgget(remote['path'])
        sh = self.system
        sh.env.GGET_TAMPON = tampon
        gloc = sh.spawn([gtool, '-path', '-host', archive, gname], output=True)
        if gloc and sh.path.exists(gloc[0]):
            return gloc[0]
        else:
            return False

    def ggetget(self, remote, local, options):
        """System call to ``gget`` external tool."""
        (gtool, archive, tampon, gname) = self._actualgget(remote['path'])
        sh = self.system
        sh.env.GGET_TAMPON = tampon

        if options is None:
            options = dict()
        fmt = options.get('fmt', 'foo')
        extract = remote['query'].get('extract', None)
        if extract and sh.path.exists(gname):
            logger.info("The resource was already fetched in a previous extract.")
            rc = True
        else:
            rc = sh.spawn([gtool, '-host', archive, gname], output=False)

        if rc and sh.path.exists(gname):
            if extract:
                # The file to extract may be in a tar file...
                if not sh.path.isdir(gname) and sh.is_tarname(gname) and sh.is_tarfile(gname):
                    destdir = sh.tarname_radix(sh.path.realpath(gname))
                    if sh.path.exists(destdir):
                        logger.info("%s was already fetched in a previous extract.", destdir)
                    else:
                        untaropts = self.ggetconfig.key_untar_properties(gname)
                        rc = len(sh.smartuntar(gname, destdir, output=False, **untaropts)) > 0
                    gname = destdir
                logger.info('GCO Central Store get %s', gname + '/' + extract[0])
                rc = rc and sh.cp(gname + '/' + extract[0], local, fmt=fmt)
            else:
                # Always move the resource to destination (fmt may influence the result)
                logger.info('GCO Central Store get %s', gname)
                rc = rc and sh.filecocoon(local)
                rc = rc and sh.mv(gname, local, fmt=fmt)
                # Automatic untar if needed... (the local file needs to end with a tar extension)
                if not sh.path.isdir(local) and sh.is_tarname(local) and sh.is_tarfile(local):
                    destdir = sh.path.dirname(sh.path.realpath(local))
                    untaropts = self.ggetconfig.key_untar_properties(gname)
                    sh.smartuntar(local, destdir, output=False, **untaropts)
        else:
            logger.warning('GCO Central Store get %s was not successful (with rc=%s)', gname, rc)
            rc = False
        return rc

    def ggetdelete(self, remote, options):
        """This operation is not supported."""
        logger.warning('Removing from GCO Store is not supported')
        return False


class GcoCacheStore(CacheStore):
    """Some kind of cache for GCO components."""

    _footprint = dict(
        info = 'GCO cache access',
        attr = dict(
            scheme = dict(
                values  = ['gget'],
            ),
            netloc = dict(
                values  = ['gco.cache.fr'],
            ),
            strategy = dict(
                default = 'mtool',
            ),
            rootdir = dict(
                default = 'auto'
            ),
            headdir = dict(
                default = 'gco',
                outcast = ['xp', 'vortex'],
            ),
            ggetconfig = dict(
                type = GcoStoreConfig,
                optional = True,
                default = GcoStoreConfig(GGET_DEFAULT_CONFIGFILE),
            )
        )
    )

    def __init__(self, *args, **kw):
        """Proxy init method. Perform a cache reset after initialisation."""
        logger.debug('GCO cache store init %s', self.__class__)
        super(GcoCacheStore, self).__init__(*args, **kw)

    def ggetcheck(self, remote, options):
        """Gateway to :meth:`incachecheck`."""
        return self.incachecheck(remote, options)

    def ggetlocate(self, remote, options):
        """Gateway to :meth:`incachelocate`."""
        return self.incachelocate(remote, options)

    def ggetget(self, remote, local, options):
        """Gateway to :meth:`incacheget`."""
        extract = remote['query'].get('extract', None)
        if extract:
            logger.warning('Skip cache get with extracted %s', extract)
            return False
        else:
            gname = remote['path'].lstrip('/').split('/').pop()
            options_tmp = options.copy() if options else dict()
            options_tmp.update(self.ggetconfig.key_untar_properties(gname))
            options_tmp['auto_tarextract'] = True
            return self.incacheget(remote, local, options_tmp)

    def ggetput(self, local, remote, options):
        """Gateway to :meth:`incacheputt`."""
        extract = remote['query'].get('extract', None)
        if extract:
            logger.warning('Skip cache put with extracted %s', extract)
            return False
        else:
            return self.incacheput(local, remote, options)

    def ggetdelete(self, remote, options):
        """Gateway to :meth:`incachedelete`."""
        return self.incachedelete(remote, options)


class GcoStore(MultiStore):
    """Combined cache and central GCO stores."""

    _footprint = dict(
        info = 'GCO multi access',
        attr = dict(
            scheme = dict(
                values   = ['gget'],
            ),
            netloc = dict(
                values   = ['gco.multi.fr'],
            ),
            refillstore = dict(
                default  = True,
            )
        )
    )

    def alternates_netloc(self):
        """Tuple of alternates domains names, e.g. ``cache`` and ``archive``."""
        return ('gco.cache.fr', 'gco.meteo.fr')


class _UgetStoreMixin(object):
    """Some very useful methods needed by all Uget stores."""

    def _actual_fancyget(self, remote, local, options):
        raise NotImplementedError('We really need _actual_fancyget !')

    def _local_auto_untar(self, local, uname):
        """Automatic untar if needed...

        (the local file needs to end with a tar extension).
        """
        if (isinstance(local, six.string_types) and not self.system.path.isdir(local) and
                self.system.is_tarname(local) and self.system.is_tarfile(local)):
            destdir = self.system.path.dirname(self.system.path.realpath(local))
            untaropts = self.ugetconfig.key_untar_properties(uname)
            self.system.smartuntar(local, destdir, output=False, **untaropts)

    def _fancy_get(self, remote, local, options):
        """Remap and ftpget sequence."""
        if options is None:
            options = dict()
        fmt = options.get('fmt', 'foo')
        extract = remote['query'].get('extract', None)
        uname = self.system.path.basename(remote['path'])
        if extract and self.system.path.exists(uname):
            logger.info("The Uget element was already fetched in a previous extract.")
            rc = True
        else:
            rc = self._actual_fancyget(remote, uname if extract else local, options)

        if rc:
            if extract:
                # The file to extract may be in a tar file...
                if (self.system.is_tarname(uname) and self.system.is_tarfile(uname)):
                    destdir = self.system.tarname_radix(self.system.path.realpath(uname))
                    if self.system.path.exists(destdir):
                        logger.info("%s was already unpacked during a previous extract.", destdir)
                    else:
                        untaropts = self.ugetconfig.key_untar_properties(uname)
                        rc = len(self.system.smartuntar(uname, destdir, output=False, **untaropts)) > 0
                # Otherwise, assume that the file to extract is in a directory
                else:
                    destdir = self.system.path.realpath(uname)
                rc = rc and self.system.cp(destdir + '/' + extract[0], local, fmt=fmt)
            else:
                self._local_auto_untar(local, uname)
        else:
            self._verbose_log(options, 'warning',
                              '%s get on %s was not successful (rc=%s)',
                              self.__class__.__name__, local, rc, slevel='info')
        return rc


class UgetArchiveStore(ArchiveStore, ConfigurableArchiveStore, _UgetStoreMixin):
    """
    Uget archive store
    """

    _eltid_cleaner0 = re.compile(r'\.m\d+$')
    _eltid_cleaner1 = re.compile(r'^(.*)\.\d+[a-zA-Z_-]*($|\.\D*$)')

    #: Path to the uget Store configuration file
    _store_global_config = '@store-uget.ini'
    _datastore_id = 'store-uget-conf'

    _footprint = dict(
        info = 'Uget Archive Store',
        attr = dict(
            scheme = dict(
                values   = ['uget'],
            ),
            netloc = dict(
                values   = ['uget.archive.fr'],
            ),
            storeroot = dict(
                default  = None,
            ),
            storehead = dict(
                default  = 'uget',
            ),
            storehash = dict(
                default = 'md5',
            ),
            ugetconfig = dict(
                alias = ['ggetconfig', ],
                type = GcoStoreConfig,
                optional = True,
                default = GcoStoreConfig(GGET_DEFAULT_CONFIGFILE),
            ),
            readonly = dict(
                default = True,
            )
        )
    )

    @property
    def realkind(self):
        """Default realkind is ``uget``."""
        return 'uget'

    @classmethod
    def _hashdir(cls, eltid):
        cleaned = cls._eltid_cleaner0.sub('', eltid)
        cleaned = cls._eltid_cleaner1.sub(r'\1\2', cleaned)
        return hashlib.md5(cleaned).hexdigest()[0]

    def _universal_remap(self, remote):
        """Reformulates the remote path to compatible vortex namespace."""
        remote = copy.copy(remote)
        xpath = remote['path'].split('/')
        f_uuid = UgetId('uget:' + xpath[2])
        remote['path'] = self.system.path.join(self.storehead, xpath[1],
                                               self._hashdir(f_uuid.id), f_uuid.id)
        if 'root' not in remote:
            remote['root'] = self._actual_storeroot(f_uuid)
        return remote

    def _list_remap(self, remote):
        """Reformulates the remote path to compatible vortex namespace."""
        rlist = []
        xpath = remote['path'].split('/')
        if re.match('^@(\w+)$', xpath[2]):
            f_uuid = UgetId('uget:fake' + xpath[2])
            for h in range(16):
                a_remote = copy.copy(remote)
                a_remote['path'] = self.system.path.join(self.storehead, xpath[1],
                                                         re.sub('0x(.)', r'\1', hex(h)))
                rlist.append(a_remote)
        else:
            f_uuid = UgetId('uget:' + xpath[2])
            a_remote = copy.copy(remote)
            a_remote['path'] = self.system.path.join(self.storehead, xpath[1],
                                                     self._hashdir(f_uuid.id), f_uuid.id)
            rlist.append(a_remote)
        for a_remote in rlist:
            if 'root' not in a_remote:
                a_remote['root'] = self._actual_storeroot(f_uuid)
        return rlist

    def ugetcheck(self, remote, options):
        """Remap and ftpcheck sequence."""
        return self.inarchivecheck(self._universal_remap(remote), options)

    def ugetlocate(self, remote, options):
        """Remap and ftplocate sequence."""
        return self.inarchivelocate(self._universal_remap(remote), options)

    def ugetlist(self, remote, options):
        """Remap and ftplocate sequence."""
        stuff = set()
        with self.system.ftppool():
            for a_remote in self._list_remap(remote):
                rc = self.inarchivelist(a_remote, options)
                if isinstance(rc, list):
                    stuff.update(rc)
                elif rc is True:
                    return rc
        return sorted([s for s in stuff if not (s.endswith('.' + self.storehash) and s[:-(len(self.storehash) + 1)] in stuff)])

    def ugetprestageinfo(self, remote, options):
        """Remap and ftpprestageinfo sequence."""
        return self.inarchiveprestageinfo(self._universal_remap(remote), options)

    def _actual_fancyget(self, remote, local, options):
        return self.inarchiveget(remote, local, options)

    def ugetget(self, remote, local, options):
        """Remap and ftpget sequence."""
        remote = self._universal_remap(remote)
        return self._fancy_get(remote, local, options)

    def ugetearlyget(self, remote, local, options):
        """Remap and inarchiveearlyget sequence."""
        # !!! Keep this method compatible with self._fancy_get !!!
        remote = self._universal_remap(remote)
        if options is None:
            options = dict()
        # Deal with extract !
        extract = remote['query'].get('extract', None)
        if extract:
            return None  # No early-get when extract=True
        return self.inarchiveearlyget(remote, local, options)

    def ugetfinaliseget(self, result_id, remote, local, options):
        """Remap and inarchivefinaliseget sequence."""
        # !!! Keep this method compatible with self._fancy_get !!!
        remote = self._universal_remap(remote)
        if options is None:
            options = dict()
        # Deal with extract !
        extract = remote['query'].get('extract', None)
        if extract:
            return False  # No early-get when extract=True
        # Actual finalise
        rc = self.inarchivefinaliseget(result_id, remote, local, options)
        # Automatic untar if needed...
        self._local_auto_untar(local, self.system.path.basename(remote['path']))
        return rc

    def ugetput(self, local, remote, options):
        """Remap root dir and ftpput sequence."""
        if not self.storetrue:
            logger.info("put deactivated for %s", str(local))
            return True
        return self.inarchiveput(local, self._universal_remap(remote), options)

    def ugetdelete(self, remote, options):
        """Remap root dir and ftpdelete sequence."""
        return self.inarchivedelete(self._universal_remap(remote), options)


class _UgetCacheStore(CacheStore, _UgetStoreMixin):
    """Some kind of cache for VORTEX experiments: one still needs to choose the cache strategy."""

    _abstract = True
    _footprint = dict(
        info = 'Uget cache access',
        attr = dict(
            scheme = dict(
                values  = ['uget'],
            ),
            rootdir = dict(
                default = 'auto'
            ),
            headdir = dict(
                default = 'uget',
            ),
            ugetconfig = dict(
                alias = ['ggetconfig', ],
                type = GcoStoreConfig,
                optional = True,
                default = GcoStoreConfig(GGET_DEFAULT_CONFIGFILE),
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Vortex cache store init %s', self.__class__)
        super(_UgetCacheStore, self).__init__(*args, **kw)
        del self.cache

    def _universal_remap(self, remote):
        """Reformulates the remote path to compatible vortex namespace."""
        remote = copy.copy(remote)
        xpath = remote['path'].split('/')
        f_uuid = UgetId('uget:' + xpath[2])
        remote['path'] = self.system.path.join(f_uuid.location, xpath[1], f_uuid.id)
        return remote

    def _list_remap(self, remote):
        """Reformulates the remote path to compatible vortex namespace."""
        remote = copy.copy(remote)
        xpath = remote['path'].split('/')
        if re.match('^@(\w+)$', xpath[2]):
            f_uuid = UgetId('uget:fake' + xpath[2])
            remote['path'] = self.system.path.join(f_uuid.location, xpath[1])
        else:
            f_uuid = UgetId('uget:' + xpath[2])
            remote['path'] = self.system.path.join(f_uuid.location, xpath[1], f_uuid.id)
        return remote

    def ugetcheck(self, remote, options):
        """Proxy to :meth:`incachecheck`."""
        return self.incachecheck(self._universal_remap(remote), options)

    def ugetlocate(self, remote, options):
        """Proxy to :meth:`incachelocate`."""
        return self.incachelocate(self._universal_remap(remote), options)

    def ugetlist(self, remote, options):
        """Proxy to :meth:`incachelocate`."""
        return self.incachelist(self._list_remap(remote), options)

    def ugetprestageinfo(self, remote, options):
        """Proxy to :meth:`incacheprestageinfo`."""
        return self.incacheprestageinfo(self._universal_remap(remote), options)

    def _actual_fancyget(self, remote, local, options):
        return self.incacheget(remote, local, options)

    def ugetget(self, remote, local, options):
        """Remap and ftpget sequence."""
        remote = self._universal_remap(remote)
        return self._fancy_get(remote, local, options)

    def ugetput(self, local, remote, options):
        """Proxy to :meth:`incacheputt`."""
        remote = self._universal_remap(remote)
        extract = remote['query'].get('extract', None)
        if extract:
            logger.warning('Skip cache put with extracted %s', extract)
            return False
        else:
            return self.incacheput(local, remote, options)

    def ugetdelete(self, remote, options):
        """Proxy to :meth:`incachedelete`."""
        return self.incachedelete(self._universal_remap(remote), options)


class UgetMtCacheStore(_UgetCacheStore):
    """Some kind of cache for VORTEX experiments: one still needs to choose the cache strategy."""

    _footprint = dict(
        info = 'Uget cache access',
        attr = dict(
            netloc = dict(
                values  = ['uget.cache.fr'],
            ),
            strategy = dict(
                default = 'mtool',
            ),
        )
    )


class UgetHackCacheStore(_UgetCacheStore):
    """Some kind of cache for VORTEX experiments: one still needs to choose the cache strategy."""

    _footprint = dict(
        info = 'Uget cache access',
        attr = dict(
            netloc = dict(
                values  = ['uget.hack.fr'],
            ),
            strategy = dict(
                default = 'hack',
            ),
            readonly = dict(
                default = True,
            )
        )
    )

    def _alternate_source(self, remote, options):
        """
        If the target remote file is a tar/tgz file, check if a directory with
        the same name (but without any extension) exists.
        """
        parrentsource = super(UgetHackCacheStore, self).ugetlocate(remote, options)
        alternate_remote = None
        sh = self.system
        if sh.is_tarname(parrentsource):
            tar_ts = sh.stat(parrentsource).st_mtime if sh.path.isfile(parrentsource) else 0
            source_tarradix = sh.tarname_radix(parrentsource)
            # Check if the directory exists...
            if sh.path.isdir(source_tarradix):
                alternate_remote = copy.copy(remote)
                alternate_remote['path'] = alternate_remote['path'].replace(sh.path.basename(parrentsource),
                                                                            sh.path.basename(source_tarradix))
                tarradix_ts = max([sh.stat(tfile).st_mtime for tfile in sh.ffind(source_tarradix)])
            if alternate_remote is not None and tarradix_ts > tar_ts:
                # Do something only if the content of the directory is more recent
                # than the Tar file
                if options is not None and options.get('auto_repack', False):
                    print("Recreating < {:s} > based on < {:s} >.".format(
                          sh.path.basename(parrentsource), source_tarradix))
                    with self.system.cdcontext(self.system.path.dirname(source_tarradix)):
                        self.system.tar(parrentsource,
                                        self.system.path.basename(source_tarradix))
                else:
                    remote = alternate_remote
        return remote, alternate_remote

    def ugetlocate(self, remote, options):
        """Proxy to :meth:`incachelocate`."""
        a_remote, _ = self._alternate_source(remote, options)
        return super(UgetHackCacheStore, self).ugetlocate(a_remote, options)

    def ugetcheck(self, remote, options):
        """Proxy to :meth:`incachecheck`."""
        a_remote, a_altremote = self._alternate_source(remote, options)
        options = options.copy() if options is not None else dict()
        # Also check if the data is a regular file with the notable exception
        # of expanded tarfiles (see _alternate_source above) and specific data
        # format (e.g. ODB databases)
        options.setdefault('isfile', not (a_remote == a_altremote or
                                          'fmt' in options))
        return super(UgetHackCacheStore, self).ugetcheck(a_remote, options)

    def ugetget(self, remote, local, options):
        """Proxy to :meth:`incacheget`."""
        a_remote, _ = self._alternate_source(remote, options)
        return super(UgetHackCacheStore, self).ugetget(a_remote, local, options)

    def ugetdelete(self, remote, options):
        """Proxy to :meth:`incachedelete`."""
        _, a_remote = self._alternate_source(remote, options)
        rc = super(UgetHackCacheStore, self).ugetdelete(remote, options)
        if a_remote is not None:
            rc = rc and super(UgetHackCacheStore, self).ugetdelete(a_remote, options)
        return rc


class UgetStore(MultiStore):
    """Combined cache and central GCO stores."""

    _footprint = dict(
        info = 'GCO multi access',
        attr = dict(
            scheme = dict(
                values   = ['uget'],
            ),
            netloc = dict(
                values   = ['uget.multi.fr'],
            ),
            refillstore = dict(
                default  = True,
            )
        )
    )

    def alternates_netloc(self):
        """Tuple of alternates domains names, e.g. ``cache`` and ``archive``."""
        return ('uget.hack.fr', 'uget.cache.fr', 'uget.archive.fr')

    def get(self, remote, local, options=None):
        """Go through internal opened stores for the first available resource."""
        # Try to deal with extracts...
        extract = remote['query'].get('extract', None)
        if extract:
            uname = self.system.path.basename(remote['path'])
            fmt = options.get('fmt', 'foo')
            # Maybe the data was fetched previous, in such a case do not bother...
            if not self.system.path.exists(uname):
                chk_options = copy.copy(options)
                chk_options['incache'] = True
                chk_options['silent'] = True
                # If the resource is not in cache fetch the whole file first
                if not self.check(remote, chk_options):
                    logger.info('Trying to refill the uget element in cache stores')
                    # Get rid of the extract clause
                    bare_remote = copy.deepcopy(remote)
                    bare_remote['query'].pop('extract', None)
                    # Generate a temporary filename
                    tmplocal = uname + self.system.safe_filesuffix()
                    # Fetch and refill the Uget tar
                    get_options = copy.copy(options)
                    get_options['silent'] = True
                    rc = super(UgetStore, self).get(bare_remote, tmplocal, get_options)
                    # Remove it
                    self.system.rm(tmplocal, fmt=fmt)
                    logger.info('The refill should be done (rc=%s)', str(rc))

        return super(UgetStore, self).get(remote, local, options)
