#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
from copy import deepcopy
logging.basicConfig(level=logging.ERROR)

from unittest import TestCase, TestLoader, TextTestRunner
from iga.services import actions as ac
from vortex.tools.services import MailService
from iga.services.services import AlarmService, BdapService, RoutingService


class Utactions(TestCase):

    def setUp(self):
        self.data = os.path.join('./data', 'corps_message.txt')
        self.dico1 = {
            'action_type': 'mail',
            'action': 'simple_mail',
            'receiver': "stephane.mejias@meteo.fr",
            'sender': "stephane.mejias@meteo.fr",
            'message': 'tout est ok',
            'subject': 'test mail vortex',
        }
        self.dico2 = {
            'action_type': 'mail',
            'action': 'file_mail',
            'receiver': "stephane.mejias@meteo.fr",
            'sender': "stephane.mejias@meteo.fr",
            'subject': 'test mail vortex',
            'file': self.data
        }
        self.dico3 = {
            'action_type': 'alarm',
            'action': 'simple_alarm',
            'message': 'Unknown problem',
            'level': 'critical'
        }
        self.dico4 = {
            'action_type': 'alarm',
            'action': 'simple_alarm',
            'message': 'Error detected',
            'level': 'error'
        }
        self.dico5 = {
            'action_type': 'sendbdap',
            'action': 'send_bdap',
            'domain': 'GLOB25',
            'localname': 'PEPM000GLOB25',
            'extra': '0',
            'srcdirectory': '/ch/mxpt/mxpt001/arpege/france/oper/data/bdap',
            'term': '6',
            'hour': '0',
            'bdapid': '271000000',
            'source': 'kumo05',
            'scalar': True
        }
        self.dico6 = deepcopy(self.dico5)
        self.dico6['scalar'] = False
        self.dico7 = {
            'action_type': 'route',
            'action': 'route',
            'producer': 'serv',
            'localname': 'tmp_kumo0512256',
            'quality': '0',
            'srcdirectory': './data',
            'term': '6',
            'date': '20120731',
            'productid': '1656000000',
            'source': 'kumo05',
            'scalar': True
        }
        self.dico8 = deepcopy(self.dico7)
        self.dico8['scalar'] = False

    def tearDown(self):
        del self.data

    def test_on_and_status(self):
        for i in ('mail', 'alarm', 'sendbdap', 'route'):
            self.assertFalse(ac.get_status(i))
        for i in ('mail', 'alarm', 'sendbdap', 'route'):
            ac.on(i)
        for i in ('mail', 'alarm', 'sendbdap', 'route'):
            self.assertTrue(ac.get_status(i))
        for i in ('mail', 'alarm', 'sendbdap', 'route'):
            ac.off(i)
        for i in ('mail', 'alarm', 'sendbdap', 'route'):
            self.assertFalse(ac.get_status(i))

        print "test on_off_status Ok"

    def test_get_act_serv(self):
        ref_serv = [
            MailService, MailService, AlarmService, AlarmService,
            BdapService, BdapService, RoutingService, RoutingService
        ]
        ref_act = [
            ac.SendMail, ac.SendMail, ac.SendAlarm, ac.SendAlarm,
            ac.SendBdap, ac.SendBdap, ac.SendBdap, ac.SendBdap
        ]
        cpt = 0
        for dic in [self.dico1, self.dico2, self.dico3, self.dico4, self.dico5,
                    self.dico6, self.dico7, self.dico8]:
            act_serv = ac.get_act_serv(**dic)
            self.assertTrue(isinstance(act_serv.get_service(), ref_serv[cpt]))
            self.assertTrue(isinstance(act_serv, ref_act[cpt]))
            cpt += 1

        print "test get_act_serv Ok"

    def test_available_services(self):
        for dic in [self.dico1, self.dico2, self.dico3, self.dico4, self.dico5,
                    self.dico6, self.dico7, self.dico8]:
            act_serv = ac.get_act_serv(**dic)
            self.assertTrue(act_serv.available_services())

        print "test available_services Ok"

if __name__ == '__main__':
    action = TestLoader().loadTestsFromTestCase
    tests = [ Utactions ]
    suites = [action(elmt) for elmt in tests]
    for suite in suites:
        TextTestRunner(verbosity=2).run(suite)
