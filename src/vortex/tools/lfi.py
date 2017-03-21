#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import re

import footprints

from vortex.util.structs import Tracker
from . import addons

#: Export nothing
__all__ = []

logger = footprints.loggers.getLogger(__name__)


def use_in_shell(sh, **kw):
    """Extend current shell with the LFI interface defined by optional arguments."""
    kw['shell'] = sh
    return footprints.proxy.addon(**kw)


class LFI_Status(object):
    """
    Store lfi commands status as a set of attributes:
      * rc = return code
      * stdout = raw standard output
      * result = an optional processing specific to each command
    """

    def __init__(self, rc=0, ok=None, stdout=None, stderr=None, result=None):
        self._rc = rc
        self._ok = ok or [0]
        self._stdout = stdout
        self._stderr = stderr
        self._result = result or list()

    def __str__(self):
        return '{0:s} | rc={1:d} result={2:d}>'.format(repr(self).rstrip('>'), self.rc, len(self.result))

    @property
    def ok(self):
        return self._ok

    def _get_rc(self):
        return self._rc

    def _set_rc(self, value):
        if value is not None:
            if type(value) is bool:
                value = 1 - int(value)
            self._rc = self._rc + value

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

    def cat(self, maxlines=None):
        """Cat the last stdout command up to ``maxlines`` lines. If maxlines is None, print all."""
        if self.stdout is not None:
            if maxlines is None:
                maxlines = len(self.stdout) + 1
            for l in self.stdout[:maxlines]:
                print l

    def __nonzero__(self):
        return bool(self.rc in self.ok)


