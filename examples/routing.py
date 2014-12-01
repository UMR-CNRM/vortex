#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

# Répertoire d'exécution dédié
rundir = e.get('RUNDIR', e.WORKDIR + '/rundir/' + tools.date.today().ymd)
sh.cd(rundir, create=True)
sh.subtitle('Rundir is ' + rundir)

# la date du jour
strdate = e.get('DMT_DATE_PIVOT', tools.date.synop(delta='-PT12H').compact())
rundate = tools.date.Date(strdate)

# maintenant, à la seconde
dtime = tools.date.now().compact()
stime = dtime[:8] + '_' + dtime[8:]


# Attributs par défaut pour toutes les résolutions d'empreintes à suivre.
t.glove.setenv(app='arpege', conf='france')
toolbox.defaults(
    model     = t.glove.vapp,           # Comment souvent, le model est l'application
    date      = rundate,                # C'est un véritable "objet" de type Date
    server   = 'smtp.meteo.fr',         # Pour le mail
)


from vortex.tools.actions import actiond as ad
from iga.tools import actions
from iga.tools import services
from vortex.tools import date

ad.alarm_on()
ad.agt_on()


do_infos = False
if do_infos:

    sh.title ('Listes des services et actions')

    import pprint
    print 'available actions:\n', pprint.pformat(ad.actions())
    print 'existing handlers:\n', pprint.pformat(ad.items())
    print 'action/handlers:'
    for act in ad.actions():
        handlers = ad.candidates(act)
        status   = ad.__getattr__(act + '_status')()
        print act,':', pprint.pformat(zip(status, handlers))


### verbosity
def logger_level(level, names):
    """sets the level of a logger (use None for all)
        e.g. ['footprints', 'mf', 'vortex', 'iga']"""
    if names is None:
        names = footprints.loggers.roots
    for name in names:
        footprints.loggers.getLogger(name).setLevel(level)

# logger = footprints.loggers.getLogger(__name__)
# logger.setLevel(logging.DEBUG)
logger_level(logging.DEBUG, ['mf', 'vortex', 'iga'])
logging.basicConfig(level=logging.DEBUG)


### Agent de transfert

sh.title ('Services de routage')

resuldir = rundir
toolbox.defaults(
    resuldir       = resuldir,
    agt_pe_cmd     = 'router_fake.sh',
    agt_pa_cmd     = 'router_fake.sh',
    soprano_target = 'piccolo',
)

if sh.sysname == 'Darwin':
    toolbox.defaults(
        agt_path       = '/Users/pascal/tmp/vortex',
        loginnode      = 'localhost',
        transfernode   = 'localhost',
)

with open('tempo.dta','w') as fp:
    contents = "Test VORTEX - " + stime
    fp.write(contents)
    print "contents:", contents

sh.subtitle ('BDAP')
ad.agt(kind='bdap', filename='tempo.dta', productid='147',
       domain='ATOUR10', term=84)

sh.subtitle ('BDPE')
ad.agt(kind='bdpe', filename='tempo.dta', productid=43,
       cleroutage=10001, term='03600', )
ad.agt(kind='bdpe', filename='tempo.dta', productid=43,
       cleroutage=10001, term=3600, )

sh.subtitle ('BDM')
ad.agt(kind='bdm', filename='tempo.dta', productid=4242)

sh.subtitle ('results')
print "log files were created in", resuldir
