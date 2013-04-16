#!/bin/env python
# -*- coding:Utf-8 -*-

# Status : TODO From a long long time...

from vortex import sessions, toolbox
import vortex.data
import olive.data
import gco.data
import gco.syntax

t = sessions.ticket()
#t.debug()

#lh1 = toolbox.rload(toto='titi',kind='modelclim', model='arpege', truncation='798,107', month='10,11',genv='cy36t1_op1.01',local='clim.(month).(truncation)')

#lh2 = toolbox.rload(kind='bdapclim', model='arpege', month='11',genv='cy36t1_op1.01',local='clim.(month).(domain)',domain='GLOB15,EUROC25')

#lh8 = toolbox.rload( kind='miscgenv',remote='tmp/rtcoef.tgz',local='rtcoef')
#lh4 = toolbox.rload( kind='miscgenv', gvar='RTCOEFTGZ', genv='cy36t1_op1.01',local='rtcoeftgz')
#lh8= toolbox.rload(kind='matfilter', genv='cy36t1_op1.01', domain='glob15,glob05', local='mat_filter_(domain)')
#lh6 = toolbox.rload(kind='matfilter',block='rep', xpid='99AZ', domain='glob15,glob05', local='mat_filter_(domain)', stretching='024',truncation='798')
#lh8 = toolbox.rload( kind='namelist', genv='cy36t1_op1.01', local='fort.4', source='namelistfp', binary='arpege')
#lh8 = toolbox.rload( kind='namutil',genv='cy36t1_op1.01',local='fort.4',source='namelist_toto', binary='utilities')
#lh8 = toolbox.rload( kind='namelist',remote='/tmp/my_namelist',local='fort.4')
#lh8 = toolbox.rload( kind='namselect',genv='cy36t1_op1.01',local='fort.4',source='select_fp', binary='arpege' , term='0',nproc='2')
#lh8 = toolbox.rload( kind='historic',local='ICMSHARPE+0003',model='arpege',date='2011111400',cutoff='production', term='3',experiment='99AA',block='forecast')
#lh8 = toolbox.rload( kind='historic',local='ICMSHARPE+0003',model='arpege',date='2011111400',cutoff='production', term='3',remote='/home/marp009/titi')
#lh8= toolbox.rload( kind='gridpoint',local='GRID+0003',model='arpege',date='2011111400',cutoff='production', term='3',origin='historic',format='grib', domain='GLOB15',remote='/home/marp009/titi')
#lh8= toolbox.rload( kind='gridpoint',local='GRID+0003',model='arpege',date='2011111400',cutoff='production', term='3',origin='analyse',format='fa', domain='GLOB15',experiment='99AA',block='forecast')
#lh8 = toolbox.rload( kind='listing',experiment='99AA',block='forecast',date='2011111400',cutoff='assim',task='fc',local='listing.forecast')
#lh8 = toolbox.rload( kind='namselectdef',genv='cy36t1_op1.01',local='xxt.def',source='xxt.def', binary='arpege' )
#lh8 = toolbox.rload(kind='modelclim', remote='tmp/climmodel.11',local='Const.Clim', truncation='798',month='11', model='arpege')
#lh8 = toolbox.rload( kind='namelist',remote='tmp/namelistfcp',local='fort.4')
#lh8=toolbox.rload( kind='elscf',experiment='99AA',block='coupling',term='3',date='2011111400',cutoff='production',model='arome',area='frangp',local='toto')
#lh8= toolbox.rload( kind='gridpoint',local='GRID+0003',model='arpege',date='2011111400',cutoff='production', term='3',origin='analyse',native_fmt='fa', domain='GLOB15',experiment='99AA',block='forecast')

print t.line

#lh8=toolbox.rload(namespace='[suite].archive.fr',kind='elscf',suite='oper',term='3',date='2011111400',cutoff='production',model='aladin',area='france',local='toto')
#lh8=toolbox.rload(namespace='[suite].archive.fr',kind='analysis',filling='surf',area='france',suite='oper',date='2011111400',cutoff='assim',member='3',model='aearp',local='toto')
#lh8 = toolbox.rload( namespace='[suite].archive.fr',kind='historic',local='toto',model='aladin',date='2011111400',cutoff='production', term='3',suite='oper',area='testmp2')
#lh8= toolbox.rload( kind='gridpoint',local='GRID+0003',model='arpege',date='2011111400',cutoff='production', term='3',origin='historic',nativefmt='grib', domain='GLOB15',suite='oper')
lh8= toolbox.rload( kind='gridpoint',local='GRID+0003',area='france', model='aladin',date='2011111406',cutoff='production', term='3',origin='historic',nativefmt='grib', domain='GLOB15',suite='oper')
print t.line

def show(r):
    print 'Provider kind : ', r.provider.realkind()
    print 'Provider attr : ', r.provider._attributes
    print 'Provider pathname : ', r.provider.pathname(r.resource)
    print 'Container kind: ', r.container.realkind()
    print 'Container attr : ', r.container._attributes
    print 'Resource kind : ' ,r.resource.realkind()
    print 'Resource archive basename  :' , r.resource.archive_basename()
    print 'Resource attr : ', r.resource._attributes
    
    print 'Options       : ', r.options

lrh=(lh8,)
for rh in lrh:
    for r in rh :
        show(r)
        r.get()
        
        
#a=lh8.pop()
#a.get()

"""
c = lh.pop()
print c
print 'Resource gvar :', c.resource.gvar
print 'Complete ?', c.complete
print 'Uri ?', c.source()
"""
"""
lh = toolbox.rload(kind='climbdap', domain='glob15', model='arpege', month=10, remote='/tmp/toto', file='titi')

c = lh.pop()

print c
print 'Resource gvar :', c.resource.gvar
print 'Complete ?', c.complete
print 'Uri ?', c.source()

print t.duration()
"""