#!/bin/env python
# -*- coding:Utf-8 -*-

r"""
Module managing the sending of messages.
Default action classes must provide four methods: on, off, status, execute.
The on, off and status functions must return a boolean value reflecting the
status of the action. As far as the execute function is concerned,
it must deals with the data (given to realize the action) and the action
to be processed: e.g. mail, sendbdap, routing, alarm.
"""

#: No automatic export
__all__ = []

from vortex.autolog import logdefault as logger

from vortex.utilities.catalogs import Catalog
from vortex.utilities.authorizations import is_authorized_user
from vortex.tools import services


class Action(object):

    def __init__(self, kind='foo', service=None, active=False):
        self.kind = kind
        if service == None:
            service = 'send' + self.kind
        self.service = service
        self._active = active

    @property
    def active(self):
        """Current status of the action as a boolean property."""
        return self._active

    def status(self):
        """Return current active status."""
        return self.active

    def on(self):
        """Switch on this action."""
        self._active = True
        return self._active

    def off(self):
        """Switch off this action."""
        self._active = False
        return self._active

    def service_kind(self, **kw):
        """Actual service kind name to be used for footprint evaluation."""
        return self.service

    def service_info(self, **kw):
        """On the fly remapping of the expected footprint."""
        info = dict()
        info.update(kw)
        info.setdefault('kind', self.service_kind(**kw))
        return info

    def get_actual_service(self, **kw):
        """Build the service instance determined by the actual description."""
        info = self.service_info(**kw)
        return services.load(**info)

    def execute(self, **kw):
        """Generic method to perform the action through a service."""
        rc = None
        if is_authorized_user(self.kind):
            if self.active:
                service = self.get_actual_service(**kw)
                if service:
                    rc = service()
                else:
                    logger.warning('Could not find any service for action %s', self.kind)
            else:
                logger.warning('Non active action %s', self.kind)
        else:
            logger.warning('User not authorized to perform %s', self.kind)
        return rc


class SendMail(Action):
    """
    Class responsible for sending emails.
    """
    def __init__(self, kind='mail', active=True, service='sendmail'):
        super(SendMail, self).__init__(kind=kind, active=active, service=service)


class Dispatcher(Catalog):
    """
    Central office for dispatching actions.
    """

    def __init__(self, **kw):
        logger.debug('Action dispatcher init %s', self)
        super(Dispatcher, self).__init__(**kw)
        self._todo = None

    def actions(self):
        return set([x.kind for x in self.items()])

    def candidates(self, kind):
        """Return a selection of the catalog's items with the specified ``kind``."""
        return filter(lambda x: x.kind == kind, self.items())

    def discard_kind(self, kind):
        """A shortcut to discard from the catalog any item with the specified ``kind``."""
        for item in self:
            if item.kind == kind:
                self.discard(item)

    def __getattr__(self, action):
        km = action.split('_')
        kind = km[0]
        if len(km) > 1:
            self._todo = ( kind, km[1] )
        else:
            self._todo = ( kind, 'execute' )
        return self._process

    def _process(self, **kw):
        rc = None
        if self._todo:
            kind, method = self._todo
            self._todo = None
            rc = list()
            for item in self.candidates(kind):
                xx = getattr(item, method, None)
                if xx:
                    rc.append(xx(**kw))
                else:
                    rc.append(None)
        return rc
        

#: Default action dispatcher... containing an anonymous SendMail action
actiond = Dispatcher()
actiond.add(SendMail())

