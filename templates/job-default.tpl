#!${python} $pyopts

# Build time: $create
# Build user: $mkuser
# Build host: $mkhost
# Build opts: $mkopts

import os, sys
appbase = os.path.abspath('$appbase')
vortexbase = os.path.join(appbase, 'vortex')
sys.path.insert(0, os.path.join(vortexbase, 'site'))
sys.path.insert(0, os.path.join(vortexbase, 'src'))
sys.path.insert(0, appbase)

import footprints
import vortex
import vortex.layout.jobs

# This temporary shell should work well enough for the autolog step
t = vortex.ticket()
sh = t.sh
e = t.env

import $package.$task as todo

rd_vapp     = '$vapp'
rd_vconf    = '$vconf'
rd_cutoff   = '$cutoff'
rd_rundate  = vortex.tools.date.Date($rundate)
rd_member   = $member
rd_xpid     = '$xpid'
rd_suitebg  = $suitebg
rd_refill   = $refill
rd_jobname  = '$name'
rd_iniconf  = '{0:s}/conf/{1:s}_{2:s}{3:s}.ini'.format(appbase, 
                                                       rd_vapp, rd_vconf, '$taskconf')

ja = footprints.proxy.jobassistant(kind = 'generic',
                                   modules = footprints.stdtypes.FPSet(($loadedmods)),
                                   addons = footprints.stdtypes.FPSet(($loadedaddons)),
                                   special_prefix='rd_',
                                   )
ja.add_plugin('tmpdir')

try:
    t, e, sh = ja.setup(actual=locals())

    opts = dict(jobassistant=ja, fullplay=True,
                defaults=dict(gnamespace='gco.multi.fr'))
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
    print 'Bye bye research...'

