#!/bin/env python
# -*- coding:Utf-8 -*-

import vortex

t = vortex.ticket()
t.warning()

from vortex.data import providers
import gco.data

print t.line

print t.prompt, 'Playing with providers'

print t.line

print t.prompt, 'This session', t, t.tag, t.started

print t.line

print providers.Remote

cat = providers.catalog()
print t.prompt, 'Catalog', cat
print t.prompt, 'Catalog called', cat()
print t.prompt, 'Catalog iterator'
for c in cat:
    print t.prompt, '  ', c

rp = providers.Remote(remfile = '/tmp/anyfile')
print t.prompt, 'Provider footprint', rp.footprint()
print t.prompt, 'Remote resolved ?', rp

print t.line

print t.prompt, 'Duration time =', t.duration()

print t.line

vortex.exit()
