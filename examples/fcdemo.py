#!/bin/env python
# -*- coding:Utf-8 -*-

# Status : In progress (v0.6.21)

import vortex
from vortex.tools import date
from vortex.syntax import footprint

import vortex.data
import vortex.algo

from vortex.data.geometries import SpectralGeometry, GridGeometry

import common.data
import olive.data
import gco.data
import gco.syntax

from gco.tools import genv 


t = vortex.ticket()
g = t.glove
e = t.env
sh = t.system()

tb = vortex.toolbox
rl = vortex.toolbox.rload

t.warning()

sh.cd(e.TMPDIR + '/rundir')
print t.prompt, sh.pwd

arpege_cycle = 'cy36t1_op2.16'

#domain = ['GLOB15','GLOB25','EURAT01','EUROC25','GLOB05']
domains = [ 'GLOB15' ]
rundate = date.Date('2011092200')
geo = SpectralGeometry(id='Current op', area='france', truncation=798)
geoBDAP = GridGeometry(area='GLOB15',resolution='15')

fpenv = footprint.envfp(
    geometry=geo,
    namespace='open.archive.fr',
    date=rundate,
    cutoff='production',
    model='arpege'
)

print t.line

if g.realkind() == 'opuser':
    prvin  = dict()
    prvout = dict()
    prvcst = dict()
else:
    prvin  = dict(experiment='99A0', block='canari')
    prvout = tb.provider(experiment='A001', block='forecast')
    prvcst = tb.provider(genv=arpege_cycle)

print t.prompt, fpenv()

print t.line

genv.register(
    # current arpege cycle
    cycle=arpege_cycle,
    # a shorthand to acces this cycle
    entry='double',
    # items to be defined
    MASTER_ARPEGE='cy36t1_masterodb-op2.12.SX20r411.x.exe',
    RTCOEF_TGZ='var.sat.misc_rtcoef.12.tgz',
    CLIM_ARPEGE_T798='clim_arpege.tl798.02',
    CLIM_DAP_GLOB15='clim_dap.glob15.07',
    MAT_FILTER_GLOB15='mat.filter.glob15.07',
    NAMELIST_ARPEGE='cy36t1_op2.11.nam'
)

print genv.cycles()

print t.line

input = (

    rl(
        prvin,
        role = 'Analysis',
        kind = 'analysis',
        local = 'ICMSHFCSTINIT',
    ),
    
    rl(
        provider = prvcst,
        role = 'RtCoef',
        kind = 'rtcoef',
        local = 'rtcoef.tgz'
    ),
    
    rl(
        provider = prvcst,
        role = 'ClimatologicalModelFile',
        kind = 'modelclim',
        month = rundate.month,
        local = 'Const.Clim',
    ),
    
    rl(
        provider = prvcst,
        role = 'ClimatologicalBDAPFile',
        kind = 'bdapclim',
        month = rundate.month,
        geometry = geoBDAP,
        local = 'const.clim.[geometry::area]',
    ),
    
    rl(
        provider = prvcst,
        role = 'MatFilter', 
        kind = 'matfilter',
        scopedomain = geoBDAP,
        local = 'matrix.fil.[scopedomain::area]',
    ),
    
    rl(
        provider = prvcst,
        role = 'DrivingNamelist',
        kind = 'namelist',
        source = 'namelistfcp',
        local = 'fort.4'
    ),
    
    rl(
        provider = prvcst,
        role = 'SelectionNamelist',
        kind = 'namselect',
        source='select_p',
        term = (0,3),
        local = 'select_p[term]',
    )
)

arpege = rl(
    provider = prvcst,
    role = 'Model',
    kind = 'nwpmodel',
    binopts = '-vmeteo -eFCST -c001 -asli -t600 -fh3',
    local = 'ARPEGE.EX',
).pop()

outputs = (

    rl(
        provider = prvout,
        role = 'ModelStateOutput',
        kind = 'historic',
        term = (0,3),
        local = 'ICMSHFCST+[term]',
    ),
    
    rl(
        provider = prvout,
        role = 'GridPointOutput',
        kind='gridpoint',
        origin='historic',
        geometry=geoBDAP,
        nativefmt='fa',
        term=(0,3),
        local='PFFPOS[geometry::area]+[term]'
    ),
    
    rl(
        provider = prvout,
        role = 'ModelListing',
        kind = 'listing',
        task = 'forecast',
        local = 'listing.forecast'
    )

)

for rh in input:
    for r in rh :
        print t.line, r.idcard()
        r.get()

print t.line

arpege.get()
print arpege.idcard()

print t.line

x = tb.component(engine='parallel')

print t.prompt, x.puredict()

x.run(arpege, mpiopts = dict(nn=1, nnp=4))

for rh in outputs:
    for r in rh :
        print t.line, r.idcard()
        r.put()

print t.prompt, 'Duration time =', t.duration()

vortex.exit()