"""
Various resources needed to build ad Data Assimilmation system.
"""

from bronx.fancies import loggers
from bronx.stdtypes.date import Time

from vortex.data.flow import FlowResource, GeoFlowResource
from vortex.data.contents import JsonDictContent
from vortex.data.executables import Script
from vortex.syntax.stddeco import namebuilding_append, namebuilding_insert
from vortex.syntax.stdattrs import FmtInt, term_deco
from ..syntax.stdattrs import gvar

#: Automatic export off
__all__ = []

logger = loggers.getLogger(__name__)


@namebuilding_insert(
    "geo", lambda s: s._geo2basename_info(add_stretching=False)
)
class _BackgroundErrorInfo(GeoFlowResource):
    """
    A generic class for data in grib format related to the background error.
    """

    _abstract = True
    _footprint = [
        term_deco,
        gvar,
        dict(
            info="Background standard deviation",
            attr=dict(
                term=dict(optional=True, default=3),
                nativefmt=dict(
                    default="grib",
                ),
                gvar=dict(default="errgrib_t[geometry:truncation]"),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "bgstdinfo"


class BackgroundStdError(_BackgroundErrorInfo):
    """Background error standard deviation.

    stage:
        * unbal/vor: unbalanced variables fields
        * scr: obs. related fields
        * profile: full variables global and latitude bands horizontal averages
        * full: full variables fields

    origin:
        * ens: diagnosed from an ensemble
        * diag: diagnosed from randomized (a priori climatological) covariances

    """

    _footprint = dict(
        info="Background error standard deviation",
        attr=dict(
            kind=dict(
                values=["bgstderr", "bg_stderr", "bgerrstd"],
                remap=dict(autoremap="first"),
            ),
            stage=dict(
                optional=True,
                default="unbal",
                values=["scr", "vor", "full", "unbal", "profile"],
                remap=dict(vor="unbal"),
            ),
            origin=dict(
                optional=True,
                values=["ens", "diag"],
                default="ens",
            ),
            gvar=dict(default="errgrib_vor_monthly"),
            nativefmt=dict(
                values=["grib", "ascii"],
                default="grib",
            ),
        ),
    )

    @property
    def realkind(self):
        return "bgstderr"

    def namebuilding_info(self):
        """Generic information for names fabric, with radical = ``bcor``."""
        infos = super().namebuilding_info()
        infos["src"].append(self.stage)
        if self.stage != "scr":
            infos["src"].append(self.origin)
        return infos

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        if self.stage in ("unbal",):
            return "(errgribfix:igakey)"
        else:
            return "errgrib_" + self.stage

    def olive_basename(self):
        """OLIVE specific naming convention."""
        if self.stage in ("unbal",):
            return "errgribvor"
        else:
            return "sigma_b"

    def gget_basename(self):
        """GGET specific naming convention."""
        return dict(suffix=".m{:02d}".format(self.date.month))


@namebuilding_append("src", lambda s: s.variable)
class SplitBackgroundStdError(BackgroundStdError):
    """Background error standard deviation, for a given variable."""

    _footprint = dict(
        info="Background error standard deviation",
        attr=dict(
            variable=dict(
                info="Variable contained in this resource.",
            ),
            gvar=dict(default="errgrib_vor_[variable]_monthly"),
        ),
    )


class BackgroundErrorNorm(_BackgroundErrorInfo):
    """Background error normalisation data for wavelet covariances."""

    _footprint = [
        dict(
            info="Background error normalisation data for wavelet covariances",
            attr=dict(
                kind=dict(
                    values=["bgstdrenorm", "bgerrnorm"],
                    remap=dict(autoremap="first"),
                ),
                gvar=dict(default="srenorm_t[geometry:truncation]"),
            ),
        )
    ]

    @property
    def realkind(self):
        return "bgstdrenorm"

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return "srenorm.{!s}".format(self.geometry.truncation)

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return "srenorm.t{!s}".format(self.geometry.truncation)

    def archive_pathinfo(self):
        """Op Archive specific pathname needs."""
        return dict(
            nativefmt=self.nativefmt,
            model=self.model,
            date=self.date,
            cutoff=self.cutoff,
            arpege_aearp_directory="wavelet",
        )


@namebuilding_insert(
    "geo", lambda s: s._geo2basename_info(add_stretching=False)
)
class Wavelet(GeoFlowResource):
    """Background error wavelet covariances."""

    _footprint = [
        term_deco,
        gvar,
        dict(
            info="Background error wavelet covariances",
            attr=dict(
                kind=dict(
                    values=["wavelet", "waveletcv"],
                    remap=dict(autoremap="first"),
                ),
                gvar=dict(default="wavelet_cv_t[geometry:truncation]"),
                term=dict(optional=True, default=3),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "wavelet"

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return "wavelet.cv.{!s}".format(self.geometry.truncation)

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return "wavelet.cv.t{!s}".format(self.geometry.truncation)

    def archive_pathinfo(self):
        """Op Archive specific pathname needs."""
        return dict(
            nativefmt=self.nativefmt,
            model=self.model,
            date=self.date,
            cutoff=self.cutoff,
            arpege_aearp_directory=self.realkind,
        )


@namebuilding_insert(
    "geo", lambda s: s._geo2basename_info(add_stretching=False)
)
class RawControlVector(GeoFlowResource):
    """Raw Control Vector as issued by minimisation, playing the role of an Increment."""

    _footprint = dict(
        info="Raw Control Vector",
        attr=dict(
            kind=dict(
                values=["rawcv", "rcv", "increment", "minimcv"],
                remap=dict(autoremap="first"),
            ),
        ),
    )

    @property
    def realkind(self):
        return "rawcv"

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return "MININCR"


@namebuilding_insert(
    "geo", lambda s: s._geo2basename_info(add_stretching=False)
)
class InternalMinim(GeoFlowResource):
    """Generic class for resources internal to minimisation."""

    _abstract = True
    _footprint = dict(
        attr=dict(
            nativefmt=dict(
                values=["fa", "lfi", "grib"],
                default="fa",
            ),
            term=dict(
                type=Time,
                optional=True,
                default=Time(-3),
            ),
        )
    )

    def olive_suffixtr(self):
        """Return BR or HR specific OLIVE suffix according to geo streching."""
        return "HR" if self.geometry.stretching > 1 else "BR"


class StartingPointMinim(InternalMinim):
    """Guess as reprocessed by the minimisation."""

    _footprint = dict(
        info="Starting Point Output Minim",
        attr=dict(
            kind=dict(
                values=["stpmin"],
            ),
        ),
    )

    @property
    def realkind(self):
        return "stpmin"

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return "STPMIN" + self.olive_suffixtr()


class AnalysedStateMinim(InternalMinim):
    """Analysed state as produced by the minimisation."""

    _footprint = dict(
        info="Analysed Output Minim",
        attr=dict(
            kind=dict(
                values=["anamin"],
            ),
        ),
    )

    @property
    def realkind(self):
        return "anamin"

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return "ANAMIN" + self.olive_suffixtr()


class PrecevMap(FlowResource):
    """Map of the precondionning eigenvectors as produced by minimisation."""

    _footprint = dict(
        info="Prec EV Map",
        attr=dict(
            kind=dict(
                values=["precevmap"],
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
        return "precevmap"


@namebuilding_append("src", lambda s: str(s.evnum))
class Precev(FlowResource):
    """Precondionning eigenvectors as produced by minimisation."""

    _footprint = dict(
        info="Starting Point Output Minim",
        attr=dict(
            kind=dict(
                values=["precev"],
            ),
            evnum=dict(
                type=FmtInt,
                args=dict(fmt="03"),
            ),
        ),
    )

    @property
    def realkind(self):
        return "precev"


class IOassignScript(Script):
    """Scripts for IOASSIGN."""

    _footprint = [
        gvar,
        dict(
            info="Script for IOASSIGN",
            attr=dict(
                kind=dict(values=["ioassign_script"]),
                gvar=dict(default="ioassign_script_[purpose]"),
                purpose=dict(
                    info="The purpose of the script",
                    values=["merge", "create"],
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "ioassign_script"
