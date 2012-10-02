#!/bin/env python
# -*- coding:Utf-8 -*-

from vortex import sessions, toolbox

import vortex.data
from vortex.data.geometries import SpectralGeometry
from vortex.syntax import footprint

import common.data
import olive.data
import gco.data
import gco.syntax


t = sessions.ticket()
t.info()

mysys = t.system()
myenv = mysys.env

mysys.chdir(myenv.TMPDIR + '/rundir')
print t.prompt, mysys.pwd

#prvin  = toolbox.provider(experiment='99A0', block='canari', namespace='olive.archive.fr')
prvin  = toolbox.provider(suite='oper', vapp='arpege')
prvout = toolbox.provider(experiment='A001', block='canari', namespace='open.meteo.fr')

print t.line

fpenv = footprint.envfp(
    model='arpege',
    geometry = SpectralGeometry(id='Current op', area='france', truncation=798),
    date='2011092200',
    cutoff='production',
)

#MTOOL include files=toto.[this:target]
print t.prompt, fpenv()

print t.line

a =  toolbox.rh(
    provider=prvin,
    kind='analysis',
    local='ICMSHFCSTINIT',
)

print t.line, a.idcard()

print a.get()

mysys.dir()

a.provider = prvout

print t.line, a.idcard()

print t.prompt, 'Duration time =', t.duration()

a.put()

print t.prompt, 'Duration time =', t.duration()
