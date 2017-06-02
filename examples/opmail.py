#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Services: opmail.
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
        status   = [ h.status() for h in handlers ]
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


def test_opmail():
    sh.title('Opmail Service')

    # machine specifics
    if sh.sysname == 'Darwin':
        if e.HOST == 'douni':
            me = 'lamboley.pascal@free.fr'
            smtpserver = 'smtp.neuf.fr'
        else:
            me = 'pascal.lamboley@meteo.fr'
            smtpserver = 'smtp.meteo.fr'
        toolbox.defaults(smtpserver = smtpserver)  # usually automatic (but not on mac)

    if e.USER == 'lamboleyp':
        me = 'pascal.lamboley@meteo.fr'

    try:
        me
    except NameError:
        raise NameError('please define "me = your_address" in the code')

    # set the sender once and for all
    t.glove.email = me   # could be: toolbox.defaults(sender=me)

    # find an image somewhere to test attachments
    image = t.glove.siteconf + '/../sphinx/vortex.jpg'

    ad.mail(
        subject     = 'test vortex: simple mail',
        to          = me,
        contents    = 'A simple mail with attachement',
        attachments = [image],
    )

    e.op_mail = 0
    ad.opmail(id='test_empty_section')
    ad.opmail(id='test_missing_section')

    for op_suite in ['oper', 'double']:
        e.op_suite = op_suite
        ad.opmail(
            id          = 'test',
            attachments = [image],
            extra       = 'extra value',
        )


ad.alarm_off()
ad.report_off()
ad.route_off()
ad.mail_on()
ad.opmail_on()

list_actions()
logger = more_debug(['iga',])
test_opmail()
