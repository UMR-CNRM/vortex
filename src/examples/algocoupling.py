#!/bin/env python
# -*- coding:Utf-8 -*-

from vortex import sessions, toolbox
import vortex.data
import common.data
import common.algo
import olive.data
import gco.data
from vortex.syntax import footprint
from vortex.tools import env
from vortex.data.geometries import SpectralGeometry
from gco.tools import genv

t = sessions.ticket()
t.warning()

g = t.glove
e = t.env
c = t.context


cr = vortex.data.resources.catalog()
cr.track = True

myenv = env.current()
mysys = t.system()

mysys.chdir(myenv.TMPDIR + '/rundir')
mysys.rmglob('-rf','*')

fpenv = footprint.envfp(
    spool=myenv.HOME + '/gco-tampon',
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



t.warning()
#toolbox.input(
input= (toolbox.rload(
            kind='clim_model', 
            genv=arpege_cycle,
            local='climarpege',
            model='arpege',
            geometry=SpectralGeometry(id='Current op',  truncation='798'),
            month='09',
            role='Fatherclim'),
        toolbox.rload(
            kind='clim_model', 
            genv=aladin_cycle,
            local='climaladin',
            month='09',
            role='Sonclim',
            model='aladin',
            geometry=SpectralGeometry(id='Current op', area='reunion', resolution='08km00')),
        toolbox.rload(
            kind='namelist', 
            genv=aladin_cycle,
            local='my_namelist',
            role='namelist',
            binary='aladin',
            model='aladin',
            source='namel_e927'),
        toolbox.rload(
            kind='historic', 
            date = '2012093000', 
            cutoff='production',
            namespace='[suite].archive.fr',
            geometry=SpectralGeometry(id='Current op', truncation='798'),
            local='ICMSHARPE+[term]',
            suite='oper',
            term='00,3',
            model='arpege',
            igakey='arpege',
            role='Couplingfile'),
       )



print t.line

t.warning()
for rh in input:
    for r in rh:
        r.get()

        
#rx = toolbox.rh(remote=e.home + '/tmp/test.sh', file='test.sh', rawopts='coucou', language=e.trueshell())
#rx = toolbox.rh(remote=e.home + '/tmp/test.sh', file='testcpl.sh', model='arpege', kind='ifsmodel')
rx = toolbox.rh(remote=e.home + '/tmp/testcpl.sh', file='testcpl.sh', language='bash', kind='script')

print t.line

#for section in c.sequence.inputs():
#    print section.role, section.stage, section.kind, section.intent, section
#    print ' > ', section.rh
#    section.rh.get()
#    print section.role, section.stage, section.kind, section.intent, section


print t.prompt, 'Resource tracker =', cr.track


rx.get()

print t.line

#print cr.track.toprettyxml(indent='    ')

print t.line


x = toolbox.component(kind='couplingexpresso', timescheme='eul', model='arpifs', fcterm=0, timestep=415.385, engine='exec', interpreter='bash')
print t.prompt, 'Engine is', x

print t.line

t.debug()
x.run(rx, mpiopts=dict(n=2))

print t.line
print t.prompt, 'Duration time =', t.duration()
print t.line