class LFI_Tool_Raw(addons.FtrawEnableAddon):
    """
    Interface to LFI commands through Perl wrappers.
    """

    LFI_HNDL_SPEC   = ':1'
    DR_HOOK_SILENT  = 1
    DR_HOOK_NOT_MPI = 1
    OMP_STACKSIZE         = '32M'
    KMP_STACKSIZE         = '32M'
    KMP_MONITOR_STACKSIZE = '32M'

    _footprint = dict(
        info = 'Default LFI system interface (Perl)',
        attr = dict(
            kind = dict(
                values   = ['lfi'],
            ),
            cmd = dict(
                alias    = ('lficmd',),
                default  = 'lfitools',
            ),
            path = dict(
                alias    = ('lfipath',),
            ),
            warnpack = dict(
                type     = bool,
                optional = True,
                default  = False,
            ),
            wraplanguage = dict(
                values   = ['perl', ],
                default  = 'perl',
                optional = True,
                doc_visibility = footprints.doc.visibility.ADVANCED,
            ),
            toolkind = dict(
                default  = 'lfitools',
            ),
        )
    )

    def _spawn(self, cmd, **kw):
        """Tube to set LFITOOLS env variable."""
        self.env.LFITOOLS = self.actual_path + '/' + self.actual_cmd
        return super(LFI_Tool_Raw, self)._spawn(cmd, **kw)

    def _spawn_wrap(self, func, cmd, **kw):
        """Tube to set LFITOOLS env variable."""
        self.env.LFITOOLS = self.actual_path + '/' + self.actual_cmd
        return super(LFI_Tool_Raw, self)._spawn_wrap(['lfi_' + func, ] + cmd, **kw)

    def is_xlfi(self, source):
        """Check if the given ``source`` is a multipart-lfi file."""
        rc = False
        if source and isinstance(source, basestring) and self.sh.path.exists(source):
            with io.open(source, 'rb') as fd:
                rc = fd.read(8) == 'LFI_ALTM'
        return rc

    def _std_table(self, lfifile, **kw):
        """
        List of contents of a lfi-file.

        Mandatory args are:
          * lfifile : lfi file name

        """
        cmd = ['lfilist', lfifile]

        kw['output'] = True

        rawout = self._spawn(cmd, **kw)

        return LFI_Status(
            rc     = 0,
            stdout = rawout,
            result = [ tuple(eval(x)[0]) for x in rawout if x.startswith('[') ]
        )

    fa_table = lfi_table = _std_table

    def _std_diff(self, lfi1, lfi2, **kw):
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
        cmd = ['lfidiff', '--lfi-file-1', lfi1, '--lfi-file-2', lfi2]

        maxprint = kw.pop('maxprint', 2)
        if maxprint:
            cmd.extend(['--max-print-diff', str(maxprint)])

        skipfields = kw.pop('skipfields', 0)
        if skipfields:
            cmd.extend(['--lfi-skip-fields', str(skipfields)])

        skiplength = kw.pop('skiplength', 0)
        if skiplength:
            cmd.extend(['--lfi-skip-length', str(skiplength)])

        kw['output'] = True

        rawout = self._spawn(cmd, **kw)
        fields = [tuple(x.split(' ', 2)[-2:]) for x in rawout if re.match(r' (?:\!=|\+\+|\-\-)', x)]

        trfields = Tracker(
            deleted = [ x[1] for x in fields if x[0] == '--' ],
            created = [ x[1] for x in fields if x[0] == '++' ],
            updated = [ x[1] for x in fields if x[0] == '!=' ],
        )

        stlist = self.lfi_table(lfi1, output=True)
        trfields.unchanged = set([x[0] for x in stlist.result]) - set(trfields)

        return LFI_Status(
            rc     = int(bool(fields)),
            stdout = rawout,
            result = trfields
        )

    fa_diff = lfi_diff = _std_diff

    def fa_empty(self, fa1, fa2, **kw):
        """
        Create an empty FA file

        Mandatory args are:
          * fa1 : The reference file
          * fa2 : The new empty file

        """
        cmd = ['faempty', fa1, fa2]
        self._spawn(cmd, **kw)

    def _pack_stream(self, source):
        return self._spawn_wrap('pack', [source, ],
                                output  = False,
                                inpipe  = True,
                                bufsize = 8192)

    def _std_ftput(self, source, destination, hostname=None, logname=None):
        """On the fly packing and ftp."""
        if self.is_xlfi(source):
            st = LFI_Status()
            if hostname is None:
                hostname = self.sh.env.VORTEX_ARCHIVE_HOST
            if hostname is None:
                st.rc = 1
                st.result = ['No archive host provided']
                return st

            if logname is None:
                logname = self.sh.env.VORTEX_ARCHIVE_USER

            ftp = self.sh.ftp(hostname, logname)
            if ftp:
                p = self._pack_stream(source)
                st.rc = ftp.put(p.stdout, destination)
                self.sh.pclose(p)
                st.result = [destination]
                st.stdout = [
                    'Connection time   : {0:f}'.format(ftp.length),
                    'Actual target size: {0:d}'.format(ftp.size(destination))
                ]
                ftp.close()
            else:
                st.rc = 1
                st.result = ['Could not connect to ' + hostname + ' as user ' + logname]
            return st
        else:
            return self.sh.ftput(source, destination, hostname=hostname, logname=logname)

    def _std_rawftput(self, source, destination, hostname=None, logname=None):
        """Use ftserv as much as possible."""
        if self.is_xlfi(source):
            if self.sh.ftraw and self.rawftshell is not None:
                newsource = self.sh.copy2ftspool(source, fmt='lfi')
                rc = self.sh.ftserv_put(newsource, destination,
                                        hostname=hostname, logname=logname,
                                        specialshell=self.rawftshell)
                self.sh.rm(newsource)  # Delete the request file
                return rc
            else:
                return self._std_ftput(source, destination, hostname, logname)
        else:
            return self.sh.rawftput(source, destination, hostname=hostname, logname=logname)

    fa_ftput = lfi_ftput = _std_ftput
    fa_rawftput = lfi_rawftput = _std_rawftput

    def _std_prepare(self, source, destination, intent='in'):
        """Check for the source and prepare the destination."""
        if intent not in ('in', 'inout'):
            raise ValueError('Incorrect value for intent ({})'.format(intent))
        st = LFI_Status()
        if not self.sh.path.exists(source):
            logger.error('Missing source %s', source)
            st.rc = 2
            st.stderr = 'No such source file or directory : [' + source + ']'
            return st
        if not self.sh.filecocoon(destination):
            raise OSError('Could not cocoon [' + destination + ']')
        if not self.lfi_rm(destination):
            raise OSError('Could not clean destination [' + destination + ']')
        return st

    def _std_remove(self, *args):
        """Remove (possibly) multi lfi files."""
        st = LFI_Status(result=list())
        for pname in args:
            for objpath in self.sh.glob(pname):
                rc = self._spawn_wrap('remove', [objpath, ], output=False)
                st.result.append(dict(path=objpath,
                                      multi=self.is_xlfi(objpath), rc=rc))
                st.rc = rc
        return st

    lfi_rm = lfi_remove = fa_rm = fa_remove = _std_remove

    def _std_copy(self, source, destination, intent='in', pack=False, silent=False):
        """Extended copy for (possibly) multi lfi file."""
        st = self._std_prepare(source, destination, intent)
        if st.rc == 0:
            st.rc = self._spawn_wrap('copy', (['-pack', ] if pack else []) +
                                     ['-intent={}'.format(intent), source, destination],
                                     output=False)
        return st

    lfi_cp = lfi_copy = fa_cp = fa_copy = _std_copy

    def _std_move(self, source, destination, intent='in', pack=False):
        """Extended mv for (possibly) multi lfi file."""
        st = self._std_prepare(source, destination, intent)
        if st.rc == 0:
            st.rc = self._spawn_wrap('move', (['-pack', ] if pack else []) +
                                     ['-intent={}'.format(intent), source, destination],
                                     output=False)
        return st

    lfi_mv = lfi_move = fa_mv = fa_move = _std_move

    def _std_scp(self, source, destination, hostname, logname=None):
        """On the fly packing and scp."""
        if not self.is_xlfi(source):
            rc = self.sh.scp(source, destination, hostname, logname)
        else:
            ssh = self.sh.ssh(hostname, logname)
            permissions = ssh.get_permissions(source)
            # remove the .d companion directory (scp_stream removes the destination)
            # go on on failure : the .d lingers on, but the lfi will be self-contained
            ssh.remove(destination + '.d')
            p = self._pack_stream(source)
            rc = ssh.scp_stream(p.stdout, destination, permissions=permissions)
            self.sh.pclose(p)
        return rc

    fa_scp = lfi_scp = _std_scp


