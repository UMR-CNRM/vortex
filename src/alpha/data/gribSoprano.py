#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies           import loggers

import footprints

from vortex.syntax.stdattrs import model_deco, date_deco, term_deco, nativefmt_deco, member
from vortex.syntax.stddeco import namebuilding_insert
from vortex.data.geometries import hgeometry_deco
from vortex.data.resources	import Resource



#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)

member_deco = footprints.DecorativeFootprint(
    member,
    decorator = [namebuilding_insert('member',
                                     lambda self: 'm' if self.member is None else 'm' + str(self.member),
                                     none_discard=True, setdefault=True), ])

class GribSoprano(Resource):
    """	ressource pour les GRIBS sur soprano """

    _footprint = [
	model_deco,
	date_deco,
	term_deco,
	nativefmt_deco,
	hgeometry_deco,
	member_deco,
        dict(
            attr = dict(
                kind = dict(
                    values = ['gribSoprano'],
                ),
		model = dict(
		    values = ['eps','pc', 'ifs']
		)
            )
        )
    ]

    @property
    def realkind(self):
        return 'gribSoprano'

