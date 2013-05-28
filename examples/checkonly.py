#!/bin/env python
# -*- coding:Utf-8 -*-

import vortex
import sandbox.data

from vortex.tools import date
from vortex.syntax.footprint import envfp

rl = vortex.toolbox.resource

t = vortex.ticket()
t.warning()

print t.line

print t.prompt, 'Checking only filter'

print t.line

print sandbox.data.resources.CheckOnlyCycle37.footprint().only

print t.line

print sandbox.data.resources.CheckOnlyCycle38.footprint().only

print t.line

x = rl(kind='onlyselect', model='arpege', date=date.today())

print t.prompt, x

print t.line

envfp(cycle='cy38t1.02')

print t.prompt, envfp()

x = rl(kind='onlyselect', model='arpege', date=date.today())

print t.prompt, x
if x:
    print t.prompt, x.realkind

print t.line

x = rl(kind='onlyselect', model='arpege', date=date.Date(2011,12,24,18))

print t.prompt, x

print t.line

print t.prompt, 'Duration time =', t.duration()

print t.line

vortex.exit()
