#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
logging.basicConfig(level=logging.ERROR)

from unittest import TestCase, TestLoader, TextTestRunner
from iga.services import actions_handling as acth

class Utactions_handling(TestCase):

    def setUp(self):
        self.al = acth.ActionsLoader()

    def tearDown(self):
        del self.al

    def test_on_and_status(self):
        self.al.alarm_on()
        self.al.mail_on()
        self.al.sendbdap_on()
        self.al.routing_on()
        self.assertTrue(self.al.alarm_status())
        self.assertTrue(self.al.mail_status())
        self.assertTrue(self.al.sendbdap_status())
        self.assertTrue(self.al.routing_status())
        print "test_on_status Ok"


    def test_off_and_status(self):
        self.al.alarm_off()
        self.al.mail_off()
        self.al.sendbdap_off()
        self.al.routing_off()
        self.assertFalse(self.al.alarm_status())
        self.assertFalse(self.al.mail_status())
        self.assertFalse(self.al.sendbdap_status())
        self.assertFalse(self.al.routing_status())
        print "test_off_status Ok"

if __name__ == '__main__':
    action = TestLoader().loadTestsFromTestCase
    tests = [ Utactions_handling ]
    suites = [action(elmt) for elmt in tests]
    for suite in suites:
        TextTestRunner(verbosity=2).run(suite)
