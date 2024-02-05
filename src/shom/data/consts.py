"""
Specific SHOM "genv" resources
"""

from bronx.fancies import loggers

from gco.syntax.stdattrs import gdomain
from common.data.consts import GenvModelGeoResource, GenvModelResource

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)

# %% Constants


class Hycom3dConsts(GenvModelResource):
    """Class for the hycom3d non geographic constants tar file"""

    _footprint = [
        dict(
            info="Hycom3d constants tar file",
            attr=dict(
                pack=dict(values=["naming"]),
                gvar=dict(default="[model]_[pack]_[rank]_tar"),
                rank=dict(type=int),
                model=dict(values=["hycom3d"])
            ),
        )
    ]

    @property
    def realkind(self):
        return "hycom3d_consts"


class Hycom3dGeoConsts(GenvModelGeoResource):
    """Class for the hycom3d geographic constants tar file"""

    _footprint = [
        gdomain,
        dict(
            info="Hycom3d geographic constants tar file",
            attr=dict(
                pack=dict(values=[
                    "nest", "regional", "tide", "run",
                    "postprod", "savefield", "split"]),
                gvar=dict(default="[model]_[pack]_[gdomain]_[rank]_tar"),
                rank=dict(type=int),
                model=dict(values=["hycom3d"])
            ),
        )
    ]

    @property
    def realkind(self):
        return "hycom3d_geo_consts"
