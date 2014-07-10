#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import vortex
import common.data
import olive.data
from common.tools.shortcuts import analysis

t = vortex.ticket()

cr = vortex.proxy.resources

print t.line

print t.prompt, 'Resource report =', cr.report

a = analysis()

print t.line

print a.idcard()

print t.line

print t.prompt, 'Resource report =', cr.report

print t.line

print cr.report.dump_all()

print t.line

print t.prompt, 'Duration time =', t.duration()

print t.line
