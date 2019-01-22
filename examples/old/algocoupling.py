#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

# Status : OK (v0.6.21)

import vortex
import vortex.data
import common.data
import common.algo
import olive.data
import gco.data
from vortex.tools import date
from vortex.data import geometries
from gco.tools import genv

t = vortex.ticket()
t.warning()

g = t.glove
e = t.env
c = t.context

sh = t.system()

if sh.cd(e.HOME + '/tmp/rundir'):
    # sh.rmglob('-rf', '*')
    print(t.prompt, sh.pwd())

today = date.today()

fpenv = vortex.toolbox.defaults(
    gspool=e.HOME + '/gco-tampon',
    date=today,
    month=today,
)

arpege_cycle = 'cy36t1_op2.16'
aladin_cycle = 'al36t1_op2.14'

gconf_arpege = genv.register(
    # current arpege cycle
    cycle=arpege_cycle,
    # a shorthand to acces this cycle
    entry='double_arp',
    # items to be defined
    MASTER_ARPEGE='cy36t1_masterodb-op2.12.SX20r411.x.exe',
    RTCOEF_TGZ='var.sat.misc_rtcoef.12.tgz',
    CLIM_ARPEGE_T798='clim_arpege.tl798.02',
    CLIM_DAP_GLOB15='clim_dap.glob15.07',
    MAT_FILTER_GLOB15='mat.filter.glob15.07',
    NAMELIST_ARPEGE='cy36t1_op2.11.nam'
)

gconf_aladin = genv.register(
    # current arpege cycle
    cycle=aladin_cycle,
    # a shorthand to acces this cycle
    entry='double_ala',
    # items to be defined
    CLIM_REUNION_08KM00='clim_reunion.08km00.02',
    CLIM_REUNION_16KM00='clim_reunion.16km00.01',
    NAMELIST_ALADIN='al36t1_reunion-op2.09.nam',
)

rl = vortex.toolbox.rload

inputs = (
    rl(
        kind='clim_model',
        genv=arpege_cycle,
        local='climarpege',
        model='arpege',
        geometry=geometries.get(tag='globalsp'),
        role='Fatherclim'
    ),
    rl(
        kind='clim_model',
        genv=aladin_cycle,
        local='climaladin',
        role='Sonclim',
        model='aladin',
        geometry=geometries.get(tag='reunionsp'),
    ),
    rl(
        kind='namelist',
        genv=aladin_cycle,
        local='my_namelist',
        role='namelist',
        binary='aladin',
        model='aladin',
        source='namel_e927'
    ),
    rl(
        kind='historic',
        cutoff='production',
        namespace='[suite].archive.fr',
        geometry=geometries.get(tag='globalsp'),
        local='ICMSHARPE+[term::fmth]',
        suite='oper',
        term=(0, 3),
        model='arpege',
        igakey='arpege',
        role='Couplingfile'
    ),
)

print(t.line)

t.warning()
for rh in inputs:
    for r in rh:
        print('Get', r.location(), '...',)
        print(r.get(insitu=False))


rx = vortex.toolbox.rh(remote=g.siteroot + '/examples/tmp/test.sh',
                       file='testcpl.sh', language='bash', kind='script')

print(t.line)

rx.get()

print(t.line)


x = vortex.toolbox.algo(kind='coupling', timescheme='eul', model='arpifs',
                        fcterm=0, timestep=415.385, engine='parallel')

print(t.prompt, 'Engine is', x)

print(t.line)

x.run(rx, mpiopts=dict(n=2))

print(t.line)
