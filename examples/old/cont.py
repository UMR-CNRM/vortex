#!/usr/bin/env python
# -*- coding:Utf-8 -*-

# Status : OK (v0.6.21)

from __future__ import print_function, absolute_import, unicode_literals, division

import vortex
from vortex.data import containers
from vortex.data.containers import Virtual, File

t = vortex.ticket()

print(t.prompt, 'Playing with containers')
print(t.prompt, 'This session', t, t.tag, t.started)

print(t.line)

c1 = vortex.proxy.containers
print(t.prompt, 'Collector', c1)
print(t.prompt, 'Collector called', c1())
print(t.prompt, 'Collector iterator')
for c in c1:
    print(t.prompt, '  ', c)

print(t.line)

c2 = vortex.proxy.containers(entry='bof')
print(t.prompt, 'Collector', c2)
print(t.prompt, 'Collector called', c2())
print(t.prompt, 'Collector iterator')
for c in c2:
    print(t.prompt, '  ', c)

print(t.line)

rc = containers.File(local='bidon')
print(t.prompt, 'Container footprint', rc.footprint_retrieve())
print(t.prompt, 'File container resolved ?', rc)

