#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import vortex
from vortex.data import providers

from sandbox.data.resources import SimpleTest

t = vortex.ticket()
rl = vortex.toolbox.rload

print t.prompt, 'Playing with toolbox loader'

lrd = dict( kind = 'analysis', foo = 'youpla' )
print t.prompt, 'Pre-defined logical resource descriptor', lrd

print t.line

rp = providers.Remote(remfile = '/tmp/anyfile')
print t.prompt, 'Load with provider', rp
r1 = rl(lrd, 2, model='arpege', provider=rp, remfile='bidon', remote='thepath', memory=True)
print t.prompt, 'Got', r1

print t.line

print t.prompt, 'Load without explicit provider'
r2 = rl(lrd, model='arpege', remfile='bidon', remote='/tmp/should/be/selected', local=['file1', 'file2'])


print t.line
t.debug()
print t.prompt, 'Load the test resource'
print t.prompt, 'SimpleTest footprint', SimpleTest.retrieve_footprint()
for gh in rl(bigmodel='arpege', remote='databox_[cutoff]', cutoff='p,a',
             kind='simple', extra=2, foo='treize', virtual=True):
    print t.line, gh.idcard()

print t.line

print t.prompt, 'Duration time =', t.duration()

print t.line
