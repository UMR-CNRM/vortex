#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Services: routing files.
"""

import sys
sys.stdout = sys.stderr

import logging

import footprints
import vortex
from vortex import toolbox
from vortex.tools import date

t = vortex.ticket()
e = t.env
sh = t.sh

sh.trace = True
e.verbose(True, sh)

# run in a dedicated directory
rundir = e.get('RUNDIR', e.WORKDIR + '/rundir/' + date.today().ymd)
sh.cd(rundir, create=True)
sh.subtitle('Rundir is ' + rundir)

# get the current hour, to the second
dtime = date.now().compact()
stime = dtime[:8] + '_' + dtime[8:]

from vortex.tools.actions import actiond as ad
from iga.tools import actions
from iga.tools import services


def list_actions():
    """List available actions, their kind and status."""
    import pprint
    sh.title('Actions information')
    sh.subtitle('available actions')
    print pprint.pformat(ad.actions)
    sh.subtitle('existing handlers')
    print pprint.pformat(ad.items())
    sh.subtitle('action -> handlers')
    for act in ad.actions:
        handlers = ad.candidates(act)
        status = [h.status() for h in handlers]
        print act, ':', pprint.pformat(zip(status, handlers))
    print


def more_debug(names=None, level=logging.DEBUG):
    if names is None:
        names = ['mf', 'vortex', 'iga', 'gco']
    alogger = footprints.loggers.getLogger(__name__)
    names.append('__main__')
    for name in names:
        footprints.loggers.getLogger(name).setLevel(level)
    return alogger


def test_route():
    import hashlib

    sh.title('Routing services')

    resuldir = rundir

    # agt_fake_cmd is defined in target-xxx.ini to be 'router_fake.sh',
    # a script installed along with the real route_p[ae].bin binaries,
    # but that logs commands instead of executing them.
    # To see what happened, use:
    #    cat $TMPDIR/vortex/router_fake.log
    toolbox.defaults(
        resuldir       = resuldir,
        agt_pa_cmd     = 'agt_fake_cmd',
        agt_pe_cmd     = 'agt_fake_cmd',
        soprano_target = 'piccolo',
    )

    if sh.sysname == 'Darwin':
        toolbox.defaults(
            agt_path = '/Users/pascal/tmp/vortex',
            sshhost  = sh.hostname,
        )

    with open('tempo.dta', 'w') as fp:
        contents = "Test VORTEX - " + stime + '\n'
        fp.write(contents)
    print "contents:", contents
    print "md5 =", hashlib.md5(contents).hexdigest()

    sh.subtitle('BDAP')
    ad.route(kind='bdap', filename='tempo.dta', productid=147, domain='ATOUR10', term=84,
             targetname='exemple_bdap.dta')

    # This BDPE call should succeed (to piccolo, not to piccolo-int).
    sh.subtitle('BDPE')
    ad.route(kind='bdpe', filename='tempo.dta', productid=43, routingkey='bdpe', term=36,
             targetname='exemple_bdpe.dta')

    sh.subtitle('BDM')
    ad.route(kind='bdm', filename='tempo.dta', productid=4242)

    sh.subtitle('results')
    print "log files were created in", resuldir


ad.alarm_off()
ad.mail_off()
ad.report_on()
ad.route_on()

list_actions()
logger = more_debug(['iga',])
test_route()
