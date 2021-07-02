# -*- coding: utf-8 -*-
# pylint: disable=unused-argument

"""
TODO: Module documentation.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import contextlib
import io

import six

import ast
import collections
import copy
import hashlib
import re
import tempfile

from bronx.fancies import loggers

from vortex.data.abstractstores import Store, ArchiveStore, MultiStore, CacheStore,\
    ConfigurableArchiveStore, CACHE_GET_INTENT_DEFAULT, ARCHIVE_GET_INTENT_DEFAULT
from vortex.tools.env import vartrue
from vortex.util.config import GenericConfigParser
from gco.syntax.stdattrs import AbstractUgetId

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)

GGET_DEFAULT_CONFIGFILE = '@gget-key-specific-conf.ini'


class GcoStoreConfig(GenericConfigParser):
    """Configuration handler for the GcoStores."""

    def __init__(self, *kargs, **kwargs):
        self.__dict__['_config_defaults'] = dict()
        self.__dict__['_config_re_cache'] = collections.defaultdict(dict)
        self.__dict__['_search_cache'] = dict()
        super(GcoStoreConfig, self).__init__(*kargs, **kwargs)

    @staticmethod
    def _decoder(value):
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


class _AutoExtractStoreMixin(object):
    """Some very useful methods needed by all GCO stores."""

    @property
    def system(self):
        raise NotImplementedError("This is a mixin class...")

    @property
    def itemconfig(self):
        raise NotImplementedError("This is a mixin class...")

    def _dump_directory_index(self, localdir, indexname=None):
        index_file = (localdir if indexname is None else indexname) + ".index"
        with self.system.cdcontext(localdir):
            all_files = set()
            for root, dirs, files in self.system.walk('.'):
                all_files.update([self.system.path.join(root, name)
                                  for name in files])
                # Empty directory (take it into account)
                if not files and not dirs:
                    all_files.add(root)
        with io.open(index_file, 'w', encoding='utf-8') as fh_index:
            fh_index.write("\n".join(sorted(all_files)))
        return index_file

    @staticmethod
    def _read_directory_index(index_file):
        with io.open(index_file, 'r', encoding='utf-8') as fh_index:
            return set(fh_index.read().split('\n'))

    def _do_local_auto_untar(self, local):
        return (isinstance(local, six.string_types) and
                not self.system.path.isdir(local) and
                self.system.is_tarname(local) and
                self.system.is_tarfile(local))

    def _autoextract_untar(self, local, gname):
        """Untar local in a dedicated directory and generate an index."""
        untaropts = self.itemconfig.key_untar_properties(gname)
        destdir_autox = local + '.autoextract'
        self.system.rm(destdir_autox)  # Just in case...
        unpacked = self.system.smartuntar(local, destdir_autox, **untaropts)
        if unpacked:
            self._dump_directory_index(destdir_autox, local)
        return unpacked, destdir_autox

    def _local_auto_untar(self, local, gname, xintent='inout'):
        """Automatic untar if needed..."""
        unpacked, destdir_autox = self._autoextract_untar(local, gname)
        rc = bool(unpacked)
        if unpacked:
            # Create another copy and move it (in order to preserve the
            # .autoextract directory)
            destdir = self.system.path.dirname(self.system.path.realpath(local))
            destdir_bis = tempfile.mkdtemp(suffix='.autoextract',
                                           dir=self.system.path.dirname(local))
            try:
                self.system.cp(destdir_autox, destdir_bis, intent=xintent)
                for to_mv in unpacked:
                    self.system.mv(self.system.path.join(destdir_bis, to_mv),
                                   self.system.path.join(destdir, to_mv))
            finally:
                self.system.rm(destdir_bis)
        return rc


class _AutoExtractCacheStore(CacheStore, _AutoExtractStoreMixin):
    """Some kind of cache for GCO components."""

    _abstract = True
    _footprint = dict(
        info = 'Cache access with auto-extract features',
        attr = dict(
            strategy = dict(
                default = 'mtool',
            ),
            rootdir = dict(
                default = 'auto'
            ),
            headdir = dict(
                outcast = ['xp', 'vortex'],
            ),
        )
    )

    _ALLOW_DIR_ITEMS = True  # Tells whether retrieved/stored item can be directories

    def __init__(self, *args, **kw):
        """Proxy init method. Perform a cache reset after initialisation."""
        logger.debug('Auto-extract abstract cache store init %s', self.__class__)
        super(_AutoExtractCacheStore, self).__init__(*args, **kw)

    @property
    def itemconfig(self):
        raise NotImplementedError("This is an abstract class...")

    @staticmethod
    def _build_remote_extract(remote, what=None):
        remote_x = copy.deepcopy(remote)
        if what:
            remote_x['path'] += '.autoextract/' + what
        else:
            remote_x['path'] += '.autoextract'
        remote_x['query'].pop('extract', None)
        return remote_x

    @staticmethod
    def _build_remote_index(remote):
        remote_x = copy.deepcopy(remote)
        remote_x['path'] += '.index'
        remote_x['query'].pop('extract', None)
        return remote_x

    @staticmethod
    def _build_raw_options(options):
        options_x = copy.copy(options)
        options_x['fmt'] = 'unknown'
        return options_x

    def _gco_xcache_check(self, remote, options):
        """Gateway to :meth:`incachecheck`."""
        extract = remote['query'].get('extract', None)
        if extract:
            return self.incachecheck(self._build_remote_extract(remote, extract[0]),
                                     self._build_raw_options(options))
        else:
            rc = self.incachecheck(remote, options)
            if rc and self._ALLOW_DIR_ITEMS:
                options_x = copy.copy(options)
                options_x['isfile'] = True
                if not self.incachecheck(remote, options_x):
                    rc = self.incachecheck(self._build_remote_index(remote),
                                           self._build_raw_options(options))
            return rc

    def _gco_xcache_locate(self, remote, options):
        """Gateway to :meth:`incachelocate`."""
        extract = remote['query'].get('extract', None)
        if extract:
            return self.incachelocate(self._build_remote_extract(remote, extract[0]),
                                      self._build_raw_options(options))
        else:
            return self.incachelocate(remote, options)

    def _gco_xcache_prestageinfo(self, remote, options):
        """Gateway to :meth:`incachelocate`."""
        extract = remote['query'].get('extract', None)
        if extract:
            return self.incacheprestageinfo(self._build_remote_extract(remote, extract[0]),
                                            self._build_raw_options(options))
        else:
            return self.incacheprestageinfo(remote, options)

    def _gco_xcache_list(self, remote, options):
        """Gateway to :meth:`incachelocate`."""
        cache_list = self.incachelist(remote, options)
        return ([i for i in cache_list
                 if not(i.endswith('.index') or i.endswith('.autoextract'))]
                if isinstance(cache_list, list) else cache_list)

    @contextlib.contextmanager
    def _gco_xcache_get_dir_index(self, remote):
        remote_idx = copy.copy(remote)
        remote_idx['path'] += '.index'
        tmplocal = tempfile.mkstemp(prefix='autoextract_dir_index_', dir='.')[1]
        try:
            rcidx = self.incacheget(remote_idx, tmplocal,
                                    dict(intent='in', silent=True))
            yield tmplocal if rcidx else None
        finally:
            self.system.rm(tmplocal)

    def _gco_xcache_index_check(self, index_file, local):
        # Check that the index file exists and that every file is
        # accounted for
        all_files = self._read_directory_index(index_file)
        rc = True
        with self.system.cdcontext(local):
            for a_file in all_files:
                rc = rc and self.system.path.exists(a_file)
        return all_files if rc else rc

    def _gco_xcache_get_index_and_check(self, remote, local):
        # Check that the index file exists and that every file is
        # accounted for
        with self._gco_xcache_get_dir_index(remote) as indexfile:
            if indexfile is None:
                return False
            else:
                return self._gco_xcache_index_check(indexfile, local)

    def _gco_xcache_get(self, remote, local, options):
        """Gateway to :meth:`incacheget`."""
        extract = remote['query'].get('extract', None)
        if extract:
            # Look for a pre-extracted source
            get_options = self._build_raw_options(options)
            get_options['silent'] = True
            rc = self.incacheget(self._build_remote_extract(remote, extract[0]),
                                 local, get_options)
            if not rc:
                # If not, get the tar, extract it and refill the extracted data in cache
                uname = self.system.path.basename(remote['path'])
                tmplocal = (self.system.path.dirname(local)
                            if isinstance(local, six.text_type) else '.')
                tmplocal = self.system.path.join(tmplocal,
                                                 uname + self.system.safe_filesuffix())
                rc = self.incacheget(remote, tmplocal, options)
                if rc:
                    unpacked, destdir = self._autoextract_untar(tmplocal, uname)
                    rc = bool(unpacked)
                    if rc:
                        self._gco_xcache_put_autoextracted(tmplocal, remote, options)
                    rc = rc and self.system.cp(self.system.path.join(destdir, extract[0]), local,
                                               fmt=options.get('fmt', 'foo'),
                                               intent=options.get('intent',
                                                                  CACHE_GET_INTENT_DEFAULT))
        else:
            rc = self.incacheget(remote, local, options)
            gname = remote['path'].lstrip('/').split('/').pop()
            if rc and isinstance(local, six.string_types):
                if self.system.path.isdir(local):
                    if self._ALLOW_DIR_ITEMS:
                        if not self._gco_xcache_get_index_and_check(remote, local):
                            logger.warning("The gname resource in MTOOL's GCO cache is incomplete. Ignoring it.")
                            self.system.rm(local)
                            rc = False
                    else:
                        logger.error("The gname resource is a directory. This should never happens !.")
                        rc = False
                elif self._do_local_auto_untar(local):
                    with self._gco_xcache_get_dir_index(remote) as indexfile:
                        if indexfile:
                            rcx = False
                            localdir = self.system.path.dirname(local)
                            self.system.mkdir(localdir)
                            tmpdir = tempfile.mkdtemp(suffix='.fromcache.autoextract', dir=localdir)
                            try:
                                rcx = self.incacheget(self._build_remote_extract(remote),
                                                      tmpdir,
                                                      self._build_raw_options(options))
                                if rcx:
                                    indexed = self._gco_xcache_index_check(indexfile, tmpdir)
                                    if not indexed:
                                        logger.warning("The auto-extract directory is incomplete. ignoring it.")
                                        rcx = False
                                    else:
                                        firstlevel = set([item_s[1] if item_s[0] == '.' else item_s[0]
                                                         for item_s in [self.system.path.split(item)
                                                                        for item in indexed]])
                                        for item in firstlevel:
                                            localdest = self.system.path.join(localdir, item)
                                            # Create the target directory if needed
                                            self.system.mkdir(self.system.path.dirname(localdest))
                                            # Actually copy each item
                                            self.system.mv(self.system.path.join(tmpdir, item),
                                                           localdest)
                            finally:
                                self.system.rm(tmpdir)
                        else:
                            rcx = False
                            logger.info("No auto-extracted item in cache. Proceeding as usual.")
                    if not rcx:
                        rc = self._local_auto_untar(local, gname,
                                                    xintent=options.get('intent',
                                                                        CACHE_GET_INTENT_DEFAULT))
                        if rc:
                            self._gco_xcache_put_autoextracted(local, remote, options)
        return rc

    def _gco_xcache_put_autoextracted(self, local, remote, options):
        if (self.system.path.exists(local + '.index') and
                self.system.path.isdir(local + '.autoextract')):
            rcx = self.incacheput(local + '.autoextract',
                                  self._build_remote_extract(remote),
                                  self._build_raw_options(options))
            rcx = rcx and self.incacheput(local + '.index',
                                          self._build_remote_index(remote),
                                          self._build_raw_options(options))
            if rcx:
                logger.info('Auto-extracted data uploaded to cache. rc=%s', str(rcx))

    def _gco_xcache_put(self, local, remote, options):
        """Gateway to :meth:`incacheputt`."""
        extract = remote['query'].get('extract', None)
        if extract:
            rc = self.incacheput(local,
                                 self._build_remote_extract(remote, extract[0]),
                                 self._build_raw_options(options))
        else:
            rc = self.incacheput(local, remote, options)
            if rc and isinstance(local, six.string_types):
                # Save the directory index + autoextract stuff
                if self.system.path.isdir(local):
                    index_file = self._dump_directory_index(local)
                    rcx = self.incacheput(index_file, self._build_remote_index(remote), options)
                    if rcx:
                        # Prepare for auto-extracts
                        rc = self.incacheput(local, self._build_remote_extract(remote), options)
                    else:
                        self.incachedelete(remote, options)
                        rc = False
                # Save any auto-extracted tar file
                elif self._do_local_auto_untar(local):
                    self._gco_xcache_put_autoextracted(local, remote, options)
        return rc

    def _gco_xcache_delete(self, remote, options):
        """Gateway to :meth:`incachedelete`."""
        extract = remote['query'].get('extract', None)
        if extract:
            rc = self.incachedelete(self._build_remote_extract(remote, extract[0]),
                                    self._build_raw_options(options))
        else:
            rc = self.incachedelete(remote, options)
            if self.incachecheck(self._build_remote_index(remote),
                                 self._build_raw_options(options)):
                rc = rc and self.incachedelete(self._build_remote_index(remote),
                                               self._build_raw_options(options))
        return rc


class GcoCentralStore(Store, _AutoExtractStoreMixin):
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
            readonly=dict(
                default=True,
            ),
            ggetcmd = dict(
                optional = True,
                default  = None
            ),
            ggetpath = dict(
                optional = True,
                default  = None
            ),
            ggetarchive = dict(
                optional = True,
                default  = None
            ),
            ggetcache = dict(
                type     = bool,
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
    def itemconfig(self):
        return self.ggetconfig

    @property
    def realkind(self):
        """Default realkind is ``gstore``."""
        return 'gstore'

    @property
    def _actual_gpath(self):
        gpath = self.ggetpath
        if gpath is None:
            if 'GGET_PATH' in self.system.env:
                gpath = self.system.env.GGET_PATH
            else:
                gpath = self.system.default_target.get('gco:ggetpath', '')
        return gpath

    @property
    def _actual_gcmd(self):
        gcmd = self.ggetcmd
        if gcmd is None:
            gcmd = self.system.default_target.get('gco:ggetcmd', 'gget')
        return gcmd

    @property
    def _actual_garchive(self):
        garchive = self.ggetarchive
        if garchive is None:
            darchive = ('hendrix' if self.system.glove is None
                        else self.system.glove.default_fthost)
            garchive = self.system.default_target.get('gco:ggetarchive', darchive)
        return garchive

    @property
    def _actual_guser(self):
        guser = None
        if self.system.glove is not None:
            guser = self.system.glove.getftuser(self._actual_garchive,
                                                defaults_to_user=False)
        return guser

    @property
    def _actual_gcache(self):
        gcache = self.ggetcache
        if gcache is None:
            gcache = self.system.default_target.get('gco:ggetcache', 'True')
            gcache = bool(vartrue.match(gcache))
        return gcache

    def _actualgget(self, rpath):
        """Return actual (gtool, garchive, tampon, gname)."""
        lpath = rpath.lstrip('/').split('/')
        gname = lpath.pop()
        cmd = [self.system.path.join(self._actual_gpath, self._actual_gcmd),
               '-host', self._actual_garchive]
        if self._actual_guser is not None:
            cmd.extend(['-user', self._actual_guser])
        if not self._actual_gcache:
            cmd.append('-no-cache')
        return cmd, gname

    def _gspawn(self, cmd):
        with self.system.env.clone() as lenv:
            # Needed for gget to work with ectrans
            if 'ectrans' in self.system.loaded_addons():
                remote = self.system.ectrans_remote_init(storage=self._actual_garchive)
                gateway = self.system.ectrans_gateway_init()
                logger.debug('ectrans setup: gateway=%s remote=%s', gateway, remote)
                lenv.ECTRANS_GATEWAY = gateway
                lenv.ECTRANS_REMOTE = remote
            # Gget needs the file to be readable to everyone (otherwise the
            # "tampon" does not work
            rc = False
            p_umask = self.system.umask(0o0022)
            try:
                logger.debug('gget command: %s', ' '.join(cmd))
                rc = self.system.spawn(cmd, output=True)
            finally:
                self.system.umask(p_umask)
            return rc

    def ggetcheck(self, remote, options):
        """Verify disponibility in GCO's tampon using ``gget`` external tool."""
        gloc = self.ggetlocate(remote, options)
        if gloc:
            return self.system.size(gloc)
        else:
            return False

    def ggetlocate(self, remote, options):
        """Get location in GCO's tampon using ``gget`` external tool."""
        (gcmd, gname) = self._actualgget(remote['path'])
        gloc = self._gspawn(gcmd + ['-path', gname])
        if gloc and self.system.path.exists(gloc[0]):
            return gloc[0]
        else:
            return False

    def ggetget(self, remote, local, options):
        """System call to ``gget`` external tool."""
        (gcmd, gname) = self._actualgget(remote['path'])
        sh = self.system
        fmt = options.get('fmt', 'foo')
        extract = remote['query'].get('extract', None)
        # Run the Gget command in a temporary directory
        if isinstance(local, six.string_types):
            localdir = self.system.path.dirname(local)
            self.system.mkdir(localdir)
        else:
            localdir = '.'
        tmpdir = tempfile.mkdtemp(dir=localdir, prefix='gco_autoextract_')
        try:
            with sh.cdcontext(tmpdir):
                # Tweak the Gget command according to extract
                if extract:
                    actual_target = extract[0]
                    retrycount = 0
                    while retrycount < 10:
                        rc = self._gspawn(gcmd + ['-extract', '-subdir=no', gname, actual_target])
                        if rc and sh.path.islink(actual_target):
                            if sh.path.exists(actual_target):
                                actual_target = sh.path.relpath(sh.path.realpath(actual_target))
                                break
                            else:
                                new_target = sh.readlink(actual_target)
                                logger.info("< %s > is a symlink. Retrying with the link target < %s >",
                                            actual_target, new_target)
                                sh.rm(actual_target)
                                actual_target = new_target
                                retrycount += 1
                        else:
                            break
                else:
                    actual_target = gname
                    rc = self._gspawn(gcmd + [gname])
            actual_target = sh.path.join(tmpdir, actual_target)
            if rc and sh.path.exists(actual_target):
                rc = rc and (not isinstance(local, six.text_type) or sh.filecocoon(local))
                rc = rc and sh.mv(actual_target, local, fmt=fmt)
            else:
                logger.warning('GCO Central Store get %s was not successful (with rc=%s)', gname, rc)
                rc = False
        finally:
            sh.rm(tmpdir)
        # Automatic untar if needed... (the local file needs to end with a tar extension)
        if rc and self._do_local_auto_untar(local):
            rc = self._local_auto_untar(local, gname,
                                        xintent=options.get('intent',
                                                            ARCHIVE_GET_INTENT_DEFAULT))
        return rc


