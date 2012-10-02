#!/bin/env python
# -*- coding:Utf-8 -*-

from vortex import sessions, toolbox
import vortex.data
from vortex.data.geometries import SpectralGeometry
from vortex.tools import date
from vortex.syntax import footprint

import common.data

import gco.syntax
import gco.data
from gco.tools import genv

t = sessions.ticket()
t.warning()

print t.prompt

rundate = date.Date('2011092200')
geo = SpectralGeometry(id='Current op', area='france', truncation=798)

print t.line

fpenv = footprint.envfp(
    geometry = geo,
    date=rundate,
    model='arpege'
)
print t.prompt, fpenv.date, fpenv.geometry 

print t.line

cm = toolbox.rload(
    kind='modelclim',
    month=rundate.month,
    gget='clim_[model].tl[geometry::truncation].02',
    local='Const.Clim',
)

print t.line

print t.prompt, cm

print t.line

for clim in cm:
    print clim.idcard()
    clim.get()

print t.line

gconf = genv.register(cycle='cy36t1_op2.16', entry='double', MASTER_ARPEGE='cy36t1_masterodb-op2.12.SX20r411.x.exe')

print t.prompt, genv.cycles()
print t.prompt, gconf

print t.line

bin = toolbox.rload(
    kind='nwpmodel',
    genv='cy36t1_op2.16',
    local='ARPEGE',
).pop()

print bin.idcard()

bin.get()

print t.prompt, 'Duration time =', t.duration()
