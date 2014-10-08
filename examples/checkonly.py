#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from pprint import pformat
import vortex
import sandbox.data

from vortex.tools import date

rl = vortex.toolbox.rh

t = vortex.ticket()
t.warning()

print t.line
print t.prompt, 'Checking only filter'

print t.line
print "CheckOnlyCycle37"
print sandbox.data.resources.CheckOnlyCycle37.footprint_retrieve().only

print t.line
print "CheckOnlyCycle37"
print sandbox.data.resources.CheckOnlyCycle38.footprint_retrieve().only

print t.line
print "without defaults"
x = rl(kind='onlyselect', model='arpege', date=date.today())
print t.prompt, "without defaults:", x

print t.line
print "with default cycle='cy38t1.02'"
vortex.toolbox.defaults(cycle='cy38t1.02')
print t.prompt, pformat(vortex.toolbox.defaults)

x = rl(kind='onlyselect', model='arpege', date=date.today())
print t.prompt, "**with** defaults:", x
if x:
    print t.prompt, x.realkind

print t.line
print "older date"
x = rl(kind='onlyselect', model='arpege', date=date.Date(2011, 12, 24, 18))
print t.prompt, x
