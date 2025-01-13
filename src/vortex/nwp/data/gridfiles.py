"""
Resources associated with the handling of gridded data (other than full model states).
"""

import re

from bronx.stdtypes.date import Time
import footprints

from vortex.data.contents import JsonDictContent
from vortex.data.flow import GeoFlowResource, FlowResource
from vortex.syntax.stdattrs import term_deco, timeperiod_deco
from vortex.syntax.stddeco import namebuilding_insert
from vortex.tools import env

#: No automatic export
__all__ = []


_ORIGIN_INFO = """Describes where the data originaly comes from. The most common
values are: ana (that stands for analysis), fcst (that stands for
forecast), hst (that stands for Historic file. i.e a file that contains a
full model state variable), stat_ad (that stands for statistical adapatation)."""
_ORIGIN_INFO = _ORIGIN_INFO.replace("\n", " ")


class AbstractGridpoint(GeoFlowResource):
    """Gridpoint file calculated in a post-processing task or module.

    * Possible formats are 'grib', 'fa' or 'netcdf'.
    * A gridpoint file can be calculated for files from different sources given
      by the "origin" attribute.

    """

    _abstract = True
    _footprint = dict(
        info="Any kind of GridPoint file.",
        attr=dict(
            origin=dict(
                info=_ORIGIN_INFO,
                values=[
                    "analyse",
                    "ana",
                    "guess",
                    "gss",
                    "arpege",
                    "arp",
                    "arome",
                    "aro",
                    "aladin",
                    "ald",
                    "historic",
                    "hst",
                    "forecast",
                    "fcst",
                    "era40",
                    "e40",
                    "era15",
                    "e15",
                    "interp",
                    "sumo",
                    "filter",
                    "stat_ad",
                ],
                remap=dict(
                    analyse="ana",
                    guess="gss",
                    arpege="arp",
                    aladin="ald",
                    arome="aro",
                    historic="hst",
                    forecast="fcst",
                    era40="e40",
                    era15="e15",
                ),
            ),
            kind=dict(
                values=["gridpoint", "gribfile", "fullpos"],
                remap=dict(fullpos="gridpoint"),
            ),
            nativefmt=dict(
                values=["grib", "grib1", "grib2", "netcdf", "fa"],
            ),
            filtername=dict(
                # Dummy argument but avoid priority related messages with footprints
                info="With GridPoint files, leave filtername empty...",
                optional=True,
                values=[
                    None,
                ],
            ),
        ),
    )

    @property
    def realkind(self):
        return "gridpoint"

    def olive_basename(self):
        """OLIVE specific naming convention (abstract)."""
        pass

    def archive_basename(self):
        """OP ARCHIVE specific naming convention (abstract)."""
        pass

    def namebuilding_info(self):
        """Generic information, radical = ``grid``."""
        ninfo = super().namebuilding_info()
        if self.origin in ("stat_ad",):
            # For new ``origin`` please use this code path... Please, no more
            # weird logic like the one hard-coded in the else statement !
            source = self.origin
        else:
            if self.model == "mocage":
                if self.origin == "hst":
                    source = "forecast"
                else:
                    source = "sumo"
            elif self.model in ("hycom", "mfwam"):
                if self.origin == "ana":
                    source = "analysis"
                else:
                    source = "forecast"
            else:
                source = "forecast"
        ninfo.update(
            radical="grid",
            src=[self.model, source],
        )
        return ninfo

    def iga_pathinfo(self):
        """Standard path information for IGA inline cache."""
        directory = dict(fa="fic_day", grib="bdap")
        return dict(
            fmt=directory[self.nativefmt],
            nativefmt=self.nativefmt,
            model=self.model,
        )


class GridPoint(AbstractGridpoint):
    """
    Gridpoint files calculated in a post-processing task or module for
    a single-term.
    """

    _abstract = True
    _footprint = [
        term_deco,
    ]


class TimePeriodGridPoint(AbstractGridpoint):
    """
    Gridpoint files calculated in a post-processing task or module for
    a given time period.
    """

    _abstract = True
    _footprint = [
        timeperiod_deco,
        dict(
            attr=dict(
                begintime=dict(
                    optional=True,
                    default=Time(0),
                )
            )
        ),
    ]


# A bunch of generic footprint declaration to ease with class creation
_NATIVEFMT_FULLPOS_FP = footprints.Footprint(
    info="Abstract nativefmt for fullpos files.",
    attr=dict(
        nativefmt=dict(
            values=["fa"],
            default="fa",
        )
    ),
)
_NATIVEFMT_GENERIC_FP = footprints.Footprint(
    info="Abstract nativefmt for any other gridpoint files.",
    attr=dict(
        nativefmt=dict(
            values=["grib", "grib1", "grib2", "netcdf"], default="grib"
        )
    ),
)
_FILTERNAME_AWARE_FPDECO = footprints.DecorativeFootprint(
    footprints.Footprint(
        info="Abstract filtering attribute (used when the filtername attribute is allowed).",
        attr=dict(
            filtername=dict(
                info="The filter used to obtain this data.",
                optional=False,
                values=[],
            )
        ),
    ),
    decorator=[
        namebuilding_insert("filtername", lambda s: s.filtername),
    ],
)


