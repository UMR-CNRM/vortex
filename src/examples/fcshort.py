#!/bin/env python
# -*- coding:Utf-8 -*-

from vortex import sessions, toolbox
from vortex.tools import date
from vortex.syntax import footprint

import vortex.data
import vortex.algo

from vortex.data.geometries import SpectralGeometry

import common.data
import common.algo
import olive.data
import gco.data
import gco.syntax


t = sessions.ticket()
g = t.glove
rl = toolbox.rload

t.warning()

mysys = g.system
myenv = mysys.env

mysys.cd(myenv.tmpdir)
print t.prompt, mysys.pwd

arpege_cycle = 'cy36t1_op2.16'

rundate = date.Date('2012041300')
geo = SpectralGeometry(id='Current op', area='france', truncation=798)

fpenv = footprint.envfp(
    geometry=geo,
    namespace='open.archive.fr',
    date=rundate,
    cutoff='production',
    model='arpege'
)

print t.prompt, fpenv()

print t.line

input = (

    rl(
        role = 'Analysis',
        kind = 'analysis',
        remote = myenv.home + '/tmp/fcdemo/fcinit',
        local = 'ICMSHFCSTINIT',
    ),

    rl(
        role = 'DrivingNamelist',
        kind = 'namelist',
        remote = myenv.home + '/tmp/fcdemo/namelistdemo',
        local = 'fort.4'
    )

)

for rh in input:
    for r in rh :
        print t.line, r.idcard()
        r.get()


arpege = rl(
    role = 'Model',
    kind = 'nwpmodel',
    binopts = '-vmeteo -eFCST -c001 -asli -t600 -fh3',
    remote = myenv.home + '/tmp/fcdemo/speedy.arp',
    local = 'ARPEGE.EX',
).pop()

output = (

    rl(
        role = 'ModelStateOutput',
        kind = 'historic',
        term = (0,3),
        remote = myenv.home + '/tmp/fcdemo/out.model.[term]',
        local = 'ICMSHFCST+[term]',
    ),
    
    rl(
        role = 'ModelListing',
        kind = 'listing',
        task = 'forecast',
        remote = myenv.home + '/tmp/fcdemo/out.listing',
        local = 'NODE.001_01'
    )

)

print t.line

arpege.get()
print arpege.idcard()

print t.line

x = toolbox.component(engine='parallel')
print t.prompt, x.puredict()

myenv.update(
    F_PROGINF="DETAIL",
    F_FTRACE="FMT2",
    F_RECLUNIT="BYTE",
    F_SYSLEN=1024,
    F_FMTBUF=131072,
    F_SETBUF=32768,
    F_SETBUF6=0,
    F_SETBUF0=0,
    F_ERRCNT=1,
    F_ADB_MODE="S",
    MPIPROGINF="DETAIL",
    MPIDEBUG="OFF",
    MPISUSPEND="ON",
    MPIEXPORT="MPIPROGINF,MPIDEBUG,DISPLAY",
    MPIRUN_EXPORT="on",
    MPIRUN_FILTER="F_,DR_HOOK,GRIB",
    DR_HOOK=0,
    DR_HOOK_IGNORE_SIGNALS="-1",
    VORTEX_DEBUG_ENV="ok",
)

x.run(arpege, mpiopts = dict(nn=1, nnp=4))

for rh in output:
    for r in rh :
        print t.line, r.idcard()
        r.put()

print t.prompt, 'Duration time =', t.duration()
