#!/bin/env python
# -*- coding:Utf-8 -*-

from vortex import sessions, toolbox
import vortex.data
import common.data
import iga.data
from vortex.data.geometries import SpectralGeometry

t = sessions.ticket()
t.warning()

cr = vortex.data.providers.catalog()
cr.track = True

ctx = t.context

ctx.system.cd(ctx.env.tmpdir + '/rundir')

print t.prompt, ctx.env.pwd

print t.line

spgeo = SpectralGeometry(id='Current op', area='france', truncation=798, stretching=24)

provider_op = toolbox.provider(suite='dbl', namespace='[suite].inline.fr', igakey='arpege')
provider_vx = toolbox.provider(experiment='DBLE', namespace='vortex.cache.fr', block='canari')

a = toolbox.rh(
    provider = provider_op,
    kind = 'analysis',
    local = 'analysis_op_[date::ymdh]',
    geometry=spgeo,
    date='2012062900',
    cutoff='assim',
    model='arpege',
)

#print cr.track.toprettyxml(indent='    ')

print t.line
print a.idcard()

print t.line
print a.locate()

a.provider = provider_vx

print t.line
print a.idcard()

print t.line
print a.locate()

print t.line

print t.prompt, 'Duration time =', t.duration()
