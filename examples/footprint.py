#!/bin/env python
# -*- coding:Utf-8 -*-

from vortex import sessions

t = sessions.ticket()
t.warning()

from vortex.syntax import Footprint
from vortex.data.resources import Resource
from vortex.syntax.stdattrs import a_model

class R01(Resource):
    
    _footprint = dict(
        info = 'test resource',
        attr = dict(
            model = a_model,
            foo = dict(
                type = str,
                optional = True,
                values = [ 'deux', 'six', 'douze' ],
                remap = dict( overflow = 'douze', treize = 'overflow' )
            ),
            kind = dict(
                values = [ 'test', 'r01' ]
            )
        ),
    )

    def realkind(self):
        return 'R01'
    
class R02(R01):
    
    _footprint = Footprint(
        nodefault = True,
        attr = dict(
            foo = dict( optional = False ),
            bidon = dict()
        )
    )

    def realkind(self):
        return 'R02'
    
    
print R01.footprint(), R01.footprint().asdict(), "\n"

print R02.footprint(), R02.footprint().asdict(), "\n"

rfp = R02.footprint()

print rfp.info, rfp.only
