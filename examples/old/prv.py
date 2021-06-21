# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import vortex

t = vortex.ticket()
t.warning()

from vortex.data import providers
import gco.data

print(t.line)

print(t.prompt, 'Playing with providers')

print(t.line)

print(t.prompt, 'This session', t, t.tag, t.started)

print(t.line)

print(providers.Remote)

clp = vortex.proxy.providers
print(t.prompt, 'Collector', clp)
print(t.prompt, 'Collector called', clp())
print(t.prompt, 'Collector iterator')
for c in clp:
    print(t.prompt, '  ', c)

rp = providers.Remote(remfile = '/tmp/anyfile')
print(t.prompt, 'Provider footprint', rp.footprint)
print(t.prompt, 'Remote resolved ?', rp)

print(t.line)

print(t.prompt, 'Duration time =', t.duration())

print(t.line)
