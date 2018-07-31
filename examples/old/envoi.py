#!/usr/bin/env python
# -*- coding:Utf-8 -*-

# Status : OK (v0.6.21)

from __future__ import print_function, absolute_import, unicode_literals, division

import os

from vortex import sessions
from vortex.tools import env
from iga.tools import services
from vortex.tools.actions import SendMail
from vortex.tools.actions import actiond as ad

PATH_DATA = 'data'
FILE_TEST = 'services.txt'
DATA = os.path.join(PATH_DATA, FILE_TEST)

t = sessions.ticket()
t.info()

operenv = env.Environment(active=True)
operenv.setvar('DEFAULT_ACTIONS', 'iga.services.actions')

current_glv = sessions.getglove(user='mxpt001', kind='oper', tag='oper')

dico1 = {
    'receiver': "stephane.mejias@meteo.fr",
    'sender': "stephane.mejias@meteo.fr",
    'message': 'tout est ok',
    'subject': 'test mail vortex',
}

dico2 = {
    'receiver': "stephane.mejias@meteo.fr stephane.mejias@meteo.fr",
    'sender': "stephane.mejias@meteo.fr",
    'message': 'tout est ok',
    'subject': 'test mail vortex',
}

dico3 = {
    'receiver': "stephane.mejias@meteo.fr",
    'sender': "stephane.mejias@meteo.fr",
    'subject': 'test mail vortex',
    'file': DATA
}

dico4 = {
    'message': 'tout est ok'
}

dico5 = {
    'domain': 'GLOB25',
    'localname': 'PEPM000GLOB25',
    'extra': '0',
    'srcdirectory': '/ch/mxpt/mxpt001/arpege/france/oper/data/bdap',
    'term': '6',
    'hour': '0',
    'bdapid': '271000000',
    'source': 'kumo05'

}

dico6 = {
    'receiver': "stephane.mejias@meteo.fr",
    'sender': "stephane.mejias@meteo.fr",
    'message': 'tout est ok',
    'subject': 'test mail report vortex',
}

ad.mail(**dico1)
ad.mail_status()
print('_'*80)

ad.mail_on()
ad.mail(**dico1)
ad.mail(**dico3)
print('_'*80)

#TODO: prepare a test to alert the supervision
ad.alarm(**dico4)
ad.alarm_status()
print('_'*80)

ad.alarm_on()
ad.alarm(**dico4)
print('_'*80)

ad.add(SendMail(kind='mailreport'))
ad.mailreport(**dico6)
print('_'*80)
