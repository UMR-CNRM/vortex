#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

# Status : OK (v0.6.21)

import vortex
import vortex.data
import common.data
import common.algo

t = vortex.ticket()
t.warning()

sh = t.system()
g = t.glove
e = t.env

print(t.line)

sh.cd(e.home + '/tmp/bidon', create=True)
print(sh.pwd())

rx = vortex.toolbox.rh(remote=g.siteroot + '/examples/tmp/test.sh',
                       file='test.sh', model='arpege', kind='ifsmodel')

print(t.line)

print(rx.idcard())

print(t.line)

x = vortex.toolbox.algo(kind='forecast', timestep=900, engine='parallel')
print(t.prompt, 'Engine is', x)

print(t.line)

rx.get()
x.run(rx, mpiopts=dict(n=2))

print(t.line)
