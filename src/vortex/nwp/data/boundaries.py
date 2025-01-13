"""
Resources to handle any boundary conditions data for a coupled model.
"""

import re

from bronx.stdtypes import date
import footprints
from vortex.tools import env
from vortex.data.flow import GeoFlowResource, GeoPeriodFlowResource
from vortex.syntax.stddeco import (
    namebuilding_append,
    namebuilding_insert,
    overwrite_realkind,
)
from vortex.syntax.stdattrs import term_deco, timeperiod_deco, a_cutoff
from vortex.data.geometries import LonlatGeometry

from ..tools.igastuff import archive_suffix

#: No automatic export
__all__ = []


@namebuilding_insert("radical", lambda s: "cpl")
@namebuilding_insert("src", lambda s: s._mysrc)
class _AbstractLAMBoundary(GeoFlowResource):
    """
    Class of a coupling file for a Limited Area Model.
    A SpectralGeometry object is needed.
    """

    _abstract = True
    _footprint = [
        term_deco,
        dict(
            info="Coupling file for a limited area model",
            attr=dict(
                kind=dict(
                    values=["boundary", "elscf", "coupled"],
                    remap=dict(autoremap="first"),
                ),
                nativefmt=dict(
                    values=[
                        "fa",
                        "grib",
                        "netcdf",
                        "ascii",
                        "wbcpack",
                        "unknown",
                    ],
                    default="fa",
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "boundary"

    @property
    def _mysrc(self):
        raise NotImplementedError

    def olive_basename(self):
        """OLIVE specific naming convention."""
        if self.mailbox.get("block", "-") == "surfan":
            hhreal = self.term
        else:
            e = env.current()
            if "HHDELTA_CPL" in e:
                actualbase = self.date - date.Time(e.HHDELTA_CPL + "H")
            else:
                actualbase = date.synop(base=self.date)
            hhreal = (self.date - actualbase).time() + self.term
        return "ELSCFALAD_" + self.geometry.area + "+" + hhreal.fmthour

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        suffix = archive_suffix(self.model, self.cutoff, self.date)
        prefix = "COUPL"
        source = (
            self._mysrc[0] if isinstance(self._mysrc, list) else self._mysrc
        )
        if re.match("assist1bis|testms1", self.geometry.area):
            prefix = "COUPL1"
        if re.match("ifs|ecmwf", source) and "16km" in self.geometry.rnice:
            prefix = "COUPLIFS"

        if self.model == "mocage":
            valid = (self.date + self.term).ymd
            return "SM" + self.geometry.area + "+" + valid

        return prefix + self.term.fmthour + ".r{!s}".format(suffix)

    def iga_pathinfo(self):
        """Standard path information for IGA inline cache."""
        if self.model == "arome":
            directory = "fic_day"
        elif self.model == "mfwam":
            directory = "guess"
        else:
            directory = "autres"
        return dict(
            fmt=directory,
            model=self.model,
            nativefmt=self.nativefmt,
        )

    def _geo2basename_info(self, add_stretching=True):
        """Particular geometry dictionnary for _AbstractLamBoundary class and derivated ones."""
        if isinstance(self.geometry, LonlatGeometry):
            lgeo = [self.geometry.area, self.geometry.rnice]
        else:
            lgeo = super()._geo2basename_info(add_stretching)
        return lgeo


class LAMBoundary(_AbstractLAMBoundary):
    """
    Class of a coupling file for a Limited Area Model.
    A SpectralGeometry object is needed and the source model is given in the footprint.
    """

    _footprint = dict(
        attr=dict(
            source=dict(
                values=[
                    "arpege",
                    "aladin",
                    "arome",
                    "ifs",
                    "ecmwf",
                    "psy4",
                    "mercator_global",
                    "glo12",
                    "mfwam",
                ]
            ),
        )
    )

    @property
    def _mysrc(self):
        return self.source


_a_source_cutoff = a_cutoff
del _a_source_cutoff["alias"]
_a_source_cutoff["optional"] = True
_a_source_cutoff["default"] = "production"


class EnhancedLAMBoundary(_AbstractLAMBoundary):
    """
    Class of a coupling file for a Limited Area Model.
    A SpectralGeometry object is needed and the source app, source conf and
    source cutoff is given in the footprint.
    """

    _footprint = dict(
        attr=dict(
            source_app=dict(),
            source_conf=dict(),
            source_cutoff=_a_source_cutoff,
        )
    )

    @property
    def _mysrc(self):
        return [
            self.source_app,
            self.source_conf,
            {"cutoff": self.source_cutoff},
        ]


_abs_forcing_fp = footprints.DecorativeFootprint(
    info="Coupling file for any offline model.",
    attr=dict(
        kind=dict(
            values=[
                "forcing",
            ],
        ),
        filling=dict(),
        source_app=dict(),
        source_conf=dict(),
        source_cutoff=_a_source_cutoff,
    ),
    decorator=[
        namebuilding_insert(
            "src",
            lambda s: [
                s.source_app,
                s.source_conf,
                {"cutoff": s.source_cutoff},
            ],
        ),
        overwrite_realkind("forcing"),
    ],
)


class _AbstractForcing(GeoFlowResource):
    """Abstract class for date-based coupling file for any offline model."""

    _abstract = True
    _footprint = [
        _abs_forcing_fp,
    ]


class _AbstractPeriodForcing(GeoPeriodFlowResource):
    """Abstract class for period-based coupling file for any offline model."""

    _abstract = True
    _footprint = [
        _abs_forcing_fp,
    ]


_abs_external_forcing_fp = footprints.DecorativeFootprint(
    dict(
        attr=dict(
            model=dict(
                outcast=[
                    "surfex",
                ],
            ),
        ),
    ),
    decorator=[namebuilding_append("src", lambda s: s.filling)],
)


class ExternalForcing(_AbstractForcing):
    """Class for date-based coupling file for any offline model.

    This class takes an optional **term** attribute.
    """

    _footprint = [term_deco, _abs_external_forcing_fp]


class ExternalTimePeriodForcing(_AbstractForcing):
    """Class for date-based coupling file for any offline model.

    This class needs a **begintime**/**endtime** attribute.
    """

    _footprint = [timeperiod_deco, _abs_external_forcing_fp]


_abs_surfex_forcing_fp = footprints.DecorativeFootprint(
    dict(
        info="Coupling/Forcing file for Surfex.",
        attr=dict(
            model=dict(
                values=[
                    "surfex",
                ],
            ),
            filling=dict(
                optional=True,
                default="atm",
            ),
            nativefmt=dict(
                values=["netcdf", "ascii", "tar"],
                default="netcdf",
            ),
        ),
    ),
    decorator=[
        namebuilding_append(
            "src",
            lambda s: None if s.filling == "atm" else s.filling,
            none_discard=True,
        )
    ],
)


class SurfexForcing(_AbstractForcing):
    """Class for date-based coupling file for Surfex.

    This class takes an optional **term** attribute.
    """

    _footprint = [
        term_deco,
        _abs_surfex_forcing_fp,
    ]


class SurfexTimePeriodForcing(_AbstractForcing):
    """Class for date-based coupling file for Surfex.

    This class needs a **begintime**/**endtime** attribute.
    """

    _footprint = [
        timeperiod_deco,
        _abs_surfex_forcing_fp,
    ]


class SurfexPeriodForcing(_AbstractPeriodForcing):
    """Class for period-based coupling file for Surfex."""

    _footprint = [
        _abs_surfex_forcing_fp,
    ]
