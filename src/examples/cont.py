#!/bin/env python
# -*- coding:Utf-8 -*-

from vortex import sessions
from vortex.data import containers
from vortex.data.containers import Virtual, File

t = sessions.ticket()

print t.prompt, 'Playing with containers'
print t.prompt, 'This session', t, t.tag, t.started

print t.line

c1 = containers.catalog()
print t.prompt, 'Catalog', c1
print t.prompt, 'Catalog called', c1()
print t.prompt, 'Catalog iterator'
for c in c1:
    print t.prompt, '  ', c

print t.line

c2 = containers.catalog(tag='zozo', itementry='bof', classes = [ Virtual ], included = True)
print t.prompt, 'Catalog', c2
print t.prompt, 'Catalog called', c2()
print t.prompt, 'Catalog iterator'
for c in c2:
    print t.prompt, '  ', c

print t.line

c3 = containers.catalog(tag='zozo', itementry='bof', classes = [ File ], included = True)
print t.prompt, 'Catalog', c3
print t.prompt, 'Catalog called', c3()
print t.prompt, 'Catalog iterator'
for c in c3:
    print t.prompt, '  ', c
    
print t.line

rc = containers.File(local='bidon')
print t.prompt, 'Container footprint', rc.footprint()
print t.prompt, 'File container resolved ?', rc

print t.prompt, 'Duration time =', t.duration()
