#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import vortex

t = vortex.ticket()
t.warning()

print(t.prompt, 'Playing with gloves')

print(t.line)

g = t.glove

print(t.prompt, 'Glove =', g)
print(t.prompt, 'dict =', g.as_dict())

print(t.line)

g = vortex.sessions.getglove(user='mxpt001', tag='test')

print(t.prompt, 'Glove =', g)
print(t.prompt, 'dict =', g.as_dict())

print(t.line)

g = vortex.sessions.getglove(user='mxpt001', kind='oper', tag='default')

print(t.prompt, 'Glove =', g)
print(t.prompt, 'dict =', g.as_dict())

print(t.line)

print(t.prompt, 'Duration time =', t.duration())

print(t.line)
