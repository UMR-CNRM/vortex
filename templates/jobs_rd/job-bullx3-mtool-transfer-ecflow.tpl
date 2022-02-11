#MTOOL set jobname=$name
#MTOOL set jobtag=[this:jobname]

# Build time: $create
# Build user: $mkuser
# Build host: $mkhost
# Build opts: $mkopts

#MTOOL set host=${target}
#MTOOL setconf files=targets.[this:host]
#MTOOL set logtarget=[this:frontend]
#MTOOL set transfer=[this:frontend] 

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

rd_vapp         = '$vapp'
rd_vconf        = '$vconf'
rd_cutoff       = '$cutoff'
if $rundate:
    rd_rundate  = bronx.stdtypes.date.Date($rundate)
rd_xpid         = '$xpid'
rd_refill       = $refill
rd_warmstart    = $warmstart
rd_jobname      = '$name'
rd_iniconf      = '{0:s}/conf/{1:s}_{2:s}{3:s}.ini'.format(appbase,
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

ja.add_plugin('epygram_setup')
ja.add_plugin('mtool', step='[this:number]', stepid='[this:id]', lastid='transfer', mtoolid='[this:count]')
ja.add_plugin('flow', backend='ecflow', jobidlabels=True, mtoolmeters=True)
for pkind in ($loadedjaplugins):
    ja.add_plugin(pkind)

flowscheduler = dict(
    ECF_TRYNO=int('%ECF_TRYNO%'),
    ECF_HOST='%ECF_FQDN%',
    ECF_PORT='%ECF_PORT%',
    ECF_VERSION='%ECF_VERSION%',
    ECF_PASS='%ECF_PASS%',
    ECF_NAME='%ECF_NAME%',
)

try:
    t, e, sh = ja.setup(actual=locals(), auto_options=auto_options, flowscheduler=flowscheduler)
    sh.ftraw = True # To activate ftserv

    opts = dict(jobassistant=ja,
                steps=ja.mtool_steps if not (rd_warmstart or rd_refill) else (),
                mstep_job_last=ja.is_last)
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
    ja.finalise()
    ja.close()
    sys.stdout.write('Bye bye research...\n')

#MTOOL step id=transfer target=[this:transfer]

#MTOOL autoclean
#MTOOL autolog
