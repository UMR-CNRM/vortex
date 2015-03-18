#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Écriture de fichiers de dayfile (messdayf).
"""

import sys
sys.stdout = sys.stderr

import logging
import footprints
import vortex
from vortex import toolbox, tools

t = vortex.ticket()
e = t.env
sh = t.sh

sh.trace = True
e.verbose(True, sh)
fpx = footprints.proxy

# run in a dedicated directory
rundir = e.get('RUNDIR', e.WORKDIR + '/rundir/' + tools.date.today().ymd)
sh.cd(rundir, create=True)
sh.subtitle('Rundir is ' + rundir)


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
        status   = [h.status() for h in handlers]
        print act, ':', pprint.pformat(zip(status, handlers))
    print


def test_dayfile():
    sh.title('Dayfile service')
    resuldir = rundir

    toolbox.defaults(
        resuldir=resuldir,
        spooldir=resuldir,
        task=sh.env.get('SLURM_JOB_NAME', 'taskname'),
    )

    for mode in ('RAW', 'TEXTE', 'ECHEANCE', 'DEBUT', 'FIN', 'ERREUR'):
        msg = '--message with mode={}--'.format(mode)
        ad.report(kind='dayfile', mode=mode, message=msg, filename='dayfile.log')
        ad.report(kind='dayfile', mode=mode, message=msg)

ad.mail_off()
ad.alarm_off()
ad.route_off()
ad.report_on()

list_services()

test_dayfile()
