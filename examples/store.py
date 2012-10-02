#!/bin/env python
# -*- coding:Utf-8 -*-

from vortex import sessions
from vortex.tools import net

t = sessions.ticket()
t.warning()

from vortex.data import stores

print t.line

finder = stores.Finder(scheme='ftp', domain='open.meteo.fr')

print t.prompt, 'Finder', finder
print t.prompt, 'dict =', finder.puredict()

print t.line

urinfo = net.uriparse('file://eric@local.meteo.fr/tmp/toto')
s = stores.load(scheme=urinfo['scheme'], netloc=urinfo['netloc'])

print t.prompt, 'Store', s
print t.prompt, 'dict =', s.puredict()

print t.line
print t.prompt, 'Duration time =', t.duration()