class LFI_Tool_Py(LFI_Tool_Raw):
    """
    Rewritten Python interface to LFITOOLS command.
    These commands are the one defined by the ``lfitools`` binary found in the IFS-ARPEGE framework.
    WARNING: This interface is broken from cy41 onward.
    """

    _footprint = dict(
        info = 'Default LFI system interface (Python)',
        attr = dict(
            wraplanguage = dict(
                values   = ['python', ],
            ),
        )
    )

    def _pack_stream(self, source):
        return self._spawn(['lfi_alt_pack', '--lfi-file-in', source,
                            '--lfi-file-out', '-'],
                           output  = False,
                           inpipe  = True,
                           bufsize = 8192)

    def _std_remove(self, *args):
        """Remove (possibly) multi lfi files."""
        st = LFI_Status(result=list())
        for pname in args:
            for objpath in self.sh.glob(pname):
                xlfi = self.is_xlfi(objpath)
                if xlfi:
                    rc = self._spawn(['lfi_alt_remv', '--lfi-file', objpath], output=False)
                else:
                    rc = self.sh.remove(objpath)
                st.result.append(dict(path=objpath, multi=xlfi, rc=rc))
                st.rc = rc
            for dirpath in self.sh.glob(pname + '.d'):
                if self.sh.path.exists(dirpath):
                    rc = self.sh.remove(dirpath)
                    st.result.append(dict(path=dirpath, multi=True, rc=rc))
                    st.rc = rc
        return st

    lfi_rm = lfi_remove = fa_rm = fa_remove = _std_remove

    def _cp_pack_read(self, source, destination):
        if self.warnpack:
            logger.warning('Suspicious packing <%s>', source)
        rc = self._spawn(['lfi_alt_pack', '--lfi-file-in', source, '--lfi-file-out', destination],
                         output=False)
        self.sh.chmod(destination, 0444)
        return rc

    def _cp_pack_write(self, source, destination):
        if self.warnpack:
            logger.warning('Suspicious packing <%s>', source)
        rc = self._spawn(['lfi_alt_pack', '--lfi-file-in', source, '--lfi-file-out', destination],
                         output=False)
        self.sh.chmod(destination, 0644)
        return rc

    def _cp_copy_read(self, source, destination):
        rc = self._spawn(['lfi_alt_copy', '--lfi-file-in', source, '--lfi-file-out', destination],
                         output=False)
        self.sh.chmod(destination, 0444)
        return rc

    def _cp_copy_write(self, source, destination):
        rc = self._spawn(['lfi_alt_copy', '--lfi-file-in', source, '--lfi-file-out', destination],
                         output=False)
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

    def _multicpmethod(self, pack=False, intent='in', samefs=False):
        return '_cp_{0:s}_{1:s}_{2:s}'.format(
            'aspack' if pack else 'nopack',
            'fsok' if samefs else 'fsko',
            'read' if intent == 'in' else 'write',
        )

    def _std_copy(self, source, destination, intent='in', pack=False, silent=False):
        """Extended copy for (possibly) multi lfi file."""
        st = LFI_Status()
        if not self.sh.path.exists(source):
            logger.error('Missing source %s', source)
            st.rc = 2
            st.stderr = 'No such source file or directory : [' + source + ']'
            return st
        if self.is_xlfi(source):
            if not self.sh.filecocoon(destination):
                raise OSError('Could not cocoon [' + destination + ']')
            if not self.lfi_rm(destination):
                raise OSError('Could not clean destination [' + destination + ']')
            xcp = self._multicpmethod(pack=pack, intent=intent, samefs=self.sh.is_samefs(source, destination))
            actualcp = getattr(self, xcp, None)
            if actualcp is None:
                raise AttributeError('No actual LFI cp command ' + xcp)
            else:
                st.rc = actualcp(source, self.sh.path.realpath(destination))
        else:
            if intent == 'in':
                st.rc = self.sh.smartcp(source, destination)
            else:
                st.rc = self.sh.cp(source, destination)
        return st

    lfi_cp = lfi_copy = fa_cp = fa_copy = _std_copy

    def _std_move(self, source, destination, intent='in', pack=False):
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

    lfi_mv = lfi_move = fa_mv = fa_move = _std_move


