#!/bin/env python
# -*- coding: utf-8 -*-

import vortex
from vortex import sessions, toolbox
import common.data
import olive.data

t = sessions.ticket()
t.warning()

cr = vortex.data.providers.catalog()

ctx = t.context

ctx.system.cd(ctx.env.tmpdir + '/rundir')

print t.prompt, ctx.system.getcwd()

print t.line

provider_op = toolbox.provider(suite='oper', namespace='[suite].archive.fr', igakey='arpege')

bcor = toolbox.rh(
    provider = provider_op,
    kind = 'bcor',
    satbias='ssmi',
    local = 'bcor_[satbias].dat',
    date='2012112812',
    cutoff='assim',
    model='arpege',
)

print t.line
print bcor.idcard()

print t.line
print bcor.locate()

#print t.line
#print cr.track.alldump()

print t.line
print bcor.check()

print t.line
print bcor.get()

print t.line
print t.prompt, ctx.system.getcwd()
ctx.system.dir(bcor.container.localpath())

print t.line
print t.prompt, 'Duration time =', t.duration()
