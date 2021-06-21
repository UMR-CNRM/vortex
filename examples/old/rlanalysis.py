# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import vortex

from vortex.data.geometries import GaussGeometry

import common.data
import olive.data

t = vortex.ticket()
t.warning()

ctx = t.context

ctx.system.cd(ctx.env.tmpdir + '/rundir')

print(t.prompt, ctx.system.pwd())

print(t.line)

spgeo = GaussGeometry(id='Current op', area='france', truncation=798, stretching=2.4, lam=False)

rh = vortex.toolbox.rload(
    namespace='oper.archive.fr',
    suite='oper',
    igakey='arpege',
    role = 'Analysis',
    kind = 'analysis',
    local = 'analysis_op_[date::ymdh]',
    geometry=spgeo,
    date=('20130501T00', '20130501T12'),
    cutoff='assim',
    model='arpege',
)

for r in rh:
    print(t.line, r.idcard())
    print('GET:', r.get())


print(t.line)

print(t.prompt, 'Duration time =', t.duration())

print(t.line)

rh = vortex.toolbox.rload(
    namespace='olive.archive.fr',
    experiment='9A0Q',
    role = 'Analysis',
    kind = 'analysis',
    local = 'analysis_xp_[date::ymdh]',
    block='canari',
    geometry=spgeo,
    date='20130501T00',
    cutoff='assim',
    model='arpege',
)

for r in rh:
    print(t.line, r.idcard())
    print('GET:', r.get())

print(t.line)

ctx.system.dir('analysis_*', output=False)

print(t.line)

print(t.prompt, 'Duration time =', t.duration())

print(t.line)
