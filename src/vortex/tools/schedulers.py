#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Interface to SMS commands.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import functools
import six

from bronx.fancies import loggers
import footprints

from .services import Service

__all__ = []

logger = loggers.getLogger(__name__)


class Scheduler(Service):
    """Abstract class for scheduling systems."""

    _abstract  = True
    _footprint = dict(
        info = 'Scheduling service class',
        attr = dict(
            muteset = dict(
                optional = True,
                default  = footprints.FPSet(),
                type     = footprints.FPSet,
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Scheduler init %s', self.__class__)
        super(Scheduler, self).__init__(*args, **kw)

    @property
    def env(self):
        return self.sh.env

    def cmd_rename(self, cmd):
        """Remap command name. Default is lowercase command name."""
        return cmd.lower()

    def mute(self, cmd):
        """Switch off the given command."""
        self.muteset.add(self.cmd_rename(cmd))

    def play(self, cmd):
        """Switch on the given command."""
        self.muteset.discard(self.cmd_rename(cmd))

    def clear(self):
        """Clear set of mute commands."""
        self.muteset.clear()


class EcmwfLikeScheduler(Scheduler):
    """Abstract class for any ECMWF scheduling systems (SMS, Ecflow)."""

    _abstract  = True
    _footprint = dict(
        attr = dict(
            env_pattern = dict(
                info = 'Scheduler configuration variables start with...',
            ),
        )
    )

    _KNOWN_CMD = ()

    def conf(self, kwenv):
        """Possibly export the provided variables and return a dictionary of positioned variables."""
        if kwenv:
            for schedvar in [ x.upper() for x in kwenv.keys() if x.upper().startswith(self.env_pattern) ]:
                self.env[schedvar] = six.text_type(kwenv[schedvar])
        subenv = dict()
        for schedvar in [ x for x in self.env.keys() if x.startswith(self.env_pattern) ]:
            subenv[schedvar] = self.env.get(schedvar)
        return subenv

    def info(self):
        """Dump current defined variables."""
        for schedvar, schedvalue in six.iteritems(self.conf(dict())):
            print('{0:s}="{1!s}"'.format(schedvar, schedvalue))

    def __call__(self, *args):
        """By default call the :meth:`info` method."""
        return self.info()

    def setup_default(self, *args):
        """Fake method for any missing callback, ie: setup_init, setup_abort, etc."""
        return True

    def close_default(self, *args):
        """Fake method for any missing callback, ie: close_init, close_abort, etc."""
        return True

    def wrap_in(self):
        """Last minute wrap before binary child command."""
        return True

    def wrap_out(self):
        """Restore execution state as before :meth:`wrap_in`."""
        pass

    def child(self, cmd, *options):
        """Miscellaneous sms/ecflow child sub-command."""
        rc  = None
        cmd = self.cmd_rename(cmd)
        if cmd in self.muteset:
            logger.warning('%s mute command [%s]', self.kind, cmd)
        else:
            if getattr(self, 'setup_' + cmd, self.setup_default)(*options):
                rc = self.wrap_in()
                if rc:
                    try:
                        rc = self._actual_child(cmd, options)
                    finally:
                        self.wrap_out()
                        getattr(self, 'close_' + cmd, self.close_default)(*options)
                else:
                    logger.warning('Actual [%s %s] command wrap_in failed', self.kind, cmd)
            else:
                logger.warning('Actual [%s %s] command skipped due to setup action',
                               self.kind, cmd)
        return rc

    def _actual_child(self, cmd, options):
        """The actual child command implementation."""
        raise NotImplementedError("This an abstract method.")

    def __getattr__(self, name):
        """Deal with any known commands."""
        if name in self._KNOWN_CMD:
            return functools.partial(self.child, name)
        else:
            return super(EcmwfLikeScheduler, self).__getattr__(name)


class SMS(EcmwfLikeScheduler):
    """
    Client interface to SMS scheduling and monitoring system.
    """

    _footprint = dict(
        info = 'SMS client service',
        attr = dict(
            kind = dict(
                values   = ['sms'],
            ),
            rootdir = dict(
                optional = True,
                default  = None,
                alias    = ('install',),
            ),
            env_pattern = dict(
                default  = 'SMS',
                optional = True,
            )
        )
    )

    _KNOWN_CMD = ('abort', 'complete', 'event', 'init', 'label', 'meter',
                  'msg', 'variable', 'fix')

    def __init__(self, *args, **kw):
        logger.debug('SMS scheduler client init %s', self)
        super(SMS, self).__init__(*args, **kw)
        self._actual_rootdir = self.rootdir
        if self._actual_rootdir is None:
            thistarget = self.sh.default_target
            guesspath  = self.env.SMS_INSTALL_ROOT or thistarget.get('sms:rootdir')
            if guesspath is None:
                logger.warning('SMS service could not guess install location [%s]', str(guesspath))
            else:
                generictarget = thistarget.generic() or self.env.TARGET
                if generictarget is None:
                    logger.warning('SMS service could not guess target name [%s]', generictarget)
                else:
                    self._actual_rootdir = guesspath + '/' + generictarget
        if self.sh.path.exists(self.cmdpath('init')):
            self.env.setbinpath(self._actual_rootdir)
        else:
            logger.warning('No SMS client found at init time [rootdir:%s]>', self._actual_rootdir)

    def cmd_rename(self, cmd):
        """Remap command name. Strip any sms prefix."""
        cmd = super(SMS, self).cmd_rename(cmd)
        while cmd.startswith('sms'):
            cmd = cmd[3:]
        return cmd

    def cmdpath(self, cmd):
        """Return a complete binary path to cmd."""
        cmd = 'sms' + self.cmd_rename(cmd)
        if self._actual_rootdir:
            return self.sh.path.join(self._actual_rootdir, cmd)
        else:
            return cmd

    def path(self):
        """Return actual binary path to SMS commands."""
        return self._actual_rootdir

    def wrap_in(self):
        """Last minute wrap before binary child command."""
        rc = super(SMS, self).wrap_in()
        self.env.SMSACTUALPATH = self._actual_rootdir
        return rc

    def wrap_out(self):
        """Restaure execution state as before :meth:`wrap_in`."""
        del self.env.SMSACTUALPATH
        super(SMS, self).wrap_out()

    def _actual_child(self, cmd, options):
        """Miscellaneous smschild subcommand."""
        args = [self.cmdpath(cmd)]
        args.extend(options)
        return self.sh.spawn(args, output=False)


class SMSColor(SMS):
    """
    Default SMS service with some extra colorful features.
    """

    _footprint = dict(
        info = 'SMS color client service',
        attr = dict(
            kind = dict(
                values   = ['smscolor'],
            ),
        )
    )

    def wrap_in(self):
        """Last minute wrap before binary child command."""
        rc = super(SMSColor, self).wrap_in()
        print("SMS COLOR")
        return rc


class EcFlow(EcmwfLikeScheduler):
    """
    Client interface to the ecFlow scheduling and monitoring system.
    """

    _footprint = dict(
        info = 'SMS client service',
        attr = dict(
            kind = dict(
                values   = ['ecflow'],
            ),
            clientpath = dict(
                info     = ("Path to the ecFlow client binary (if omitted, " +
                            "it's read in the configuration file)"),
                optional = True,
                default  = None,
            ),
            env_pattern = dict(
                default  = 'ECF_',
                optional = True,
            )
        )
    )

    _KNOWN_CMD = ('abort', 'complete', 'event', 'init', 'label', 'meter', 'msg', 'alter')

    def __init__(self, *args, **kw):
        logger.debug('EcFlow scheduler client init %s', self)
        super(EcFlow, self).__init__(*args, **kw)
        self._actual_clientpath = self.clientpath
        self._tunnel = None

    def path(self):
        """Return the actual binary path to the EcFlow client."""
        if self._actual_clientpath is None:
            thistarget = self.sh.default_target
            guesspath = self.env.ECF_CLIENT_PATH or thistarget.get('ecflow:clientpath')
            ecfversion = self.env.get('ECF_VERSION', 'default')
            guesspath = guesspath.format(version=ecfversion)
            if guesspath is None:
                logger.warning('ecFlow service could not guess the install location [%s]', str(guesspath))
            else:
                self._actual_clientpath = guesspath
        if not self.sh.path.exists(self._actual_clientpath):
            logger.warning('No ecFlow client found at init time [path:%s]>', self._actual_clientpath)
        return self._actual_clientpath

    def wrap_in(self):
        """When running on an node without network access create an SSH tunnel."""
        rc = super(EcFlow, self).wrap_in()
        if not self.sh.default_target.isnetworknode:
            # wait and retries from config
            thistarget = self.sh.default_target
            sshwait = thistarget.get('ecflow:sshproxy_wait', 6)
            sshretries = thistarget.get('ecflow:sshproxy_retries', 2)
            sshretrydelay = thistarget.get('ecflow:sshproxy_retrydelay', 1)
            # Build up an SSH tunnel to convey the EcFlow command
            ecconf = self.conf(dict())
            echost = ecconf.get('{:s}HOST'.format(self.env_pattern), None)
            ecport = ecconf.get('{:s}PORT'.format(self.env_pattern), None)
            if not (echost and ecport):
                rc = False
            else:
                sshobj = self.sh.ssh('network', virtualnode=True,
                                     maxtries=sshretries, triesdelay=sshretrydelay)
                self._tunnel = sshobj.tunnel(echost, int(ecport), maxwait=sshwait)
                if not self._tunnel:
                    rc = False
                else:
                    newvars = {'{:s}HOST'.format(self.env_pattern): 'localhost',
                               '{:s}PORT'.format(self.env_pattern): self._tunnel.entranceport}
                    self.env.delta(** newvars)
                    rc = True
        return rc

    def wrap_out(self):
        """Close the tunnel and restore the environment."""
        if self._tunnel:
            self._tunnel.close()
            self._tunnel = None
            self.env.rewind()
        super(EcFlow, self).wrap_out()

    def _actual_child(self, cmd, options):
        """Miscellaneous ecFlow sub-command."""
        args = [self.path(), ]
        if options:
            args.append('--{:s}={!s}'.format(cmd, options[0]))
            if len(options) > 1:
                args.extend(options[1:])
        else:
            args.append('--{:s}'.format(cmd))
        args = [six.text_type(a) for a in args]
        logger.info('Issuing the ecFlow command: %s', ' '.join(args[1:]))
        return self.sh.spawn(args, output=False)

    def abort(self, *opts):
        """Gateway to :meth:`child` abort method."""
        actual_opts = list(opts)
        if not actual_opts:
            # For backward compatibility with SMS
            actual_opts.append("No abort reason provided")
        return self.child('abort', *actual_opts)
