#!/usr/bin/env python
# -*- coding:Utf-8 -*-

# Status : OK (v0.6.21)

import vortex
import vortex.data
import common.data
import common.algo
import olive.data
from vortex.data.geometries import SpectralGeometry
from vortex.tools import env, date

t = vortex.ticket()
t.warning()

g = t.glove
e = t.env
c = t.context

sh = t.system()

if sh.cd(e.HOME + '/tmp/rundir'):
    sh.rmglob('-rf', '*')

vortex.toolbox.defaults(
    date = date.today(),
    source='arpege',
    model='arome',
    cutoff='production',
    geometry=SpectralGeometry(id='Current op', area='frangp', resolution=2.5, runit='km'),
)

rl = vortex.toolbox.rload

inputs = (
    rl(
        kind='elscf',
        namespace='[suite].archive.fr',
        local='ELSCFAROME+[term::fmth]',
        suite='oper',
        term=(0, 3),
        igakey='arome',
        role='BoundaryCondition'
    ),
    rl(
        kind='elscf',
        remote='ELSCFAROME+0000',
        local='Inifile',
        term=0,
        role='InitialCondition'
    )
)


print t.line

for rh in inputs:
    for r in rh:
        print 'Get', r.location(), '...',
        print r.get()

rx = vortex.toolbox.rh(remote=g.siteroot + '/examples/tmp/test.sh',
                       file='test.sh', model='arpege', kind='ifsmodel')

print t.line

rx.get()

print t.line

x = vortex.toolbox.algo(kind='fclam', timestep=900, engine='parallel')

print t.prompt, 'Engine is', x

print t.line

x.run(rx, mpiopts=dict(n=2))

print t.line

