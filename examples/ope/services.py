#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test manuel des services.
Les exemples qui correspondent et devraient être à jour:
- examples/alarm.py
- examples/dayfile.py
- examples/opmail.py
- examples/routing.py
"""

from __future__ import division, print_function, absolute_import

import logging

import footprints
import vortex
from bronx.stdtypes import date
from vortex import toolbox
from vortex.tools.actions import actiond as ad

t = vortex.ticket()
e = t.env
sh = t.sh

sh.trace = True
e.verbose(True, sh)

# run in a dedicated directory
rundir = e.get('RUNDIR', e.WORKDIR + '/rundir/' + date.today().ymd)
sh.cd(rundir, create=True)
sh.subtitle('Rundir is ' + rundir)

# the date of the run
strdate = e.get('DMT_DATE_PIVOT', date.synop(delta='-PT12H').compact())
rundate = date.Date(strdate)

# get the current hour, to the second
dtime = date.now().compact()
stime = dtime[:8] + '_' + dtime[8:]

# default attributes for all footprint resolutions to come
t.glove.setenv(app='arpege', conf='france')
toolbox.defaults(
    model=t.glove.vapp,  # as is often the case, the model is the application
    date=rundate,  # a true 'Date' object
)


def list_actions():
    """List available actions, their kind and status."""

    import pprint
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


def test_mail():
    sh.title('Mail Service')
    # share the sender's address
    # me = 'pascal.lamboley@meteo.fr'
    me = 'webmcsi@mirage.meteo.fr'
    t.glove.email = me
    # other mail tunings
    toolbox.defaults(
        # sender  = me,                # alternative to t.glove.email
        # to      = me,
        smtpserver='smtp.meteo.fr',  # usually automatic (but not on my mac)
    )

    ad.mail(
        # to='herve.bonneu@meteo.fr ' + me,
        to=me,
        subject="un pangramme, c'est énôrme !!",
        # à, â, é, è, ê, ë, î, ï, ô, ù, û, ü, ç, œ, æ
        body="Portez ce vieux whisky au juge blond qui fume: dès Noël "
             "où un zéphyr haï le vêt de glaçons würmiens, il dîne "
             "d’exquis rôtis de bœuf au kir et à l’aÿ d’âge mûr, et "
             "cætera, en s'écriant: \"À Â É È Ê Ë Î Ï Ô Ù Û Ü Ç Œ Æ\"."
             "\n\n--\nMail envoyé depuis mon iVortex."
    )

    # pj1 = '/Users/pascal/tmp/test.jpg'
    # pj2 = '/Users/pascal/tmp/tt.cc'
    # ad.mail(to=me, subject='test 1 ' + stime, attachments=(pj1,))
    # ad.mail(to=me, subject='test 2 ' + stime, attachments=(pj1, pj2,))


def test_route():
    import hashlib
    sh.title('Routing services')
    resuldir = rundir
    toolbox.defaults(
        resuldir=resuldir,
        agt_pa_cmd='agt_fake_cmd',
        agt_pe_cmd='agt_fake_cmd',
        soprano_target='piccolo',
    )

    if sh.sysname == 'Darwin':
        # cd  ~/tmp/vortex
        # ln -s ~/at_work/dev/vortex/dev/services/validation/router_fake.sh ./
        # ln -s router_fake.sh router_pa.sh
        # ln -s router_fake.sh router_pe.sh
        toolbox.defaults(
            agt_path='/Users/pascal/tmp/vortex',
            sshhost=sh.hostname,
        )

    with open('tempo.dta', 'w') as fp:
        contents = "Test VORTEX - " + stime + '\n'
        fp.write(contents)
    print("contents:", contents)
    print("md5 =", hashlib.md5(contents).hexdigest())

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
    print("log files were created in", resuldir)


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
            # ad.report(kind='dayfile', mode=mode, message=msg + '  Sync Named', filename='dayfile.log')
            ad.report(kind='dayfile', mode=mode, message=msg + ' ASync Named', filename='dayfile.log',
                      async=True)
            # ad.report(kind='dayfile', mode=mode, message=msg + '  Sync Anon')
            ad.report(kind='dayfile', mode=mode, message=msg + ' Async Anon', async=1)


def test_opmail():
    sh.title('Opmail service')
    # machine specifics
    if e.HOST == 'douni':
        print('On My Mac at home !')
        me = 'lamboley.pascal@free.fr'
        smtpserver = 'smtp.neuf.fr'
    else:
        me = 'pascal.lamboley@meteo.fr'
        smtpserver = 'smtp.meteo.fr'
    t.glove.email = me
    img = t.glove.siteconf + '/../sphinx/vortex.jpg'
    toolbox.defaults(
        smtpserver=smtpserver,  # usually automatic (but not on my mac)
        sender=me,  # alternative to t.glove.email
        )

    try_simple_mail = False
    if try_simple_mail:
        ad.mail(
            subject='test vortex: simple mail',
            to='opmcsi@meteo.fr',
            contents='Un simple mail avec attachement',
            attachments=[img],
        )

    e.op_mail = 0
    ad.opmail(id='test_empty_section')
    ad.opmail(id='test_missing_section')

    for op_suite in ['oper', 'double']:
        e.op_suite = op_suite
        ad.opmail(
            id='test',
            attachments=[img],
            extra='extra value',
        )

ad.alarm_on()
ad.mail_on()
ad.report_on()
ad.route_on()

# list_actions()
logger = more_debug(['iga', 'vortex'])
# test_alarms()
# test_mail()
# test_route()
# test_dayfile()
test_opmail()
