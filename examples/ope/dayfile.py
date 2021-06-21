# -*- coding: utf-8 -*-

"""
OPE Services: writing to the dayfile.

The async part of this example needs a running jeeves daemon.
With $vortex being the home of the project:
  mkdir -p ~/jeeves/test
  cd       ~/jeeves/test
  ln -s    $vortex/conf/jeeves-test.ini  test.ini
  $vortex/bin/litj.py start test
...
To stop the daemon at end
  $vortex/bin/litj.py stop test
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


def test_dayfile():
    sh.title('Dayfile service')

    resuldir = rundir

    toolbox.defaults(
        resuldir=resuldir,
        spooldir=resuldir,
        task=sh.env.get('SLURM_JOB_NAME', 'taskname'),
    )

    sh.trace = False
    for i in range(1):
        for mode in ('RAW', 'TEXTE', 'ECHEANCE', 'DEBUT', 'FIN', 'ERREUR'):
            msg = '--message with mode={}--'.format(mode)
            ad.report(kind='dayfile', mode=mode, message=msg + '  Sync Named', filename='dayfile.log')
            ad.report(kind='dayfile', mode=mode, message=msg + ' ASync Named', filename='dayfile.log',
                      asynchronous=True)
            ad.report(kind='dayfile', mode=mode, message=msg + '  Sync Anon')
            ad.report(kind='dayfile', mode=mode, message=msg + ' Async Anon', asynchronous=1)


# only reporting needs to be 'on'
ad.alarm_off()
ad.mail_off()
ad.opmail_off()
ad.report_on()
ad.route_off()

list_actions()
logger = more_debug(['iga', ])
test_dayfile()
