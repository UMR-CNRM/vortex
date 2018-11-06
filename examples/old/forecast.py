#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex import sessions, toolbox

import vortex.data
from vortex.data.geometries import GaussGeometry, LonlatGeometry
from vortex.algo import components
from vortex.tools import env, date

import common.data
import olive.data
import gco.data
import gco.syntax


t = sessions.ticket()
t.warning()

myenv = env.current()
mysys = t.system()

mysys.chdir(myenv.TMPDIR + '/rundir')
print(t.prompt, mysys.pwd())

#domain = ['GLOB15','GLOB25','EURAT01','EUROC25','GLOB05']
domains = [ 'GLOB15' ]
rundate = date.Date('2011092200')
geo = GaussGeometry(id='Current op', area='france', truncation=798, lam=False)
geoBDAP = LonlatGeometry(area='GLOB15', resolution=1.5, runit='dg')

inputdir = myenv.HOME + '/tmp/inputs/'

prvin  = dict(experiment = '99A0', block='canari')
prvout = dict(experiment = 'A001', block='forecast')

print(t.line)

fpenv = vortex.toolbox.defaults(
    geometry = geo,
    namespace='open.archive.fr',
    date=rundate,
    cutoff='production',
    model='arpege'
)

print(t.prompt, fpenv())

print(t.line)

analysis = toolbox.rload(
    prvin,
    kind='analysis',
    local='ICMSHFCSTINIT',
)

rtcoef = toolbox.rload(
    kind='miscgenv',
    remote=inputdir+'rtcoef.tgz',
    local='rtcoef.tgz'
)

climmodel = toolbox.rload(
    kind='modelclim',
    month=rundate.month,
    remote=inputdir+'climmodel.[month]',
    local='Const.Clim',
)

climbdap = toolbox.rload(
    kind='bdapclim',
    month=rundate.month,
    geometry=geoBDAP,
    remote=inputdir+'climbdap.[geometry::area].[month]',
    local='const.clim.[geometry::area]',
)

matfilter = toolbox.rload(
    kind='matfilter',
    remote=inputdir+'matfilter.[scopedomain::area]',
    scopedomain=geoBDAP,
    local='matrix.fil.[scopedomain::area]',
)

namfcp = toolbox.rload(
    kind='namelist',
    remote=inputdir+'namelistfcp',
    local='fort.4'
)

namselect = toolbox.rload(
    kind='namselect',
    term=(0, 3),
    remote=inputdir+'selectfp',
    local='selectfp+[term::fmth]',
)

arpege = toolbox.rload(
    remote=inputdir+'MASTER_ARPEGE',
    local='ARPEGE',
    language='bash'
)

historic = toolbox.rload(
    prvout,
    kind='historic',
    term=(0, 3),
    local='ICMSHFCST+[term::fmth]',
)

gridpoint = toolbox.rload(
    prvout,
    kind='gridpoint',
    origin='historic',
    geometry=geoBDAP,
    nativefmt='fa',
    term=(0, 3),
    local='PFFPOS[geometry::area]+[term::fmth]'
)

listing = toolbox.rload(
    prvout,
    kind='listing',
    task='forecast',
    local='listing.forecast'
)

inputs = ( rtcoef, analysis, climmodel, climbdap, namfcp, namselect, matfilter, arpege )
outputs = ( historic, gridpoint, listing )

for rh in inputs:
    for r in rh:
        print(t.line, r.idcard())
        r.get()

print(t.line)

arpege = arpege.pop()

x = components.load(engine='launch', interpreter=arpege.resource.language)
print(t.prompt, x.as_dict())

x.run(arpege)

for rh in outputs:
    for r in rh:
        print(t.line, r.idcard())
        r.put()

print(t.prompt, 'Duration time =', t.duration())
