#MTOOL set jobname=$name
#MTOOL set jobtag=[this:jobname]
#MTOOL profile target=${target}cn
#SBATCH --cpus-per-task=$openmp
#SBATCH --export=NONE
#SBATCH --job-name=[this:jobname]
#SBATCH --mem=$mem
#SBATCH --nodes=$nnodes
#SBATCH --ntasks-per-node=$ntasks
#SBATCH --partition=$partition
#SBATCH --time=$time
#SBATCH --$exclusive
#SBATCH --$verbose
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

import locale
locale.setlocale(locale.LC_ALL, '$defaultencoding')

import bronx.stdtypes.date
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
    sh.ftraw = True # To activate ftserv

    opts = dict(jobassistant=ja, steps=ja.mtool_steps)
    driver = todo.setup(t, **opts)
    driver.setup()
    driver.run()

    ja.complete()

except Exception as trouble:
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
