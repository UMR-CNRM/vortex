#!/bin/env python
# -*- coding:Utf-8 -*-

import vortex
import vortex.data
from vortex.data.geometries import SpectralGeometry
from vortex.syntax import footprint
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

print t.prompt, sh.pwd

prvin  = vortex.toolbox.provider(suite='oper', vapp='arpege')
prvout = vortex.toolbox.provider(experiment='A001', block='canari', namespace='open.meteo.fr')

print t.line

fpenv = footprint.envfp(
    model='arpege',
    geometry = SpectralGeometry(id='Current op', area='france', truncation=798, lam=False),
    date=Date('2013050100'),
    cutoff='production',
)

print t.prompt, fpenv()

print t.line

a = vortex.toolbox.rh(
    provider=prvin,
    kind='analysis',
    local='ICMSHFCSTINIT',
)

print t.line, a.idcard()

print 'GET:', a.get()

print t.line

sh.dir(output=False)

a.provider = prvout

print t.line, a.idcard()

print t.line

print t.prompt, 'Duration time =', t.duration()

print t.line

print 'PUT:', a.put()

print t.prompt, 'Duration time =', t.duration()

print t.line

vortex.exit()
