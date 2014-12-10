#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import vortex

from vortex import toolbox
from vortex.tools import date
from vortex.data import geometries

import common, olive, gco
from gco.tools import genv

t = vortex.ticket()
t.warning()

sh = t.context.system
e = t.context.env

print t.line

tg = vortex.proxy.target(hostname=sh.hostname)
print t.prompt, tg.hostname, tg.sysname, tg.inifile

print t.line

nstep = 1
getinsitu = True

rundir = tg.get('rundir', e.HOME  + '/tmp/bidon')
sh.cd(rundir)
print t.prompt, sh.pwd(), 'pass:', nstep

genv.genvcmd  = tg.get('gco:genvcmd', 'genvfake')
genv.genvpath = tg.get('gco:genvpath', e.HOME + '/bin')
genv.autofill('cy37t1_op1.20')

print t.line
print t.prompt, 'CYCLES', genv.cycles()

rundate = date.today()

fp = toolbox.defaults(
    geometry=geometries.get(tag='globalsp'),
    namespace='open.archive.fr',
    date=rundate,
    cutoff='production',
    model='arpege',
    ggetpath=tg.get('gco:ggetpath', e.HOME + '/bin'),
)

print t.line, fp(), t.line

geofp = [ geometries.get(tag=x) for x in ('glob15', 'glob25', 'euroc25', 'glob05', 'eurat01') ]

prvin  = vortex.proxy.provider(suite='oper', namespace='oper.archive.fr', vapp='arpege')
prvout = vortex.proxy.provider(experiment='A001', block='forecast', namespace='vortex.multi.fr')
prvcst = vortex.proxy.provider(genv='cy37t1_op1.20', gspool=tg.get('gco:tampon', e.HOME + '/gco-tampon'))

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
    geometry = geofp,
    local    = 'const.clim.[geometry::area]',
)

toolbox.input(
    provider = prvcst,
    role     = 'MatFilter',
    kind     = 'matfilter',
    scope    = geofp,
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
    print 'DEBUG', xxt
    xxt = xxt[0]
    print xxt.idcard()
    print t.line
    for k, v in sorted(xxt.contents.items()):
        print k, v
else:
    exit()

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
    term     = (0, 1),
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

x = vortex.proxy.component(kind='forecast', engine='parallel', fcterm=1)

print t.prompt, 'COMPONENT', x.as_dict()

e.VORTEX_DEBUG_ENV = 'ok'

print t.line

for s in t.context.sequence.inputs():
    print 'GET', s.rh.location(), '...'
    print ' >', s.rh.get(insitu=getinsitu)


if nstep == 0 or nstep == 2:

    print t.line
    t.info()
    x.run(arpege, mpiopts=dict(nn=1, nnp=8))


if nstep == 0 or nstep >= 2:

    print t.line
    t.warning()

    for s in t.context.sequence.outputs():
        print 'PUT', s.rh.location(), '...'
        print ' >', s.rh.locate()
        print ' >', s.rh.put()

print t.line

print t.prompt, 'Duration time =', t.duration()

print t.line
