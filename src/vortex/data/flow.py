#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []


from .resources  import Resource
from .geometries import HorizontalGeometry
from .contents   import FormatAdapter

from vortex.syntax.stdattrs import model, date, cutoff


class FlowResource(Resource):
    """Abstract resource bound to a model, a date and a cutoff."""

    _abstract = True
    _footprint = [model, date, cutoff]

    def vortex_pathinfo(self):
        """Default path informations (used by :class:`vortex.data.providers.Vortex`)."""
        return dict(
            nativefmt = self.nativefmt,
            model     = self.model,
            date      = self.date,
            cutoff    = self.cutoff,
        )


class GeoFlowResource(FlowResource):
    """Class which is a :class:`FlowResource` bound to a geometry."""

    _abstract = True
    _footprint = dict(
        attr = dict(
            geometry = dict(
                type = HorizontalGeometry,
            ),
            clscontents = dict(
                default = FormatAdapter,
            ),
        )
    )

    def vortex_pathinfo(self):
        """Default path informations (used by :class:`vortex.data.providers.Vortex`)."""
        return dict(
            nativefmt = self.nativefmt,
            model     = self.model,
            date      = self.date,
            cutoff    = self.cutoff,
            geometry  = self.geometry
        )

    def footprint_export_geometry(self):
        """Return the ``geometry`` attribute as its id tag."""
        return self.geometry.tag
