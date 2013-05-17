#!/bin/env python
# -*- coding: utf-8 -*-

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
t.warning()

g = t.glove
mysys = g.system
myenv = mysys.env
mysys.cd(myenv.tmpdir)
print t.prompt, mysys.pwd

cache = myenv.home + '/tmp/fcdemo/'

arpege_cycle = 'cy36t1_op2.16'

rundate = date.Date('2012041300')
geo = SpectralGeometry(id='Current op', area='france', truncation=798, lam=False)

fpenv = footprint.envfp(
    geometry=geo,
    namespace='open.archive.fr',
    date=rundate,
    cutoff='production',
    model='arpege'
)

print t.prompt, fpenv()

print t.line

analyse = toolbox.input(
    role = 'Analysis',
    kind = 'analysis',
    remote = cache + 'fcinit',
    local = 'ICMSHFCSTINIT',
)

namelist = toolbox.input(
    role = 'DrivingNamelist',
    kind = 'namelist',
    remote = cache + 'namelistdemo',
    local = 'fort.4'
)

for rl in ( analyse, namelist ):
    for r in rl:
        print t.line, r.idcard()
        r.get()

print t.line

arpege = toolbox.rload(
    role = 'Model',
    kind = 'nwpmodel',
    binopts = '-vmeteo -eFCST -c001 -asli -t600 -fh3',
    remote = cache + 'speedy.arp',
    local = 'ARPEGE.EX',
).pop()

print arpege.idcard()
arpege.get()

toolbox.output(
    role = 'ModelStateOutput',
    kind = 'historic',
    term = (0,3),
    remote = cache + 'out.model.[term::fmth]',
    local = 'ICMSHFCST+[term::fmth]',
)

toolbox.output(
    role = 'ModelListing',
    kind = 'listing',
    task = 'forecast',
    remote = cache + 'out.listing',
    local = 'NODE.001_01'
)

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
