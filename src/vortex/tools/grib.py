#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import re
import urlparse

import footprints

from . import addons

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


def use_in_shell(sh, **kw):
    """Extend current shell with the LFI interface defined by optional arguments."""
    kw['shell'] = sh
    return footprints.proxy.addon(**kw)


class GRIB_Tool(addons.FtrawEnableAddon):
    """
    Handle multipart-GRIB files properly.
    """
    _footprint = dict(
        info = 'Default GRIB system interface',
        attr = dict(
            kind = dict(
                values   = ['grib'],
            ),
        )
    )

    def _std_grib_index_get(self, source):
        with io.open(source, 'r') as fd:
            gribparts = fd.read().splitlines()
        return [urlparse.urlparse(url).path for url in gribparts]

    xgrib_index_get = _std_grib_index_get

    def _std_grib_index_write(self, destination, gribpaths):
        gribparts = [unicode(urlparse.urlunparse(('file', '', path, '', '', '')))
                     for path in gribpaths]
        tmpfile = destination + self.sh.safe_filesuffix()
        with io.open(tmpfile, 'w') as fd:
            fd.write('\n'.join(gribparts))
        return self.sh.move(tmpfile, destination)

    def is_xgrib(self, source):
        """Check if the given ``source`` is a multipart-GRIB file."""
        rc = False
        if source and isinstance(source, basestring) and self.sh.path.exists(source):
            with io.open(source, 'rb') as fd:
                rc = fd.read(7) == 'file://'
        return rc

    def _backend_cp(self, source, destination, intent='in'):
        return self.sh.cp(source, destination, intent=intent, smartcp=True)

    def _backend_rm(self, *args):
        return self.sh.rm(*args)

    def _backend_mv(self, source, destination):
        return self.sh.mv(source, destination)

    def _std_remove(self, *args):
        """Remove (possibly) multi GRIB files."""
        rc = True
        for pname in args:
            for objpath in self.sh.glob(pname):
                if self.is_xgrib(objpath):
                    idx = self._std_grib_index_get(objpath)
                    target_dirs = set()
                    for a_mpart in idx:
                        target_dirs.add(self.sh.path.dirname(a_mpart))
                        rc = rc and self.sh._backend_rm(a_mpart)
                    for a_dir in target_dirs:
                        # Only if the directory is empty
                        if not self.sh.listdir(a_dir):
                            rc = rc and self.sh._backend_rm(a_dir)
                    rc = rc and self.sh._backend_rm(objpath)
                else:
                    rc = rc and self.sh._backend_rm(objpath)
        return rc

    grib_rm = grib_remove = _std_remove

    def _std_copy(self, source, destination, intent='in', pack=False, silent=False):
        """Extended copy for (possibly) multi GRIB file."""
        # Might be multipart
        if self.is_xgrib(source):
            rc = True
            if isinstance(destination, basestring) and not pack:
                idx = self._std_grib_index_get(source)
                destdir = self.sh.path.abspath(self.sh.path.expanduser(destination) + ".d")
                rc = rc and self.sh.mkdir(destdir)
                target_idx = list()
                for (i, a_mpart) in enumerate(idx):
                    target_idx.append(self.sh.path.join(destdir, 'GRIB_mpart{:06d}'.format(i)))
                    rc = rc and self.sh._backend_cp(a_mpart, target_idx[-1], intent=intent)
                    rc = rc and self._std_grib_index_write(destination, target_idx)
                if intent == 'in':
                    self.sh.chmod(destination, 0444)
            else:
                rc = rc and self.xgrib_pack(source, destination)
        else:
            # Usual file or file descriptor
            rc = self.sh._backend_cp(source, destination, intent=intent)
        return rc

    grib_cp = grib_copy = _std_copy

    def _std_move(self, source, destination):
        """Extended mv for (possibly) multi GRIB file."""
        # Might be multipart
        if self.is_xgrib(source):
            intent = 'inout' if self.sh.access(source, self.sh.W_OK) else 'in'
            rc = self._std_copy(source, destination, intent=intent)
            rc = rc and self._std_remove(source)
        else:
            rc = self._backend_mv(source, destination)
        return rc

    grib_mv = grib_move = _std_move

    def _pack_stream(self, source, stdout=True):
        cmd = ['cat', ]
        cmd.extend(self._std_grib_index_get(source))
        return self.sh.popen(cmd, stdout=stdout, bufsize=8192)

    def xgrib_pack(self, source, destination, intent='in'):
        """Manually pack a multi GRIB."""
        if isinstance(destination, basestring):
            tmpfile = destination + self.sh.safe_filesuffix()
            with io.open(tmpfile, 'wb') as fd:
                p = self._pack_stream(source, stdout=fd)
            self.sh.pclose(p)
            if intent == 'in':
                self.sh.chmod(tmpfile, 0444)
            return self.sh.move(tmpfile, destination)
        else:
            p = self._pack_stream(source, stdout=destination)
            self.sh.pclose(p)
            return True

    def _std_ftput(self, source, destination, hostname=None, logname=None):
        """On the fly packing and ftp."""
        if self.is_xgrib(source):
            if hostname is None:
                hostname = self.sh.env.VORTEX_ARCHIVE_HOST
            if hostname is None:
                return False
            if logname is None:
                logname = self.sh.env.VORTEX_ARCHIVE_USER

            ftp = self.sh.ftp(hostname, logname)
            if ftp:
                p = self._pack_stream(source)
                rc = ftp.put(p.stdout, destination)
                self.sh.pclose(p)
                ftp.close()
            else:
                rc = False
            return rc
        else:
            return self.sh.ftput(source, destination, hostname=hostname, logname=logname)

    def _std_rawftput(self, source, destination, hostname=None, logname=None):
        """Use ftserv as much as possible."""
        if self.is_xgrib(source):
            if self.sh.ftraw and self.rawftshell is not None:
                # Copy the GRIB pieces individually
                pieces = self.xgrib_index_get(source)
                newsources = [self.sh.copy2ftspool(piece) for piece in pieces]
                request = newsources[0] + '.request'
                with open(request, 'w') as request_fh:
                    request_fh.writelines('\n'.join(newsources))
                self.sh.readonly(request)
                rc = self.sh.ftserv_put(request, destination,
                                        hostname=hostname, logname=logname,
                                        specialshell=self.rawftshell)
                self.sh.rm(request)
                return rc
            else:
                return self._std_ftput(source, destination,
                                       hostname=hostname, logname=logname)
        else:
            return self.sh.rawftput(source, destination, hostname=hostname, logname=logname)

    grib_ftput = _std_ftput
    grib_rawftput = _std_rawftput


