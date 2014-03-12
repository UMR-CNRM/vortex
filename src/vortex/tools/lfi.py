#!/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import io
import weakref
import types

import footprints

from vortex.autolog import logdefault as logger

LFI_HNDL_SPEC   = ':1'
DR_HOOK_SILENT  = 1
DR_HOOK_NOT_MPI = 1


def use_in_shell(sh, **kw):
    """Extend current shell with the LFI interface defined by optional arguments."""
    kw.setdefault('lficmd', 'lfitools')
    lfi = footprints.proxy.addon(**kw)
    if lfi:
        sh.extend(lfi)
    return lfi


class LFI_Status(object):
    """
    Store lfi commands status as a set of attributes:
      * rc = return code
      * stdout = raw standard output
      * result = an optional processing specific to each command
    """

    def __init__(self, rc=0, ok=None, stdout=None, stderr=None, result=None):
        self._rc = rc
        self._ok = ok or [ 0 ]
        self._stdout = stdout
        self._stderr = stderr
        self._result = result

    @property
    def ok(self):
        return self._ok

    def _get_rc(self):
        return self._rc

    def _set_rc(self, value):
        if value is not None:
            self._rc = bool(value == 0)
        else:
            self._rc = False

    rc = property(_get_rc, _set_rc, None, None)

    def _get_stdout(self):
        return self._stdout

    def _set_stdout(self, value):
        self._stdout = list(value)

    stdout = property(_get_stdout, _set_stdout, None, None)

    def _get_stderr(self):
        return self._stderr

    def _set_stderr(self, value):
        self._stderr = list(value)

    stderr = property(_get_stderr, _set_stderr, None, None)

    def _get_result(self):
        return self._result

    def _set_result(self, value):
        self._result = list(value)

    result = property(_get_result, _set_result, None, None)

    def __nonzero__(self):
        return bool(self.rc in self.ok)


class LFI_Tool(footprints.FootprintBase):
    """
    Root class for any :class:`LFI_Tool` system subclasses.
    """

    _abstract  = True
    _collector = ('addon',)
    _footprint = dict(
        info = 'Default LFI system interface',
        attr = dict(
            lficmd = dict(),
            lfipath = dict(
                optional = True,
                default = None,
            )
        )
    )

    def __init__(self, *args, **kw):
        """Abstract LFI Tool initialisation."""
        logger.debug('Abstract LFI Tool init %s', self.__class__)
        super(LFI_Tool, self).__init__(*args, **kw)
        self._sh = None
        self._env = footprints.util.UpperCaseDict()

    @property
    def realkind(self):
        return 'addon'

    def get_sh(self):
        return self._sh

    def set_sh(self, value):
        self._sh = weakref.proxy(value)

    sh = property(get_sh, set_sh, None, None)

    def setenv(self, **kw):
        """Store some default environment values for execution."""
        self._env.update(kw)
        return self._env

    def is_xlfi(self, source):
        rc = False
        with io.open(source, 'rb') as fd:
            rc = fd.read(8) == 'LFI_ALTM'
        return rc

    def _spawn(self, cmd, **kw):
        """Internal method setting local environment and calling standard shell spawn."""

        # Insert the actual lfi tool command as first argument
        cmd.insert(0, self.lficmd)
        if self.lfipath is not None:
            cmd[0] = self.lfipath + '/' + cmd[0]

        # Set global module env variable to a local environement object
        # activated temporarily for the curren spawned command.
        g = globals()
        localenv = self.sh.env.clone()
        for k in [ x for x in g.keys() if x.isupper() ]:
            localenv[k] = g[k]

        # Overwrite global module env values with specific ones
        localenv.update(self._env)

        # Ask the attached shell to run the lfi tool command
        localenv.active(True)
        rc = self.sh.spawn(cmd, **kw)
        localenv.active(False)
        return rc


