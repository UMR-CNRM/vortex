#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from .resources  import Resource
from .geometries import HorizontalGeometry, GaussGeometry, ProjectedGeometry
from .contents   import FormatAdapter
from vortex.syntax.stdattrs import model

#: No automatic export
__all__ = []


class NoDateResource(Resource):

    _abstract = True
    _footprint = dict(
        attr = dict(
            kind = dict(
                info        = "The resource's kind.",
                doc_zorder  = 90,
            ),
        )
    )


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
                info = "The resource's horizontal geometry.",
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

    def _geo2basename_info(self, add_stretching=True):
        """Return an array describing the geometry for the Vortex's name builder."""
        if isinstance(self.geometry, GaussGeometry):
            lgeo = [{'truncation': self.geometry.truncation}, ]
            if add_stretching:
                lgeo.append({'stretching': self.geometry.stretching})
        elif isinstance(self.geometry, ProjectedGeometry):
            lgeo = [self.geometry.area, self.geometry.rnice]
        else:
            lgeo = self.geometry.area  # Default: always defined
        return lgeo