class GribApiComponent(object):
    """Extend Algo Components with GribApi features."""

    def gribapi_setup(self, rh, opts):
        # First set the GRIB-API paths by inspecting the binary
        libs = self.system.ldd(rh.container.localpath()) if rh is not None else {}
        gribapi_lib = None
        for lib in libs.iterkeys():
            if re.match(r'^libgrib_api(?:-[.0-9]+)?\.so(?:\.[.0-9]+)?$', lib):
                gribapi_lib = lib
                break
        if gribapi_lib is not None:
            gribapi_root = self.system.path.dirname(libs[gribapi_lib])
            gribapi_root = self.system.path.split(gribapi_root)[0]
            gribapi_share = self.system.path.join(gribapi_root, 'share', 'grib_api')
            if 'GRIB_DEFINITION_PATH' not in self.env:
                # This one is for compatibility with old versions of the gribapi !
                self.env.setgenericpath('GRIB_DEFINITION_PATH',
                                        self.system.path.join(gribapi_root, 'share', 'definitions'))
                # This should be the lastest one:
                self.env.setgenericpath('GRIB_DEFINITION_PATH',
                                        self.system.path.join(gribapi_share, 'definitions'))
            if 'GRIB_SAMPLES_PATH' not in self.env:
                # This one is for compatibility with old versions of the gribapi !
                self.env.setgenericpath('GRIB_SAMPLES_PATH',
                                        self.system.path.join(gribapi_root, 'ifs_samples', 'grib1'))
                # This should be the lastest one:
                self.env.setgenericpath('GRIB_SAMPLES_PATH',
                                        self.system.path.join(gribapi_share, 'ifs_samples', 'grib1'))
        else:
            # Use the default GRIB-API config if the ldd approach fails
            self.export('gribapi')
        # Then, inspect the context to look for customised search paths
        for a_role, a_var in (('AdditionalGribAPIDefinitions', 'GRIB_DEFINITION_PATH'),
                              ('AdditionalGribAPISamples', 'GRIB_SAMPLES_PATH')):
            for gdef in self.context.sequence.effective_inputs(role=a_role):
                local_path = gdef.rh.container.localpath()
                new_path = (local_path if self.system.path.isdir(local_path)
                            else self.system.path.dirname(local_path))
                # NB: Grib-API doesn't understand relative paths...
                new_path = self.system.path.abspath(new_path)
                self.env.setgenericpath(a_var, new_path, pos=0)
        # Recap
        for a_var in ('GRIB_DEFINITION_PATH', 'GRIB_SAMPLES_PATH'):
            logger.info('After gribapi_setup %s = %s', a_var, self.env.getvar(a_var))


