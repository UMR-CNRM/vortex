#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
OPE Services: mail and opmail.

Please initialize variable 'mail_address' near the end of this script.
It won't run without this change, to avoid sending emails to unwilling destinees.
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


def check_address(address):
    """
    Most of his is not needed, it only simplifies this script maintenance.
    """

    me = None

    # machine specifics
    if sh.sysname == 'Darwin':
        if e.HOST == 'douni':
            me = 'lamboley.pascal@free.fr'
            smtpserver = 'smtp.neuf.fr'
        else:
            # me = 'webmcsi@mirage.meteo.fr'
            me = 'pascal.lamboley@meteo.fr'
            smtpserver = 'smtp.meteo.fr'
        toolbox.defaults(smtpserver=smtpserver)  # usually automatic (but not on mac)

    # specific users
    if e.USER == 'lamboleyp':
        me = 'pascal.lamboley@meteo.fr'
    elif e.USER == 'meunierlf':
        me = 'louis-francois.meunier@meteo.fr'
    elif e.USER == 'rigougyg':
        me = 'gaelle.rigoudy@meteo.fr'

    address = address or me

    if address is None:
        print('Please define "mail_address = your_address" near the end of this script.')
        exit(1)

    return address


def test_mail(address):
    sh.title('Mail Service')

    address = check_address(address)

    # share the sender's address
    t.glove.email = address

    # or alternatively
    # toolbox.defaults(sender=me)

    # find images somewhere to test attachments
    pj1 = t.glove.siteconf + '/../sphinx/vortex.jpg'
    pj2 = t.glove.siteconf + '/../sphinx/favicon.png'

    ad.mail(
        to=address,
        subject="un pangramme, c'est énôrme !!",
        body="Portez ce vieux whisky au juge blond qui fume: dès Noël "
             "où un zéphyr haï le vêt de glaçons würmiens, il dîne "
             "d’exquis rôtis de bœuf au kir et à l’aÿ d’âge mûr, et "
             "cætera, en s'écriant: \"À Â É È Ê Ë Î Ï Ô Ù Û Ü Ç Œ Æ\"."
             "\n\n--\nMail envoyé depuis mon iVortex.",
        attachments=(pj1, pj2),
    )


def test_opmail(address):
    sh.title('Opmail Service')

    address = check_address(address)

    # set the sender once and for all
    t.glove.email = address  # could also be: toolbox.defaults(sender=me)

    # find an image somewhere to test attachments
    image = t.glove.siteconf + '/../sphinx/vortex.jpg'

    # test special cases
    sh.subtitle('op_mail=0: mails are not sent')
    e.op_mail = 0
    ad.opmail(id='test_empty_section')
    ad.opmail(id='test_missing_section')

    # test more common cases
    for e.op_mail, op_suite in [(1, 'oper'), (0, 'double')]:
        sh.subtitle('op_mail={} - op_suite={}'.format(e.op_mail, op_suite))
        ad.opmail(
            id='test',
            attachments=[image],
            extra='extra=' + op_suite,
            to='pascal',
        )


# both 'mail' and 'opmail' must be 'on'
ad.alarm_off()
ad.mail_on()
ad.opmail_on()
ad.report_off()
ad.route_off()

list_actions()
logger = more_debug(['iga', ])

# mail_address = 'firstname.lastname@meteo.fr'
mail_address = None

test_mail(mail_address)
test_opmail(mail_address)
