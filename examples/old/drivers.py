#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Status : OK (v0.9.18)

from __future__ import print_function, absolute_import, unicode_literals, division

import vortex

from vortex.tools import date
from vortex.layout.nodes import *

print(Driver, Family, Task)

t = vortex.ticket()
t.sh.trace = True

d = Driver(
    tag    = 'test',
    ticket = t,
    nodes  = [
        Family(tag='foo', ticket=t),
        Task(tag='zut', ticket=t)
    ]
)

print(d)

d.setup(date=date.synop())

print(d.contents)

d.run()
