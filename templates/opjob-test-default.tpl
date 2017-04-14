#!$python $pyopts
# -*- coding: utf-8 -*-
#SBATCH --cpus-per-task=$openmp
#SBATCH --export=NONE
#SBATCH --job-name=$name
#SBATCH --mem=$mem
#SBATCH --nodes=$nnodes
#SBATCH --ntasks-per-node=$ntasks
#SBATCH --partition=$partition
#SBATCH --qos=essai
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
    op_rootapp  = os.path.dirname(os.environ["DMT_PATH_EXEC"])
else:
    op_rootapp  = os.path.dirname(os.getcwd())
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
op_jeeves   = '{0}_$jeeves'.format(op_xpid)
op_phase    = $phase

sys.stderr = sys.stdout

pathdirs = [ os.path.join(op_rootapp, xpath) for xpath in ('', 'vortex/site', 'vortex/src', 'epygram', 'epygram/site', 'epygram/grib_api') ]
for d in pathdirs :
    if os.path.isdir(d):
        sys.path.insert(0, d)

import footprints
import vortex
import vortex.layout.jobs
import  iga.tools.op

ja = footprints.proxy.jobassistant(kind = 'op_default',
                                   modules = footprints.stdtypes.FPSet((
                                       'common', 'gco', 'previmar', 'iga',
                                       'vortex.tools.lfi', 'vortex.tools.odb', 'vortex.tools.grib',
                                       'vortex.tools.surfex', 'vortex.tools.rawfiles',
                                       'common.util.usepygram')),
                                   addons = footprints.stdtypes.FPSet(('lfi', 'iopoll', 'odb', 'sfx', 'grib', 'rawfiles')),
                                   special_prefix='op_',
                                   )


import $package.$task as todo

try:
    t, e, sh = ja.setup(actual=locals())
    from vortex.tools.actions import actiond as ad
    ad.opmail_on()
    ad.route_off()
    ad.phase_tune(jname='{0}_phase'.format(op_xpid))
    ad.phase_on()
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

