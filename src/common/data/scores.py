#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

from bronx.stdtypes.date import Time
import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.data.flow         import GeoFlowResource
from vortex.data.contents     import JsonDictContent
from vortex.syntax.stdattrs   import a_date, a_term
from vortex.data.geometries import HorizontalGeometry
from vortex.data.resources import Resource


class Score(GeoFlowResource):
    """
    Files produced to contain the scores values
    """

    _footprint = dict(
        info = 'Ensemble scores',
        attr = dict(
            kind = dict(
                values   = ['score'],
            ),
            clscontents = dict(
                default = JsonDictContent,
            ),
            nativefmt = dict(
                values   = ['json'],
                optional = True,
            ),
            term = a_term,
            score = dict(
                type   = str,
            ),
            parameter = dict(
                type   = str,
            ),
            level = dict(
                type   = str,
            ),
            event = dict(
                optional = True,
                type   = str,
            ),
        )
    )

    @property
    def realkind(self):
        return self.score

    def basename_info(self):
        """Generic information for names fabric."""
        radsocle = self.realkind + '_' + self.parameter + self.level
        if self.event is not None: radsocle += ('_' + self.event)
        return dict(
            radical = radsocle,
            fmt     = self.nativefmt,
            geo     = self.geometry.area,
            term    = self.term,
            src     = self.model,
        )


class GraphicScore(Resource):
    """
    Files produced to contain the scores graphs
    """

    _footprint = dict(
        info = 'Ensemble scores graphs',
        attr = dict(
            date = a_date,
            kind = dict(
                values   = ['score'],
            ),
            geometry = dict(
                type = HorizontalGeometry,
            ),
            nativefmt = dict(
                values   = ['pdf'],
                optional = True,
            ),
            score = dict(
                type   = str,
            ),
            calcul = dict(
                type   = str,
            ),
            parameter = dict(
                type   = str,
            ),
            level = dict(
                type   = str,
            ),
            term = dict(
                type     = Time,
                optional = True,
            )
        )
    )

    @property
    def realkind(self):
        return self.calcul + '_' + self.score

    def basename_info(self):
        """Generic information for names fabric."""
        dico = dict(
            radical = self.realkind + '_' + self.parameter + self.level,
            fmt     = self.nativefmt,
            geo     = self.geometry.area,
        )
        if hasattr(self, 'term'):
            dico['term'] = self.term
        return dico

    def vortex_pathinfo(self):
        """Default path informations (used by :class:`vortex.data.providers.Vortex`)."""
        return dict(
            nativefmt = self.nativefmt,
            date      = self.date,
            geometry  = self.geometry
        )

    def footprint_export_geometry(self):
        """Return the ``geometry`` attribute as its id tag."""
        return self.geometry.tag


class Obset(Resource):
    """
    Files produced to contain the extracted obs sets.
    """

    _footprint = dict(
        info = 'Observation sets',
        attr = dict(
            kind = dict(
                values   = ['obset'],
            ),
            date = a_date,
            geometry = dict(
                type = HorizontalGeometry,
            ),
            nativefmt = dict(
                values   = ['ascii'],
                optional = True,
            ),
            parameter = dict(
                type   = str,
            ),
            window = dict(
                type   = int,
            ),
        )
    )

    @property
    def realkind(self):
        return 'obset'

    def basename_info(self):
        """Generic information for names fabric."""
        return dict(
            radical = self.realkind + '_' + self.parameter + '_' + str(self.window),
            fmt     = self.nativefmt,
            geo     = self.geometry.area,
        )

    def vortex_pathinfo(self):
        """Default path informations (used by :class:`vortex.data.providers.Vortex`)."""
        return dict(
            nativefmt = self.nativefmt,
            date      = self.date,
            geometry  = self.geometry
        )

    def footprint_export_geometry(self):
        """Return the ``geometry`` attribute as its id tag."""
        return self.geometry.tag
