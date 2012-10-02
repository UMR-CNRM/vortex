#!/bin/env python
# -*- coding:Utf-8 -*-

from vortex import sessions, toolbox
import vortex.data
import common.data
import common.algo
import olive.data
from vortex.data.geometries import SpectralGeometry

t = sessions.ticket()
t.warning()

g = t.glove
e = t.env
c = t.context


cr = vortex.data.resources.catalog()
cr.track = True

#toolbox.input(
input=(toolbox.rload(
            kind='elscf', 
            date = '2012071900', 
            cutoff='production',
            namespace='[suite].archive.fr',
            geometry=SpectralGeometry(id='Current op', area='frangp', resolution='02km50'),
            local='ELSCFAROME+[term]',
            source='arpege',
            suite='oper',
            term='00,3',
            model='arome',
            igakey='arome',
            role='BoundaryCondition'),
       toolbox.rload(
            kind='elscf', 
            remote='ELSCFAROME+0000',
            local='Inifile',
            date = '2012071900', 
            cutoff='production',
            geometry=SpectralGeometry(id='Current op', area='frangp', resolution='02km50'),
            source='arpege',
            term='00',
            model='arome',
            role='InitialCondition')
       )


print t.line

for rh in input:
    for r in rh:
        r.get()

        
#rx = toolbox.rh(remote=e.home + '/tmp/test.sh', file='test.sh', rawopts='coucou', language=e.trueshell())
rx = toolbox.rh(remote=e.home + '/tmp/test.sh', file='test.sh', model='arpege', kind='ifsmodel')

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


x = toolbox.component(kind='fclam', timestep=900, engine='parallel')
print t.prompt, 'Engine is', x

print t.line

x.run(rx, mpiopts=dict(n=2))

print t.line
print t.prompt, 'Duration time =', t.duration()
print t.line
