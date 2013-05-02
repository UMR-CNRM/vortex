#!/bin/env python
# -*- coding:Utf-8 -*-

import vortex

t = vortex.ticket()
t.warning()

from vortex.syntax.footprint import Footprint
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

print t.line

print R01.footprint(), R01.footprint().as_dict(), "\n"

print t.line

print R02.footprint(), R02.footprint().as_dict(), "\n"

print t.line

rfp = R02.footprint()
print rfp.info, rfp.only

print t.line

print t.prompt, 'Duration time =', t.duration()

print t.line

vortex.exit()
