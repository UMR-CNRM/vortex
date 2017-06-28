#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division

import tempfile

import footprints
from . import addons

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)

_folder_exposed_methods = set(['cp', 'mv', 'ftget', 'rawftget', 'ftput', 'rawftput'])


def folderize(cls):
    """Create the necessary methods in a class that inherits from :class:`FolderShell`."""
    addon_kind = cls.footprint_retrieve().get_values('kind')
    if len(addon_kind) != 1:
        raise SyntaxError("Authorised values for a given Addon's kind must be unique")
    addon_kind = addon_kind[0]
    for basic_mtdname in _folder_exposed_methods:
        expected_mtdname = '{:s}_{:s}'.format(addon_kind, basic_mtdname)
        if not hasattr(cls, expected_mtdname):
            parent_mtd = getattr(cls, '_folder_{:s}'.format(basic_mtdname))
            setattr(cls, expected_mtdname, parent_mtd)
    return cls


class FolderShell(addons.FtrawEnableAddon):
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
                default  = 'folder_tmpunpack',
            ),
            pipeget = dict(
                type     = bool,
                optional = True,
                default  = False,
            ),
            supportedfmt = dict(
                optional = True,
                default  = '[kind]',
            ),
        )
    )

    def _folder_cp(self, source, destination, intent='in', silent=False):
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

    def _folder_mv(self, source, destination):
        """Shortcut to :meth:`move` method (file or directory)."""
        if not isinstance(source, basestring) or not isinstance(destination, basestring):
            rc = self.sh.hybridcp(source, destination)
            if isinstance(source, basestring):
                rc = rc and self.sh.remove(source)
        else:
            rc, source, destination = self.sh.tarfix_out(source, destination)
            rc = rc and self.sh.move(source, destination)
            if rc:
                rc, source, destination = self.sh.tarfix_in(source, destination)
        return rc

    def _folder_credentials(self, hostname=None, logname=None):
        """Some heuristic to get proper values for these arguments."""
        if hostname is None:
            hostname = self.sh.env.VORTEX_ARCHIVE_HOST

        if logname is None:
            logname = self.sh.env.VORTEX_ARCHIVE_USER

        return (hostname, logname)

    def _folder_preftget(self, source, destination):
        """Prepare source and destination"""
        if not (source.endswith('.tgz') or source.endswith('.tar')):
            source += '.tgz'
        self.sh.rm(destination)
        destination = self.sh.path.abspath(destination)
        return source, destination

    def _folder_postftget(self, destination, loccwd, loctmp):
        """Move the untared stuff to the destination and clean-up things."""
        try:
            unpacked = self.sh.glob('*')
            if unpacked:
                if (len(unpacked) == 1 and
                        self.sh.path.isdir(self.sh.path.join(unpacked[-1]))):
                    # This is the most usual case... (ODB, DDH packs produced by Vortex)
                    self.sh.mv(unpacked[-1], destination)
                else:
                    # Old-style DDH packs (produced by Olive)
                    self.sh.mkdir(destination)
                    for item in unpacked:
                        self.sh.mv(item, self.sh.path.join(destination, item))
            else:
                logger.error('Nothing to unpack')
        except StandardError as trouble:
            logger.critical('Unable to proceed folder post-ftget step')
            raise trouble
        finally:
            self.sh.cd(loccwd)
            self.sh.rm(loctmp)

    def _folder_ftget(self, source, destination, hostname=None, logname=None,
                      cpipeline=None):
        """Proceed direct ftp get on the specified target."""
        if cpipeline is not None:
            raise IOError("It's not allowed to compress folder like data.")
        hostname, logname = self._folder_credentials(hostname, logname)
        if hostname is None:
            return False

        source, destination = self._folder_preftget(source, destination)
        ftp = self.sh.ftp(hostname, logname)
        if ftp:
            loccwd = self.sh.getcwd()
            loctmp = tempfile.mkdtemp(prefix='folder_', dir=loccwd)
            self.sh.cd(loctmp)
            try:
                if self.pipeget:
                    p = self.sh.popen(
                        # the z option is omitted consequently it also works if the file is not compressed
                        ['tar', 'xvf', '-'],
                        stdin   = True,
                        output  = False,
                        bufsize = 8192,
                    )
                    rc = ftp.get(source, p.stdin)
                    self.sh.pclose(p)
                else:
                    extname = self.sh.path.splitext(source)[1]
                    try:
                        rc = ftp.get(source, self.tmpname + extname)
                        # Auto compress=False -> let tar deal automatically with the compression
                        self.sh.untar(self.tmpname + extname, autocompress=False)
                    finally:
                        self.sh.rm(self.tmpname + extname)
            finally:
                ftp.close()
                self._folder_postftget(destination, loccwd, loctmp)
            return rc
        else:
            return False

    def _folder_rawftget(self, source, destination, hostname=None, logname=None,
                         cpipeline=None):
        """Use ftserv as much as possible."""
        if cpipeline is not None:
            raise IOError("It's not allowed to compress folder like data.")
        if self.sh.ftraw and self.rawftshell is not None:
            source, destination = self._folder_preftget(source, destination)
            loccwd = self.sh.getcwd()
            loctmp = tempfile.mkdtemp(prefix='folder_', dir=loccwd)
            self.sh.cd(loctmp)
            try:
                extname = self.sh.path.splitext(source)[1]
                try:
                    rc = self.sh.ftserv_get(source, self.tmpname + extname,
                                            hostname=hostname, logname=logname)
                    self.sh.untar(self.tmpname + extname, autocompress=False)
                finally:
                    self.sh.rm(self.tmpname + extname)
            finally:
                self._folder_postftget(destination, loccwd, loctmp)
            return rc
        else:
            return self._folder_ftget(source, destination, hostname, logname)

    def _packed_size(self, source):
        """Size of the final file, must be exact or be an overestimation.

        A file 1 byte bigger than this estimation might be rejected,
        hence the conservative options:
        - tar adds 1% with a minimum of 1 Mbytes
        - compression gain is 0%
        """
        dir_size = self.sh.treesize(source)
        tar_mini = 1024 * 1024  # 1 Mbytes
        tar_loss = 1  # 1%
        zip_gain = 0
        tar_size = dir_size + max(tar_mini, (dir_size * tar_loss) // 100)
        return (tar_size * (100 - zip_gain)) // 100

    def _folder_ftput(self, source, destination, hostname=None, logname=None,
                      cpipeline=None):
        """Proceed direct ftp put on the specified target."""
        if cpipeline is not None:
            raise IOError("It's not allowed to compress folder like data.")
        hostname, logname = self._folder_credentials(hostname, logname)
        if hostname is None:
            return False

        if not destination.endswith('.tgz'):
            destination += '.tgz'

        source = self.sh.path.abspath(source)
        source_name = self.sh.path.basename(source)
        source_dirname = self.sh.path.dirname(source)

        ftp = self.sh.ftp(hostname, logname)
        if ftp:
            packed_size = self._packed_size(source)
            p = self.sh.popen(
                ['tar', '--directory', source_dirname, '-cz', source_name],
                stdout  = True,
                output  = False,
                bufsize = 8192,
            )
            rc = ftp.put(p.stdout, destination, size=packed_size, exact=False)
            self.sh.pclose(p)
            ftp.close()
            return rc
        else:
            return False

    def _folder_rawftput(self, source, destination, hostname=None, logname=None,
                         cpipeline=None):
        """Use ftserv as much as possible."""
        if cpipeline is not None:
            raise IOError("It's not allowed to compress folder like data.")
        if self.sh.ftraw and self.rawftshell is not None:
            if not destination.endswith('.tgz'):
                destination += '.tgz'
            newsource = self.sh.copy2ftspool(source, nest=True,
                                             fmt=self.supportedfmt)
            request = self.sh.path.dirname(newsource) + '.request'
            with open(request, 'w') as request_fh:
                request_fh.write(self.sh.path.dirname(newsource))
            self.sh.readonly(request)
            rc = self.sh.ftserv_put(request, destination,
                                    hostname=hostname, logname=logname,
                                    specialshell=self.rawftshell)
            self.sh.rm(request)
            return rc
        else:
            return self._folder_ftput(source, destination, hostname, logname)