class GridPointMap(FlowResource):
    """Map of the gridpoint files as produced by fullpos."""

    _footprint = dict(
        info="Gridpoint Files Map",
        attr=dict(
            kind=dict(
                values=["gridpointmap", "gribfilemap", "fullposmap"],
                remap=dict(
                    fullposmap="gridpointmap",
                ),
            ),
            clscontents=dict(
                default=JsonDictContent,
            ),
            nativefmt=dict(
                values=["json"],
                default="json",
            ),
        ),
    )

    @property
    def realkind(self):
        return "gridpointmap"


class GridPointFullPos(GridPoint):
    """Gridpoint file produced by FullPos in ``fa`` format."""

    _footprint = [
        _NATIVEFMT_FULLPOS_FP,
        dict(info="GridPoint file produced by Fullpos (with a single term)"),
    ]

    def olive_basename(self):
        """OLIVE specific naming convention."""

        t = self.term.hour
        e = env.current()
        if "VORTEX_ANA_TERMSHIFT" not in e and self.origin == "ana":
            t = 0

        name = None
        if self.model == "mocage":
            if self.origin == "hst":
                name = "HM" + self.geometry.area + "+" + self.term.fmthour
            elif self.origin == "sumo":
                deltastr = "PT{!s}H".format(self.term.hour)
                deltadate = self.date + deltastr
                name = (
                    "SM" + self.geometry.area + "_void" + "+" + deltadate.ymd
                )
            elif self.origin == "interp":
                deltastr = "PT{!s}H".format(self.term.hour)
                deltadate = self.date + deltastr
                name = (
                    "SM" + self.geometry.area + "_interp" + "+" + deltadate.ymd
                )
        else:
            name = (
                "PFFPOS"
                + self.origin.upper()
                + self.geometry.area
                + "+"
                + self.term.nice(t)
            )

        if name is None:
            raise ValueError(
                "Could not build a proper olive name: {!s}".format(self)
            )

        return name

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""

        deltastr = "PT{!s}H".format(self.term.hour)
        deltadate = self.date + deltastr

        name = None
        if self.origin == "hst":
            if self.model == "ifs":
                name = "PFFPOS" + self.geometry.area + "+" + self.term.fmthour
            else:
                name = "HM" + self.geometry.area + "+" + deltadate.ymdh
        elif self.origin == "interp":
            name = "SM" + self.geometry.area + "+" + deltadate.ymd

        if name is None:
            raise ValueError(
                "Could not build a proper archive name: {!s}".format(self)
            )

        return name


class GridPointExport(GridPoint):
    """Generic single term gridpoint file using a standard format."""

    _footprint = [
        _NATIVEFMT_GENERIC_FP,
        dict(info="Generic gridpoint file (with a single term)"),
    ]

    def olive_basename(self):
        """OLIVE specific naming convention."""

        t = self.term.hour
        e = env.current()
        if "VORTEX_ANA_TERMSHIFT" not in e and self.origin == "ana":
            t = 0
        return (
            "GRID"
            + self.origin.upper()
            + self.geometry.area
            + "+"
            + self.term.nice(t)
        )

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""

        name = None
        if re.match("aladin|arome", self.model):
            name = (
                "GRID"
                + self.geometry.area
                + "r{!s}".format(self.date.hour)
                + "_"
                + self.term.fmthour
            )
        elif re.match("arp|hycom|surcotes", self.model):
            name = "(gribfix:igakey)"
        elif self.model == "ifs":
            deltastr = "PT{!s}H".format(self.term.hour)
            deltadate = self.date + deltastr
            name = "MET" + deltadate.ymd + "." + self.geometry.area + ".grb"

        if name is None:
            raise ValueError(
                "Could not build a proper archive name: {!s}".format(self)
            )

        return name


class FilteredGridPointExport(GridPointExport):
    """Generic single term gridpoint file using a standard format."""

    _footprint = [
        _FILTERNAME_AWARE_FPDECO,
    ]


class TimePeriodGridPointExport(TimePeriodGridPoint):
    """Generic multi term gridpoint file using a standard format."""

    _footprint = [
        _NATIVEFMT_GENERIC_FP,
    ]


class FilteredTimePeriodGridPointExport(TimePeriodGridPointExport):
    """Generic multi term gridpoint file using a standard format."""

    _footprint = [
        _FILTERNAME_AWARE_FPDECO,
    ]
