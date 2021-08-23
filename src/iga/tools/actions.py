# -*- coding: utf-8 -*-

"""
Actions specific to operational needs.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import six

import footprints
from bronx.compat.moves import collections_abc
from bronx.fancies import loggers
from vortex.data.handlers import Handler
from vortex.toolbox import sessions
from vortex.tools.actions import Action, TemplatedMail, actiond
from vortex.tools.services import Directory

#: Export nothing
__all__ = []

logger = loggers.getLogger(__name__)


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


class OpMail(TemplatedMail):
    """
    Class responsible for sending pre-defined mails.
    """

    def __init__(self, kind='opmail', service='opmail', active=True,
                 directory=None, catalog=None, inputs_charset=None):
        super(OpMail, self).__init__(kind=kind, active=active, service=service,
                                     catalog=catalog, inputs_charset=inputs_charset)
        self.directory = directory or Directory('@{:s}-address-book.ini'.format(kind),
                                                encoding=inputs_charset)

    def service_info(self, **kw):
        """Kindly propose the permanent directory and catalog to the final service"""
        kw.setdefault('directory', self.directory)
        return super(OpMail, self).service_info(**kw)


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
        self._section = None
        self._tuning = dict()
        self.configure(configuration)

    @staticmethod
    def actions():
        """
        Create Actions to handle the several Phase configurations described in
        the `target-xxx.ini` configuration file.
        """
        target = sessions.system().default_target
        if 'phase' in target.sections():
            active_actions = target.getx(key='phase:active_actions', aslist=True)
        else:
            active_actions = []
        return [OpPhase(action) for action in active_actions]

    @property
    def sh(self):
        return self._sh

    @property
    def shtarget(self):
        return self.sh.default_target

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
        self._section = section
        if section not in self.shtarget.sections():
            raise KeyError('No section "{}" in "{}"'.format(section, self.shtarget.config.file))
        if show:
            self.show_config()

    def show_config(self):
        """Show the current configuration (for debugging purposes)."""
        from pprint import pprint
        print('\n=== Phase configuration:', self._section)
        pprint(self.shtarget.items(self._section))
        if self._tuning:
            print('\n+++ Fine tuning:')
            pprint(self._tuning)
            print('\n+++ Real configuration:')
            final_dict = dict(self.shtarget.items(self._section))
            final_dict.update(self._tuning)
            pprint(final_dict)
        print()

    def getx(self, key, *args, **kw):
        """Shortcut to access the configuration overridden by the tuning."""
        if key in self._tuning:
            return self._tuning[key]
        return self.shtarget.getx(key=self._section + ':' + key, *args, **kw)

    @property
    def immediate(self):
        mode = self.getx('mode', default='immediate')
        if mode == 'immediate':
            return True
        if mode == 'atend':
            return False
        logger.warning('Phase mode should be "immediate" or "atend", not "%s". '
                       'Using "immediate".', mode)
        return True

    def execute(self, *args, **kw):
        """Perform the requested action.

        * Accepts lists of resource handlers (any iterable, nested ot not)
        * In immediate mode (or if given flush=True), do it now.
        * Else keep track of resources for a later call to flush()
        """

        def isiterable(item):
            return (
                isinstance(item, collections_abc.Iterable) and
                not isinstance(item, six.string_types)
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
            logger.warning('OpPhase is not active (e.OP_PHASE={})'.format(env.get('OP_PHASE', '<not set>')))

        rc = True
        for rh in rhlist:
            rc = rc and self._sendone(rh, active, **opts)
            self._rhdone.append(rh)
        return rc

    def _sendone(self, rh, active, **opts):
        """Ask Jeeves to phase a resource.

        Several paths are involved, possibly different:

        - incache_path: the path to the resource in a cache. The resource may not be
          present here yet, since hooks are called **before** the put(), but this
          should be where to phase on the remote machine.
        - effective_path: where the resource exists. Might be incache_path, or the
          container's local path.
        - remote_path: the path to use on the remote machine. This is incache_path,
          but possibly modified according to the basepaths configuration.
        """
        paths_in_cache = rh.locate(incache=True, inpromise=False) or ''
        first_path = paths_in_cache.split(';')[0]
        if first_path == '':
            raise ValueError('No access from a cache to the resource')
        incache_path = self.sh.path.abspath(first_path)

        if self.sh.path.exists(incache_path):
            effective_path = incache_path
        else:
            effective_path = self.sh.path.abspath(rh.container.localpath())

        protocol = self.getx('protocol', silent=False)
        jname = self.getx('jname', silent=False)

        # possibly change the destination prefix
        basepaths = self.getx('basepaths', default='', aslist=True)
        if basepaths:
            src, dst = basepaths
            if not self.sh.path.commonpath((incache_path, src,)) == src:
                dst, src = src, dst
                if not self.sh.path.commonpath((incache_path, src,)) == src:
                    msg = "Basepaths are incompatible with resource path\n\tpath={}\n\tbasepaths={}".format(
                        incache_path, basepaths)
                    raise ValueError(msg)
            if not src.endswith('/'):
                src += '/'
            lastpart = incache_path.replace(src, '')
            remote_path = self.sh.path.join(dst, lastpart)
        else:
            remote_path = incache_path

        # Phase is inactive : tell what would be done
        if not active:
            logger.warning('-- Would phase: %s', effective_path)
            logger.warning('            to: %s', remote_path)
            return True

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
            if effective_path == remote_path:
                msg = "Cannot locally phase file onto itself."
                msg += "\npath={}\nbasepaths={}".format(effective_path, basepaths)
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
            source=hide(effective_path),
            destination=remote_path,
            original=self.sh.path.abspath(effective_path),
            **opts
        )

        return actiond.jeeves(**jeeves_opts)


actiond.add(SendAlarm(), Route(), DMTEvent(), OpMail(inputs_charset='utf-8'),
            *OpPhase.actions())
