#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import re

import vortex
from vortex.syntax import cycles
import copy

t = vortex.sessions.ticket()
t.warning()

print t.prompt, cycles.maincycles
print t.prompt, cycles.subcycles
print t.prompt, dir(cycles)

print 'Single cycle : ', cycles.cy36t1, cycles.cy36t1.__dict__
dbcy36 = copy.deepcopy(cycles.cy36t1)
print 'Double cycle : ', dbcy36, dbcy36.__dict__

test_cycle = cycles.cy36t1
test_str = 'cy36'
print t.prompt, test_cycle.findall(test_str + 't1')
print t.prompt, test_cycle.findall(test_str)
print t.prompt, test_cycle.findall(test_str + 't2')
print t.prompt, test_cycle.findall(test_str + 't1_op')

cycles.maincycles = [ x for x in cycles.maincycles if x > 33 ]
cycles.subcycles = [ x for x in cycles.subcycles if re.search(r'op', x) ]

print t.prompt, cycles.maincycles
print t.prompt, cycles.subcycles
cycles.generate()
print t.prompt, dir(cycles)

for c in ( 'cy36op', 'cy36t1op2', 'cyt1_op2', '36t2_op1', 'cy36t2_op1', 'cy36t2_model-op2' ):
    print t.prompt, 'Oper', c.ljust(16), '?', cycles.oper.search(c)

print t.prompt, 'Reminder:', cycles.defined()

print t.prompt, 'Duration time =', t.duration()
