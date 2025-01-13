"""
Abstract class for any flow-dependant "Resource".

By "flow-dependant", we mean a "Resource" that has to be described by ``model``,
``date`` and ``cutoff`` attributes. See :class:`FlowResource`

The :class:`GeoFlowResource` abstract class is to be used for flow-dependant
resources associated with an horizontal geometry.
"""

from .resources import Resource
from .geometries import hgeometry_deco
from .contents import FormatAdapter

from vortex.syntax.stdattrs import (
    model_deco,
    date_deco,
    dateperiod_deco,
    cutoff_deco,
    term_deco,
)
from vortex.syntax.stddeco import namebuilding_insert

#: No automatic export
__all__ = []


class FlowResource(Resource):
    """Abstract resource bound to a model, a date and a cutoff."""

    _abstract = True
    _footprint = [model_deco, date_deco, cutoff_deco]


@namebuilding_insert("radical", lambda s: s.nickname)
class UnknownFlow(FlowResource):
    _footprint = [
        term_deco,
        dict(
            info="Unknown assumed NWP Flow-Resource (development only !)",
            attr=dict(
                unknownflow=dict(
                    info="Activate the unknown flow resource", type=bool
                ),
                term=dict(
                    optional=True,
                ),
                nickname=dict(
                    info="The string that serves the purpose of Vortex's basename radical",
                    optional=True,
                    default="unknown",
                ),
                clscontents=dict(default=FormatAdapter),
            ),
            fastkeys={"unknownflow"},
        ),
    ]

    _extension_remap = {
        k: None for k in ("auto", "autoconfig", "foo", "unknown")
    }

    def olive_basename(self):
        target = self.nickname
        if self.term is not None:
            target += "+" + self.term.fmth
        return target


class GeoFlowResource(FlowResource):
    """Class which is a :class:`FlowResource` bound to a geometry."""

    _abstract = True
    _footprint = [
        hgeometry_deco,
        dict(
            attr=dict(
                clscontents=dict(
                    default=FormatAdapter,
                ),
            )
        ),
    ]


class PeriodFlowResource(Resource):
    """Abstract resource bound to a model, a begindate, enddate and a cutoff."""

    _abstract = True
    _footprint = [model_deco, dateperiod_deco, cutoff_deco]

    _footprint = [
        model_deco,
        dateperiod_deco,
        cutoff_deco,
        dict(
            attr=dict(
                cutoff=dict(
                    optional=True,
                ),
            )
        ),
    ]


class GeoPeriodFlowResource(PeriodFlowResource):
    """Class which is a :class:`PeriodFlowResource` bound to a geometry."""

    _abstract = True
    _footprint = [
        hgeometry_deco,
        dict(
            attr=dict(
                clscontents=dict(
                    default=FormatAdapter,
                ),
            )
        ),
    ]
