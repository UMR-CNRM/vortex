#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

from resources import Resource
from geometries import SpectralGeometry
from vortex.syntax.stdattrs import model


class NoDateResource(Resource):
    _abstract = True


class ModelResource(NoDateResource):

    _footprint = [ model ]
    _abstract = True

    def vortex_pathinfo(self):
        """Default path informations (used by :class:`vortex.data.providers.Vortex`)."""
        return dict(
            model = self.model,
            nativefmt = self.nativefmt
        )


class StaticResource(ModelResource):

    _footprint = dict(
        attr = dict(
            geometry = dict(
                type = SpectralGeometry,
            )
        )
    )
    _abstract = True

    def vortex_pathinfo(self):
        """Default path informations (used by :class:`vortex.data.providers.Vortex`)."""
        return dict(
            model = self.model,
            nativefmt = self.nativefmt,
            geometry = self.geometry,
        )
