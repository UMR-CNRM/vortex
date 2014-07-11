#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from footprints.priorities import top

import vortex
from sandbox.data.resources import SimpleTest
u_fill_fp_catalogs = SimpleTest

t = vortex.ticket()
t.warning()

print t.line

print t.prompt, 'Playing with priorities'

print t.prompt, 'Priorities', top
for x in top:
    print t.prompt, ' >', x

print t.line

test = vortex.toolbox.rh(
    remote='databox',
    kind='simple',
    cutoff='long',
    extra=2,
    foo='douze',
    bigmodel='arpege',
    virtual=True
)

print t.line

print t.prompt, 'SimpleTest from load 1', test
print t.prompt, 'SimpleTest handler complete ?', test.complete
print t.prompt, 'SimpleTest resource ?', test.resource.realkind, test.resource

print 'xtest() :', test.resource.xtest()

print t.line

print t.prompt, top()
print t.prompt, top.OLIVE.rank
top.OLIVE.up()
print t.prompt, top()
print t.prompt, top.OLIVE.rank

print t.line

test = vortex.toolbox.rh(
    remote='databox',
    kind='simple',
    cutoff='long',
    extra=2,
    foo='douze',
    bigmodel='arpege',
    virtual=True
)

print t.line

print t.prompt, 'SimpleTest from load 2', test
print t.prompt, 'SimpleTest handler complete ?', test.complete
print t.prompt, 'SimpleTest resource ?', test.resource.realkind, test.resource

print 'xtest() :', test.resource.xtest()

print t.line

top.reset()
print top()
top.insert('olive', after='toolbox')
top.insert('oper', before='debug')
print top()

print t.line

test = vortex.toolbox.rh(
    remote='databox',
    kind='simple',
    cutoff='long',
    extra=2,
    foo='douze',
    bigmodel='arpege',
    virtual=True
)

print t.line

print t.prompt, 'SimpleTest from load 3', test
print t.prompt, 'SimpleTest handler complete ?', test.complete
print t.prompt, 'SimpleTest resource ?', test.resource.realkind, test.resource

print 'xtest() :', test.resource.xtest()

print t.line

print t.prompt, 'Duration time =', t.duration()

print t.line
