"""
Resources to handle any NWP model state variable.
"""

import re

from bronx.fancies import loggers

from vortex.data.flow import GeoFlowResource
from vortex.syntax.stdattrs import term_deco, term
from vortex.syntax.stddeco import namebuilding_insert
from bronx.stdtypes.date import Time

from ..tools.igastuff import archive_suffix
from vortex.data.geometries import CurvlinearGeometry

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


@namebuilding_insert("src", lambda s: [s.filling, s.model])
class AbstractAnalysis(GeoFlowResource):
    """Analysis resource.

    It can be an atmospheric, surface or full analysis (full = atmospheric + surface).
    """

    _abstract = True
    _footprint = dict(
        info="Analysis",
        attr=dict(
            kind=dict(values=["analysis", "analyse", "atm_analysis"]),
            nativefmt=dict(
                values=["fa", "grib", "lfi", "netcdf", "txt", "unknown"],
                default="fa",
            ),
            filtering=dict(
                info="The filtering that was applied during the generating process.",
                optional=True,
                values=["dfi"],
                doc_zorder=-5,
            ),
            filling=dict(
                info="The content/coverage of the analysis.",
                optional=True,
                default="full",
                values=[
                    "surface",
                    "surf",
                    "atmospheric",
                    "atm",
                    "full",
                    "soil",
                ],
                remap=dict(
                    surface="surf",
                    atmospheric="atm",
                ),
            ),
        ),
    )

    @property
    def realkind(self):
        return "analysis"


class Analysis3D(AbstractAnalysis):
    """3D Analysis resource (i.e. the resource has no term attribute).

    The data is assumed to be valid for **date** (i.e. term = 0).
    """

    _footprint = [
        term,
        dict(
            attr=dict(
                term=dict(
                    values=[
                        Time(0),
                    ],
                    optional=True,
                    default=Time(0),
                )
            )
        ),
    ]

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        ananame = "analyse"
        if "surf" in self.filling:
            if re.match("aladin|arome", self.model):
                ananame = "analyse_surf"
            elif self.model == "surfex":
                ananame = "analyse"
            elif self.model in ("hycom", "mfwam"):
                ananame = (
                    "(prefix:modelkey)(termfix:modelkey)(suffix:modelkey)"
                )
            else:
                ananame = "analyse_surface1"

        if self.filtering is not None:
            if "aladin" in self.model:
                ananame = "ANALYSE_DFI"

        if self.model == "surfex":
            ananame += ".sfx"

        return ananame

    def olive_basename(self):
        """OLIVE specific naming convention."""
        olivename_map = {
            "atm": "TRAJ" + self.model[:4].upper() + "+0000",
            "surf": "surfanalyse",
            "full": "analyse",
        }
        if self.model != "arpege":
            olivename_map["surf"] = "analyse"
            if self.model == "surfex":
                olivename_map = {
                    k: x + ".sfx" for k, x in olivename_map.items()
                }
        return olivename_map[self.filling]

    def iga_pathinfo(self):
        """Standard path information for IGA inline cache."""
        if self.model == "arome":
            if self.filling == "surf":
                directory = "fic_day"
            else:
                directory = "workdir/analyse"
        elif self.model == "arpege":
            if self.filling == "surf":
                directory = "workdir/analyse"
            else:
                directory = "autres"
        elif self.model in ("hycom", "mfwam"):
            if self.filling == "surf":
                directory = "guess"
        elif self.model == "surfex":
            directory = "fic_day"
        else:
            if self.filling == "surf":
                directory = "autres"
            else:
                directory = "workdir/analyse"
        return dict(
            fmt=directory,
            model=self.model,
            nativefmt=self.nativefmt,
        )


class Analysis4D(AbstractAnalysis):
    """4D Analysis resource (i.e. the resource has a term attribute)."""

    _footprint = [
        term_deco,
        dict(
            attr=dict(
                term=dict(
                    outcast=[
                        Time(0),
                    ]
                )
            )
        ),
    ]


