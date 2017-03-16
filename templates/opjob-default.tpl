#!$python $pyopts
# -*- coding: utf-8 -*-
#SBATCH --cpus-per-task=$openmp
#SBATCH --export=NONE
#SBATCH --job-name=$name
#SBATCH --mem=$mem
#SBATCH --nodes=$nnodes
#SBATCH --ntasks-per-node=$ntasks
#SBATCH --partition=$partition
#SBATCH --time=$time
#SBATCH --$exclusive
#SBATCH --$verbose

# Build time: $create
# Build user: $mkuser
# Build host: $mkhost
# Build opts: $mkopts

import os, sys, re

op_jobname  = '$name'
if 'DMT_PATH_EXEC' in os.environ:
    op_rootapp  = re.sub(os.path.sep + 'jobs$', '',
                         os.path.realpath(os.environ["DMT_PATH_EXEC"]))
else:
    op_rootapp  = re.sub(os.path.sep + 'jobs$', '', 
                         os.path.realpath(os.getcwd()))
op_xpid     = op_rootapp.split('/')[-3]
op_vapp     = op_rootapp.split('/')[-2]
op_vconf    = op_rootapp.split('/')[-1]
op_suitebg  = $suitebg
op_cutoff   = '$cutoff'
op_rundate  = $rundate
op_runtime  = $runtime
op_runstep  = $runstep
op_iniconf  = '{0:s}/conf/{1:s}_{2:s}.ini'.format(op_rootapp, op_vapp, op_vconf)
op_fullplay = $fullplay
op_refill   = $refill
op_mail     = $mail
op_jeeves   = '$jeeves'


sys.stderr = sys.stdout

pathdirs = [ os.path.join(op_rootapp, xpath) for xpath in ('', 'vortex/site', 'vortex/src', 'epygram', 'epygram/site', 'epygram/grib_api') ]
for d in pathdirs :
    if os.path.isdir(d):
        sys.path.insert(0, d)

import footprints
import vortex
import vortex.layout.jobs
import iga.tools.op

ja = footprints.proxy.jobassistant(kind = 'op_default',
                                   modules = footprints.stdtypes.FPSet((
                                       'common', 'gco', 'previmar', 'iga',
                                       'vortex.tools.lfi', 'vortex.tools.odb', 'vortex.tools.grib', 'vortex.tools.surfex',
                                       'common.util.usepygram')),
                                   addons = footprints.stdtypes.FPSet(('lfi', 'iopoll', 'odb', 'sfx', 'grib')),
                                   special_prefix='op_',
                                   )


import $package.$task as todo

try:
    t, e, sh = ja.setup(actual=locals())
    from vortex.tools.actions import actiond as ad
    ad.opmail_on()
    ad.route_on()
    opts = dict(jobassistant=ja, play=op_fullplay)
    driver = todo.setup(t, **opts)
    driver.setup()
    driver.run()
    ja.complete()
except Exception as trouble:
    ja.fulltraceback(trouble)
    ja.rescue()
finally:
    ja.finalise()
    ja.close()

