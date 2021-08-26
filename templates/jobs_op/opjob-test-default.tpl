#!$python $pyopts
# -*- coding: utf-8 -*-
#SBATCH --cpus-per-task=$openmp
#SBATCH --export=NONE
#SBATCH --job-name=$name
#SBATCH --mem=$mem
#SBATCH --nodes=$nnodes
#SBATCH --ntasks-per-node=$ntasks
#SBATCH --partition=$partition
#SBATCH --qos=$qos
#SBATCH --time=$time
#SBATCH --$exclusive
#SBATCH --account=$account
#SBATCH --$verbose
#SBATCH --no-requeue

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

vortexbase = os.path.join(op_rootapp, 'vortex')

op_xpid      = op_rootapp.split('/')[-3]
op_vapp      = op_rootapp.split('/')[-2]
op_vconf     = op_rootapp.split('/')[-1]
op_suitebg   = $suitebg
op_cutoff    = '$cutoff'
op_rundate   = $rundate
op_runtime   = $runtime
op_runstep   = $runstep
op_iniconf   = '{0:s}/conf/{1:s}_{2:s}.ini'.format(op_rootapp, op_vapp, op_vconf)
op_fullplay  = $fullplay
op_warmstart = $warmstart
op_refill    = $refill
op_mail      = $mail
op_jeeves    = '{0}_$jeeves'.format(op_xpid)
op_jroute    = '{0}_$jroute'.format(op_xpid)
op_phase     = $phase
op_hasmember = $hasmember

sys.stderr = sys.stdout

# Alter path for extra packages
for d in [os.path.join(op_rootapp, p) for p in ($extrapythonpath)]:
    if os.path.isdir(d):
        sys.path.insert(0, d)
    else:
        sys.stderr.write("<< {:s} >> does not exists : it won't be pre-pended to sys.path\n"
                         .format(d))
# Alter path for current tasks + vortex (mandatory)
sys.path.insert(0, os.path.join(vortexbase, 'site'))
sys.path.insert(0, os.path.join(vortexbase, 'src'))
sys.path.insert(0, op_rootapp)

import locale
locale.setlocale(locale.LC_ALL, '$defaultencoding')

from bronx.system.interrupt import SignalInterruptError
import footprints
import vortex
import vortex.layout.jobs
import iga.tools.op
import $package.$task as todo

ja = footprints.proxy.jobassistant(kind = 'op_default',
                                   modules = footprints.stdtypes.FPSet(($loadedmods)),
                                   addons = footprints.stdtypes.FPSet(($loadedaddons)),
                                   ldlibs = footprints.stdtypes.FPSet(($ldlibs)),
                                   special_prefix='op_',
                                   )
ja.add_plugin('epygram_setup')
for pkind in ($loadedjaplugins):
    ja.add_plugin(pkind)

try:
    t, e, sh = ja.setup(actual=locals())
    from vortex.tools.actions import actiond as ad
    ad.opmail_off()
    ad.dmt_off()
    ad.route_off()
    ad.phase_tune(jname='{0}_phase'.format(op_xpid))
    ad.phase_on()
    opts = dict(jobassistant=ja, play=op_fullplay)
    driver = todo.setup(t, **opts)
    driver.setup()
    driver.run()
    ja.complete()
except (Exception, SignalInterruptError, KeyboardInterrupt) as trouble:
    ja.fulltraceback(trouble)
    ja.rescue()
finally:
    ja.finalise()
    ja.close()