class InitialCondition(AbstractAnalysis):
    """
    Class for initial condition resources : anything from which a model run can be performed.
    """

    _footprint = dict(
        info="Initial condition",
        attr=dict(
            kind=dict(
                values=["initial_condition", "ic", "starting_point"],
                remap=dict(autoremap="first"),
            ),
        ),
    )

    @property
    def term(self):
        """Fake term for duck typing."""
        return Time(0)

    @property
    def realkind(self):
        return "ic"

    def olive_basename(self):
        """OLIVE specific naming convention."""
        logger.warning(
            "The member number is only known by the provider, so the generic historic name is returned."
        )
        return "ICMSH" + self.model[:4].upper() + "+" + self.term.fmthour

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return "ICFC_(memberfix:member)"


class Historic(GeoFlowResource):
    """
    Class for historical state of a model (e.g. from a forecast).
    """

    _footprint = [
        term_deco,
        dict(
            info="Historic forecast file",
            attr=dict(
                kind=dict(
                    values=["historic", "modelstate"],
                    remap=dict(modelstate="historic"),
                ),
                subset=dict(
                    # Dummy argument but avoid priority related messages with footprints
                    info="With Historical files, leave subset empty...",
                    optional=True,
                    values=[
                        None,
                    ],
                ),
                nativefmt=dict(
                    values=["fa", "grib", "lfi", "netcdf", "unknown", "nc"],
                    remap=dict(nc="netcdf"),
                    default="fa",
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "historic"

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        if self.model in ("mfwam", "hycom"):
            prefix = "(prefix:modelkey)"
            midfix = ""
        else:
            prefix = "(icmshfix:modelkey)"
            midfix = "(histfix:igakey)"
        termfix = "(termfix:modelkey)"
        suffix = "(suffix:modelkey)"

        if self.geometry.lam and re.match(
            "testms1|testmp1|testmp2", self.geometry.area
        ):
            suffix = ".r" + archive_suffix(self.model, self.cutoff, self.date)

        if self.model == "mocage":
            prefix = "HM"
            midfix = self.geometry.area
            if self.nativefmt == "netcdf":
                suffix = ".nc"

        return prefix + midfix + termfix + suffix

    def olive_basename(self):
        """OLIVE specific naming convention."""
        if self.model == "mesonh":
            return ".".join(
                (
                    self.model.upper(),
                    self.geometry.area[:4].upper() + "+" + self.term.fmthour,
                    self.nativefmt,
                )
            )
        else:
            return "ICMSH" + self.model[:4].upper() + "+" + self.term.fmthour

    def _geo2basename_info(self, add_stretching=True):
        """Return an array describing the geometry for the Vortex's name builder."""
        if (
            isinstance(self.geometry, CurvlinearGeometry)
            and self.model == "hycom"
        ):
            # return the old naming convention for surges restart files
            lgeo = [self.geometry.area, self.geometry.rnice]
            return lgeo
        else:
            return super()._geo2basename_info(add_stretching=add_stretching)


@namebuilding_insert("filtername", lambda s: s.subset)
class HistoricSubset(GeoFlowResource):
    """
    Class for a subset of the historical state of a model (e.g. from a forecast).
    """

    _footprint = [
        term_deco,
        dict(
            info="Subset of an historic forecast file",
            attr=dict(
                kind=dict(
                    values=["historic", "modelstate"],
                    remap=dict(modelstate="historic"),
                ),
                subset=dict(
                    info="The subset of fields contained in this data.",
                ),
                nativefmt=dict(
                    values=["fa", "grib", "lfi", "netcdf", "unknown", "nc"],
                    remap=dict(nc="netcdf"),
                    default="fa",
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "historic"


class BiasDFI(GeoFlowResource):
    """
    Class for some kind of DFI bias (please add proper documentation).
    """

    _footprint = [
        term_deco,
        dict(
            info="DFI bias file",
            attr=dict(
                kind=dict(
                    values=["biasdfi", "dfibias"],
                    remap=dict(dfibias="biasdfi"),
                ),
                nativefmt=dict(
                    values=["fa"],
                    default="fa",
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "biasdfi"

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return "BIASDFI+{:04d}".format(self.term.hour)

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return "BIASDFI{:s}+{:04d}".format(
            self.model[:4].upper(), self.term.hour
        )
