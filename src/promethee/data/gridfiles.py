#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Promethee gridfiles
"""
from __future__ import print_function, absolute_import, unicode_literals, division
from vortex.data.outflow import StaticResource
from common.data.gridfiles import TimePeriodGridPoint
from promethee.syntax.stdattrs import param_deco, version_deco, promid_deco, step_deco
from vortex.syntax.stddeco import namebuilding_insert

#: No automatic export
__all__ = []


class PrometheeGridPoint(TimePeriodGridPoint):
    """PrometheeGridPoint : GridPoint file containing all the terms (with a fixed
    step) of a single weather parameter of a single run.

    This kind of GridPoint file is the result of a pre-processing task in the
    Promethee flow, where usual GridPoint files (from other models) are processed :
        - weather parameter extracted,
        - terms concatenated,
        - accumulations calculated,
        - grid transformed and adapted if necessary,
        - etc.

    Inheritance:
        common.data.gridfiles.TimePeriodGridPoint

    Attrs:
        kind (str) : The resource's kind. Among 'gridpoint' and 'promethee_gridpoint'.
        model (str) : The model's name (from a source code perspective).
            Must be 'promethee'.
        cutoff (str) : The cutoff's type of the generating process.
        origin (str) : Describes where the data originaly comes from.
            Must be 'post' (stands for 'post-processing').
        geometry (vortex.data.geometries.HorizontalGeometry) : The resource's
            horizontal geometry.
        date (bronx.stdtypes.date.Datetime) : The run of the resource's generating
            process.
        begintime (bronx.stdtypes.date.Time) : The resource's begin forecast term.
        endtime (bronx.stdtypes.date.Time) : The resource's end forecast term.
        step (bronx.stdtypes.date.Time) : The resource's fixed time step between two
            consecutive terms.
        parameter (str) : The weather parameter name.
        nativefmt (str) : The resource's storage format. Should be 'netcdf'.
    """
    _footprint = [
        param_deco,
        step_deco,
        dict(
            info = "Gridpoint file with all the terms (fixed time step) of a single parameter of a single run.",
            attr = dict(
                kind = dict(
                    optional = False,
                    values = ["gridpoint", "promethee_gridpoint"],
                ),
                model = dict(
                    optional = False,
                    values = ["promethee"],
                ),
                origin = dict(
                    values = ["post"],
                ),
            )
        )
    ]


@namebuilding_insert("radical", lambda s: s.realkind)
class PrometheeMask(StaticResource):
    """PrometheeMask : Static netcdf file containing raster representations
    of all the geographical areas covered by a promethee production, on multiple
    grids.

    Then, a PrometheeMask is like a dataset of ndarrays. Each ndarray is the
    representation (a binary matrix) on a given geometry (e.g. 'EURW1S100') and
    has the following dimensions :
        - latitude
        - longitude
        - id (i.e. geographical zone identifier, e.g. "Haute-Garonne").

    A mask is a static resource because it can be used ad vitam eternam, as long
    as its configuration does not change. That is the reason why a given mask (
    identified by its 'promid' attribute) is versioned : if its configuration changes,
    the version also changes, thus the Resource itself changes.

    Inheritance:
        vortex.data.outflow.StaticResource

    Attrs:
        kind (str) : The resource's kind. Among 'promethee_mask' or 'mask'.
        promid (str) : The Promethee production identifier.
        version (str) : The version of the mask used. Usually it is the MD5 sum of
            the resource's configuration.
        nativefmt (str) : The resource's storage format. Must be 'netcdf'.
    """
    _footprint = [
        promid_deco,
        version_deco,
        dict(
            info = "Promethee mask",
            attr = dict(
                kind    = dict(
                    optional    = False,
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
