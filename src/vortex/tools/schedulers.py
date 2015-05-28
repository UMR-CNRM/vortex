#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
Interface to SMS commands.
"""

__all__ = []

from types import *   # @UnusedWildImport

import footprints
logger = footprints.loggers.getLogger(__name__)

from .services import Service


class Scheduler(Service):
    """Abstract class for scheduling systems."""

    _abstract  = True
    _footprint = dict(
        info = 'Scheduling service class',
        attr = dict(
            rootdir = dict(
                optional = True,
                default  = None,
                alias    = ('install',),
                access   = 'rwx',
            ),
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


class SMS(Scheduler):
    """
    Client interface to SMS scheduling and monitoring system.
    """

    _footprint = dict(
        info = 'SMS client service',
        attr = dict(
            kind = dict(
                values   = ['sms'],
            ),
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('SMS scheduler client init %s', self)
        super(SMS, self).__init__(*args, **kw)
        if self.rootdir is None:
            thistarget = self.sh.target()
            guesspath  = self.env.SMS_INSTALL_ROOT or thistarget.get('sms:rootdir')
            if guesspath is None:
                logger.warning('SMS service could not guess install location [%s]', str(guesspath))
            else:
                generictarget = thistarget.generic() or self.env.TARGET
                if generictarget is None:
                    logger.warning('SMS service could not guess target name [%s]', generictarget)
                else:
                    self.rootdir = guesspath + '/' + generictarget
        if self.sh.path.exists(self.cmdpath('init')):
            self.env.setbinpath(self.rootdir)
        else:
            logger.warning('No SMS client found at init time [rootdir:%s]>', self.rootdir)

    def cmd_rename(self, cmd):
        """Remap command name. Strip any sms prefix."""
        cmd = super(SMS, self).cmd_rename(cmd)
        while cmd.startswith('sms'):
            cmd = cmd[3:]
        return cmd

    def conf(self, kwenv):
        """Possibly export the provided sms variables and return a dictionary of positioned variables."""
        if kwenv:
            for smsvar in [ x.upper() for x in kwenv.keys() if x.upper().startswith('SMS') ]:
                self.env[smsvar] = str(kwenv[smsvar])
        subenv = dict()
        for smsvar in [ x for x in self.env.keys() if x.startswith('SMS') ]:
            subenv[smsvar] = self.env.get(smsvar)
        return subenv

    def info(self):
        """Dump current defined sms variables."""
        for smsvar, smsvalue in self.conf(dict()).iteritems():
            print '{0:s}="{1:s}"'.format(smsvar, str(smsvalue))

    def __call__(self, *args):
        """By default call the :meth:`info` method."""
        return self.info()

    def cmdpath(self, cmd):
        """Return a complete binary path to cmd."""
        cmd = 'sms' + self.cmd_rename(cmd)
        if self.rootdir:
            return self.sh.path.join(self.rootdir, cmd)
        else:
            return cmd

    def path(self):
        """Return actual binary path to SMS commands."""
        return self.rootdir

    def wrap_in(self):
        """Last minute wrap before binary child command."""
        self.env.SMSACTUALPATH = self.rootdir

    def wrap_out(self):
        """Restaure execution state as before :meth:`wrap_in`."""
        del self.env.SMSACTUALPATH

    def setup_default(self, *args):
        """Fake method for any missing callback, ie: setup_init, setup_abort, etc."""
        return True

    def close_default(self, *args):
        """Fake method for any missing callback, ie: close_init, close_abort, etc."""
        return True

    def child(self, cmd, options):
        """Miscellaneous smschild subcommand."""
        rc  = None
        cmd = self.cmd_rename(cmd)
        if cmd in self.muteset:
            logger.warning('SMS mute command [%s]', cmd)
        else:
            args = [self.cmdpath(cmd)]
            if type(options) is ListType or type(options) is TupleType:
                args.extend(options)
            else:
                args.append(options)
            if getattr(self, 'setup_' + cmd, self.setup_default)(*options):
                self.wrap_in()
                rc = self.sh.spawn(args, output=False)
                self.wrap_out()
                getattr(self, 'close_' + cmd, self.close_default)(*options)
            else:
                logger.warning('Actual [sms%s] command skipped due to setup action', cmd)
        return rc

    def abort(self, *opts):
        """Gateway to :meth:`child` abort method."""
        return self.child('abort', opts)

    def complete(self, *opts):
        """Gateway to :meth:`child` complete method."""
        return self.child('complete', opts)

    def event(self, *opts):
        """Gateway to :meth:`child` event method."""
        return self.child('event', opts)

    def init(self, *opts):
        """Gateway to :meth:`child` init method."""
        return self.child('init', opts)

    def label(self, *opts):
        """Gateway to :meth:`child` label method."""
        return self.child('label', opts)

    def meter(self, *opts):
        """Gateway to :meth:`child` meter method."""
        return self.child('meter', opts)

    def msg(self, *opts):
        """Gateway to :meth:`child` msg method."""
        return self.child('msg', opts)

    def variable(self, *opts):
        """Gateway to :meth:`child` variable method."""
        return self.child('variable', opts)


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
        super(SMSColor, self).wrap_in()
        print "SMS COLOR"
