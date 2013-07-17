#!/bin/env python
# -*- coding:Utf-8 -*-

from vortex.autolog import logdefault as logger

from vortex.data.resources import Resource
from vortex.data.flow import FlowResource

from vortex.syntax.stdattrs import a_model, a_date, a_cutoff, cutoff
from vortex.syntax.cycles import cy37t1_op1, cy37t1_op2, cy38t1

from vortex.syntax.priorities import top
from vortex.tools.date import Date


class Analysis(FlowResource):
    
    _footprint = dict(
        info = 'Atmospheric Analysis',
        attr = dict(
            kind = dict(
                values = [ 'analysis', 'analyse', 'atm_analysis' ]
            )
        ),
    )

    @property
    def realkind(self):
        return 'analysis'

    def vortex_basename(self):
        return 'analysis'

    def olive_basename(self):
        return 'analyse'


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
            level = top.OLIVE
        ),
    ) ]

    def __init__(self, *args, **kw):
        logger.debug('SimpleTest resource init %s', self)
        super(SimpleTest, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'simpletest'

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
            level = top.OPER
        ),
    )

    def __init__(self, *args, **kw):
        logger.debug('SimpleTest resource init %s', self)
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
        logger.debug('CheckOnlyBase resource init %s', self)
        super(CheckOnlyBase, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'onlyselect'

    def xtest(self):
        return 'Check Only Base'


class CheckOnlyCycle37(CheckOnlyBase):

    _footprint = dict(
        only = dict(
            cycle = [ cy37t1_op1, cy37t1_op2 ]
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('CheckOnlyBase resource init %s', self)
        super(CheckOnlyBase, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'only37'

    def xtest(self):
        return 'Check Cycle 37'


class CheckOnlyCycle38(CheckOnlyBase):

    _footprint = dict(
        only = dict(
            cycle = cy38t1,
            after_date = Date(2012, 5, 1, 18)
        )
    )

    @property
    def realkind(self):
        return 'only38'

    def xtest(self):
        return 'Check Cycle 38'
