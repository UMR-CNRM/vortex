#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from .resources  import Resource
from .geometries import hgeometry_deco
from .contents   import FormatAdapter
from vortex.syntax.stdattrs import model_deco

#: No automatic export
__all__ = []


class StaticResource(Resource):

    _abstract = True
    _footprint = dict(
        attr = dict(
            kind = dict(
                info        = "The resource's kind.",
                doc_zorder  = 90,
            ),
        )
    )


class StaticGeoResource(StaticResource):
    """A :class:`ModelResource` bound to a geometry."""

    _abstract = True
    _footprint = [
        hgeometry_deco,
        dict(
            attr = dict(
                clscontents = dict(
                    default = FormatAdapter,
                ),
            )
        )
    ]


class ModelResource(StaticResource):

    _abstract = True
    _footprint = [ model_deco ]


class ModelGeoResource(ModelResource):
    """A :class:`ModelResource` bound to a geometry."""

    _abstract = True
    _footprint = [
        hgeometry_deco,
        dict(
            attr = dict(
                clscontents = dict(
                    default = FormatAdapter,
                ),
            )
        )
    ]