class IO_Poll(addons.Addon):
    """
    Default interface to ``io_poll`` utility.
    This addon is in charge of multi-file reshaping after IFS-ARPEGE execution.
    """

    LFI_HNDL_SPEC   = ':1'
    DR_HOOK_SILENT  = 1
    DR_HOOK_NOT_MPI = 1
    OMP_STACKSIZE         = '32M'
    KMP_STACKSIZE         = '32M'
    KMP_MONITOR_STACKSIZE = '32M'

    _footprint = dict(
        info = 'Default io_poll system interface',
        attr = dict(
            kind = dict(
                values  = ['iopoll', 'io_poll'],
                remap   = dict(
                    io_poll = 'iopoll',
                )
            ),
            cfginfo = dict(
                default = 'lfi',
            ),
            cmd = dict(
                alias   = ('iopollcmd', 'io_pollcmd', 'io_poll_cmd'),
                default = 'io_poll',
            ),
            path = dict(
                alias   = ('iopollpath', 'io_pollpath', 'io_poll_path', 'iopath'),
            ),
            interpreter = dict(
                values  = ['perl', 'none', 'None'],
                remap   = dict({'None': 'none', }),
                default = 'perl',
                optional = True,
            ),
            toolkind = dict(
                default = 'iopoll'
            )
        )
    )

    def __init__(self, *args, **kw):
        """Abstract Addon initialisation."""
        logger.debug('IO_Poll init %s', self.__class__)
        super(IO_Poll, self).__init__(*args, **kw)
        self._polled = set()

    def _spawn(self, cmd, **kw):
        """Tube to set LFITOOLS env variable."""
        if 'LFITOOLS' not in self.env:
            active_lfi = (LFI_Tool_Raw.in_shell(self.sh) or
                          LFI_Tool_Py.in_shell(self.sh))
            if active_lfi is None:
                raise RuntimeError('Could not find any active LFI Tool')
            self.env.LFITOOLS = active_lfi.actual_path + '/' + active_lfi.actual_cmd
        # Is there a need for an interpreter ?
        if self.interpreter != 'none':
            kw['interpreter'] = self.interpreter
        return super(IO_Poll, self)._spawn(cmd, **kw)

    def io_poll(self, prefix, nproc_io=None):
        """Do the actual job of polling files prefixed by ``prefix``."""
        cmd = ['--prefix', prefix]
        if nproc_io is None:
            if not self.sh.path.exists('fort.4'):
                raise IOError('The proc_io option or a fort.4 file should be provided.')
        else:
            cmd.extend(['--nproc_io', str(nproc_io)])

        # Catch the file processed
        rawout = self._spawn(cmd)

        # Cumulative results
        st = LFI_Status()
        st.result = rawout
        for polledfile in st.result:
            self._polled.add(polledfile)
        st.rc &= self.sh.rclast
        return st

    @property
    def polled(self):
        """List of files already polled."""
        return sorted(self._polled)
