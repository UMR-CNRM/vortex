#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

from vortex.toolbox import sessions
from vortex.tools.actions import Action, actiond
from vortex.tools.services import Directory
from vortex.util.config import GenericConfigParser

import footprints
logger = footprints.loggers.getLogger(__name__)


class SendAlarm(Action):
    """
    Class responsible for sending alarms.
    """

    def __init__(self, kind='alarm', service='sendalarm', active=False):
        super(SendAlarm, self).__init__(kind=kind, active=active, service=service)

    def service_info(self, **kw):
        """Avoid forcing the user to tell it's hostname."""
        sh = sessions.system()
        kw.setdefault('hostname', sh.hostname)
        return super(SendAlarm, self).service_info(**kw)


class Route(Action):
    """
    Class responsible for routing data to the Transfer Agent (BDAP, BDPE, BDM).
    """

    def __init__(self, kind='route', service=None, active=False):
        super(Route, self).__init__(kind=kind, active=active, service=service)


class DMTEvent(Action):
    """
    Class responsible for routing data to the Transfer Agent (BDAP, BDPE, BDM).
    """

    def __init__(self, kind='dmt', service='dmtevent', active=False):
        super(DMTEvent, self).__init__(kind=kind, active=active, service=service)


class OpMail(Action):
    """
    Class responsible for sending pre-defined mails.
    """

    def __init__(self, kind='opmail', service='opmail', active=True, directory = None, catalog=None):
        super(OpMail, self).__init__(kind=kind, active=active, service=service)
        self.directory = directory or Directory('@opmail-directory.ini')
        self.catalog = catalog or GenericConfigParser('@opmail-catalog.ini')

    def service_info(self, **kw):
        """Kindly propose the permanent directory and catalog to the final service"""
        kw.setdefault('directory', self.directory)
        kw.setdefault('catalog', self.catalog)
        return super(OpMail, self).service_info(**kw)

    def execute(self, *args, **kw):
        """Perform the action through a service. Extraneous arguments (not included in the footprint)
        are collected and explicitely transmitted to the service in a dictionary."""
        rc = None
        service = self.get_active_service(**kw)
        if service:
            options = { k:v for k,v in kw.items() if k not in service.footprint_attributes }
            rc = service(options)
        return rc


actiond.add(SendAlarm(), Route(), DMTEvent(), OpMail())
