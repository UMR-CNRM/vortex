#MTOOL set jobname=$name
#MTOOL set jobtag=[this:jobname]
#MTOOL profile target=${target}cn
# PBSPROPREFIX -l EC_hyperthreads=$hyperthreading
# PBSPROPREFIX -l EC_memory_per_task=$mem
# PBSPROPREFIX -l EC_nodes=$nnodes
# PBSPROPREFIX -l EC_tasks_per_node=$ntasks
# PBSPROPREFIX -l EC_threads_per_task=$openmp
# PBSPROPREFIX -l EC_total_tasks=
# PBSPROPREFIX -l EC_billing_account=
# PBSPROPREFIX -N [this:jobname]
# PBSPROPREFIX -S /bin/ksh
# PBSPROPREFIX -j oe
# PBSPROPREFIX -q ns
# PBSPROPREFIX -l walltime=$time
#MTOOL end

# Build time: $create
# Build user: $mkuser
# Build host: $mkhost
# Build opts: $mkopts

#MTOOL setconf files=targets.[this:host]
#MTOOL set logtarget=[this:frontend]
#MTOOL set fetch=[this:frontend]
#MTOOL set compute=[this:cpunodes]
#MTOOL set backup=[this:frontend]

#MTOOL set bangline=${python}_$pyopts
#MTOOL configure submitcmd=$submitcmd

import os, sys
appbase = os.path.abspath('$target_appbase')
vortexbase = os.path.join(appbase, 'vortex')
# Alter path for extra packages
for d in [os.path.join(appbase, p) for p in ($extrapythonpath)]:
    if os.path.isdir(d):
        sys.path.insert(0, d)
    else:
        sys.stderr.write("<< {:s} >> does not exists : it won't be pre-pended to sys.path\n"
                         .format(d))
# Alter path for current tasks + vortex (mandatory)
sys.path.insert(0, os.path.join(vortexbase, 'site'))
sys.path.insert(0, os.path.join(vortexbase, 'src'))
sys.path.insert(0, appbase)

import bronx.stdtypes.date
from bronx.system.interrupt import SignalInterruptError
import footprints
import vortex
import vortex.layout.jobs

# This temporary shell should work well enough for the autolog step
t = vortex.ticket()
sh = t.sh
e = t.env

#MTOOL common not=autolog

import $package.$task as todo

rd_vapp     = '$vapp'
rd_vconf    = '$vconf'
rd_cutoff   = '$cutoff'
if $rundate:
    rd_rundate  = bronx.stdtypes.date.Date($rundate)
rd_xpid     = '$xpid'
rd_refill   = $refill
rd_jobname  = '$name'
rd_iniconf  = '{0:s}/conf/{1:s}_{2:s}{3:s}.ini'.format(appbase,
                                                       rd_vapp, rd_vconf, '$taskconf')

# Any options passed on the command line
auto_options = dict(
$auto_options
)

ja = footprints.proxy.jobassistant(kind = 'generic',
                                   modules = footprints.stdtypes.FPSet(($loadedmods)),
                                   addons = footprints.stdtypes.FPSet(($loadedaddons)),
                                   ldlibs = footprints.stdtypes.FPSet(($ldlibs)),
                                   special_prefix='rd_',
                                   )
ja.add_plugin('mtool', step='[this:number]', stepid='[this:id]', lastid='backup', mtoolid='[this:count]')

try:
    t, e, sh = ja.setup(actual=locals(), auto_options=auto_options)

    opts = dict(jobassistant=ja, steps=ja.mtool_steps)
    driver = todo.setup(t, **opts)
    driver.setup()
    driver.run()

    ja.complete()

except (Exception, SignalInterruptError, KeyboardInterrupt) as trouble:
    ja.fulltraceback(trouble)
    ja.rescue()
    #MTOOL include files=epilog.step
    #MTOOL include files=submit.last

finally:
    #MTOOL include files=epilog.clean.step
    ja.finalise()
    ja.close()
    sys.stdout.write('Bye bye research...\n')

#MTOOL step id=fetch target=[this:fetch]
#MTOOL step id=compute target=[this:compute]
#MTOOL step id=backup target=[this:backup]

#MTOOL autoclean
#MTOOL autolog
