#!/bin/env python
# -*- coding:Utf-8 -*-

from vortex import sessions

t = sessions.ticket()
t.warning()

print t.prompt, 'Playing with gloves'

print t.line

g = t.glove

print t.prompt, 'Glove =', g
print t.prompt, 'dict =', g.puredict()

print t.line

g = sessions.glove(user='mxpt001', tag='test')

print t.prompt, 'Glove =', g
print t.prompt, 'dict =', g.puredict()

print t.line

g = sessions.glove(user='mxpt001', kind='oper', tag='default')

print t.prompt, 'Glove =', g
print t.prompt, 'dict =', g.puredict()

print t.line

print t.prompt, 'Duration time =', t.duration()

