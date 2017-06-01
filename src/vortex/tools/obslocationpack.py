#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from . import folder


@folder.folderize
class ObsLocationPackShell(folder.FolderShell):
    """
    Default interface to  Obs Location packs commands.
    These commands extend the shell.
    """

    _footprint = dict(
        info = 'Default Obs Location packs system interface',
        attr = dict(
            kind = dict(
                values   = ['obslocationpack'],
            ),
        )
    )
