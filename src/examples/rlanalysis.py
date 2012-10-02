#!/bin/env python
# -*- coding:Utf-8 -*-

from vortex import sessions, toolbox

from vortex.data.geometries import SpectralGeometry

import common.data
import olive.data

t = sessions.ticket()
t.warning()

ctx = t.context

ctx.system.cd(ctx.env.tmpdir + '/rundir')

print t.prompt, ctx.env.pwd

print t.line

spgeo = SpectralGeometry(id='Current op', area='france', truncation=798, stretching=24)

rh=toolbox.rload(
    namespace='oper.archive.fr',
    suite='oper',
    igakey='arpege',
    role = 'Analysis',
    kind = 'analysis',
    local = 'analysis_op_[date::ymdh]',
    geometry=spgeo,
    date=('2012060500', '2012060512'),
    cutoff='assim',
    model='arpege',
)

for r in rh:
    print t.line, r.idcard()
    r.get()


print t.prompt, 'Duration time =', t.duration()


rh=toolbox.rload(
    namespace='olive.archive.fr',
    experiment='9A0Q',
    role = 'Analysis',
    kind = 'analysis',
    local = 'analysis_xp_[date::ymdh]',
    block='canari',
    geometry=spgeo,
    date='2012060500',
    cutoff='assim',
    model='arpege',
)

for r in rh:
    print t.line, r.idcard()
    r.get()

print t.line

ctx.system.dir()

print t.line

print t.prompt, 'Duration time =', t.duration()
