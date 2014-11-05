#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import footprints

from vortex.autolog import logdefault as logger

from vortex.data.resources import Resource
from vortex.data.flow import FlowResource

import common.data.modelstates
from vortex.syntax.stdattrs import a_model, a_date, a_cutoff, cutoff
from vortex.syntax.cycles import cy38t1_op1, cy38t1_op2, cy40_op1
from vortex.tools.date import Date


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


class CheckOnlyBase(Resource):

    _abstract = True
    _footprint = dict(
        info = 'Some Test Resource for cycle selection',
        attr = dict(
            model = a_model,
            date = a_date,
            kind = dict(
                values = [ 'onlyselect' ]
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('CheckOnlyBase resource init %s', self.__class__)
        super(CheckOnlyBase, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'onlyselect'

    def xtest(self):
        return 'Check Only Base'


class CheckOnlyCycle38(CheckOnlyBase):

    _footprint = dict(
        only = dict(
            cycle = [ cy38t1_op1, cy38t1_op2 ]
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('CheckOnlyBase resource init %s', self.__class__)
        super(CheckOnlyBase, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'only38'

    def xtest(self):
        return 'Check Cycle 38'


class CheckOnlyCycle40(CheckOnlyBase):

    _footprint = dict(
        only = dict(
            cycle = cy40_op1,
            after_date = Date(2012, 5, 1, 18)
        )
    )

    @property
    def realkind(self):
        return 'only40'

    def xtest(self):
        return 'Check Cycle 40'
