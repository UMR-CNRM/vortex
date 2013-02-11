#!/bin/env python
# -*- coding:Utf-8 -*-

r"""
Module managing the sending of messages. It's the by default module given to the
actions_handling main module.
This module must provide four high level functions:
    -on, off, status, execute.
The on, off and status functions must return a boolean value reflecting the
status of action passed argument. As far as the execute function is concerned,
it must deals with the data (given to realize the action) and the action
to be processed: mail, sendbdap, routing, alarm.  
For now, it also contains several global variables (_ACTIONS_DICT, _MAP_ACTIONS, 
_COMPONENTS). 
_ACTIONS_DICT : determine and store the status of the actions
_MAP_ACTIONS : link an action to a class dedicated to that action
_COMPONENTS : link an action to a service dedicated to that action
"""


import sys
import logging

from vortex.tools.actions import SendData, actioninterface


class StatusSendData(SendData):

    def __init__(self, action, service):
        super(StatusSendData, self).__init__(action, service)

    def status(self):
        return status(self.action)

class SendMail(StatusSendData):
    r"""

    Class responsible for sending emails. You never call this class
    directly. You must use x :func:`mailx`.

    Arguments:
        kw (dict): mandatory arguments used to send the email
    """
    def __init__(self, action, service):
        super(SendMail, self).__init__(action, service)

    def mail(self):
        """docstring for mail"""
        logging.info('mail ')
        self.service.mail()

class SendAlarm(StatusSendData):
    r"""

    Class responsible for sending alarm. You never call this class
    directly. You must use x :func:`logger`.

    """

    def __init__(self, action, service):
        super(SendAlarm, self).__init__(action, service)
        logging.debug("service passe %s", service)

    def alarm(self):
        r"""
        Allow to send a simple text alarm 
        """
        logging.info('alarm ')
        self.service.alarm()

class SendBdap(StatusSendData):
    r"""

    Class responsible for sending data towards the BDAP machine. You never call this class
    directly. You must use x :func:`sendbdap`.


    Arguments:
        kw (dict): mandatory arguments used to send the data
    """


    def __init__(self, action, service):
        super(SendBdap, self).__init__(action, service)
        
    def sendbdap(self):
        r"""
        Execute the command line to be processed so as to send the product to the BDAP.
        """
        logging.info('sendbdap ')
        self.service.sendbdap()

    def route(self):
        r"""
        Execute the command line to be processed so as to route the product to
        the server.
        """
        logging.info('route ')
        self.service.route()


_ACTIONS_DICT = {
    'mail': False,
    'alarm': False,
    'sendbdap': False,
    'route': False
}

_MAP_ACTIONS_CLS = {
    'mail': SendMail,
    'alarm': SendAlarm,
    'sendbdap': SendBdap,
    'route': SendBdap
}


actioninterface(sys.modules.get(__name__), _ACTIONS_DICT, _MAP_ACTIONS_CLS)
