#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from . import folder


@folder.folderize
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