class GRIBAPI_Tool(addons.Addon):
    """
    Interface to gribapi commands (designed as a shell Addon).
    """

    _footprint = dict(
        info = 'Default GRIBAPI system interface',
        attr = dict(
            kind = dict(
                values   = ['gribapi'],
            ),
        )
    )

    def __init__(self, *args, **kw):
        """Addon initialisation."""
        super(GRIBAPI_Tool, self).__init__(*args, **kw)
        # Additionaly, check for the GRIB_API_ROOTDIR key in the config file
        if self.path is None and self.cfginfo is not None:
            tg = self.sh.target()
            addon_rootdir = tg.get(self.cfginfo + ':grib_api_rootdir', None)
            if addon_rootdir is not None:
                self.path = addon_rootdir

    def _spawn_wrap(self, cmd, **kw):
        """Internal method calling standard shell spawn."""
        cmd[0] = 'bin' + self.sh.path.sep + cmd[0]
        return super(GRIBAPI_Tool, self)._spawn_wrap(cmd, **kw)

    def grib_diff(self, grib1, grib2, skipkeys=('generatingProcessIdentifier',), **kw):
        """
        Difference between two grib-file (using the GRIB-API

        :param grib1: first file to compare
        :param grib2: second file to compare
        :param skipkeys: List of GRIB keys that will be ignored

        GRIB messages may not be in the same order in both files.

        If *grib1* or *grib2* are multipart files, they will be concatenated
        prior to the comparison.
        """

        # Are multipart GRIB suported ?
        xgrib_support = 'grib' in self.sh.loaded_addons()
        grib1_ori = grib1
        grib2_ori = grib2
        if xgrib_support:
            if self.sh.is_xgrib(grib1):
                grib1 = grib1_ori + '_diffcat' + self.sh.safe_filesuffix()
                self.sh.xgrib_pack(grib1_ori, grib1)
            if self.sh.is_xgrib(grib2):
                grib2 = grib2_ori + '_diffcat' + self.sh.safe_filesuffix()
                self.sh.xgrib_pack(grib2_ori, grib2)

        cmd = [ 'grib_compare', '-r', '-b', ','.join(skipkeys), grib1, grib2 ]

        kw['fatal'] = False
        kw['output'] = False

        rc = self._spawn_wrap(cmd, **kw)

        if xgrib_support and grib1 != grib1_ori:
            self.sh.grib_rm(grib1)
        if xgrib_support and grib2 != grib2_ori:
            self.sh.grib_rm(grib2)

        return rc
