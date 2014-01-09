#!/bin/env python
# -*- coding:Utf-8 -*-

from vortex import sessions, toolbox

import vortex.data
import vortex.algo

from vortex.data.geometries import SpectralGeometry, GridGeometry
from vortex.tools import env, date
from gco.tools import genv 
 
import common.data
import olive.data
import gco.data
import gco.syntax


t = sessions.ticket()
#t.debug()

myenv = env.current()
mysys = t.system()

mysys.chdir(myenv.TMPDIR + '/rundir')
print t.prompt, mysys.pwd()

#domain = ['GLOB15','GLOB25','EURAT01','EUROC25','GLOB05']
domains = [ 'GLOB15' ]
rundate = date.Date('2011092200')
geo = SpectralGeometry(id='Current op', area='france', truncation=798, lam=False)
geo_bdap = GridGeometry(id='Current op', area='GLOB15')
inputdir = myenv.HOME + '/tmp/inputs/'
prvin = dict(experiment = '99A0') 
prvout = dict(experiment = 'A000')

arome_cycle='al36t1_arome-op2.22'
arpege_cycle='cy36t1_op2.16'

print t.line

fpenv = vortex.toolbox.defaults(
    geometry = geo,
    namespace='open.archive.fr',
    date=rundate,
    cutoff='production',
    model='arpege',
    gspool=myenv.HOME + '/gco-tampon',
)

print t.prompt, fpenv()

print t.line

gconf = genv.register(cycle=arpege_cycle, entry='double', MASTER_ARPEGE='cy36t1_masterodb-op2.12.SX20r411.x.exe')
gconf = genv.register(cycle=arpege_cycle, entry='double', RTCOEF_TGZ='var.sat.misc_rtcoef.12.tgz')
gconf = genv.register(cycle=arpege_cycle, entry='double', CLIM_ARPEGE_T798='clim_arpege.tl798.02')
gconf = genv.register(cycle=arpege_cycle, entry='double', CLIM_DAP_GLOB15='clim_dap.glob15.07')
gconf = genv.register(cycle=arpege_cycle, entry='double', MAT_FILTER_GLOB15='mat.filter.glob15.07')
gconf = genv.register(cycle=arpege_cycle, entry='double', NAMELIST_ARPEGE='cy36t1_op2.11.nam')
#gconf = genv.register(cycle=arome_cycle, entry='double', NAMELIST_AROME='al36t1_arome-op2.13.nam')

print t.prompt, ">>>>> GENV :", genv.cycles()
print t.prompt, gconf

analysis =  toolbox.rload(
    prvin,
    kind='analysis',
    block='canari',
    local='ICMSHFCSTINIT',
)

rtcoef = toolbox.rload(
    kind='miscgenv',
    genv='cy36t1_op2.16',
    local='rtcoef.tgz',
    gvar='RTCOEF_TGZ',
)

climmodel = toolbox.rload(
    kind='modelclim',
    month=rundate.month,
    genv='cy36t1_op2.16',
    local='Const.Clim',
)

climbdap = toolbox.rload(
    kind='bdapclim',
    month=rundate.month,
    geometry=geo_bdap,
    genv='cy36t1_op2.16',
    local='const.clim.[geometry::area]',
)

matfilter = toolbox.rload(
    kind='matfilter',
    scopedomain=geo_bdap,
    geometry=geo,
    genv='cy36t1_op2.16',
    local='matrix.fil.[scopedomain::area]',
)

namfcp = toolbox.rload(
    kind='namelist',
    binary='arpege',
    genv='cy36t1_op2.16',
    source='namelistfcp',
    local='fort.4'
)

xxtdef = toolbox.rload(
    kind='namselectdef',
    binary='arpege',
    genv=arpege_cycle,
    source='xxt.def',
    local='xxt.def',
)

#t.debug()
namselect = toolbox.rload(
    kind='namselect',
    binary='arpege',
    term=(0,3),
    genv=arpege_cycle,
    source='select_p',
    local='selectfp[term::fmth]',
)

arpege = toolbox.rload(
    kind='nwpmodel',
    genv='cy36t1_op2.16',
    local='ARPEGE',
)

historic = toolbox.rload(
    prvout,
    kind='historic',
    term=(0,3),
    block='forecast',
    local='ICMSHFCST+[term::fmth]',
)

gridpoint = toolbox.rload(
    prvout,
    kind='gridpoint',
    origin='historic',
    geometry=geo_bdap,
    nativefmt='fa',
    term=(0,3),
    block='forecast',
    local='PFFPOS[geometry::area]+[term::fmth]'
)

listing = toolbox.rload(
    prvout,
    kind='listing',
    task='forecast',
    block='listing',
    local='listing.forecast'
)  


inputs = ( rtcoef, analysis, climmodel, climbdap, namfcp, xxtdef, namselect, matfilter, arpege )

outputs = ( historic, gridpoint, listing )

myenv.update(
    SWAPP_XXT_DEF='1',
)

for rh in inputs:
    for r in rh :
        print r
        print 'Resource attr : ', r.resource._attributes
        print 'Provider attr: ', r.provider._attributes
        print 'Container attr: ', r.container._attributes
        # print t.line, r.idcard()
        r.get()

print t.line

"""
arpege = arpege.pop()

#x = components.load(engine='launch', interpreter=arpege.resource.language)
x = components.load(engine='launch')
print t.prompt, x.as_dict()

x.run(arpege)

for rh in outputs:
    for r in rh :
        print t.line, r.idcard()
        r.put()

print t.prompt, 'Duration time =', t.duration()
"""