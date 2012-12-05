#!/bin/env python
# -*- coding: utf-8 -*-

"""
Module managing the sending of messages. It's the by default module given to the
actions_handling main module.

This module must provide four high level functions:

   * on, off, get_status, execute.

The on, off and get_status functions must return a boolean value reflecting the
status of action passed argument. As far as the execute function is concerned,
it must deals with the data (given to realize the action) and the action
to be processed: mail, sendbdap, routing, alarm.

For now, it also contains several global variables:

  * _ACTIONS_DICT : determine and store the status of the actions
  * _MAP_ACTIONS : link an action to a class dedicated to that action
  * _COMPONENTS : link an action to a service dedicated to that action
"""

#: Automatic export
__all__ = ['on', 'off', 'get_status', 'execute']


from smtplib import SMTP

from email.mime.text import MIMEText
from email.utils import COMMASPACE

import logging
import services
from vortex.tools.services import catalog as svcatalog
from authorizations_handling import is_user_authorized


class SendData(object):
    """
    This is an abstract class which represent the general way to deal with
    sendind all kind of messages. The method used is:

       * parse the arguments,
       * check if the service is available,
       * check if the user is authorized to realize the action
       * send the message

    Argument:
      * data (dict): named argument, all mandatory parameters for the chosen action
    """
    def __init__(self, action, service):
        self.action = action
        self.service = service

    def available_services(self):
        """
        Check if the service is implemented. If that's the case, the attribute
        :attr:`_currentaction` is set to the action to be performed.
        Returns True or False
        """
        #check if the service is available
        #action = self.service.get_action()
        if hasattr(getattr(self, self.action), "__func__"):
            self._currentaction = getattr(self, self.action)
            return True
        else:
            return False

    def send(self):
        """Call the chosen action pointed by _currentaction."""
        #check if the user is authorized to realize the action
        #check if the action can be processed by the instance
        #check if the action is authorized
        if is_user_authorized(self.service.get_action_type()):
            if self.available_services() and get_status(self.action):
                self._currentaction()
            else:
                logging.warning('Non authorized action %s', self.action)
        else:
            logging.warning('user not authorized to use %s',
                            self.service.get_action_type())

    def get_service(self):
        return self.service


class SendMail(SendData):
    """
    Class responsible for sending emails. You never call this class
    directly. You must use x :func:`mailx`.

    Arguments:

      * kw (dict): mandatory arguments used to send the email
    """
    def __init__(self, action, service):
        super(SendMail, self).__init__(action, service)

    def sendmail(self, message):
        """Actually send the email."""
        send_to, send_from, subject, level = self.service.get_data()
        msg = SimpleTextEmail(message, send_to, send_from, subject)
        s = SimpleSMTP()
        msg_from, msg_string = msg.info()
        #s.set_debuglevel(True)
        s.sendmail(msg_from, send_to, msg_string)
        s.quit()

    def simple_mail(self):
        """Allow to send a simple text email."""
        message = self.service.get_message()
        self.sendmail(message)

    def file_mail(self):
        """Allow to send a simple file email."""
        message = self.service.get_file()
        self.sendmail(message)


class SimpleTextEmail(MIMEText):
    """
    Class inheriting from MIMEText specialized so as to have a hook to read
    the passed argument. You never call this class directly. It is used by the
    class SendMail.

    Arguments:

      * message (str): text to be passed as a payload
      * send_to (str): email address of the recipient
      * send_from (str): email address of the sender
      * subject (str): subject of the email
    """

    def __init__(self, message, send_to, send_from, subject):
        MIMEText.__init__(self, message)
        self['Subject'] = subject
        self['From'] = send_from
        self['To'] = COMMASPACE.join(send_to)

    def info(self):
        return self['From'], self.as_string()


class SimpleSMTP(SMTP):
    """
    The simple SMTP client. You never call this class directly. It is used by the
    class SendMail.

    Arguments:

      * server (str): name of the DNS server to be used
    """
    def __init__(self, server='localhost'):#, server='cadillac.meteo.fr'):
        SMTP.__init__(self, server)


class SendAlarm(SendData):
    """
    Class responsible for sending alarm. You never call this class
    directly. You must use x :func:`logger`.
    """

    def __init__(self, action, service):
        super(SendAlarm, self).__init__(action, service)

    def sendalarm(self, message):
        """Actually send the alarm."""
        logger_func = self.service.get_loggerservice()
        logger_func(message)

    def simple_alarm(self):
        """Allow to send a simple text alarm."""
        message = self.service.get_message()
        self.sendalarm(message)


class SendBdap(SendData):
    """
    Class responsible for sending data towards the BDAP machine. You never call this class
    directly. You must use x :func:`sendbdap`.

    Arguments:

      * kw (dict): mandatory arguments used to send the data
    """

    def __init__(self, action, service):
        super(SendBdap, self).__init__(action, service)

    def send_bdap(self):
        """Execute the command line to be processed so as to send the product to the BDAP."""
        system = self.service.get_system()
        cmdline = self.service.get_cmdline()
        logging.info('sendbdap %s', cmdline)
        system.spawn(cmdline, shell=True)

    def route(self):
        """Execute the command line to be processed so as to route the product to the server."""
        system = self.service.get_system()
        cmdline = self.service.get_cmdline()
        logging.info('route %s', cmdline)
        system.spawn(cmdline, shell=True)


_ACTIONS_DICT = {
    'mail': False,
    'alarm': False,
    'sendbdap': False,
    'route': False
}

_MAP_ACTIONS = {
    'mail': SendMail,
    'alarm': SendAlarm,
    'sendbdap': SendBdap,
    'route': SendBdap
}

def on(action):
    """Set the boolean value associated with the passed argument action to True."""
    global _ACTIONS_DICT
    _ACTIONS_DICT[action] = True

def off(action):
    """Set the boolean value associated with the passed argument action to False."""
    global _ACTIONS_DICT
    _ACTIONS_DICT[action] = False

def get_status(action):
    """Return the boolean value associated with the passed argument action."""
    global _ACTIONS_DICT
    logging.info("Status of %s is %s", action, _ACTIONS_DICT[action])
    return _ACTIONS_DICT[action]

def get_act_serv(**kw):
    """
    Build the instance determined by the action, through
    _MAP_ACTIONS dictionary, and associated with the correct service.
    """
    action_type = kw['action_type']
    action = kw['action']
    ctlg = svcatalog()
    serv = ctlg.findbest(kw)
    return _MAP_ACTIONS[action_type](action, serv)

def execute(**kw):
    """
    Call the send method of the built instance returned by get_act_serv by the action.
    """
    obj = get_act_serv(**kw)
    obj.send()

