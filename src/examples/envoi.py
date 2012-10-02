#!/bin/env python
# -*- coding:Utf-8 -*-

import os

from vortex import sessions
from iga.services.actions_handling import ActionsLoader

PATH_DATA = 'data'
FILE_TEST = 'services.txt'
DATA = os.path.join(PATH_DATA, FILE_TEST)

current_glv = sessions.glove(user='mxpt001', kind='oper', tag='oper')

dico1 = {
    'action_type': 'simple_mail',
    'to': "stephane.mejias@meteo.fr",
    'from': "stephane.mejias@meteo.fr",
    'message': 'tout est ok',
    'subject': 'test mail vortex',
    'file': 'None'
}

dico3 = {
    'action_type': 'file_mail',
    'to': "stephane.mejias@meteo.fr",
    'from': "stephane.mejias@meteo.fr",
    'subject': 'test mail vortex',
    'file': DATA
}

dico4 = {
    'action_type': 'simple_alarm',
    'message': 'tout est ok'
}

dico5 = {
    'action_type': 'send_bdap',
    'domain': 'GLOB25',
    'localname': 'PEPM000GLOB25',
    'extra': '0',
    'srcdirectory': '/ch/mxpt/mxpt001/arpege/france/oper/data/bdap',
    'term': '6',
    'hour': '0',
    'bdapid': '271000000',
    'source': 'kumo05'

}

al = ActionsLoader()

al.mail(**dico1)
al.mail_status()
print '_'*150
al.mail_on()
al.mail(**dico1)
al.mail(**dico3)
print '_'*150
#TODO: prepare a test to alert the supervision
al.alarm(**dico4)
al.alarm_status()
print '_'*150
al.alarm_on()
al.alarm(**dico4)
print '_'*150


