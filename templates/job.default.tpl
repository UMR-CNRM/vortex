#!$python $pyopts
#SBATCH --cpus-per-task=$openmp
#SBATCH --export=NONE
#SBATCH --job-name=$name
#SBATCH --mem=$mem
#SBATCH --nodes=$nnodes
#SBATCH --ntasks-per-node=$ntasks
#SBATCH --partition=$partition
#SBATCH --time=$time
#SBATCH --exclusive
#SBATCH --verbose

# Build time: $create
# Build user: $mkuser
# Build host: $mkhost

op_jobname  = '$name'
op_suite    = '$suite'
op_suitebg  = '$suitebg'
op_vapp     = '$vapp'
op_vconf    = '$vconf'
op_cutoff   = '$cutoff'
op_rundate  = $rundate
op_runtime  = $runtime
op_rootdir  = '$rootdir/{0:s}/{1:s}/{2:s}'.format(op_suite, op_vapp, op_vconf)
op_jobfile  = '$file'
op_thisjob  = '{0:s}/jobs/{1:s}.py'.format(op_rootdir, op_jobfile)
op_iniconf  = '{0:s}/conf/{1:s}_{2:s}_{3:s}.ini'.format(op_rootdir, op_vapp, op_vconf, '$task')
op_alarm    = $alarm
op_archive  = $archive
op_public   = $public
op_fullplay = $fullplay
op_retry    = $retry
op_tplfile  = '$tplfile'
op_tplinit  = '$tplinit'

oplocals = locals()

import os, sys
sys.stderr = sys.stdout

pathdirs = [ os.path.join(op_rootdir, xpath) for xpath in ('', 'src', 'vortex/site', 'vortex/src') ]
sys.path.extend(
    [ os.path.realpath(d) for d in pathdirs if os.path.isdir(d) ]
)

from iga.tools import op
from $package import $task as todo

try:
    t = op.setup(actual=oplocals)
    e = op.setenv(t, actual=oplocals)
    opts = t.sh.rawopts(defaults=dict(play=op_fullplay))
    for app in todo.setup(t, **opts):
        app.title(name=op_jobname)
        app.run()
    op.complete(t)
except Exception:
    op.fulltraceback(locals())
    op.rescue(actual=locals())
    raise
finally:
    print 'Bye bye Op...'
