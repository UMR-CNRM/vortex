#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Status : OK (v0.6.21)

import vortex
import vortex.data
import common.algo

t = vortex.ticket()
t.warning()

g = t.glove
e = t.env
sh = t.system()
sh.cd(e.HOME + '/tmp/rundir')

tb = vortex.toolbox

print t.line

script = tb.rh(remote=g.siteroot + '/examples/tmp/test.sh', file='test.sh', rawopts='coucou', language=e.trueshell())

print script.idcard()

print t.line

print t.prompt, "Get resource... ", script.get()

print t.line

x = tb.component(engine='launch', interpreter=script.resource.language)

print t.prompt, x
print t.prompt, x.as_dict()
print t.prompt, script.container.localpath()

print t.line

x.run(script)

print t.line

x = tb.component(engine='blind')

print t.prompt, x
print t.prompt, x.as_dict()

print t.line

x.run(script)

print t.line

x = tb.component(engine='parallel')

print t.prompt, x
print t.prompt, x.as_dict()

e.vortex_debug_env = True

print t.line

x.run(script, mpiopts=dict(n=2))

print t.line