class LFI_Standard(LFI_Tool):
    """As long as cycling is not concerned..."""

    def lfi_diff(self, lfi1, lfi2, **kw):
        """
        Difference between two lfi-files.
        
        Mandatory args are:
          * lfi1 : first file to compare
          * lfi2 : second file to compare
        
        Options are:
          * maxprint   : Maximum number of values to print
          * skipfields : LFI fields not to be compared
          * skiplength : Offset at which the comparison starts for each LFI fields
        """
        cmd = [ 'diff', '--lfi-file-1', lfi1, '--lfi-file-2', lfi2 ]

        maxprint = kw.pop('maxprint', 2)
        if maxprint:
            cmd.extend(['--max-print-diff', str(maxprint)])

        skipfields = kw.pop('skipfields', 0)
        if skipfields:
            cmd.extend(['--lfi-skip-fields', str(skipfields)])

        skiplength = kw.pop('skiplength', 0)
        if skiplength:
            cmd.extend(['--lfi-skip-length', str(skiplength)])

        rawout = self._spawn(cmd, **kw)
        fields = [ x.partition('!= ')[-1] for x in rawout if x.startswith(' !=') ]

        return LFI_Status(rc=len(fields), stdout=rawout, result=fields)

    def lfi_rm(self, *args):
        """Remove (possibly) multi lfi files."""
        st = LFI_Status(result=list())
        for pname in args:
            for objpath in self.sh.glob(pname):
                xlfi = self.is_xlfi(objpath)
                rc = self.sh.remove(objpath)
                if xlfi:
                    rc = self.sh.remove(objpath + '.d') and rc
                st.result.append(dict(path=objpath, multi=xlfi, rc=rc))
                st.rc = st.rc + ( 1 - int(rc))
        return st

    def _cp_pack_read(self, source, destination):
        rc = self._spawn(['lfi_alt_pack', '--lfi-file-in', source, '--lfi-file-out', destination])
        self.sh.chmod(destination, 0444)
        return rc

    def _cp_pack_write(self, source, destination):
        rc = self._spawn(['lfi_alt_pack', '--lfi-file-in', source, '--lfi-file-out', destination])
        self.sh.chmod(destination, 0644)
        return rc

    def _cp_copy_read(self, source, destination):
        rc = self._spawn(['lfi_alt_copy', '--lfi-file-in', source, '--lfi-file-out', destination])
        self.sh.chmod(destination, 0444)
        return rc

    def _cp_copy_write(self, source, destination):
        rc = self._spawn(['lfi_alt_copy', '--lfi-file-in', source, '--lfi-file-out', destination])
        self.sh.chmod(destination, 0644)
        return rc

    _cp_aspack_fsok_read  = _cp_pack_read
    _cp_aspack_fsok_write = _cp_pack_write
    _cp_aspack_fsko_read  = _cp_pack_read
    _cp_aspack_fsko_write = _cp_pack_write

    _cp_nopack_fsok_read  = _cp_copy_read
    _cp_nopack_fsok_write = _cp_copy_write
    _cp_nopack_fsko_read  = _cp_pack_read
    _cp_nopack_fsko_write = _cp_pack_write

    def multicpmethod(self, pack=False, intent='in', samefs=False):
        return '_cp_{0:s}_{1:s}_{2:s}'.format(
            'aspack' if pack else 'nopack',
            'fsok' if samefs else 'fsko',
            'read' if intent == 'in' else 'write',
        )

    def lfi_cp(self, source, destination, intent='in', pack=False):
        """Extended copy for (possibly) multi lfi file."""
        st = LFI_Status()
        if self.is_xlfi(source):
            if self.sh.filecocoon(destination) and self.lfi_rm(destination):
                xcp = self.multicpmethod(pack, intent, self.sh.is_samefs(source, destination))
                actualcp = getattr(self, xcp, None)
                if actualcp is None:
                    raise AttributeError('No actual LFI cp command ' + xcp)
                else:
                    st.rc = actualcp(source, self.sh.path.realpath(destination))
            else:
                raise OSError('Could not prepare destination copy [' + destination + ']')
        else:
            if intent == 'in':
                st.rc = self.sh.smartcp(source, destination)
            else:
                st.rc = self.sh.cp(source, destination)
        return st

    def lfi_mv(self, source, destination, intent='in', pack=False):
        """Extended mv for (possibly) multi lfi file."""
        if self.is_xlfi(source):
            st = self.lfi_cp(source, destination, intent=intent, pack=pack)
            if st:
                st = self.lfi_rm(source)
        else:
            st = LFI_Status()
            st.rc = self.sh.mv(source, destination)
            if intent == 'in':
                self.sh.chmod(destination, 0444)
            else:
                self.sh.chmod(destination, 0644)
        return st
