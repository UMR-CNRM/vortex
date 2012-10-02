#!/bin/env python
# -*- coding:Utf-8 -*-

from vortex import sessions
import vortex.data
import common.data
import olive.data
from common.tools.shortcuts import analysis

t = sessions.ticket()

cr = vortex.data.resources.catalog()
cr.track = True

print t.line

print t.prompt, 'Resource tracker =', cr.track

a = analysis()

print t.line

print a.idcard()

print t.line

print t.prompt, 'Resource tracker =', cr.track

print t.line

print cr.track.toprettyxml(indent='    ')

print t.line
print t.prompt, 'Duration time =', t.duration()
print t.line
