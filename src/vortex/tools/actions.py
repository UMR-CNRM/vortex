# -*- coding: utf-8 -*-

"""
Module managing the sending of messages.
Default action classes must provide four methods: on, off, status, execute.
The on, off and status functions must return a boolean value reflecting the
status of the action. As far as the execute function is concerned,
it must deal with the data (given to realize the action) and the action
to be processed: e.g. mail, routing, alarm.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers
import bronx.stdtypes.catalog
import footprints

from vortex.util.authorizations import is_authorized_user
from vortex import sessions

#: Export nothing
__all__ = []

logger = loggers.getLogger(__name__)


class Action(object):
    """
    An ``Action`` object is intended to produce a dedicated service through a simple command
    which internally refers to the :meth:`execute` method.
    Such an action could be activated or not, and is basically driven by permissions settings.
    """

    def __init__(self, kind='foo', service=None, active=False, permanent=False):
        if service is None:
            service = 'send' + kind
        self._service = service
        self._kind = kind
        self._active = active
        self._permanent = permanent
        self._frozen = None

    @property
    def kind(self):
        """Kind name of this action."""
        return self._kind

    @property
    def service(self):
        """Standard service associated to this action."""
        return self._service

    @property
    def active(self):
        """Current status of the action as a boolean property."""
        return self._active

    def permanent(self, update=None):
        """Return or update the permanent status of this action."""
        if update is not None:
            self._permanent = bool(update)
            if not self._permanent:
                self._frozen = None
        return self._permanent

    def clear_service(self):
        """Clear the possibly defined permanent service."""
        self._frozen = None

    def status(self, update=None):
        """Return or update current active status."""
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
        info = dict(kw)
        info.setdefault('kind', self.service_kind(**kw))
        return info

    def get_actual_service(self, **kw):
        """Return the service instance determined by the actual description."""
        info = self.service_info(**kw)
        if self.permanent():
            if self._frozen is None:
                self._frozen = footprints.proxy.services.default(**info)
            a_service = self._frozen
        else:
            a_service = footprints.proxy.service(**info)
        return a_service

    def get_active_service(self, **kw):
        """Return the actual service according to active status and user authorizations."""
        a_service = None
        if is_authorized_user(action=self.kind):
            if self.active:
                a_service = self.get_actual_service(**kw)
                if a_service is None:
                    logger.warning('Could not find any service for action %s', self.kind)
            else:
                logger.warning('Action %s is not active', self.kind)
        else:
            logger.warning('User is not authorized to perform %s', self.kind)
        return a_service

    def execute(self, *args, **kw):
        """Generic method to perform the action through a service."""
        rc = None
        service = self.get_active_service(**kw)
        if service:
            rc = service(*args)
        return rc


class TunableAction(Action):
    """An Action that may be tuned

    - may have it's own section in the target configuration files
    - accepts the syntax `ad.action_tune(key=value)` (which has priority)
    """

    def __init__(self, configuration=None, **kwargs):
        super(TunableAction, self).__init__(**kwargs)
        self._tuning = dict()
        self._conf_section = None
        self.configure(configuration)

    @property
    def _shtarget(self):
        return sessions.current().sh.default_target

    def configure(self, section, show=False):
        """Check and set the configuration: a section in the target-xxx.ini file."""
        self._conf_section = section
        if section is not None:
            if section not in self._shtarget.sections():
                raise KeyError('No section "{}" in "{}"'.format(section, self._shtarget.config.file))
        if show:
            self.show_config()

    def tune(self, section=None, **kw):
        """Add options to override the .ini file configuration.

        ``section`` is a specific section name, or ``None`` for all.
        """
        if section is None or section == self._conf_section:
            self._tuning.update(kw)

    def _get_config_dict(self):
        final_dict = dict()
        final_dict.update(self._shtarget.items(self._conf_section))
        final_dict.update(self._tuning)
        return final_dict

    def show_config(self):
        """Show the current configuration (for debugging purposes)."""
        from pprint import pprint
        print('\n=== Phase configuration:', self._conf_section)
        final_dict = dict()
        if self._conf_section is not None:
            pprint(self._shtarget.items(self._conf_section))
            final_dict.update(self._shtarget.items(self._conf_section))
        if self._tuning:
            print('\n+++ Fine tuning:')
            pprint(self._tuning)
            print('\n+++ Real configuration:')
            final_dict.update(self._tuning)
            pprint(final_dict)
        print()

    def getx(self, key, *args, **kw):
        """Shortcut to access the configuration overridden by the tuning."""
        if key in self._tuning:
            return self._tuning[key]
        elif self._conf_section is not None:
            return self._shtarget.getx(key=self._conf_section + ':' + key, *args, **kw)
        elif 'default' in kw:
            return kw['default']
        else:
            raise KeyError('The "{:s}" entry was not found in any configuration'.format(key))


class SendMail(Action):
    """
    Class responsible for sending emails.
    """

    def __init__(self, kind='mail', service='sendmail', active=True, quoteprintable=True):
        super(SendMail, self).__init__(kind=kind, active=active, service=service)
        if quoteprintable:
            from email import charset
            charset.add_charset('utf-8', charset.QP, charset.QP, 'utf-8')


class Report(Action):
    """
    Class responsible for sending reports.
    """

    def __init__(self, kind='report', service='sendreport', active=True):
        super(Report, self).__init__(kind=kind, active=active, service=service)


class SSH(Action):
    """
    Class responsible for sending commands to an SSH proxy.
    """

    def __init__(self, kind='ssh', service='ssh', active=True):
        super(SSH, self).__init__(kind=kind, active=active, service=service)


class AskJeeves(TunableAction):
    """
    Class responsible for posting requests to Jeeves daemon.
    """

    def __init__(self, kind='jeeves', service='askjeeves', active=True):
        super(AskJeeves, self).__init__(configuration=None, kind=kind, active=active, service=service)

    def execute(self, *args, **kw):
        """Generic method to perform the action through a service."""
        rc = None
        if 'kind' in kw:
            kw['fwd_kind'] = kw.pop('kind')
        for k, v in self._get_config_dict():
            kw.setdefault(k, v)
        service = self.get_active_service(**kw)
        if service:
            talk = {k: v for k, v in kw.items() if k not in service.footprint_attributes}
            rc = service(talk)
        return rc


class Prompt(Action):
    """
    Fake action that could be used for any real action.
    """

    def __init__(self, kind='prompt', service='prompt', active=True):
        super(Prompt, self).__init__(kind=kind, active=active, service=service)

    def execute(self, *args, **kw):
        """Do nothing but prompt the actual arguments."""
        # kind could be unintentionally given, force it back
        kw['kind'] = self.kind
        service = self.get_active_service(**kw)
        rc = False
        if service:
            options = {k: v for k, v in kw.items() if k not in service.footprint_attributes}
            rc = service(options)
        return rc

    def foo(self, *args, **kw):
        """Yet an other foo method."""
        print('#FOO', self.kind, '/ args:', args, '/ kw:', kw)
        return True


class FlowSchedulerGateway(Action):
    """
    Send a child command to any ECMWF's workfow scheduler.
    """

    _KNOWN_CMD = dict(sms=['abort', 'complete', 'event', 'init', 'label', 'meter', 'msg', 'variable', 'fix'],
                      ecflow=['abort', 'complete', 'event', 'init', 'label', 'meter', 'msg'])

    def __init__(self, kind='flow', service=None, active=True, permanent=True):
        """
        The `service` attribute must be specified (it can be either sms or ecflow).
        """
        if service is None:
            raise ValueError('The service name must be provided')
        super(FlowSchedulerGateway, self).__init__(kind=kind, active=active,
                                                   service=service, permanent=permanent)

    def gateway(self, *args, **kw):
        """Ask the Scheduler to run any (but known) command."""
        rc = None
        service = self.get_active_service(**kw)
        if service and self._schedcmd is not None:
            kwbis = {k: v for k, v in kw.items() if k in ('critical', )}
            rc = getattr(service, self._schedcmd)(*args, **kwbis)
        self._schedcmd = None
        return rc

    def __getattr__(self, attr):
        if attr.startswith('_'):
            raise AttributeError
        if attr in (['conf', 'info', 'clear', 'mute', 'play', 'path', ] +
                    self._KNOWN_CMD[self.service]):
            self._schedcmd = attr
            return self.gateway
        else:
            self._schedcmd = None
            return None


class SmsGateway(FlowSchedulerGateway):
    """Send a child command to an SMS server."""

    def __init__(self, kind='sms', service='sms', active=True, permanent=True):
        super(SmsGateway, self).__init__(kind=kind, active=active, service=service, permanent=permanent)


class EcflowGateway(FlowSchedulerGateway):
    """Send a child command to an Ecflow server."""

    def __init__(self, kind='ecflow', service='ecflow', active=True, permanent=True):
        super(EcflowGateway, self).__init__(kind=kind, active=active, service=service, permanent=permanent)


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
            if xx is not None:
                rc.append(xx(*args, **kw))
            else:
                rc.append(None)
        return rc


class Dispatcher(bronx.stdtypes.catalog.Catalog):
    """
    Central office for dispatching actions.
    """

    def __init__(self, **kw):
        logger.debug('Action dispatcher init %s', self)
        super(Dispatcher, self).__init__(**kw)

    @property
    def actions(self):
        """A set of kind names of actual actions registered in that Dispatcher."""
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
actiond.add(SendMail(), Report(), AskJeeves(), SSH(), Prompt())
