#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.stdout = sys.stderr

import footprints
import vortex
from vortex import toolbox, tools

t = vortex.ticket()
e = t.env
sh = t.sh

sh.trace = True
e.verbose(True, sh)

# run in a dedicated directory
rundir = e.get('RUNDIR', e.WORKDIR + '/rundir/' + tools.date.today().ymd)
sh.cd(rundir, create=True)
sh.subtitle('Rundir is ' + rundir)

# get the current hour, to the second
dtime = tools.date.now().compact()
stime = dtime[:8] + '_' + dtime[8:]

from vortex.tools.actions import actiond as ad
from iga.tools import actions
from iga.tools import services


def list_services():
    """List services, actions, and their relation."""
    import pprint
    sh.title('List of services and actions')
    sh.subtitle('available actions')
    print pprint.pformat(ad.actions())
    sh.subtitle('existing handlers')
    print pprint.pformat(ad.items())
    sh.subtitle('action -> handlers')
    for act in ad.actions():
        handlers = ad.candidates(act)
        status   = ad.__getattr__(act + '_status')()
        print act,':', pprint.pformat(zip(status, handlers))
    print

ad.mail_off()
ad.alarm_off()
ad.route_on()

list_services()

sh.title('Routing services')

resuldir = rundir
toolbox.defaults(
    resuldir       = resuldir,
    agt_pe_cmd     = 'router_fake.sh',
    agt_pa_cmd     = 'router_fake.sh',
    soprano_target = 'piccolo-int',
)

if sh.sysname == 'Darwin':
    toolbox.defaults(
        agt_path       = '/Users/pascal/tmp/vortex',
        loginnode      = 'localhost',
        transfernode   = 'localhost',
)

with open('tempo.dta','w') as fp:
    contents = "Test VORTEX - " + stime
    fp.write(contents)
    print "contents:", contents

sh.subtitle('BDAP')
ad.route(kind='bdap', filename='tempo.dta', productid=147,
         domain='ATOUR10', term=84)

sh.subtitle('BDPE')
ad.route(kind='bdpe', filename='tempo.dta', productid=43,
         routingkey=10001, term=36, )

sh.subtitle('BDM')
ad.route(kind='bdm', filename='tempo.dta', productid=4242)

sh.subtitle('results')
print "log files were created in", resuldir
