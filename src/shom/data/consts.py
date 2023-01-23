"""
Hycom3d files
"""

from gco.syntax.stdattrs import gdomain
from common.data.consts import GenvModelGeoResource, GenvModelResource

__all__ = []


# %% Constants

class Hycom3dConsts(GenvModelResource):
    """TODO Class Documentation."""

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
    """TODO Class Documentation."""

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
