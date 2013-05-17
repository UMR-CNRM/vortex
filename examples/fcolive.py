#!/bin/env python
# -*- coding:Utf-8 -*-

import vortex

from vortex import toolbox
from vortex.tools import date
from vortex.data import geometries 

import common.data
import common.algo
import olive.data
import gco.data
import gco.syntax
from gco.tools import genv 

t = vortex.ticket()
t.warning()

sh = t.context.system
e = t.context.env

print t.line

firstpass = False
getinsitu = True

sh.cd('/utmp/mtool/mrpm631/bidon')
print t.prompt, sh.pwd, 'pass:', firstpass

genv.genvtool = '/cnrm/gp/mrpm/mrpm631/bin/genvfake'
genv.autofill('cy37t1_op1.20')

print t.line
print t.prompt, 'CYCLES', genv.cycles()

rundate = date.today()

fp = toolbox.defaults(
    geometry=geometries.getbyname('globalsp'),
    namespace='open.archive.fr',
    date=rundate,
    cutoff='production',
    model='arpege',
    gcopath='/mf/dp/marp/marp001/public/bin',
)

print t.line, fp(), t.line

geotargets = [ geometries.getbyname(x) for x in ('glob15', 'glob25', 'euroc25', 'glob05', 'eurat01') ]

prvin  = toolbox.provider(suite='oper', namespace='oper.archive.fr', vapp='arpege')
prvout = toolbox.provider(experiment='A001', block='forecast', namespace='vortex.cache.fr')
prvcst = toolbox.provider(genv='cy37t1_op1.20')

toolbox.input(
    provider = prvin,
    role     = 'InitialCondition',
    kind     = 'analysis',
    local    = 'ICMSHFCSTINIT',
)

toolbox.input(
    provider = prvcst,
    role     = 'RtCoef',
    kind     = 'rtcoef',
    local    = 'rtcoef.tgz'
)

toolbox.input(
    provider = prvcst,
    role     = 'ModelClimatology',
    kind     = 'clim_model',
    month    = rundate.month,
    local    = 'Const.Clim',
)

toolbox.input(
    provider = prvcst,
    role     = 'BDAPClimatology',
    kind     = 'clim_bdap',
    month    = rundate.month,
    geometry = geotargets,
    local    = 'const.clim.[geometry::area]',
)

toolbox.input(
    provider = prvcst,
    role     = 'MatFilter',
    kind     = 'matfilter',
    scope    = geotargets,
    local    = 'matrix.fil.[scope::area]',
)

toolbox.input(
    provider = prvcst,
    role     = 'Namelist',
    kind     = 'namelist',
    source   = 'namelistfcp',
    local    = 'fort.4'
)

xxt = toolbox.input(
    provider = prvcst,
    role     = 'NamelistFPDef',
    kind     = 'namselectdef',
    local    = 'xxt.def',
    now      = True,
)

if xxt:
    xxt = xxt[0]
    print xxt.idcard()
    print t.line
    for k, v in sorted(xxt.contents.items()):
        print k, v

toolbox.input(
    provider = prvcst,
    role     = 'NamelistFP',
    kind     = 'namselect',
    term     = (0, 1),
    source   = '[helper::xxtsrc]',
    local    = '[helper::xxtnam]',
    helper   = xxt.contents
)

arpege = toolbox.executable(
    provider = prvcst,
    role     = 'Binary',
    kind     = 'mfmodel',
    local    = 'ARPEGE.EX',
)

toolbox.output(
    provider = prvout,
    role     = 'ModelState',
    kind     = 'historic',
    term     = (0,1),
    local    = 'ICMSHFCST+[term::fmth]',
)
    
toolbox.output(
    provider = prvout,
    role     = 'Listing',
    kind     = 'listing',
    task     = 'forecast',
    local    = 'NODE.001_01'
)

print t.line

x = vortex.toolbox.component(kind='forecast', engine='parallel', fcterm=1)

print t.prompt, 'COMPONENT', x.puredict()

e.update(
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

print t.line

for s in t.context.sequence.inputs():
    print 'GET', s.rh.location(), '...'
    print s.rh.get(insitu=getinsitu)

print t.line

if not firstpass:
    t.info()
    x.run(arpege, mpiopts = dict(nn=1, nnp=8))

    print t.line
    t.warning()

    for s in t.context.sequence.outputs():
        print 'PUT', s.rh.location(), '...'
        print s.rh.put()

    print t.line

    print t.prompt, 'Duration time =', t.duration()

    print t.line

vortex.exit()

