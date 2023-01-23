"""
Typical ressources for promethee use.
"""

from vortex.data.resources import Resource
from vortex.data.outflow import StaticResource
from vortex.data.geometries import hgeometry_deco
from vortex.syntax.stdattrs import model_deco, cutoff_deco
from promethee.syntax.stdattrs import promid_deco, version_deco, task_deco


#: No automatic export
__all__ = []


class PrometheeMask(StaticResource):
    """
    Static netcdf file containing raster representations of all the geographical
    areas covered by a promethee production, on multiple grids.

    Then, a PrometheeMask is like a dataset of ndarrays. Each ndarray is the
    representation (a binary matrix) on a given geometry (e.g. 'EURW1S100') and
    has the following dimensions :

    * latitude
    * longitude
    * id (i.e. geographical zone identifier, e.g. "Haute-Garonne").

    A mask is a static resource because it can be used ad vitam eternam, as long
    as its configuration does not change. That is the reason why a given mask (
    identified by its 'promid' attribute) is versioned : if its configuration changes,
    the version also changes, thus the Resource itself changes.

    Inheritance:

    * :class:`vortex.data.outflow.StaticResource`

    Attrs:

    * kind (str) : The resource's kind. Among 'promethee_mask' or 'mask'.
    * promid (str) : The Promethee production identifier.
    * version (str) : The version of the mask used. Usually it is the MD5 sum of
      the resource's configuration.
    * nativefmt (str) : The resource's storage format. Must be 'netcdf'.

    """

    _footprint = [
        promid_deco,
        version_deco,
        dict(
            info = "Promethee mask",
            attr = dict(
                kind    = dict(
                    values      = ["promethee_mask", "mask"]
                ),
                nativefmt = dict(
                    optional    = True,
                    values      = ["netcdf", ],
                    default     = "netcdf"
                )
            )
        )
    ]

    @property
    def realkind(self):
        return "mask"


class PrometheeGeoMask(PrometheeMask):
    """
    Static netcdf file containing raster representations of all the geographical
    areas covered by a promethee production, on multiple grids.

    Then, a PrometheeMask is like a dataset of ndarrays. Each ndarray is the
    representation (a binary matrix) on a given geometry (e.g. 'EURW1S100') and
    has the following dimensions :

    * latitude
    * longitude
    * id (i.e. geographical zone identifier, e.g. "Haute-Garonne").

    A mask is a static resource because it can be used ad vitam eternam, as long
    as its configuration does not change. That is the reason why a given mask (
    identified by its 'promid' attribute) is versioned : if its configuration changes,
    the version also changes, thus the Resource itself changes.

    Inheritance:

    * :class:`vortex.data.outflow.StaticGeoResource`

    Attrs:

    * kind (str) : The resource's kind. Among 'promethee_mask' or 'mask'.
    * promid (str) : The Promethee production identifier.
    * version (str) : The version of the mask used. Usually it is the MD5 sum of
      the resource's configuration.
    * nativefmt (str) : The resource's storage format. Must be 'netcdf'.

    """

    _footprint = [
        hgeometry_deco,
        dict(
            info = "Promethee mask (with geometry)",
            attr = dict(
                kind    = dict(
                    values      = ["promethee_geomask", "geomask"]
                )
            )
        )
    ]


class PrometheeNoDateBdpeResource(Resource):
    """Undated BDPE resource bound to a model and a cutoff."""

    _footprint = [
        model_deco,
        cutoff_deco,
        task_deco,
        version_deco,
        dict(
            info = ("Undated BDPE resource for Promethee usage. It is a resource " +
                    "that has version, model, and cutoff tags and is related to a specific task."),
            attr = dict(
                kind = dict(
                    values = ["bdpe"]
                ),
                model = dict(
                    values = ['promethee']
                ),
                nativefmt = dict(
                    values = ["tgz"],
                    default = "tgz"
                ),
            ),
        )
    ]

    @property
    def realkind(self):
        return 'bdpe'
