#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import vortex
from vortex.data.geometries import GaussGeometry
from vortex.tools import date

import common.data

import gco.syntax
import gco.data
from gco.tools import genv

t = vortex.ticket()
g = t.glove
e = t.env
sh = t.system()

t.warning()

sh.cd(e.TMPDIR + '/rundir')
print t.prompt, sh.pwd()

rundate = date.Date('2011092200')
geo = GaussGeometry(id='Current op', area='france', truncation=798, lam=False)

print t.line

fpenv = vortex.toolbox.defaults(
    geometry=geo,
    date=rundate,
    model='arpege',
    gspool=e.HOME + '/gco-tampon',
)

print t.prompt, fpenv.date
print t.prompt, fpenv.geometry

print t.line

cm = vortex.toolbox.rload(
    kind='clim_model',
    month=rundate.month,
    gget='clim_[model].tl[geometry::truncation].02',
    local='Const.Clim',
)

print t.line

print t.prompt, cm

print t.line

for clim in cm:
    print clim.idcard()
    print clim.get()

print t.line

gconf = genv.register(cycle='cy37t1_op1.17', entry='double',
                      MASTER_ARPEGE='cy37t1_master-op1.09.SX20r411.x.exe')

print t.prompt, genv.cycles()
print t.prompt, gconf

print t.line

arp = vortex.toolbox.rload(
    kind='mfmodel',
    genv='cy37t1_op1.17',
    local='ARPEGE.EX',
).pop()

print t.line, arp.idcard()

print 'GET:', arp.get()

print t.line

print t.prompt, 'Duration time =', t.duration()

print t.line
