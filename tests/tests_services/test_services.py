#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os

import footprints

from vortex.tools import services
from iga.services import services as sviga
from vortex.tools.date import Date
from unittest import TestCase, main
import logging

PATH_DATA = '/ch/mxpt/mxpt001/steph_perso/python/Vortex/IgaServices'
FILE_TEST = 'corps_message.txt'
DATA = os.path.join(PATH_DATA, FILE_TEST)


class utdate(TestCase):

    def setUp(self):
        self.ctlg = footprints.proxy.services

    def tearDown(self):
        del self.ctlg

    def test_mailservices(self):
        dico1 = {
            'action_type': 'mail',
            'receiver': "stephane.mejias@meteo.fr",
            'sender': "stephane.mejias@meteo.fr",
            'message': 'tout est ok',
            'subject': 'test mail vortex',
        }
        dico2 = {
            'receiver': "stephane.mejias@meteo.fr",
            'sender': "stephane.mejias@meteo.fr",
            'subject': 'test mail vortex',
            'file': DATA
        }

        ms = sv.MailService(**dico1)
        self.assertEquals(ms.action_type, dico1['action_type'])
        self.assertEquals(ms.receiver, dico1['receiver'])
        self.assertEquals(ms.sender, dico1['sender'])
        self.assertEquals(ms.message, dico1['message'])
        self.assertEquals(ms.subject, dico1['subject'])
        self.assertEquals(
            ms.get_data(),
            ( dico1['receiver'], dico1['sender'], dico1['subject'], 'info')
        )
        self.assertEquals(ms.get_message(), dico1['message'])

        ms = sv.MailService(**dico2)
        self.assertEquals(ms.action_type, dico1['action_type'])
        self.assertEquals(ms.receiver, dico2['receiver'])
        self.assertEquals(ms.sender, dico2['sender'])
        self.assertEquals(ms.subject, dico2['subject'])
        self.assertEquals(ms.file, dico2['file'])
        self.assertEquals(
            ms.get_data(),
            ( dico2['receiver'], dico2['sender'], dico2['subject'], 'info')
        )
        self.assertEquals(ms.get_file(), 'Test Vortex : envoi message\n')
        print "test Mail services ok"

    def test_alarmservices(self):
        dico1 = {
            'action_type': 'alarm',
            'message': 'Unknown problem',
            'level': 'critical'
        }
        dico2 = {
            'action_type': 'alarm',
            'message': 'Error detected',
            'level': 'error'
        }
        ref_logger = logging.getLogger()
        al = sviga.AlarmService(**dico1)
        self.assertEquals(al.action_type, dico1['action_type'])
        self.assertEquals(al.message, dico1['message'])
        self.assertEquals(al.get_message(), dico1['message'])
        self.assertEquals(al.get_loggerservice(),ref_logger.critical)

        al = sviga.AlarmService(**dico2)
        self.assertEquals(al.action_type, dico2['action_type'])
        self.assertEquals(al.message, dico2['message'])
        self.assertEquals(al.get_message(), dico2['message'])
        self.assertEquals(al.get_loggerservice(), ref_logger.error)
        print "test alarm services ok"

    def test_bdapservices(self):
        dico1 = {
            'action_type': 'sendbdap',
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
        al = sviga.BdapService(**dico1)
        self.assertEquals(al.action_type, dico1['action_type'])
        self.assertEquals(al.domain, dico1['domain'])
        self.assertEquals(al.localname, dico1['localname'])
        self.assertEquals(al.extra, dico1['extra'])
        self.assertEquals(al.srcdirectory, dico1['srcdirectory'])
        self.assertEquals(al.term, dico1['term'])
        self.assertEquals(al.hour, dico1['hour'])
        self.assertEquals(al.bdapid, dico1['bdapid'])
        self.assertEquals(al.source, dico1['source'])
        self.assertTrue(al.scalar)
        ref_cmd_line = "%s %s %s %s %s %s/%s" % (
            dico1['domain'], dico1['extra'], dico1['term'], dico1['hour'],
            dico1['bdapid'], dico1['srcdirectory'], dico1['localname']
        )
        nom_exec = 'envoi_bdap_tx'
        self.assertEquals(al.get_cmd_line(), [nom_exec + ' ' + ref_cmd_line])

        dico1['scalar'] = False
        al = sviga.BdapService(**dico1)
        ref_cmd_line = "%s %s %s %s %s %s %s/%s" % (
            dico1['source'], dico1['domain'], dico1['extra'], dico1['term'],
            dico1['hour'], dico1['bdapid'], dico1['srcdirectory'],
            dico1['localname']
        )
        nom_exec = 'send_bdap'
        self.assertEquals(al.get_cmd_line(), [nom_exec + ' ' + ref_cmd_line])
        print "test Bdap services ok"

    def test_routingservices(self):
        dico1 = {
            'action_type': 'route',
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
        al = sviga.RoutingService(**dico1)
        self.assertEquals(al.action_type, dico1['action_type'])
        self.assertEquals(al.producer, dico1['producer'])
        self.assertEquals(al.localname, dico1['localname'])
        self.assertEquals(al.quality, dico1['quality'])
        self.assertEquals(al.srcdirectory, dico1['srcdirectory'])
        self.assertEquals(al.term, dico1['term'])
        self.assertEquals(al.date, Date(dico1['date']))
        self.assertEquals(al.productid, dico1['productid'])
        self.assertEquals(al.source, dico1['source'])
        self.assertTrue(al.scalar)
        self.assertEquals(al.binary, 'router_pe_sx')
        self.assertEquals(al.path_exec, '/ch/mxpt/mxpt001/util/agt/')
        ref_cmd_line = "%s/%s %s -p %s -n %s -e %s -d %s -q %s" % (
            dico1['srcdirectory'], dico1['localname'], dico1['productid'],
            dico1['producer'], dico1['productid'][0:4], dico1['term'],
            Date(dico1['date']), dico1['quality']
        )
        nom_exec = os.path.join('/ch/mxpt/mxpt001/util/agt/', 'router_pe_sx')
        self.assertEquals(al.get_cmd_line(), [nom_exec + ' ' + ref_cmd_line])

        dico1['scalar'] = False
        al = sviga.RoutingService(**dico1)
        nom_exec = os.path.join('/ch/mxpt/mxpt001/util/agt/', 'router_pe')
        self.assertEquals(al.get_cmd_line(), [nom_exec + ' ' + ref_cmd_line])
        print "test Routing services ok"

    def test_mail_serv_via_ctlg(self):
        dico1 = {
            'action_type': 'mail',
            'receiver': "stephane.mejias@meteo.fr",
            'sender': "stephane.mejias@meteo.fr",
            'message': 'tout est ok',
            'subject': 'test mail vortex',
        }
        dico2 = {
            'receiver': "stephane.mejias@meteo.fr",
            'sender': "stephane.mejias@meteo.fr",
            'subject': 'test mail vortex',
            'file': DATA
        }

        ms = self.ctlg.findbest(dico1)
        self.assertEquals(ms.action_type, dico1['action_type'])
        self.assertEquals(ms.receiver, dico1['receiver'])
        self.assertEquals(ms.sender, dico1['sender'])
        self.assertEquals(ms.message, dico1['message'])
        self.assertEquals(ms.subject, dico1['subject'])
        self.assertEquals(
            ms.get_data(),
            ( dico1['receiver'], dico1['sender'], dico1['subject'], 'info')
        )
        self.assertEquals(ms.get_message(), dico1['message'])

        ms = self.ctlg.findbest(dico2)
        self.assertEquals(ms.action_type, dico1['action_type'])
        self.assertEquals(ms.receiver, dico2['receiver'])
        self.assertEquals(ms.sender, dico2['sender'])
        self.assertEquals(ms.subject, dico2['subject'])
        self.assertEquals(ms.file, dico2['file'])
        self.assertEquals(
            ms.get_data(),
            ( dico2['receiver'], dico2['sender'], dico2['subject'], 'info')
        )
        self.assertEquals(ms.get_file(), 'Test Vortex : envoi message\n')
        print "test Mail services via the collector ok"

    def test_alarmserv_via_ctlg(self):
        dico1 = {
            'action_type': 'alarm',
            'message': 'Unknown problem',
            'level': 'critical'
        }
        dico2 = {
            'action_type': 'alarm',
            'message': 'Error detected',
            'level': 'error'
        }
        ref_logger = logging.getLogger()
        al = self.ctlg.findbest(dico1)
        self.assertEquals(al.action_type, dico1['action_type'])
        self.assertEquals(al.message, dico1['message'])
        self.assertEquals(al.get_message(), dico1['message'])
        self.assertEquals(al.get_loggerservice(),ref_logger.critical)

        al = self.ctlg.findbest(dico2)
        self.assertEquals(al.action_type, dico2['action_type'])
        self.assertEquals(al.message, dico2['message'])
        self.assertEquals(al.get_message(), dico2['message'])
        self.assertEquals(al.get_loggerservice(), ref_logger.error)
        print "test alarm services via the collector ok"

    def test_bdapserv_via_ctlg(self):
        dico1 = {
            'action_type': 'sendbdap',
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
        al = self.ctlg.findbest(dico1)
        self.assertEquals(al.action_type, dico1['action_type'])
        self.assertEquals(al.domain, dico1['domain'])
        self.assertEquals(al.localname, dico1['localname'])
        self.assertEquals(al.extra, dico1['extra'])
        self.assertEquals(al.srcdirectory, dico1['srcdirectory'])
        self.assertEquals(al.term, dico1['term'])
        self.assertEquals(al.hour, dico1['hour'])
        self.assertEquals(al.bdapid, dico1['bdapid'])
        self.assertEquals(al.source, dico1['source'])
        self.assertTrue(al.scalar)
        ref_cmd_line = "%s %s %s %s %s %s/%s" % (
            dico1['domain'], dico1['extra'], dico1['term'], dico1['hour'],
            dico1['bdapid'], dico1['srcdirectory'], dico1['localname']
        )
        nom_exec = 'envoi_bdap_tx'
        self.assertEquals(al.get_cmd_line(), [nom_exec + ' ' + ref_cmd_line])

        dico1['scalar'] = False
        al = self.ctlg.findbest(dico1)
        ref_cmd_line = "%s %s %s %s %s %s %s/%s" % (
            dico1['source'], dico1['domain'], dico1['extra'], dico1['term'],
            dico1['hour'], dico1['bdapid'], dico1['srcdirectory'],
            dico1['localname']
        )
        nom_exec = 'send_bdap'
        self.assertEquals(al.get_cmd_line(), [nom_exec + ' ' + ref_cmd_line])
        print "test Bdap services via the collector ok"

    def test_routingserv_via_ctlg(self):
        dico1 = {
            'action_type': 'route',
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
        al = self.ctlg.findbest(dico1)
        self.assertEquals(al.action_type, dico1['action_type'])
        self.assertEquals(al.producer, dico1['producer'])
        self.assertEquals(al.localname, dico1['localname'])
        self.assertEquals(al.quality, dico1['quality'])
        self.assertEquals(al.srcdirectory, dico1['srcdirectory'])
        self.assertEquals(al.term, dico1['term'])
        self.assertEquals(al.date, Date(dico1['date']))
        self.assertEquals(al.productid, dico1['productid'])
        self.assertEquals(al.source, dico1['source'])
        self.assertTrue(al.scalar)
        self.assertEquals(al.binary, 'router_pe_sx')
        self.assertEquals(al.path_exec, '/ch/mxpt/mxpt001/util/agt/')
        ref_cmd_line = "%s/%s %s -p %s -n %s -e %s -d %s -q %s" % (
            dico1['srcdirectory'], dico1['localname'], dico1['productid'],
            dico1['producer'], dico1['productid'][0:4], dico1['term'],
            Date(dico1['date']), dico1['quality']
        )
        nom_exec = os.path.join('/ch/mxpt/mxpt001/util/agt/', 'router_pe_sx')
        self.assertEquals(al.get_cmd_line(), [nom_exec + ' ' + ref_cmd_line])

        dico1['scalar'] = False
        al = self.ctlg.findbest(dico1)
        nom_exec = os.path.join('/ch/mxpt/mxpt001/util/agt/', 'router_pe')
        self.assertEquals(al.get_cmd_line(), [nom_exec + ' ' + ref_cmd_line])
        print "test Routing services via the collector ok"


if __name__ == '__main__':
    main()
