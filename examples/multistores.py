#!/bin/env python
# -*- coding:Utf-8 -*-

import vortex
from vortex.data import geometries
from vortex.tools.date import Date

import common.data
import olive.data
import gco.data
import gco.syntax


t = vortex.ticket()
t.info()

g = t.glove
e = t.env
sh = t.system()
sh.cd(e.HOME + '/tmp/rundir')

print t.line

print t.prompt, sh.pwd()

print t.line

prvin  = vortex.toolbox.provider(suite='oper', vapp='arpege')
prvout = vortex.toolbox.provider(experiment='A001', block='canari', namespace='multi.olive.fr')

fpenv = vortex.toolbox.defaults(
    model='arpege',
    geometry = geometries.getbyname('globalsp'),
    date=Date('2013050100'),
    cutoff='production',
)

print t.prompt, fpenv()

a = vortex.toolbox.rh(
    provider=prvin,
    kind='analysis',
    local='ICMSHFCSTINIT',
)

print t.line, a.idcard(), t.line

print 'GET', a.location(), '...', a.get()

print t.line

sh.dir(output=False)

a.provider = prvout

print t.line, a.idcard()

print t.line

print t.prompt, 'Duration time =', t.duration()

print t.line

print 'PUT', a.location(), '...', a.put()

print t.prompt, 'Duration time =', t.duration()

print t.line
