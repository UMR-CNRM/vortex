#!/usr/bin/python -u
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

op_suite    = '$suite'
op_suitebg  = '$suitebg'
op_vapp     = '$vapp'
op_vconf    = '$vconf'
op_rootdir  = '$rootdir/{0:s}/{1:s}/{2:s}'.format(op_suite, op_vapp, op_vconf)
op_jobname  = '$name'
op_jobfile  = '$file'
op_thisjob  = '{0:s}/jobs/{1:s}.py'.format(op_rootdir, op_jobfile)
op_daterun  = '$daterun'
op_alarm    = $alarm
op_archive  = $archive
op_public   = $public
op_retry    = $retry
op_tplfile  = '$tplfile'
op_tplinit  = '$tplinit'

oplocals = locals()

import os, sys
sys.stderr = sys.stdout

pathdirs = [os.path.join(op_rootdir, xpath) for xpath in ('', 'src', 'vortex/src', 'vortex/site')]
sys.path.extend([os.path.realpath(d) for d in pathdirs if os.path.isdir(d)])

from iga.tools import op
from $package import $task as todo

try:
    t = op.setup(actual=oplocals)
    e = op.setenv(t, actual=oplocals)
    for app in todo.setup(t):
        app.title('starting ' + op_jobname + ' for HH = ' + str(app.ticket.env.DATE.hour))
        app.process()
        app.complete()
    op.complete(t)
except Exception:
    op.fulltraceback(locals())
    op.rescue(actual=locals())
    raise
finally:
    print 'Bye bye Op...'

