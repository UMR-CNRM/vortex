#!/bin/env python
# -*- coding:Utf-8 -*-

# Status : out of date
# TODO phasing iga tools with new vortex.tools.services design

import os

from vortex import sessions
from vortex.tools.actions_handling import ActionsLoader
from iga.services import services

PATH_DATA = 'data'
FILE_TEST = 'services.txt'
DATA = os.path.join(PATH_DATA, FILE_TEST)

current_glv = sessions.glove(user='mxpt001', kind='oper', tag='oper')

dico1 = {
    'action_type': 'mail',
    'receiver': "stephane.mejias@meteo.fr",
    'sender': "stephane.mejias@meteo.fr",
    'message': 'tout est ok',
    'subject': 'test mail vortex',
    'file': 'None'
}

dico3 = {
    'action_type': 'mail',
    'to': "stephane.mejias@meteo.fr",
    'sender': "stephane.mejias@meteo.fr",
    'subject': 'test mail vortex',
    'file': DATA
}

dico4 = {
    'action_type': 'alarm',
    'message': 'tout est ok'
}

dico5 = {
    'action_type': 'sendbdap',
    'domain': 'GLOB25',
    'localname': 'PEPM000GLOB25',
    'srcdirectory': '/ch/mxpt/mxpt001/arpege/france/oper/data/bdap',
    'term': '6',
    'hour': '0',
    'bdapid': '271000000',
    'source': 'kumo05'

}

dico6 = {
    'action_type': 'sendbdap',
    'domain': 'domain',
    'localname': 'test',
    'srcdirectory': '/ch/mxpt/mxpt001/steph_perso/python/Vortex/IgaServices/data',
    'term': '0',
    'hour': '0',
    'bdapid': '8086000000',
    'source': 'kumo05'

}

dico7 = {
    'action_type': 'route',
    'localname': 'test',
    'srcdirectory': '/ch/mxpt/mxpt001/steph_perso/python/Vortex/IgaServices/data',
    'term': '0',
    'date': '0',
    'productid': '1656000000',

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
#bdap part
al.sendbdap(**dico5)
al.sendbdap_status()
print '_'*150
#al.sendbdap_on()
al.sendbdap(**dico6)
print '_'*150
al.routedata(**dico7)
al.routing_status()
print '_'*150
al.routing_on()
al.routedata(**dico7)



