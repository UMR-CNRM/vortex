# -*- coding: utf-8 -*-

"""
Promethee gridfiles
"""
from __future__ import print_function, absolute_import, unicode_literals, division
from common.data.gridfiles import TimePeriodGridPoint
from promethee.syntax.stdattrs import param_deco, step_deco

#: No automatic export
__all__ = []


class PrometheeGridPoint(TimePeriodGridPoint):
    """
    GridPoint file containing all the terms (with a fixed step) of a single
    weather parameter of a single run.

    This kind of GridPoint file is the result of a pre-processing task in the
    Promethee flow, where usual GridPoint files (from other models) are processed:

    * weather parameter extracted,
    * terms concatenated,
    * accumulations calculated,
    * grid transformed and adapted if necessary,
    * etc.

    Inheritance:

    * :class:`common.data.gridfiles.TimePeriodGridPoint`

    Attrs:

    * kind (str) : The resource's kind. Among 'gridpoint' and 'promethee_gridpoint'.
    * model (str) : The model's name (from a source code perspective).
      Must be 'promethee'.
    * cutoff (str) : The cutoff's type of the generating process.
    * origin (str) : Describes where the data originaly comes from.
      Must be 'post' (stands for 'post-processing').
    * geometry (:class:`vortex.data.geometries.HorizontalGeometry`) : The resource's
      horizontal geometry.
    * date (:class:`bronx.stdtypes.date.Date`) : The run of the resource's generating
      process.
    * begintime (:class:`bronx.stdtypes.date.Time`) : The resource's begin forecast term.
    * endtime (:class:`bronx.stdtypes.date.Time`) : The resource's end forecast term.
    * step (:class:`bronx.stdtypes.date.Time`) : The resource's fixed time step between two
      consecutive terms.
    * parameter (str) : The weather parameter name.
    * nativefmt (str) : The resource's storage format. Should be 'netcdf'.

    """

    _footprint = [
        param_deco,
        step_deco,
        dict(
            info = ("Gridpoint file with all the terms (fixed time step) of a " +
                    "single parameter of a single run."),
            attr = dict(
                kind = dict(
                    values = ["gridpoint", "promethee_gridpoint"],
                ),
                model = dict(
                    values = ["promethee"],
                ),
                origin = dict(
                    values = ["post"],
                ),
            )
        )
    ]
