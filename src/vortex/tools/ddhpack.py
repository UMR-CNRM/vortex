#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from . import folder


class DdhPackShell(folder.FolderShell):
    """
    Default interface to DDHpack commands.
    These commands extend the shell.
    """

    _footprint = dict(
        info = 'Default DDHpack system interface',
        attr = dict(
            kind = dict(
                values   = ['ddhpack'],
            ),
        )
    )

    def ddhpack_cp(self, source, destination, intent='in'):
        """Extended copy for ODB repository."""
        return super(DdhPackShell, self)._folder_cp(source, destination, intent)

    def ddhpack_ftget(self, source, destination, hostname=None, logname=None):
        """Proceed direct ftp get on the specified target."""
        return super(DdhPackShell, self)._folder_ftget(source, destination,
                                                       hostname, logname)

    def ddhpack_ftput(self, source, destination, hostname=None, logname=None):
        """Proceed direct ftp get on the specified target."""
        return super(DdhPackShell, self)._folder_ftput(source, destination,
                                                       hostname, logname)

    def ddhpack_rawftput(self, source, destination, hostname=None, logname=None):
        """Proceed direct ftp get on the specified target."""
        return super(DdhPackShell, self)._folder_rawftput(source, destination,
                                                          hostname, logname)

    ddhpack_rawftget = ddhpack_ftget
