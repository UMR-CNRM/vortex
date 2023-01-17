#!${python_mkjob}

from __future__ import print_function, absolute_import, unicode_literals, division

import os, sys
appbase = os.path.abspath('$appbase')
vortexbase = os.path.join(appbase, 'vortex')
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
from vortex.layout.nodes import NODE_STATUS

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
                                   special_prefix='rd_',
                                   )

t, e, sh = ja.setup(actual=locals(), auto_options=auto_options)

opts = dict(jobassistant=ja, dryrun=True)
driver = todo.setup(t, **opts)
driver.setup()

info_file = '{:s}_dryrun_infos.txt'.format(rd_jobname)
with open(info_file, 'w') as fh_i:
    fh_i.write("The mkjob command argumets where:\n\n".upper())
    fh_i.write("$mkopts" + "\n")
    fh_i.write("\n")
    fh_i.write("The families and tasks tree is:\n\n".upper())
    fh_i.write(driver.tree_str(statuses_filter=(NODE_STATUS.READY, )) + "\n")
    fh_i.write("\n")
    fh_i.write("The families and tasks tree (with configuration data) is:\n".upper())
    fh_i.write("(displayed configuration entries add up or overwrite those of the parent).\n\n")
    fh_i.write(driver.tree_str(statuses_filter=(NODE_STATUS.READY, ),
                               with_conf=True) + "\n")


print()
print("The following report was created: {:s}".format(info_file))
print()
