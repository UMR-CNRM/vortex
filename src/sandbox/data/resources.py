#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.data.resources import Resource

import common.data.modelstates
from vortex.syntax.stdattrs import a_model, a_cutoff, cutoff


class Analysis(common.data.modelstates.Analysis):
    _footprint = dict(
        info = 'Atmospheric Analysis',
        attr = dict(
            model = dict(
                values = [ 'robin' ]
            )
        ),
    )

    @property
    def realkind(self):
        return 'coucou'


class SimpleTest(Resource):

    _footprint = [ cutoff, dict(
        info = 'The test resource',
        attr = dict(
            bigmodel = a_model,
            foo = dict(
                type = str,
                optional = True,
                values = [ 'deux', 'six', 'douze' ],
                remap = dict(
                    overflow = 'douze',
                    treize = 'overflow'
                )
            ),
            kind = dict(
                values = [ 'test', 'simpletest', 'simple' ]
            )
        ),
        priority = dict(
            level = footprints.priorities.top.OLIVE
        ),
    ) ]

    def __init__(self, *args, **kw):
        logger.debug('SimpleTest resource init %s', self.__class__)
        super(SimpleTest, self).__init__(*args, **kw)

    def xtest(self):
        return 'Boooooooohhh'


class Parasite(Resource):

    _footprint = dict(
        info = 'Insidious parasite resource',
        attr = dict(
            cutoff = a_cutoff,
            bigmodel = a_model,
            foo = dict(
                type = str,
                optional = True,
                values = [ 'deux', 'six', 'douze' ],
            ),
            kind = dict(
                values = [ 'simple' ]
            )
        ),
        priority = dict(
            level = footprints.priorities.top.OPER
        ),
    )

    def __init__(self, *args, **kw):
        logger.debug('SimpleTest resource init %s', self.__class__)
        super(Parasite, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'simple'

    def xtest(self):
        return 'Gnark Gnark Gnark'
