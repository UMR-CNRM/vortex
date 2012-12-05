#!/bin/env python
# -*- coding: utf-8 -*-

"""
Standard services to be used by user defined actions.
With the abstract class Service (inheritating from BFootprint)
a default Mail Service is provided.
"""

#: No automatic export
__all__ = []

import os, sys, re

import logging
from vortex.syntax import BFootprint
from vortex.utilities.catalogs import ClassesCollector, cataloginterface


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
        return (self.receiver, self.sender, self.subject, self.level)

    def get_message(self):
        return self.message

    def get_file(self):
        file_to_message = self.file
        tmp = open(file_to_message, 'r')
        message = tmp.read()
        tmp.close()
        return message


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

