#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

from resources import Resource
from geometries import HorizontalGeometry
from contents   import FormatAdapter
from vortex.syntax.stdattrs import model


class NoDateResource(Resource):
    _abstract = True


class ModelResource(NoDateResource):

    _abstract = True
    _footprint = [ model ]

    def vortex_pathinfo(self):
        """Default path informations (used by :class:`vortex.data.providers.Vortex`)."""
        return dict(
            model = self.model,
            fmt   = self.nativefmt,
        )


class StaticGeoResource(ModelResource):
    """A :class:`ModelResource` bound to a geometry."""

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
            model    = self.model,
            fmt      = self.nativefmt,
            geometry = self.geometry,
        )

    def footprint_export_geometry(self):
        """Return the ``geometry`` attribute as its id tag."""
        return self.geometry.tag
