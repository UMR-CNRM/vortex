#!/bin/env python
# -*- coding:Utf-8 -*-

from vortex import sessions, toolbox
import vortex.data
import common.data
import common.algo

t = sessions.ticket()
t.warning()

g = t.glove
e = t.env

cr = vortex.data.resources.catalog()
cr.track = True

print t.line

#rx = toolbox.rh(remote=e.home + '/tmp/test.sh', file='test.sh', rawopts='coucou', language=e.trueshell())
rx = toolbox.rh(remote=e.home + '/tmp/test.sh', file='test.sh', model='arpege', kind='ifsmodel')

print t.line

print t.prompt, 'Resource tracker =', cr.track

print t.line

print cr.track.toprettyxml(indent='    ')

print t.line

print rx.idcard()

print t.line

x = toolbox.component(kind='forecast', timestep=900, engine='parallel')
print t.prompt, 'Engine is', x

print t.line

x.run(rx, mpiopts=dict(n=2))

print t.line
print t.prompt, 'Duration time =', t.duration()
print t.line
