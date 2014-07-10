#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import vortex
from vortex.data.geometries import SpectralGeometry

import common.data
import iga.data

t = vortex.ticket()
t.warning()

ctx = t.context

ctx.system.cd(ctx.env.tmpdir + '/rundir')

print t.prompt, ctx.system.pwd()

print t.line

spgeo = SpectralGeometry(id='Current op', area='france', truncation=798, stretching=2.4, lam=False)

provider_op = vortex.toolbox.provider(suite='dbl', namespace='[suite].inline.fr', igakey='arpege')
provider_vx = vortex.toolbox.provider(experiment='DBLE', namespace='vortex.cache.fr', block='canari')

a = vortex.toolbox.rh(
    provider=provider_op,
    kind='analysis',
    local='analysis_op_[date::ymdh]',
    geometry=spgeo,
    date='20130501T18',
    cutoff='assim',
    model='arpege',
)

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

print t.line
