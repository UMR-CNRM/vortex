#!/usr/bin/env python
# -*- coding:Utf-8 -*-

# Status : TODO From a long long time...

import vortex
from vortex.data import geometries
from vortex.tools import date
import common.data
import olive.data
import gco.data
import gco.syntax

t = vortex.sessions.ticket()

#lh1 = toolbox.rload(toto='titi',kind='modelclim', model='arpege', truncation='798,107', month='10,11',genv='cy36t1_op1.01',local='clim.(month).(truncation)')
#lh2 = toolbox.rload(kind='bdapclim', model='arpege', month='11',genv='cy36t1_op1.01',local='clim.(month).(domain)',domain='GLOB15,EUROC25')
#lh8 = toolbox.rload( kind='miscgenv',remote='tmp/rtcoef.tgz',local='rtcoef')
#lh4 = toolbox.rload( kind='miscgenv', gvar='RTCOEFTGZ', genv='cy36t1_op1.01',local='rtcoeftgz')
#lh8= toolbox.rload(kind='matfilter', genv='cy36t1_op1.01', domain='glob15,glob05', local='mat_filter_(domain)')
#lh6 = toolbox.rload(kind='matfilter',block='rep', xpid='99AZ', domain='glob15,glob05', local='mat_filter_(domain)', stretching='024',truncation='798')
#lh8 = toolbox.rload( kind='namelist', genv='cy36t1_op1.01', local='fort.4', source='namelistfp', binary='arpege')
#lh8 = toolbox.rload( kind='namutil',genv='cy36t1_op1.01',local='fort.4',source='namelist_toto', binary='utilities')
#lh8 = toolbox.rload( kind='namelist',remote='/tmp/my_namelist',local='fort.4')
#lh8 = toolbox.rload( kind='namselect',genv='cy36t1_op1.01',local='fort.4',source='select_fp', binary='arpege' , term=0,nproc='2')
#lh8 = toolbox.rload( kind='historic',local='ICMSHARPE+0003',model='arpege',date='2011111400',cutoff='production', term=3,experiment='99AA',block='forecast')
#lh8 = toolbox.rload( kind='historic',local='ICMSHARPE+0003',model='arpege',date='2011111400',cutoff='production', term=3,remote='/home/marp009/titi')
#lh8= toolbox.rload( kind='gridpoint',local='GRID+0003',model='arpege',date='2011111400',cutoff='production', term=3,origin='historic',format='grib', domain='GLOB15',remote='/home/marp009/titi')
#lh8= toolbox.rload( kind='gridpoint',local='GRID+0003',model='arpege',date='2011111400',cutoff='production', term=3,origin='analyse',format='fa', domain='GLOB15',experiment='99AA',block='forecast')
#lh8 = toolbox.rload( kind='listing',experiment='99AA',block='forecast',date='2011111400',cutoff='assim',task='fc',local='listing.forecast')
#lh8 = toolbox.rload( kind='namselectdef',genv='cy36t1_op1.01',local='xxt.def',source='xxt.def', binary='arpege' )
#lh8 = toolbox.rload(kind='modelclim', remote='tmp/climmodel.11',local='Const.Clim', truncation='798',month='11', model='arpege')
#lh8 = toolbox.rload( kind='namelist',remote='tmp/namelistfcp',local='fort.4')
#lh8=toolbox.rload( kind='elscf',experiment='99AA',block='coupling',term=3,date='2011111400',cutoff='production',model='arome',area='frangp',local='toto')
#lh8= toolbox.rload( kind='gridpoint',local='GRID+0003',model='arpege',date='2011111400',cutoff='production', term=3,origin='analyse',native_fmt='fa', domain='GLOB15',experiment='99AA',block='forecast')
#lh8=toolbox.rload(namespace='[suite].archive.fr',kind='elscf',suite='oper',term=3,date='2011111400',cutoff='production',model='aladin',area='france',local='toto')
#lh8=toolbox.rload(namespace='[suite].archive.fr',kind='analysis',filling='surf',area='france',suite='oper',date='2011111400',cutoff='assim',member='3',model='aearp',local='toto')
#lh8 = toolbox.rload( namespace='[suite].archive.fr',kind='historic',local='toto',model='aladin',date='2011111400',cutoff='production', term=3,suite='oper',area='testmp2')
#lh8= toolbox.rload( kind='gridpoint',local='GRID+0003',model='arpege',date='2011111400',cutoff='production', term=3,origin='historic',nativefmt='grib', domain='GLOB15',suite='oper')

print t.line

vortex.toolbox.fast_resolve = True

lh8 = vortex.toolbox.rload(
    kind='gridpoint', model='arpege', vapp='arpege', vconf='france',
    date=date.today(), cutoff='production', term=3, origin='historic',
    nativefmt='grib', suite='oper',
    geometry = geometries.getbyname('glob15'),
    local = 'GRID+[term::fmth]',
)

lrh = (lh8,)
for rh in lrh:
    for r in rh:
        print t.line, r.idcard(), t.line
        print 'GET', r.location(), '...', r.get()

print t.line
