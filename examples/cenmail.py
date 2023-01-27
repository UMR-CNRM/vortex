#!/usr/bin/env python3

"""
Tests for the cenmail Service.
See also: opmail is very close.
"""

import logging
import pprint
import sys

import footprints
import vortex
from bronx.stdtypes import date
from cen.tools import actions
from cen.tools import services
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
        names = ['mf', 'vortex', 'iga', 'gco', 'cen']
    alogger = footprints.loggers.getLogger(__name__)
    names.append('__main__')
    for name in names:
        footprints.loggers.getLogger(name).setLevel(level)
    return alogger


def check_address(address, smtpuser, smtppass):
    """
    Most of his is not needed, it only simplifies this script maintenance.
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


def test_cenmail(address, smtpuser=None, smtppass=None):
    sh.title('Cenmail Service')

    address = check_address(address, smtpuser, smtppass)

    # set the sender once and for all
    t.glove.email = address

    sh.subtitle('send a preformatted cenmail')
    ad.cenmail(id='test_1', to=address, extra='extra_var')


# both 'mail' and 'cenmail' must be 'on'
ad.mail_on()
ad.cenmail_on()

ad.alarm_off()
ad.report_off()
ad.route_off()
ad.opmail_off()

list_actions()
logger = more_debug(['cen', ])

# mail_address = 'firstname.lastname@meteo.fr'
mail_address = None

# if needed (tests from home during the COVID crisis...)
smtpuser = smtppass = None

# Pascal
# mail_address = 'lamboley.pascal@neuf.fr'
# smtpuser = 'lamboley.pascal@orange.fr'
# smtppass = 'TULSORAPA'

test_cenmail(mail_address, smtpuser, smtppass)
