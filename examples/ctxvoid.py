#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import vortex
from vortex.tools import date

import vortex.data
import vortex.algo

from vortex.data.geometries import SpectralGeometry, GridGeometry

import common.data
import olive.data
import gco.data
import gco.syntax


t = vortex.sessions.ticket()
c = t.context
g = t.glove

t.warning()

e = t.env
sh = t.system()
sh.cd(e.HOME + '/tmp/rundir')

print t.prompt, sh.pwd()

arpege_cycle = 'cy36t1_op2.16'

#domain = ['GLOB15','GLOB25','EURAT01','EUROC25','GLOB05']
domains = [ 'GLOB15' ]
rundate = date.Date('2011092200')
geo = SpectralGeometry(id='Current op', area='france', truncation=798, lam=False)
geoBDAP = GridGeometry(area='GLOB15',resolution=1.5, runit='dg')


fpenv = vortex.toolbox.defaults(
    geometry=geo,
    namespace='olive.cache.fr',
    date=rundate,
    cutoff='production',
    model='arpege'
)

print t.line

if g.realkind == 'opuser':
    prvin  = dict()
    prvout = dict()
    prvcst = dict()
else:
    prvin  = dict(experiment='99A0', block='canari')
    prvout = vortex.toolbox.provider(experiment='A001', block='forecast')
    prvcst = vortex.toolbox.provider(genv=arpege_cycle)

print t.prompt, fpenv()
print t.prompt, prvin

print t.line

vortex.toolbox.input(
    prvin,
    role = 'Analysis',
    kind = 'analysis',
    local = 'ICMSHFCSTINIT',
)

print t.line

for section in c.sequence.inputs():
    print section.role, section.stage, section.kind, section.intent, section
    print ' > ', section.rh
    print section.rh.get()

print t.line

for section in c.sequence:
    print section.role, section.stage, section.kind, section.intent, section

print t.line

print 'Sequence inputs:', c.sequence.inputs()
