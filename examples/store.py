#!/bin/env python
# -*- coding:Utf-8 -*-

import vortex
from vortex.tools import net
from vortex.data import stores


t = vortex.ticket()
t.warning()

print t.line

finder = stores.Finder(scheme='ftp', domain='open.meteo.fr')

print t.prompt, 'Finder', finder
print t.prompt, 'dict =', finder.as_dict()

print t.line

urinfo = net.uriparse('file://eric@local.meteo.fr/tmp/toto')
s = stores.load(scheme=urinfo['scheme'], netloc=urinfo['netloc'])

print t.prompt, 'Store', s
print t.prompt, 'dict =', s.as_dict()

print t.line

print t.prompt, 'Duration time =', t.duration()

print t.line
