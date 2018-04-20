#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division, unicode_literals

import footprints

from vortex.data.outflow import NoDateResource
from vortex.data.flow    import GeoFlowResource
from gco.syntax.stdattrs import gvar
from vortex.data.contents import DataTemplate
from common.data.gridfiles import GridPoint

"""
Ctpini files
"""

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


class CtpiniDirectiveFile(GeoFlowResource):
    """
    Class dealing with Ctpini directive file.
    """

    _footprint = dict(
        info = "Ctpini directive file",
        attr = dict(
            kind = dict(
                values = ["ctpini_directives_file", ],
            ),
            nativefmt = dict(
                default = "ascii"
            )
        )
    )

    @property
    def realkind(self):
        return "ctpini_directives_file"

    def basename_info(self):
        """Generic informations for the name builder."""
        return dict(
            radical = self.realkind,
            fmt     = self.nativefmt,
            src     = self.model,
            geo     = self._geo2basename_info(),
        )


class AsciiFiles(NoDateResource):
    """
    Class to deal with miscellaneous ascii files coming from genv.
    """

    _abstract = True
    _footprint = [
        gvar,
        dict(
            info = 'Abstract class for ascii files from genv.',
        )
    ]


class CtpiniAsciiFiles(AsciiFiles):
    """
    Class to deal with Genv Ctpini ascii files.
    """

    _footprint = [
        dict(
            info = "Ctpini Genv ascii files.",
            attr = dict(
                kind = dict(
                    values = ["ctpini_ascii_file"],
                ),
                source = dict(
                    values = ["levels", "covano", "fort61", "coor", "cov46"],
                ),
                gvar = dict(
                    default = "tsr_misc_[source]",
                ),
                clscontents=dict(
                    default = DataTemplate
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return "ctpini_ascii_file"


class GridPointCtpini(GridPoint):
    """
    Class to deal with Gridpoint files used as input in Ctpini.
    """

    _footprint = dict(
        info = 'Ctpini Gridpoint Fields',
        attr = dict(
            kind = dict(
                values = ['ctpini_gridpoint', ],
            ),
            origin = dict(
                values = ['oper', 'PS', 'dble', 'PX', 'ctpini', 'PTSR', ],
                remap = dict(
                    PS = 'oper',
                    PX = 'dble',
                    PTSR = 'ctpini',
                ),
            ),
            parameter = dict(
                values = ['PMERSOL', 'T850HPA', 'Z15PVU', 'Z20PVU', 'Z07PVU', 'TROPO'],
            ),
            run_ctpini = dict(
                optional = True,
                default = None,
            ),
            nativefmt = dict(
                values = ['geo', ],
                default = 'geo',
            ),
        )
    )

    @property
    def realkind(self):
        return "ctpini_gridpoint"

    def basename_info(self):
        """Generic information, radical = ``grid``."""

        if self.origin == 'ctpini' and self.run_ctpini is not None:
            source = [self.model, self.origin, self.parameter, self.run_ctpini]
        else:
            source = [self.model, self.origin, self.parameter]

        return dict(
            radical = 'ctpini-grid',
            fmt     = self.nativefmt,
            src     = source,
            geo     = self._geo2basename_info(),
            term    = self.term.fmthm
        )
