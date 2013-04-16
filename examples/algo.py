#!/bin/env python
# -*- coding:Utf-8 -*-

# Status : OK (v0.6.21)

from vortex import sessions, toolbox
import vortex.data
import common.algo

t = sessions.ticket()
t.warning()

g = t.glove
e = t.env
sh = t.system()
sh.cd(e.HOME + '/tmp/rundir')

print t.line

script = toolbox.rh(remote=g.siteroot + '/examples/tmp/test.sh', file='test.sh', rawopts='coucou', language=e.trueshell())

print script.idcard()

print t.line

print t.prompt, "Get resource... ", script.get()

print t.line

x = toolbox.component(engine='launch', interpreter=script.resource.language)

print t.prompt, x
print t.prompt, x.puredict()
print t.prompt, script.container.localpath()

print t.line

x.run(script)

print t.line

x = toolbox.component(engine='blind')

print t.prompt, x
print t.prompt, x.puredict()

print t.line

x.run(script)

print t.line

x = toolbox.component(engine='parallel')

print t.prompt, x
print t.prompt, x.puredict()

e.vortex_debug_env = True

print t.line

x.run(script, mpiopts=dict(n=2))

print t.line
print t.prompt, 'Duration time =', t.duration()
print t.line
