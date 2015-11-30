#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import tempfile

import footprints
logger = footprints.loggers.getLogger(__name__)

from . import addons


class FolderShell(addons.Addon):
    """
    This abstract class defines methods to manipulate folders.
    """

    _abstract = True
    _footprint = dict(
        info = 'Tools for manipulating folders',
        attr = dict(
            kind = dict(
                values   = ['folder'],
            ),
            tmpname = dict(
                optional = True,
                default  = 'folder_tmpunpack.tgz',
            ),
            pipeget = dict(
                type     = bool,
                optional = True,
                default  = True,
            ),
        )
    )

    def _folder_cp(self, source, destination, intent='in'):
        """Extended copy for a folder repository."""
        rc, source, destination = self.sh.tarfix_out(source, destination)
        rc = rc and self.sh.cp(source, destination, intent=intent)
        if rc:
            rc, source, destination = self.sh.tarfix_in(source, destination)
            if rc and intent == 'inout':
                self.sh.stderr('chmod', 0644, destination)
                oldtrace, self.sh.trace = self.sh.trace, False
                for infile in self.sh.ffind(destination):
                    self.sh.chmod(infile, 0644)
                self.sh.trace = oldtrace
        return rc

    def _folder_credentials(self, hostname=None, logname=None):
        """Some heuristic to get proper values for these arguments."""
        if hostname is None:
            hostname = self.sh.env.VORTEX_ARCHIVE_HOST

        if logname is None:
            logname = self.sh.env.VORTEX_ARCHIVE_USER

        return (hostname, logname)

    def _folder_ftget(self, source, destination, hostname=None, logname=None):
        """Proceed direct ftp get on the specified target."""
        hostname, logname = self._folder_credentials(hostname, logname)

        if hostname is None:
            return False

        if not source.endswith('.tgz'):
            source += '.tgz'

        self.sh.rm(destination)

        destination = self.sh.path.abspath(destination)

        ftp = self.sh.ftp(hostname, logname)
        if ftp:
            loccwd = self.sh.getcwd()
            loctmp = tempfile.mkdtemp(prefix='folder_', dir=loccwd)
            self.sh.cd(loctmp)
            try:
                if self.pipeget:
                    p = self.sh.popen(
                        ['tar', 'xvfz', '-'],
                        stdin   = True,
                        output  = False,
                        bufsize = 8192,
                    )
                    rc = ftp.get(source, p.stdin)
                    self.sh.pclose(p)
                else:
                    rc = ftp.get(source, self.tmpname)
                    self.sh.untar(self.tmpname)
                    self.sh.rm(self.tmpname)
            finally:
                ftp.close()
                try:
                    unpacked = self.sh.glob('*')
                    if unpacked:
                        self.sh.mv(unpacked[-1], destination)
                    else:
                        logger.error('Nothing to unpack')
                except StandardError as trouble:
                    logger.critical('Unable to proceed folder post-ftget step')
                    raise trouble
                finally:
                    self.sh.cd(loccwd)
                    self.sh.rm(loctmp)
            return rc
        else:
            return False

    def _folder_ftput(self, source, destination, hostname=None, logname=None):
        """Proceed direct ftp put on the specified target."""
        hostname, logname = self._folder_credentials(hostname, logname)

        if hostname is None:
            return False

        if not destination.endswith('.tgz'):
            destination += '.tgz'

        ftp = self.sh.ftp(hostname, logname)
        if ftp:
            p = self.sh.popen(
                ['tar', 'cvfz', '-', source],
                stdout  = True,
                output  = False,
                bufsize = 8192,
            )
            rc = ftp.put(p.stdout, destination)
            self.sh.pclose(p)
            ftp.close()
            return rc
        else:
            return False

    _folder_rawftput = _folder_ftput
    _folder_rawftget = _folder_ftget
