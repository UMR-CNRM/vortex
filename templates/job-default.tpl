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

op_jobname  = '$name'
op_xpid     = '$xpid'
op_suitebg  = '$suitebg'
op_vapp     = '$vapp'
op_vconf    = '$vconf'
op_cutoff   = '$cutoff'
op_rundate  = $rundate
op_runtime  = $runtime
op_runstep  = $runstep
op_rootapp  = '$rootapp/{0:s}/{1:s}/{2:s}'.format(op_suitebg, op_vapp, op_vconf)
op_jobfile  = '$file'
op_thisjob  = '{0:s}/jobs/{1:s}.py'.format(op_rootapp, op_jobfile)
op_iniconf  = '{0:s}/conf/{1:s}_{2:s}_{3:s}.ini'.format(op_rootapp, op_vapp, op_vconf, '$taskconf')
op_alarm    = $alarm
op_archive  = $archive
op_public   = $public
op_fullplay = $fullplay
op_retry    = $retry
op_tplfile  = '$tplfile'
op_tplinit  = '$tplinit'
op_mail     = $mail
op_jeeves   = '$jeeves'

oplocals = locals()

import os, sys
sys.stderr = sys.stdout

pathdirs = [ os.path.join(op_rootapp, xpath) for xpath in ('', 'src', 'vortex/site', 'vortex/src') ]
sys.path.extend(
    [ os.path.realpath(d) for d in pathdirs if os.path.isdir(d) ]
)

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
    toolbox.defaults(smtpserver='smtp.meteo.fr', sender='dsiop_igasc@meteo.fr')
    opts = t.sh.rawopts(defaults=dict(play=op_fullplay))
    driver = todo.setup(t, **opts)
    driver.setup()
    driver.run()
    op.complete(t)
except Exception as trouble:
    op.fulltraceback(locals())
    op.rescue(actual=locals())
finally:
    print 'Bye bye Op...'
