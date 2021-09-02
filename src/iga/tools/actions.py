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
from vortex.tools.actions import Action, TunableAction, actiond
from vortex.tools.services import Directory
from vortex.util.config import GenericConfigParser

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


class Route(TunableAction):
    """
    Class responsible for routing data to the Transfer Agent (BDAP, BDPE, BDM).
    """

    def __init__(self, kind='route', service=None, active=False):
        super(Route, self).__init__(kind=kind, active=active, service=service)


class DMTEvent(Action):
    """
    Class responsible for handling Soprano DMT events (mainly for resources availability)
    """

    def __init__(self, kind='dmt', service='dmtevent', active=False):
        super(DMTEvent, self).__init__(kind=kind, active=active, service=service)


class OpMail(TunableAction):
    """
    Class responsible for sending pre-defined mails.
    """

    def __init__(self, kind='opmail', service='opmail', active=False,
                 directory=None, catalog=None, inputs_charset=None):
        super(OpMail, self).__init__(configuration=None, kind=kind, active=active, service=service)
        self.directory = directory or Directory('@opmail-address-book.ini',
                                                encoding=inputs_charset)
        self.catalog = catalog or GenericConfigParser('@opmail-inventory.ini',
                                                      encoding=inputs_charset)
        self.inputs_charset = inputs_charset

    def service_info(self, **kw):
        """Kindly propose the permanent directory and catalog to the final service"""
        kw.setdefault('directory', self.directory)
        kw.setdefault('catalog', self.catalog)
        kw.setdefault('inputs_charset', self.inputs_charset)
        return super(OpMail, self).service_info(**kw)

    def execute(self, *args, **kw):
        """
        Perform the action through a service. Extraneous arguments (not included
        in the footprint) are collected and explicitely transmitted to the service
        in a dictionary.
        """
        rc = None
        service = self.get_active_service(**kw)
        if service:
            options = {k: v for k, v in kw.items() if k not in service.footprint_attributes}
            rc = service(options)
        return rc


class OpPhase(TunableAction):
    """
    Class responsible for phasing resources to a fall-back machine
    or to a redundant filesystem, for crash recovery.
    The configuration must be a section in the target-xxx.ini file.
    """

    def __init__(self, configuration, kind='phase', service=None, active=False):
        if configuration is None:
            raise ValueError("The configuration argument cannot be `None`")
        super(OpPhase, self).__init__(configuration=configuration, kind=kind, active=active, service=service)
        self._rhtodo = list()
        self._rhdone = list()

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
    def immediate(self):
        """Tell whether we are in 'immediate' (or 'atend') mode."""
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

        active = not self.getx('dryrun', default=False)
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
        sh = sessions.current().sh
        paths_in_cache = rh.locate(incache=True, inpromise=False) or ''
        first_path = paths_in_cache.split(';')[0]
        if first_path == '':
            raise ValueError('No access from a cache to the resource')
        incache_path = sh.path.abspath(first_path)

        if sh.path.exists(incache_path):
            effective_path = incache_path
        else:
            effective_path = sh.path.abspath(rh.container.localpath())

        protocol = self.getx('protocol', silent=False)
        jname = self.getx('jname', silent=False)

        # possibly change the destination prefix
        basepaths = self.getx('basepaths', default='', aslist=True)
        if basepaths:
            src, dst = basepaths
            if not sh.path.commonpath((incache_path, src,)) == src:
                dst, src = src, dst
                if not sh.path.commonpath((incache_path, src,)) == src:
                    msg = "Basepaths are incompatible with resource path\n\tpath={}\n\tbasepaths={}".format(
                        incache_path, basepaths)
                    raise ValueError(msg)
            if not src.endswith('/'):
                src += '/'
            lastpart = incache_path.replace(src, '')
            remote_path = sh.path.join(dst, lastpart)
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
            original=sh.path.abspath(effective_path),
            **opts
        )

        return actiond.jeeves(**jeeves_opts)


actiond.add(SendAlarm(), Route(), DMTEvent(), OpMail(inputs_charset='utf-8'),
            *OpPhase.actions())
