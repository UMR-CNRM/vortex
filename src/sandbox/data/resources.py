#!/bin/env python
# -*- coding:Utf-8 -*-

from vortex.autolog import logdefault as logger

from vortex.data.resources import Resource
from vortex.data.flow import FlowResource

from vortex.syntax.stdattrs import a_model, a_cutoff
from vortex.syntax.stdattrs import cutoff
from vortex.syntax.cycles import cy36t1
from vortex.syntax.priorities import top
 

class Analysis(FlowResource):
    
    _footprint = dict(
        info = 'Atmospheric Analysis',
        attr = dict(
            kind = dict(
                values = [ 'analysis', 'analyse', 'atm_analysis' ]
            )
        ),
        only = dict(
            cycles = [ cy36t1 ]
        )
    )
    
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
                remap = dict( overflow = 'douze', treize = 'overflow' )
            ),
            kind = dict(
                values = [ 'test', 'simpletest', 'simple' ]
            )
        ),
        priority = dict(
            level = top.OLIVE
        ),
        only = dict(
            cycles = [ cy36t1 ]
        )
    ) ]

    def __init__(self, *args, **kw):
        logger.debug('SimpleTest resource init %s', self)
        super(SimpleTest, self).__init__(*args, **kw)

    def realkind(self):
        return 'simpletest'

    def zozo(self):
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
        only = dict(
            cycles = [ cy36t1 ]
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('SimpleTest resource init %s', self)
        super(Parasite, self).__init__(*args, **kw)

    def realkind(self):
        return 'simple'

    def zozo(self):
        return 'Gnark Gnark Gnark'
