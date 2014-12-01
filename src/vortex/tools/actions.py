#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
Module managing the sending of messages.
Default action classes must provide four methods: on, off, status, execute.
The on, off and status functions must return a boolean value reflecting the
status of the action. As far as the execute function is concerned,
it must deal with the data (given to realize the action) and the action
to be processed: e.g. mail, sendbdap, routing, alarm.
"""

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.util.authorizations import is_authorized_user
from vortex.tools import services


class Action(object):

    def __init__(self, kind='foo', service=None, active=False):
        self.kind = kind
        if service is None:
            service = 'send' + self.kind
        self.service = service
        self._active = active

    @property
    def active(self):
        """Current status of the action as a boolean property."""
        return self._active

    def status(self, update=None):
        """Return current active status."""
        if update is not None:
            self._active = bool(update)
        return self._active

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
        return footprints.proxy.service(**info)

    def execute(self, *args, **kw):
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
    def __init__(self, kind='mail', service='sendmail', active=True):
        super(SendMail, self).__init__(kind=kind, active=active, service=service)


class Report(Action):
    """
    Class responsible for sending reports.
    """
    def __init__(self, kind='report', service='sendreport', active=True):
        super(Report, self).__init__(kind=kind, active=active, service=service)


class SpooledActions(object):
    """
    Delayed action to be processed.
    """
    def __init__(self, kind=None, method=None, actions=None):
        """Store effective action and method to be processed."""
        self._kind = kind
        self._method = method
        self._actions = actions

    @property
    def kind(self):
        return self._kind

    @property
    def method(self):
        return self._method

    @property
    def actions(self):
        return self._actions[:]

    def __call__(self, *args, **kw):
        return self.process(*args, **kw)

    def process(self, *args, **kw):
        """Process the actual method for all action candidates of a given kind."""
        rc = list()
        for item in self.actions:
            xx = getattr(item, self.method, None)
            if xx:
                rc.append(xx(*args, **kw))
            else:
                rc.append(None)
        return rc


class Dispatcher(footprints.util.Catalog):
    """
    Central office for dispatching actions.
    """

    def __init__(self, **kw):
        logger.debug('Action dispatcher init %s', self)
        super(Dispatcher, self).__init__(**kw)

    def actions(self):
        return set([x.kind for x in self.items()])

    def candidates(self, kind):
        """Return a selection of the dispatcher's items with the specified ``kind``."""
        return [x for x in self.items() if x.kind == kind]

    def discard_kind(self, kind):
        """A shortcut to discard from the dispatcher any item with the specified ``kind``."""
        for item in self:
            if item.kind == kind:
                self.discard(item)

    def __getattr__(self, attr):
        if attr.startswith('_'):
            raise AttributeError
        a_kind, u_sep, a_method = attr.partition('_')
        if not a_method:
            a_method = 'execute'
        return SpooledActions(a_kind, a_method, self.candidates(a_kind))


#: Default action dispatcher... containing an anonymous SendMail action
actiond = Dispatcher()
actiond.add(SendMail(), Report())

