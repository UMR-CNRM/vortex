#!/bin/env python
# -*- coding:Utf-8 -*-

from vortex import sessions

t = sessions.ticket()
t.warning()

g = t.glove
e = g.system.env

c = t.context()

c.active()

c.freeze()

c.dump()

c.exit()


print t.line

