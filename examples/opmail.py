# -*- coding: utf-8 -*-

"""
Puts at work some capabilities of the opmail Service.

This Service has been designed to meet operational needs:
- an adressbook is available for the definition of aliases to address
  lists, and offers recursive address lists resolution
- Vortex maintains a catalog of predefined mails, specified as templates:
  they may contain variables, automatically resolved at send time

Ordinary users are not allowed to use this Service, only operational
and developper profiles can play with this toy.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import pprint
import sys

import footprints
import vortex
from bronx.stdtypes import date
from iga.tools import actions, services
from vortex import toolbox
from vortex.tools.actions import actiond as ad

# cleanly mix stdout and stderr
sys.stdout = sys.stderr

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
        toolbox.defaults(smtpserver=smtpserver)  # usually automatic (but not on mac)

    if e.USER == 'lamboleyp':
        me = 'pascal.lamboley@meteo.fr'
    elif e.USER == 'meunierlf':
        me = 'louis-francois.meunier@meteo.fr'
        if e.HOST == 'lxgmap45':
            smtpserver = 'smtp.cnrm.meteo.fr'
            toolbox.defaults(smtpserver=smtpserver)

    try:
        me
    except NameError:
        raise NameError('please define "me = your_address" in the code')

    # set the sender once and for all
    t.glove.email = me  # could be: toolbox.defaults(sender=me)

    # find an image somewhere to test attachments
    image = t.glove.siteconf + '/../sphinx/vortex.jpg'

    sh.subtitle('send a simple mail')
    ad.mail(
        subject     = 'test vortex: simple mail',
        to          = me,
        contents    = 'A simple mail with attachement',
        attachments = [image],
    )

    sh.subtitle('op_mail=0: mails are not sent')
    e.op_mail = 0
    ad.opmail(id='test_empty_section')
    ad.opmail(id='test_missing_section')

    for e.op_mail, op_suite in [(1, 'oper'), (0, 'double')]:
        sh.subtitle('op_mail={} - op_suite={}'.format(e.op_mail, op_suite))
        ad.opmail(
            id          = 'test',
            attachments = [image],
            extra       = 'extra=' + op_suite,
            to          = 'pascal',
        )


ad.alarm_off()
ad.report_off()
ad.route_off()
ad.mail_on()
ad.opmail_on()

list_actions()
logger = more_debug(['iga', ])
test_opmail()
