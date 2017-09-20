#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.data.outflow import NoDateResource
from vortex.data.flow    import GeoFlowResource
from gco.syntax.stdattrs import gvar

"""
Ctpini files
"""

#: No automatic export
__all__ = []


class CtpiniDirectives (GeoFlowResource):
    """Abstract class to deal with Ctpini directive file"""

    _footprint = dict(
        info = "Ctpini directives directory",
        attr = dict(
            kind = dict(
                values = ["ctpini_directives_directory",],
            ),
            nativefmt = dict(
                optional = True,
                values = ['ctpinidirpack'],
                default = 'ctpinidirpack',
            ),
        )
    )

    @property
    def realkind(self):
        return 'ctpini_directives_directory'

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return "infoctpini.tar"

    def basename_info(self):
        """Generic information for names fabric."""
        return dict(
            radical = self.realkind,
            fmt = self.nativefmt,
        )


class AsciiFiles(NoDateResource):
    """Class to deal with miscealenous ascii files coming from genv."""

    _abstract = True
    _footprint = [
        gvar,
        dict(
            info = 'Abstract class for ascii files from genv.',
        )
    ]


class CtpiniAsciiFiles(AsciiFiles):
    """Class to deal with Ctpini ascii files."""

    _footprint = [
        dict(
            info = "Ctpini ascii files.",
            attr = dict(
                kind = dict(
                    values = ["ctpini_ascii_file"],
                ),
                source = dict(
                    values = ["levels", "covano", "fort61", "coor","cov46"],
                ),
                gvar = dict(
                    default = "tsr_misc_[source]",
                )
            )
        )
    ]

    @property
    def realkind(self):
        return "ctpini_ascii_file"