class GcoCacheStore(_AutoExtractCacheStore):
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
            headdir = dict(
                default = 'gco',
            ),
            ggetconfig=dict(
                type=GcoStoreConfig,
                optional=True,
                default=GcoStoreConfig(GGET_DEFAULT_CONFIGFILE),
            )
        )
    )

    @property
    def itemconfig(self):
        return self.ggetconfig

    def ggetcheck(self, remote, options):
        return self._gco_xcache_check(remote, options)

    def ggetlocate(self, remote, options):
        return self._gco_xcache_locate(remote, options)

    def ggetlist(self, remote, options):
        return self._gco_xcache_list(remote, options)

    def ggetprestageinfo(self, remote, options):
        return self._gco_xcache_prestageinfo(remote, options)

    def ggetget(self, remote, local, options):
        return self._gco_xcache_get(remote, local, options)

    def ggetput(self, local, remote, options):
        return self._gco_xcache_put(local, remote, options)

    def ggetdelete(self, remote, options):
        return self._gco_xcache_delete(remote, options)


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
        return 'gco.cache.fr', 'gco.meteo.fr'


class UgetArchiveStore(ArchiveStore, ConfigurableArchiveStore, _AutoExtractStoreMixin):
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
            storehead = dict(
                optional = True,
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

    @property
    def itemconfig(self):
        return self.ugetconfig

    @classmethod
    def _hashdir(cls, eltid):
        if six.PY2:
            eltid = six.text_type(eltid)
        cleaned = cls._eltid_cleaner0.sub('', eltid)
        cleaned = cls._eltid_cleaner1.sub(r'\1\2', cleaned)
        return hashlib.md5(cleaned.encode(encoding="utf-8")).hexdigest()[0]

    def _universal_remap(self, remote):
        """Reformulates the remote path to compatible vortex namespace."""
        remote = copy.copy(remote)
        xpath = remote['path'].split('/')
        f_uuid = AbstractUgetId('uget:' + xpath[2])
        remote['path'] = self.system.path.join(self.storehead, xpath[1],
                                               self._hashdir(f_uuid.id), f_uuid.id)
        if 'root' not in remote:
            remote['root'] = self._actual_storeroot(f_uuid)
        return remote

    def _list_remap(self, remote):
        """Reformulates the remote path to compatible vortex namespace."""
        rlist = []
        xpath = remote['path'].split('/')
        if re.match(r'^@(\w+)$', xpath[2]):
            f_uuid = AbstractUgetId('uget:fake' + xpath[2])
            for h in range(16):
                a_remote = copy.copy(remote)
                a_remote['path'] = self.system.path.join(self.storehead, xpath[1],
                                                         re.sub('0x(.)', r'\1', hex(h)))
                rlist.append(a_remote)
        else:
            f_uuid = AbstractUgetId('uget:' + xpath[2])
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
        return sorted([s for s in stuff
                       if not (s.endswith('.' + self.storehash) and
                               s[:-(len(self.storehash) + 1)] in stuff
                               )
                       ])

    def ugetprestageinfo(self, remote, options):
        """Remap and ftpprestageinfo sequence."""
        return self.inarchiveprestageinfo(self._universal_remap(remote), options)

    def ugetget(self, remote, local, options):
        """Remap and ftpget sequence."""
        remote = self._universal_remap(remote)
        xintent = options.get('intent', ARCHIVE_GET_INTENT_DEFAULT)
        # Extract what to do ?
        extract = remote['query'].get('extract', None)
        uname = self.system.path.basename(remote['path'])
        if isinstance(local, six.text_type):
            full_uname = self.system.path.dirname(local)
        else:
            full_uname = '.'
        full_uname = self.system.path.join(full_uname, uname)
        # Actually fetch the data
        rc = self.inarchiveget(remote,
                               full_uname if extract else local,
                               options)
        if rc:
            if extract:
                if self.system.is_tarfile(full_uname):
                    unpacked, destdir_autox = self._autoextract_untar(full_uname, uname)
                    fmt = options.get('fmt', 'foo')
                    rc = rc and self.system.cp(destdir_autox + '/' + extract[0],
                                               local, fmt=fmt, intent=xintent)
                else:
                    logger.error('Improper file type to deal with an extract query !')
                    rc = False
            else:
                # Automatic untar if needed... (the local file needs to end with a tar extension)
                if self._do_local_auto_untar(local):
                    rc = self._local_auto_untar(local, uname, xintent=xintent)
        else:
            self._verbose_log(options, 'warning',
                              '%s get on %s was not successful (rc=%s)',
                              self.__class__.__name__, local, rc, slevel='info')
        return rc

    def ugetearlyget(self, remote, local, options):
        """Remap and inarchiveearlyget sequence."""
        remote = self._universal_remap(remote)
        # Deal with extract !
        if remote['query'].get('extract', None):
            return None  # No early-get when extract=True
        return self.inarchiveearlyget(remote, local, options)

    def ugetfinaliseget(self, result_id, remote, local, options):
        """Remap and inarchivefinaliseget sequence."""
        remote = self._universal_remap(remote)
        # Deal with extract !
        if remote['query'].get('extract', None):
            return False  # No early-get when extract=True
        # Actual finalise
        rc = self.inarchivefinaliseget(result_id, remote, local, options)
        # Automatic untar if needed...
        if rc and self._do_local_auto_untar(local):
            rc = self._local_auto_untar(local,
                                        self.system.path.basename(remote['path']),
                                        xintent=options.get('intent',
                                                            ARCHIVE_GET_INTENT_DEFAULT))
        return rc

    def ugetput(self, local, remote, options):
        """Remap root dir and ftpput sequence."""
        if not self.storetrue:
            logger.info("put deactivated for %s", str(local))
            return True
        if remote['query'].get('extract', None):
            return False  # No put with extracts
        return self.inarchiveput(local, self._universal_remap(remote), options)

    def ugetdelete(self, remote, options):
        """Remap root dir and ftpdelete sequence."""
        if remote['query'].get('extract', None):
            return False  # No delete with extracts
        return self.inarchivedelete(self._universal_remap(remote), options)


class _UgetCacheStoreMixin(object):

    @property
    def system(self):
        raise NotImplementedError('This is a mixin class.')

    def universal_remap(self, remote):
        """Reformulates the remote path to compatible vortex namespace."""
        remote = copy.copy(remote)
        xpath = remote['path'].split('/')
        f_uuid = AbstractUgetId('uget:' + xpath[2])
        remote['path'] = self.system.path.join(f_uuid.location, xpath[1], f_uuid.id)
        return remote

    def _list_remap(self, remote):
        """Reformulates the remote path to compatible vortex namespace."""
        remote = copy.copy(remote)
        xpath = remote['path'].split('/')
        if re.match(r'^@(\w+)$', xpath[2]):
            f_uuid = AbstractUgetId('uget:fake' + xpath[2])
            remote['path'] = self.system.path.join(f_uuid.location, xpath[1])
        else:
            f_uuid = AbstractUgetId('uget:' + xpath[2])
            remote['path'] = self.system.path.join(f_uuid.location, xpath[1], f_uuid.id)
        return remote


class _UgetCacheStore(_AutoExtractCacheStore, _UgetCacheStoreMixin):
    """Some kind of cache for VORTEX experiments: one still needs to choose the cache strategy."""

    _abstract = True
    _footprint = dict(
        info = 'Uget cache access',
        attr = dict(
            scheme = dict(
                values  = ['uget'],
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

    _ALLOW_DIR_ITEMS = False  # Tells whether retrieved/stored item can be directories

    @property
    def itemconfig(self):
        return self.ugetconfig

    def ugetcheck(self, remote, options):
        """Proxy to :meth:`_gco_xcache_check`."""
        return self._gco_xcache_check(self.universal_remap(remote), options)

    def ugetlocate(self, remote, options):
        """Proxy to :meth:`_gco_xcache_locate`."""
        return self._gco_xcache_locate(self.universal_remap(remote), options)

    def ugetlist(self, remote, options):
        """Proxy to :meth:`_gco_xcache_check_list`."""
        return self._gco_xcache_list(self._list_remap(remote), options)

    def ugetprestageinfo(self, remote, options):
        """Proxy to :meth:`_gco_xcache_prestageinfo`."""
        return self._gco_xcache_prestageinfo(self.universal_remap(remote), options)

    def ugetget(self, remote, local, options):
        """Proxy to :meth:`_gco_xcache_get`."""
        remote = self.universal_remap(remote)
        return self._gco_xcache_get(remote, local, options)

    def ugetput(self, local, remote, options):
        """Proxy to :meth:`_gco_xcache_put`."""
        remote = self.universal_remap(remote)
        return self._gco_xcache_put(local, remote, options)

    def ugetdelete(self, remote, options):
        """Proxy to :meth:`_gco_xcache_delete`."""
        return self._gco_xcache_delete(self.universal_remap(remote), options)


class UgetMtCacheStore(_UgetCacheStore):
    """Some kind of cache for VORTEX experiments: one still needs to choose the cache strategy."""

    _footprint = dict(
        info = 'Uget MTOOL cache access',
        attr = dict(
            netloc = dict(
                values  = ['uget.cache-mt.fr'],
            ),
            strategy = dict(
                default = 'mtool',
            ),
        )
    )


class UgetMarketCacheStore(_UgetCacheStore):
    """Some kind of cache for VORTEX experiments: one still needs to choose the cache strategy."""

    _footprint = dict(
        info = 'Uget Marketplace cache access',
        attr = dict(
            netloc = dict(
                values  = ['uget.cache-market.fr'],
            ),
            strategy = dict(
                default = 'marketplace',
            ),
        )
    )


class UgetCacheStore(MultiStore):

    _footprint = dict(
        info = 'Uget cache access',
        attr = dict(
            scheme = dict(
                values  = ['uget'],
            ),
            netloc = dict(
                values  = ['uget.cache.fr', ],
            ),
            refillstore = dict(
                default = False,
            )
        )
    )

    def filtered_readable_openedstores(self, remote):
        ostores = [self.openedstores[0], ]
        for sto in self.openedstores[1:]:
            try:
                r_remote = sto.universal_remap(remote)
            except ValueError:
                r_remote = sto._list_remap(remote)
            if sto.cache.allow_reads(r_remote['path']):
                ostores.append(sto)
        return ostores

    def filtered_writeable_openedstores(self, remote):
        ostores = [self.openedstores[0], ]
        for sto in self.openedstores[1:]:
            r_remote = sto.universal_remap(remote)
            if sto.cache.allow_writes(r_remote['path']):
                ostores.append(sto)
        return ostores

    def alternates_netloc(self):
        """For Non-Op users, Op caches may be accessed in read-only mode."""
        return ['uget.cache-mt.fr', 'uget.cache-market.fr']


class UgetHackCacheStore(CacheStore, _UgetCacheStoreMixin, _AutoExtractStoreMixin):
    """Some kind of cache for VORTEX experiments: one still needs to choose the cache strategy."""

    _footprint = dict(
        info = 'Uget cache access',
        attr = dict(
            scheme=dict(
                values=['uget'],
            ),
            netloc = dict(
                values  = ['uget.hack.fr'],
            ),
            strategy = dict(
                default = 'hack',
            ),
            headdir=dict(
                default='uget',
            ),
            rootdir=dict(
                default='auto'
            ),
            readonly = dict(
                default = True,
            ),
            ugetconfig=dict(
                alias=['ggetconfig', ],
                type=GcoStoreConfig,
                optional=True,
                default=GcoStoreConfig(GGET_DEFAULT_CONFIGFILE),
            ),
        )
    )

    @property
    def itemconfig(self):
        return self.ugetconfig

    @staticmethod
    def _build_remote_extract(remote, extract):
        a_remote = copy.deepcopy(remote)
        a_remote['query'].pop('extract', None)
        a_remote['path'] += '/' + extract[0]
        return a_remote

    @staticmethod
    def _build_raw_options(options):
        options_x = copy.deepcopy(options)
        options_x['fmt'] = 'unknown'
        return options_x

    def _alternate_source(self, remote, options):
        """
        If the target remote file is a tar/tgz file, check if a directory with
        the same name (but without any extension) exists.
        """
        parrentsource = self.incachelocate(remote, options)
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
        remote = self.universal_remap(remote)
        a_remote, _ = self._alternate_source(remote, options)
        a_location = self.incachelocate(a_remote, options)
        a_extract = a_remote['query'].get('extract', None)
        if a_extract and self.system.path.isdir(a_location):
            return self.incachelocate(self._build_remote_extract(a_remote, a_extract),
                                      self._build_raw_options(options))
        else:
            return a_location

    def ugetcheck(self, remote, options):
        """Proxy to :meth:`incachecheck`."""
        remote = self.universal_remap(remote)
        a_remote, a_altremote = self._alternate_source(remote, options)
        a_extract = remote['query'].get('extract', None)
        options = options.copy()
        # Also check if the data is a regular file with the notable exception
        # of expanded tarfiles (see _alternate_source above) and specific data
        # format (e.g. ODB databases)
        if a_remote == a_altremote:
            if a_extract:
                return self.incachecheck(self._build_remote_extract(a_remote, a_extract),
                                         self._build_raw_options(options))
            else:
                return self.incachecheck(a_remote, self._build_raw_options(options))
        else:
            options.setdefault('isfile', 'fmt' not in options)
            return self.incachecheck(a_remote, options)

    def ugetget(self, remote, local, options):
        """Proxy to :meth:`incacheget`."""
        sh = self.system
        remote = self.universal_remap(remote)
        a_remote, a_altremote = self._alternate_source(remote, options)
        a_extract = a_remote['query'].get('extract', None)
        if a_extract:
            if a_remote == a_altremote:
                rc = self.incacheget(self._build_remote_extract(a_remote, a_extract),
                                     local,
                                     self._build_raw_options(options))
            else:
                # Fetch the targeted tar file
                uname = sh.path.basename(remote['path'])
                full_uname = (sh.path.dirname(local)
                              if isinstance(local, six.text_type) else '.')
                full_uname = sh.path.join(full_uname, uname)
                if sh.path.exists(full_uname):
                    logger.info("'%s' already fetched during previous extract.", full_uname)
                    rc = True
                else:
                    rc = self.incacheget(a_remote, full_uname, options)
                if rc:
                    if sh.path.isfile(full_uname) and sh.is_tarfile(full_uname):
                        destdir = sh.tarname_radix(sh.path.realpath(full_uname))
                        if sh.path.exists(destdir):
                            logger.info("'%s' was already unpacked during a previous extract.", destdir)
                        else:
                            sh.mkdir(destdir)
                            untaropts = self.itemconfig.key_untar_properties(uname)
                            rc = len(sh.smartuntar(full_uname, destdir, **untaropts)) > 0
                        rc = rc and sh.cp(sh.path.join(destdir, a_extract[0]), local,
                                          fmt=options.get('fmt', 'foo'),
                                          intent=options.get('intent', CACHE_GET_INTENT_DEFAULT))
                    else:
                        logger.error("'%s' should be a tarfile", full_uname)
                        rc = False
        else:
            rc = self.incacheget(a_remote, local, options)
            # Automatic untar if needed... (the local file needs to end with a tar extension)
            if rc and self._do_local_auto_untar(local):
                rc = self._local_auto_untar(local,
                                            sh.path.basename(remote['path']),
                                            xintent=options.get('intent', CACHE_GET_INTENT_DEFAULT))
            # If a pre-extracted directory was fetched...
            elif isinstance(local, six.text_type) and sh.path.isdir(local):
                if sh.is_tarname(local):
                    # Move the directory content one level up
                    for item in sh.listdir(local):
                        rc = rc and sh.mv(sh.path.join(local, item),
                                          sh.path.join(sh.path.dirname(local), item))
                else:
                    logger.error("This is really odd (while getting %s): " +
                                 "The hack cache contains a directory but a tar file is requested",
                                 local)
                    rc = False
        return rc

    def ugetput(self, local, remote, options):
        """Proxy to :meth:`incacheput`."""
        remote = self.universal_remap(remote)
        extract = remote['query'].get('extract', None)
        if extract:
            logger.warning('Skip cache put with extracted %s', extract)
            return False
        else:
            return self.incacheput(local, remote, options)

    def ugetdelete(self, remote, options):
        """Proxy to :meth:`incachedelete`."""
        remote = self.universal_remap(remote)
        _, a_remote = self._alternate_source(remote, options)
        rc = self.incachedelete(remote, options)
        if a_remote is not None:
            rc = rc and self.incachedelete(a_remote, options)
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
        return 'uget.hack.fr', 'uget.cache.fr', 'uget.archive.fr'

    def get(self, remote, local, options=None):
        """Go through internal opened stores for the first available resource."""
        options = self._options_fixup(options)
        # Try to deal with extracts...
        extract = remote['query'].get('extract', None)
        if extract:
            uname = self.system.path.basename(remote['path'])
            fmt = options.get('fmt', 'foo')
            # Get rid of the extract clause
            bare_remote = copy.deepcopy(remote)
            bare_remote['query'].pop('extract', None)
            # Fail quietly
            chk_options = copy.copy(options)
            chk_options['incache'] = True
            chk_options['silent'] = True
            # If the resource is not in cache, fetch the whole file first
            if not self.check(bare_remote, chk_options):
                logger.info("Trying to refill the '%s' uget element in cache stores", uname)
                # Generate a temporary filename
                tmplocal = (self.system.path.dirname(local)
                            if isinstance(local, six.text_type) else '.')
                tmplocal = self.system.path.join(tmplocal,
                                                 uname + self.system.safe_filesuffix())
                # Fetch and refill the Uget tar
                get_options = copy.copy(options)
                get_options['silent'] = True
                rc = self.get(bare_remote, tmplocal, get_options)
                # Remove it
                self.system.rm(tmplocal, fmt=fmt)
                logger.info('The refill should be done (rc=%s)', str(rc))
        return super(UgetStore, self).get(remote, local, options)
