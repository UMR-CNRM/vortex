#!/usr/bin/env python3

"""
OPE Services: sending Mails.

Puts at work some capabilities of the mail and opmail Services.

The opmail Service has been designed to meet operational needs:
- an adressbook is available for the definition of aliases to address
  lists, and offers recursive address lists resolution.
- Vortex maintains a catalog of predefined mails, specified as templates:
  they may contain variables, automatically resolved at send time.

Ordinary users are not allowed to use this Service, only operational
and developper profiles can play with this toy.
"""

import logging
import pprint
import sys

import footprints
import vortex
from bronx.stdtypes import date
from iga.tools import actions
from iga.tools import services
from vortex import toolbox
from vortex.tools.actions import actiond as ad

# prevent IDEs from removing seemingly unused imports
assert any([actions, services])

# don't mix stderr and stdout
sys.stdout = sys.stderr

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


def check_address(address, smtpuser, smtppass):
    """
    Most of this is not needed, it only simplifies this script maintenance.
    """

    me = None

    # machine specifics
    if sh.sysname == 'Darwin':
        if e.HOST == 'douni':
            me = 'lamboley.pascal@free.fr'
            smtpserver = 'smtp.orange.fr'
            smtpport = 587
        else:
            me = 'pascal.lamboley@meteo.fr'
            smtpserver = 'smtp.meteo.fr'
        toolbox.defaults(smtpserver=smtpserver)  # usually automatic (but not on mac)
        try:
            toolbox.defaults(smtpport=smtpport)
        except NameError:
            pass

    # specific users
    if e.USER == 'lamboleyp':
        me = 'pascal.lamboley@meteo.fr'
    elif e.USER == 'meunierlf':
        me = 'louis-francois.meunier@meteo.fr'
        if e.HOST == 'pxalgo2':
            smtpserver = 'smtp.cnrm.meteo.fr'
            toolbox.defaults(smtpserver=smtpserver)

    if smtpuser:
        toolbox.defaults(smtpuser=smtpuser)
    if smtppass:
        toolbox.defaults(smtppass=smtppass)

    address = address or me
    if address is None:
        print('Please define "mail_address = your_address" near the end of this script.')
        exit(1)

    return address


def test_mail(address, smtpuser=None, smtppass=None):
    sh.title('Mail Service')

    address = check_address(address, smtpuser, smtppass)

    # share the sender's address
    t.glove.email = address

    # or alternatively
    # toolbox.defaults(sender=address)

    # find images somewhere to test attachments
    pj1 = t.glove.siteconf + '/../sphinx/vortex.jpg'
    pj2 = t.glove.siteconf + '/../sphinx/favicon.png'

    ad.mail(
        to          = address,
        subject     = "Un pangramme, c'est énôrme !!",
        attachments = (pj1, pj2),
        body        = "Portez ce vieux whisky au juge blond qui fume: dès Noël "
                      "où un zéphyr haï le vêt de glaçons würmiens, il dîne "
                      "d’exquis rôtis de bœuf au kir et à l’aÿ d’âge mûr, et "
                      "cætera, en s'écriant: \"À Â É È Ê Ë Î Ï Ô Ù Û Ü Ç Œ Æ\"."
                      "\n\n--\nMail envoyé depuis mon iVortex.",
    )


def test_opmail(address, smtpuser=None, smtppass=None):
    sh.title('Opmail Service')

    address = check_address(address, smtpuser, smtppass)

    # set the sender once and for all
    t.glove.email = address

    # find an image somewhere to test attachments
    image = t.glove.siteconf + '/../sphinx/vortex.jpg'

    sh.subtitle('send a simple mail')
    ad.mail(
        subject     = 'Test vortex: simple mail',
        to          = address,
        contents    = 'A simple mail with attachement',
        attachments = [image],
    )

    # test special cases
    sh.subtitle('op_mail=0: mails are not sent')
    e.op_mail = 0
    ad.opmail(id='test_empty_section')
    ad.opmail(id='test_missing_section')

    # test more common cases
    # when e.op_mail==1, the mail is really sent
    # when e.op_mail==0, it is built the same way, but only sent to stderr
    e.env_var = 'from the env !'
    for e.op_mail, op_suite in [(1, 'oper'), (0, 'double')]:
        sh.subtitle('op_mail={} - op_suite={}'.format(e.op_mail, op_suite))
        ad.opmail(
            id          = 'test',
            attachments = [image],
            to          = 'pascal_home',
            # those are not in the footprint, they will be transmitted
            # for template variable substitution (case insensitive)
            extra       = 'extra_' + op_suite,
            op_suite    = op_suite,
        )


# both 'mail' and 'opmail' must be 'on'
ad.mail_on()
ad.opmail_on()

ad.alarm_off()
ad.report_off()
ad.route_off()

list_actions()
logger = more_debug(['iga', ])

# mail_address = 'firstname.lastname@meteo.fr'
mail_address = None

# if needed (tests from home during the COVID crisis...)
smtpuser = smtppass = None

# Pascal
# mail_address = 'lamboley.pascal@neuf.fr'
# smtpuser = 'lamboley.pascal@orange.fr'
# smtppass = 'TULSORAPA'

test_mail(mail_address, smtpuser, smtppass)
test_opmail(mail_address, smtpuser, smtppass)
