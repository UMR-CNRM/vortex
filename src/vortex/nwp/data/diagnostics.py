"""
TODO: Module documentation.
"""

import footprints

from vortex.data.flow import GeoFlowResource, GeoPeriodFlowResource
from vortex.syntax.stdattrs import term_deco
from vortex.syntax.stddeco import (
    namebuilding_append,
    namebuilding_insert,
    overwrite_realkind,
)

#: No automatic export
__all__ = []


class ISP(GeoFlowResource):
    """Class for Forecasted Satellite Image resource. Obsolete."""

    _footprint = dict(
        info="Forecasted Satellite Image",
        attr=dict(
            kind=dict(values=["isp", "fsi"]),
            nativefmt=dict(
                values=[
                    "foo",
                ],
                default="foo",
            ),
        ),
    )

    @property
    def realkind(self):
        return "isp"

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return "anim0"

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return "ISP" + self.model[:4].upper()


@namebuilding_insert("radical", lambda s: "ddh")
@namebuilding_append("src", lambda s: s.scope)
class _DDHcommon(GeoFlowResource):
    """
    Abstract class for Horizontal Diagnostics.
    """

    _abstract = True
    _footprint = dict(
        info="Diagnostic on Horizontal Domains",
        attr=dict(
            kind=dict(values=["ddh", "dhf"], remap=dict(dhf="ddh")),
            nativefmt=dict(),
            scope=dict(
                values=["limited", "dlimited", "global", "zonal"],
                remap=dict(limited="dlimited"),
            ),
        ),
    )


class DDH(_DDHcommon):
    """
    Class for Horizontal Diagnostics.
    Used to be a ``dhf`` !
    """

    _footprint = [
        term_deco,
        dict(
            info="Diagnostic on Horizontal Domains",
            attr=dict(
                nativefmt=dict(
                    values=["lfi", "lfa"],
                    default="lfi",
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "ddh"

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return "dhf{:s}{:s}+{:s}".format(
            self.scope[:2].lower(), self.model[:4].lower(), self.term.fmth
        )

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return "DHF{:s}{:s}+{:s}".format(
            self.scope[:2].upper(), self.model[:4].upper(), self.term.fmth
        )


class DDHpack(_DDHcommon):
    """
    Class for Horizontal Diagnostics with all terms packed in a single directory.
    Used to be a ``dhf`` !
    """

    _footprint = dict(
        info="Diagnostic on Horizontal Domains packed in a single directory",
        attr=dict(
            nativefmt=dict(
                values=[
                    "ddhpack",
                ],
            ),
        ),
    )

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return "DHF{:s}{:s}.tar".format(
            self.scope[:2].upper(), self.model[:4].upper()
        )

    @property
    def realkind(self):
        return "ddhpack"


_surfex_diag_decofp = footprints.DecorativeFootprint(
    info="Diagnostic files outputed by surfex during a model run",
    attr=dict(
        kind=dict(
            values=[
                "diagnostics",
            ]
        ),
        scope=dict(),
        model=dict(
            values=[
                "surfex",
            ]
        ),
        nativefmt=dict(
            values=[
                "netcdf",
                "grib",
            ],
            default="netcdf",
            optional=True,
        ),
    ),
    decorator=[
        namebuilding_append("src", lambda s: s.scope),
        overwrite_realkind("diagnostics"),
    ],
)


class SurfexDiagnostics(GeoFlowResource):
    """Diagnostic files outputed by surfex during a model run (date/term version)."""

    _footprint = [_surfex_diag_decofp, term_deco]


class SurfexPeriodDiagnostics(GeoPeriodFlowResource):
    """Diagnostic files outputed by surfex during a model run (period version)."""

    _footprint = [
        _surfex_diag_decofp,
    ]


class ObjTrack(GeoFlowResource):
    """Class for Object Tracks."""

    _footprint = dict(
        info="Object Tracks json file",
        attr=dict(
            kind=dict(values=["objtrack"]),
            nativefmt=dict(
                values=[
                    "json",
                    "hdf5",
                    "foo",
                ],
                default="foo",
            ),
        ),
    )

    @property
    def realkind(self):
        return "objtrack"

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return "track{:s}{:s}+{:s}".format(
            self.scope[:2].lower(), self.model[:4].lower(), self.term.fmth
        )

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return "track{:s}{:s}+{:s}".format(
            self.scope[:2].upper(), self.model[:4].upper(), self.term.fmth
        )
