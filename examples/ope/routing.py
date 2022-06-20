#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OPE Services: routing files.

20210528 - PL updated and adapted for python3 compatibility
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import pprint

import footprints
import vortex
from bronx.stdtypes import date
from iga.tools import actions, services
from vortex.tools.actions import actiond as ad

# prevent IDEs from removing seemingly unused imports
assert any([actions, services])

# join stderr and stdout for a more interpretable output
# sys.stderr = sys.stdout

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
    print(ad.actions)
    sh.subtitle('existing handlers')
    print(pprint.pformat(list(ad.items())))
    sh.subtitle('action -> handlers')
    for act in ad.actions:
        handlers = ad.candidates(act)
        status = [h.status() for h in handlers]
        print('{:6s}:'.format(act), pprint.pformat(list(zip(status, handlers))))
    print()


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

    # agt_fake_cmd is defined in target-machine.ini [agt] to be 'router_fake.sh',
    # which is a script installed along with the real route_p[ae].bin binaries,
    # that simply logs commands instead of executing them, in:
    #     $TMPDIR/vortex/router_fake.log
    fake_opts = dict(
        resuldir=resuldir,
        agt_pa_cmd='agt_fake_cmd',
        agt_pe_cmd='agt_fake_cmd',
        soprano_target='piccolo',
        defer=True,
    )

    if sh.sysname == 'Darwin':
        # in target-machine.ini, please give access to the local
        # version of router_fake.sh this way:
        # [services]
        #     agt_path = /Users/pascal/proc/vortex/examples/ope

        # replace the distant call by a local one
        fake_opts.update(
            sshhost=sh.hostname,
        )

        # and have the minimal mandatory soprano env variables
        e.DMT_DATE_PIVOT = date.synop().ymdhms  # e.g. 20210528120000

    datafile = 'tempo.dta'
    sh.rm(datafile)
    with open(datafile, 'wt') as fp:
        contents = "Test VORTEX - " + stime + '\n'
        fp.write(contents)
    print("contents:", contents)
    print("md5 =", hashlib.md5(contents.encode()).hexdigest())

    sh.subtitle('BDAP')
    ad.route(kind='bdap', filename=datafile, productid=147, domain='ATOUR10',
             term=14, targetname='exemple_bdap.dta', **fake_opts)
    ad.route(kind='bdap', filename=datafile, productid=147, domain='ATOUR20',
             term=18, **fake_opts)

    sh.subtitle('FTPPRO')
    ad.route(kind='ftppro', filename=datafile, productid=42, domain='ARIEGE',
             term=24, targetname='exemple_ftppro.dta', **fake_opts)
    ad.route(kind='ftppro', filename=datafile, productid=43, domain='ALLIER',
             term=28, **fake_opts)

    # This BDPE call should succeed (to piccolo, not to piccolo-int).
    sh.subtitle('BDPE')
    ad.route(kind='bdpe', filename=datafile, productid=43, routingkey='bdpe',
             term=34, targetname='exemple_bdpe.dta', **fake_opts)
    ad.route(kind='bdpe', filename=datafile, productid=44, routingkey='bdpe',
             term=38, **fake_opts)

    sh.subtitle('BDM')
    ad.route(kind='bdm', filename=datafile, productid=4242, **fake_opts)

    sh.subtitle('results')
    print("log files were created in", resuldir)


# reporting must be on for errors to be sent
ad.route_on()
ad.report_on()

ad.alarm_off()
ad.mail_off()
ad.opmail_off()

list_actions()
logger = more_debug(['iga', ])
test_route()
