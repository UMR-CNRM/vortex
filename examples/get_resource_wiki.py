#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Exemple du wiki
http://sicompas/vortex/doku.php/documentation:faq:rhandler
"""

import os
import sys

import common.data
import olive.data
import vortex
from vortex.data.geometries import Geometry
from vortex.tools import date


sys.stdout = sys.stderr
assert any([common.data, olive.data])


rundate = date.today() + date.Period('PT00H')
os.chdir('/Users/pascal/tmp/vortex')

rh = vortex.toolbox.rh(
    cutoff         = 'production',
    date           = rundate,
    format         = 'fa',
    kind           = 'historic',
    local          = 'CPLINIT+[term::fmthm]',
    model          = 'arpege',
    namespace      = '[suite].archive.fr',
    suite          = 'oper',
    term           =  8,
    vapp           = '[model]',
    vconf          = '4dvarfr',
    geometry       = Geometry(tag='globalsp2'),
)

print('container :', rh.container)
print('provider :', rh.provider)
print('resource :', rh.resource)
print('idcard() :', rh.idcard())
print('complete :', rh.complete)
print('location():', rh.location())
# print 'get()     :', rh.get()
print('check() :', rh.check())
print('locate() :', rh.locate())
