"""
Resources needed to build the Ensemble Data Assimilation system.
"""

from bronx.fancies import loggers

from vortex.data.flow import GeoFlowResource
from .assim import _BackgroundErrorInfo
from vortex.syntax.stdattrs import term_deco
from vortex.syntax.stddeco import namebuilding_insert
from ..syntax.stdattrs import gvar

#: Automatic export off
__all__ = []

logger = loggers.getLogger(__name__)


@namebuilding_insert(
    "geo", lambda s: s._geo2basename_info(add_stretching=False)
)
class RawFiles(GeoFlowResource):
    """Input files for wavelet covariances estimation. To be removed soon."""

    _footprint = [
        term_deco,
        gvar,
        dict(
            info="Input files for wavelet covariances estimation",
            attr=dict(
                kind=dict(
                    values=["rawfiles"],
                ),
                nativefmt=dict(
                    values=["rawfiles", "unknown"],
                ),
                gvar=dict(default="aearp_rawfiles_t[geometry:truncation]"),
                ipert=dict(
                    type=int,
                    optional=True,
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return self.kind

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return "RAWFILEP(memberfix:member)+{:s}.{:d}".format(
            self.term.fmthour, self.geometry.truncation
        )

    def olive_basename(self):
        """OLIVE specific naming convention."""
        raise NotImplementedError()

    def gget_basename(self):
        """GGET specific naming convention."""
        if self.ipert is None:
            raise ValueError("ipert is mandatory with the GCO provider")
        return dict(suffix=".{:03d}.tar".format(self.ipert))


@namebuilding_insert(
    "geo", lambda s: s._geo2basename_info(add_stretching=False)
)
class RandBFiles(GeoFlowResource):
    """Input files for wavelet covariances estimation."""

    _footprint = [
        term_deco,
        gvar,
        dict(
            info="Input files for wavelet covariances estimation",
            attr=dict(
                kind=dict(
                    values=["randbfiles", "famembers"],
                    remap=dict(autoremap="first"),
                ),
                nativefmt=dict(
                    values=["fa", "unknown"],
                ),
                gvar=dict(default="aearp_randb_t[geometry:truncation]"),
                ipert=dict(
                    type=int,
                    optional=True,
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "randbfiles"

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return "famember(memberfix:member)+{:s}.{:d}".format(
            self.term.fmthour, self.geometry.truncation
        )

    def olive_basename(self):
        """OLIVE specific naming convention."""
        raise NotImplementedError()

    def gget_basename(self):
        """GGET specific naming convention."""
        if self.ipert is None:
            raise ValueError("ipert is mandatory with the GCO provider")
        return dict(suffix=".{:03d}.{}".format(self.ipert, "fa"))


class InflationFactor(_BackgroundErrorInfo):
    """
    Inflation factor profiles.
    """

    _footprint = dict(
        info="Inflation factor profiles",
        attr=dict(
            kind=dict(
                values=["infl_factor", "infl", "inflation_factor"],
                remap=dict(autoremap="first"),
            ),
            gvar=dict(default="inflation_factor"),
            nativefmt=dict(
                values=["ascii"],
                default="ascii",
            ),
            term=dict(optional=True, default=3),
        ),
    )

    @property
    def realkind(self):
        return "inflation_factor"

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return self.realkind

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return self.realkind
