#!/usr/bin/env python
# -*- coding:Utf-8 -*-
# vim: set ts=4 sw=4 expandtab et:

from vortex import sessions, toolbox
from vortex.tools import env
from vortex.syntax.stdattrs import Term
import mercator.data


t = sessions.ticket()
mysys = t.system()
myenv = env.current()
t.warning()

local_dir='/tmp/'
if myenv.RUN_TMP: local_dir=myenv.RUN_TMP+'/'

# resources descriptions:
grid = 'orca025'
rd = dict(
    cexper = grid.upper()+'_LIM-T00',
    namespace = 'mercator.archive.fr',
    grid = grid,
)

namelists = [ 
    ('main', 'namelist'), 
    ('io','namelistio'), 
    ('ice', 'namelist_ice'),
]

statics = [
    ('bathymetry', 'bathymetry.nc'),
    ('runoff', 'runoff.nc'),
]

resources_list = []

### model Namelist
for n in namelists:
    resources_list.append( toolbox.rload(rd, 
        kind = 'namelist', nmtype=n[0], local=local_dir+n[1]).pop()
    )

### Statics files
for s in statics:
    resources_list.append( toolbox.rload(rd, 
        kind=s[0], grid=grid, local=local_dir+s[1]).pop()
    )

### moorings positions:
for i in range(1,16):
    id_moor = Term(i)
    resources_list.append( toolbox.rload(rd, 
        kind='moorings', grid=grid, term=id_moor, 
        local=local_dir+'position_ijproc.moor_bin_'+str(id_moor)).pop()
    )

## mooring:
for type in [ 'moor', 'sect' ]:
    resources_list.append( toolbox.rload(rd,
        kind='moorings', model='psy3',grid=grid, type=type, 
        local=local_dir+'position.'+type+'.PSY3V2R2').pop()
    )

## coordinates
resources_list.append( toolbox.rload(rd,
    kind = 'coordinates', grid=grid, 
    local=local_dir+'coordinates_'+grid.upper()+'_LIM.nc').pop()
)

## binaries
resources_list.append( toolbox.rload(rd,
    kind = 'binary', assim=True, type='main', term=0, 
    local=local_dir+'/palm_main').pop()
)

for id_block in range(1,5):
    resources_list.append( toolbox.rload(rd,
        kind = 'binary', assim=True, type='block', term=id_block, 
        local=local_dir+'main_block_'+str(id_block)).pop()
    )

resources_list.append( toolbox.rload(rd,
    kind = 'binary', assim=True, type='pil', term=0, 
    local=local_dir+'SAMIAU_PALM_MULTIMP.pil').pop()
)

resources_list.append( toolbox.rload(rd,
    kind = 'binary', assim=False, term=0, type='build_nc', 
    local=local_dir+'build_nc').pop()
)

resources_list.append( toolbox.rload(rd,
    kind = 'binary', assim=True, term=0, type='anolist', 
    local=local_dir+'createlisttxtbylib.x').pop()
)

## climato
clim_month='11'
clim_year='05'
clim_fields = [ 'Sal', 'Tem' ]
for f in clim_fields:
    resources_list.append( toolbox.rload(rd,
        kind = 'climatology', grid=grid, year=clim_year, month=clim_month, field=f, 
        local=local_dir+'Levitus'+clim_year+'_'+f+'_'+grid.upper()+'m'+clim_month+'.nc').pop()
    )

## assim files:
#t.debug()
resources_list.append( toolbox.rload(rd, 
    kind='bathymetry', assim=True, grid=grid, 
    local=local_dir+'bathy3D.cmz').pop()
)

resources_list.append( toolbox.rload(rd,
    kind='namelist', assim=True, nmtype='kernel', 
    local=local_dir+'kernel.prm').pop()
)

resources_list.append( toolbox.rload(rd,
    kind='namelist', assim=True, nmtype='palm', 
    local=local_dir+'palm.prm').pop()
)

bogus_namelist = [
    ( 'hbr', 'DS_BOGUS_HBR.list'),
    ( 'hbrst', 'DS_BOGUS_HBRST.list'),
    ( 'gradhbr', 'DS_BOGUS_gradHBR.list'),
    ( 'hunderice', 'IS_BOGUS_HunderICE.list'),
    ( 'runoff', 'VP_BOGUS_RUNOFF.list'),
    ( 'tsuvontrop', 'VP_BOGUS_TSUVonTROP.list'),
    ( 'tsuvunderice', 'VP_BOGUS_TSUVunderICE.list'),
]

for bogus in bogus_namelist:
    resources_list.append( toolbox.rload(rd,
        kind='namelist', assim=True, nmtype=bogus[0], 
        local=local_dir+bogus[1]).pop()
    )


#resources_list.append( toolbox.rload(rd,
#        kind='atmforcing', grid=grid, field='BULKCLOU', origin='ECMWF', 
#        timecoverage='daily', start_date='20111228', end_date='20111228',
#        remote='proutproutprout',
#        local=local_dir+'test.nc').pop()
#    )

################################################################################
print t.prompt, "Resources loading duration=",t.duration()

#exit() ### cougar down ...

# fetch all resources
for r in resources_list:
    try:
        print t.prompt, "fetch resource: "+r.provider.uri(r.resource)
        r.get()
    except TypeError:
        print dir(r.resource)
        print r.resource.retrieve_footprint()
        raise

print t.prompt, "Resources get duration=",t.duration()

# cleanup
total_size = 0
for r in resources_list: 
    file = r.container.localpath()
    file_size = mysys.path.getsize(file)
    total_size += file_size
    print t.prompt, file_size,' -> '+mysys.path.dirname(file)+'/'+mysys.path.basename(file)
    mysys.unlink(file)

print t.prompt, "Total size fetched = ",float(total_size)/1024/1024,"MO"
print t.prompt, "Total duration=",t.duration()


