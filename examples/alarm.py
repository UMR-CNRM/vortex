#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
sys.stdout = sys.stderr

import logging

import footprints
import vortex
from vortex import tools

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
    print pprint.pformat(ad.actions)
    sh.subtitle('existing handlers')
    print pprint.pformat(ad.items())
    sh.subtitle('action -> handlers')
    for act in ad.actions:
        handlers = ad.candidates(act)
        status   = [ h.status() for h in handlers ]
        print act, ':', pprint.pformat(zip(status, handlers))
    print

# alarms with 'critical' level are relayed to messdayf
ad.alarm_on()
ad.report_on()

list_services()

vortex.logger.setLevel(logging.DEBUG)
footprints.loggers.getLogger('iga').setLevel(logging.DEBUG)

# on Mac, use localhost as login node for the remote 'logger' execution
if sh.sysname == 'Darwin':
    e.loginnode = sh.hostname

ad.alarm(
    message ='an AlarmLogService at ' + stime,
    level   = 'warning',
    spooldir = rundir,
)

# change the alarm service into a logging-only service
e.op_alarm = 0

ad.alarm(
    message ='a (deactivated) AlarmLogService at ' + stime,
    level   = 'critical',
    spooldir = rundir,
)

ad.alarm(
    message = 'a (deactivated) AlarmRemoteService (with syshost) at ' + stime,
    level   = 'debug',
    syshost = 'localhost',
    spooldir = rundir,
)
