#!/bin/env python
# -*- coding: utf-8 -*-

"""
Standard services to be used by user defined actions.
With the abstract class Service (inheritating from BFootprint)
a default Mail Service is provided.
"""

#: No automatic export
__all__ = []

import sys, re

import logging
from smtplib import SMTP
from email.mime.text import MIMEText
from email.utils import COMMASPACE

from vortex.syntax import BFootprint
from vortex.utilities.catalogs import ClassesCollector, cataloginterface

_UPDATE_DICTIONARY = 'action_type'

class Service(BFootprint):
    """Abstract base class for services"""

    _footprint = dict(
        info = 'Abstract services class',
        attr = dict(
            action_type = dict()
        )
    )

    def get_action_type(self):
        return self.action_type

    @classmethod
    def realkind(self):
        return 'service'


class MailService(Service):
    """
    Class responsible for handling email data.
    You never call this class directly.
    To be refined.
    """

    _footprint = dict(
        info = 'Mail services class',
        attr = dict(
            action_type = dict(
                values = ['mail']
            ),
            sender = dict(),
            receiver = dict(),
            message = dict(
                optional = True,
            ),
            file = dict(
                optional = True,
                default = None
            ),
            subject = dict(),
            level = dict(
                optional = True,
                default = 'info',
                values = ['info', 'error', 'warning', 'critical']
            )
        )
    )

    def get_data(self):
        #the receiver is transformed into a list
        return (self.receiver, self.sender, self.subject, self.level)

    def get_message(self):
        print "self.file %s" % self.file
        if self.file:
            print "Je passe dans self.file"
            return self.get_file()
        else:
            print "Je passe dans self.message"
            return self.message

    def get_file(self):
        file_to_message = self.file
        tmp = open(file_to_message, 'r')
        message = tmp.read()
        tmp.close()
        return message

    def mail(self):
        """docstring for mail"""
        message = self.get_message()
        send_to, send_from, subject, level = self.get_data()
        msg = SimpleTextEmail(message, send_to, send_from, subject)
        s = SimpleSMTP()
        msg_from, msg_string = msg.info()
        s.sendmail(msg_from, send_to.split(), msg_string)
        s.quit()

class SimpleTextEmail(MIMEText):
    r"""
    Class inheriting from MIMEText specialized so as to have a hook to read
    the passed argument. You never call this class directly. It is used by the
    class SendMail.

    Arguments:
        message (str): text to be passed as a payload
        send_to (str): email address of the recipient
        send_from (str): email address of the sender
        subject (str): subject of the email

    """

    def __init__(self, message, send_to, send_from, subject):
        MIMEText.__init__(self, message)
        self['Subject'] = subject
        self['From'] = send_from
        self['To'] = COMMASPACE.join(send_to.split())
        print "SimpleTextEmail To %s" % self['To']

    def info(self):
        return self['From'], self.as_string()

class SimpleSMTP(SMTP):
    r"""
    The simple SMTP client. You never call this class directly. It is used by the
    class SendMail.

    Arguments:
        server (str): name of the DNS server to be used

    """
    def __init__(self, server='localhost'):#, server='cadillac.meteo.fr'):
        SMTP.__init__(self, server)

class ServicesCatalog(ClassesCollector):
    """Class in charge of collecting :class:`MpiTool` items."""

    def __init__(self, **kw):
        logging.debug('Services catalog init %s', self)
        cat = dict(
            remod = re.compile(r'.*\.services'),
            classes = [ Service ],
            itementry = Service.realkind()
        )
        cat.update(kw)
        super(ServicesCatalog, self).__init__(**cat)

    @classmethod
    def tablekey(cls):
        return 'services'


cataloginterface(sys.modules.get(__name__), ServicesCatalog)

