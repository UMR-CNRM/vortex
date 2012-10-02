#!/bin/env python
# -*- coding:Utf-8 -*-

from vortex import toolbox, sessions
from vortex.syntax.priorities import top
from sandbox.data.resources import SimpleTest

t = sessions.ticket()
t.warning()

def jumpzozo(self):
    return 'Ah que coucou'

SimpleTest.zozo = jumpzozo

print t.line

print t.prompt, 'Playing with priorities'

print t.prompt, 'Priorities', top
for x in top:
    print t.prompt, ' >', x

print t.line

test = toolbox.rload(remote='databox', kind='simple', cutoff='long', extra=2, foo='douze', bigmodel='arpege', virtual=True).pop()
print t.prompt, 'SimpleTest from load', test
print t.prompt, 'SimpleTest handler complete ?', test.complete
print t.prompt, 'SimpleTest resource ?', test.resource.realkind(), test.resource

print test.resource.zozo()

print t.line

print t.prompt, top()
print t.prompt, top.OLIVE.value
top.OLIVE.up()
print t.prompt, top()
print t.prompt, top.OLIVE.value

print t.line

test = toolbox.rload(remote='databox', kind='simple', cutoff='long', extra=2, foo='douze', bigmodel='arpege', virtual=True).pop()
print t.prompt, 'SimpleTest from load', test
print t.prompt, 'SimpleTest handler complete ?', test.complete
print t.prompt, 'SimpleTest resource ?', test.resource.realkind(), test.resource

print test.resource.zozo()

print t.line

print t.prompt, 'Duration time =', t.duration()
