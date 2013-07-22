#!/bin/env python
# -*- coding:Utf-8 -*-

import vortex
import common.data
import olive.data
from common.tools.shortcuts import analysis

t = vortex.ticket()

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

print cr.track.dump_all()

print t.line

print t.prompt, 'Duration time =', t.duration()

print t.line

vortex.exit()
