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

if 'DMT_PATH_EXEC' in os.environ:
    op_rootapp  = os.path.realpath(os.environ["DMT_PATH_EXEC"]).rstrip('/jobs')
else:
    op_rootapp  = os.path.realpath(os.getcwd()).rstrip('/jobs')



op_jobname  = '$name'
op_xpid     = op_rootapp.split('/')[-3]
op_vapp     = op_rootapp.split('/')[-2]
op_vconf    = op_rootapp.split('/')[-1]
op_suitebg  = '$suitebg'
op_cutoff   = '$cutoff'
op_rundate  = $rundate
op_runtime  = $runtime
op_runstep  = $runstep
op_jobfile  = '$file'
op_thisjob  = '{0:s}/jobs/{1:s}.py'.format(op_rootapp, op_jobfile)
op_iniconf  = '{0:s}/conf/{1:s}_{2:s}.ini'.format(op_rootapp, op_vapp, op_vconf)
op_alarm    = $alarm
op_archive  = $archive
op_fullplay = $fullplay
op_refill   = $refill
op_mail     = $mail 
op_jeeves   = '$jeeves'

oplocals = locals()

sys.stderr = sys.stdout

pathdirs = [ os.path.join(op_rootapp, xpath) for xpath in ('', 'vortex/site', 'vortex/src', 'epygram', 'epygram/site', 'epygram/grib_api') ]
for d in pathdirs :
    if os.path.isdir(d):
        sys.path.insert(0, d)

import iga.tools.op as op
import $package.$task as todo
from vortex import toolbox
from vortex.tools.actions import actiond as ad
from iga.tools import actions
from iga.tools import services

try:
    t = op.setup(actual=oplocals)
    e = op.setenv(t, actual=oplocals)
    ad.opmail_on()
    ad.route_off()
    toolbox.defaults(smtpserver='smtp.meteo.fr', sender='dt_dsi_op_iga_sc@meteo.fr')
    opts = t.sh.rawopts(defaults=dict(play=op_fullplay))
    driver = todo.setup(t, **opts)
    driver.setup()
    driver.run()
    op.complete(t)
except Exception as trouble:
    op.fulltraceback(locals())
    op.simulate_complete(t)
finally:
    print 'Bye bye Op...'
