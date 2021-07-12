#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OPE Services: sending Alarms.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import pprint

import footprints
import vortex
from bronx.stdtypes import date
from iga.tools import actions
from iga.tools import services
from vortex import toolbox
from vortex.tools.actions import actiond as ad

# prevent IDEs from removing seemingly unused imports
assert any([actions, services])

t = vortex.ticket()
e = t.env
sh = t.sh

sh.trace = True
e.verbose(True, sh)

# run in a dedicated directory
rundir = e.get('RUNDIR', e.get('WORKDIR', '/tmp') + '/rundir/' + date.today().ymd)
sh.cd(rundir, create=True)
sh.subtitle('Rundir is ' + rundir)

# get the current hour, to the second
dtime = date.now().compact()
stime = dtime[:8] + '_' + dtime[8:]


def list_actions():
    """List available actions, their kind and status."""
    sh.title('Actions information')
    sh.subtitle('available actions')
    print(pprint.pformat(ad.actions))
    sh.subtitle('existing handlers')
    print(pprint.pformat(ad.items()))
    sh.subtitle('action -> handlers')
    for act in ad.actions:
        handlers = ad.candidates(act)
        status = [h.status() for h in handlers]
        print(act, ':', pprint.pformat(zip(status, handlers)))
    print()


def more_debug(names=None, level=logging.DEBUG):
    if names is None:
        names = ['mf', 'vortex', 'iga', 'gco']
    alogger = footprints.loggers.getLogger(__name__)
    names.append('__main__')
    for name in names:
        footprints.loggers.getLogger(name).setLevel(level)
    return alogger


def test_alarms():
    sh.title('Alarm Services')

    # on local machines, use localhost as login and transfer
    # node for the remote executions (logger, ftput...)
    if sh.sysname == 'Darwin':
        toolbox.defaults(
            sshhost=sh.hostname,
        )

    ad.alarm(
        message='an AlarmLogService at ' + stime,
        level='debug',
        spooldir=rundir,
    )

    # change the alarm service into a logging-only service
    e.op_alarm = 0

    # this is better said once and for all
    toolbox.defaults(
        spooldir=rundir,
    )

    ad.alarm(
        message='an AlarmRemoteService (with syshost) at ' + stime,
        level='debug',
        syshost='localhost',
    )

    ad.alarm(
        message='an AlarmLogService at ' + stime,
        level='critical',
    )


# reporting must be 'on': alarms with 'critical' level are relayed to messdayf
ad.alarm_on()
ad.mail_off()
ad.opmail_off()
ad.report_on()
ad.route_off()

list_actions()
logger = more_debug(['iga', 'vortex'])
test_alarms()
