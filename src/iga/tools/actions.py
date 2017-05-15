#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
Actions specific to operational needs.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import collections

import footprints
from vortex.data.handlers import Handler
from vortex.toolbox import sessions
from vortex.tools.actions import Action, actiond
from vortex.tools.services import Directory
from vortex.util.config import GenericConfigParser

#: Export nothing
__all__ = []

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

    def __init__(self, kind='opmail', service='opmail', active=True, directory=None, catalog=None):
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
            options = {k: v for k, v in kw.items() if k not in service.footprint_attributes}
            rc = service(options)
        return rc


class OpPhase(Action):
    """
    Class responsible for phasing resources to a fall-back machine
    or to a redundant filesystem, for crash recovery.
    The configuration must be a section in the target-xxx.ini file.
    """

    def __init__(self, configuration, kind='phase', service=None, active=True):
        super(OpPhase, self).__init__(kind=kind, active=active, service=service)
        self._rhtodo = list()
        self._rhdone = list()
        self._sh = sessions.system()
        self._parser = None
        self._section = None
        self._tuning = dict()
        self.configure(configuration)

    @staticmethod
    def actions():
        """Create Actions to handle the several Phase configurations
           described in the configuration file target-xxx.ini."""
        parser = sessions.system().target().config
        if parser.has_section('phase'):
            active_actions = parser.getx(key='phase:active_actions', aslist=True)
        else:
            active_actions = []
        return [OpPhase(action) for action in active_actions]

    @property
    def sh(self):
        return self._sh

    @property
    def section(self):
        return self._section

    def tune(self, section=None, **kw):
        """Add options to override the .ini file configuration.
           ``section`` is a specific section name, or ``None`` for all.
        """
        if section is None or section == self._section:
            self._tuning.update(kw)

    def configure(self, section, show=False):
        """Check and set the configuration: a section in the target-xxx.ini file."""
        target = self.sh.target()
        self._parser = target.config
        self._section = section
        if section not in self._parser.sections():
            raise KeyError('No section "{}" in "{}"'.format(section, self._parser.file))
        if show:
            self.show_config()

    def show_config(self):
        """Show the current configuration (for debugging purposes)."""
        from pprint import pprint
        print('\n=== Phase configuration:', self._section)
        pprint(self._parser.as_dict()[self._section])
        if self._tuning:
            print('\n+++ Fine tuning:')
            pprint(self._tuning)
            print('\n+++ Real configuration:')
            final_dict = dict(self._parser.as_dict()[self._section])
            final_dict.update(self._tuning)
            pprint(final_dict)
        print()

    def getx(self, key, *args, **kw):
        """Shortcut to access the configuration overridden by the tuning."""
        if key in self._tuning:
            return self._tuning[key]
        return self._parser.getx(key=self._section + ':' + key, *args, **kw)

    @property
    def immediate(self):
        mode = self.getx('mode', default='immediate')
        if mode == 'immediate':
            return True
        if mode == 'atend':
            return False
        logger.warn('Phase mode should be "immediate" or "atend", not "%s". '
                    'Using "immediate".', mode)
        return True

    def execute(self, *args, **kw):
        """Perform the action:

            * Accepts lists of resource handlers (any iterable, nested ot not)
            * In immediate mode (or if given flush=True), do it now.
            * Else keep track of resources for a later call to flush()
        """

        def isiterable(item):
            return (
                isinstance(item, collections.Iterable)
                and not isinstance(item, basestring)
            )

        def flatten(iterable):
            """Recursively flattens an iterable.
            >>> list(flatten(([[1], [2, 3]],)))
            [1, 2, 3]
            """
            for item in iterable:
                if isiterable(item):
                    for p in flatten(item):
                        yield p
                else:
                    yield item

        rhs = {rh for rh in flatten(args) if isinstance(rh, Handler)}
        sendnow = kw.pop('flush', False) or self.immediate
        if sendnow:
            return self._send(rhs, **kw)
        else:
            self._rhtodo.extend(rhs)
            return True

    def flush(self, **kw):
        """Send resources accumulated by previous calls."""
        if self._rhtodo:
            self._send(self._rhtodo, **kw)
            self._rhtodo = list()

    def _send(self, rhlist, **opts):
        """Send a list of resources.
        The env variable OP_PHASE controls global de/activation.
        """
        t = sessions.current()
        env = t.env

        active = bool(env.get('OP_PHASE', 1))
        if not active:
            logger.warn('OpPhase is not active (e.OP_PHASE={})'.format(env.get('OP_PHASE', '<not set>')))
            for r in rhlist:
                logger.warn('-- Would phase: %s', str(r))
            return True

        rc = True
        for rh in rhlist:
            rc = rc and self._sendone(rh, **opts)
            self._rhdone.append(rh)
        return rc

    def _sendone(self, rh, **opts):
        """Ask Jeeves to phase a resource."""
        sh = sessions.system()
        paths_in_cache = rh.locate(incache=True, inpromise=False) or ''
        first_path = paths_in_cache.split(';')[0]
        if first_path is '':
            raise ValueError('No access from a cache to the resource')
        rh_path = sh.path.abspath(first_path)

        protocol = self.getx('protocol', silent=False)
        jname = self.getx('jname', silent=False)

        # possibly change the destination prefix
        basepaths = self.getx('basepaths', default='', aslist=True)
        if basepaths:
            src, dst = basepaths
            if not rh_path.startswith(src):
                dst, src = basepaths
                if not rh_path.startswith(src):
                    msg = "Basepaths are incompatible with resource path\n\tpath={}\n\tbasepaths={}".format(
                        rh_path, basepaths)
                    raise ValueError(msg)
            if not src.endswith('/'):
                src += '/'
            lastpart = rh_path.replace(src, '')
            destination = sh.path.join(dst, lastpart)
        else:
            destination = rh_path

        jeeves_opts = dict(
            jname=jname,
            rhandler=rh.as_dict(),
        )

        # protocol-specific part
        if protocol == 'scp':
            phase_loginnode = self.getx('phase_loginnode', silent=False)
            phase_transfernode = self.getx('phase_transfernode', silent=False)
            jeeves_opts.update(
                todo='phase_scp',
                phase_loginnode=phase_loginnode,
                phase_transfernode=phase_transfernode,
                logname=self.getx('phase_logname', silent=False),
            )

        elif protocol == 'ftp':
            phase_loginnode = self.getx('phase_loginnode', silent=False)
            phase_transfernode = self.getx('phase_transfernode', silent=False)
            jeeves_opts.update(
                todo='phase_ftput',
                phase_loginnode=phase_loginnode,
                phase_transfernode=phase_transfernode,
                logname=self.getx('phase_logname', silent=False),
            )
        elif protocol == 'cp':
            if rh_path == destination:
                msg = "Cannot locally phase file onto itself."
                msg += "path={} basepaths={}".format(rh_path, basepaths)
                raise ValueError(msg)
            jeeves_opts.update(
                todo='cp',
            )
        else:
            raise ValueError('Phase: unknown protocol %s.', protocol)

        # common part (create the hidden copy when config problems are over)
        fmt = rh.container.actualfmt
        hide = footprints.proxy.service(kind='hiddencache', asfmt=fmt)
        jeeves_opts.update(
            fmt=fmt,
            source=hide(rh_path),
            destination=destination,
            **opts
        )

        return actiond.jeeves(**jeeves_opts)


actiond.add(SendAlarm(), Route(), DMTEvent(), OpMail(), *OpPhase.actions())
