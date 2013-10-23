#!/bin/env python
# -*- coding:Utf-8 -*-

"""
Interface to SMS commands.
"""

__all__ = []

from vortex.autolog import logdefault as logger
from vortex import sessions

class SMSGateway(object):

    def __init__(self, tag='void', system=None, env=None, path=None):
        logger.debug('SMS gateway init %s', self)
        self.tag = tag
        self._system = system
        if not self._system:
            self._system = sessions.current().context.system
        self._env = env
        if not self._env:
            self._env = sessions.current().context.env
        self.binpath(path)
        if not self._system.path.exists(self.cmdpath('init')):
            logger.warning('No SMS client found at init time [sms tag:%s]>', self.tag)

    def setenv(self, **kw):
        """Possibly export the provided sms variables and return a dictionary of positioned variables."""
        if kw:
            for smsvar in [ x.upper() for x in kw.keys() if x.upper().startswith('SMS') ]:
                self._env[smsvar] = str(kw[smsvar])
        subenv = dict()
        for smsvar in [ x for x in self._env.keys() if x.startswith('SMS') ]:
            subenv[smsvar] = self._env.get(smsvar)
        return subenv

    def info(self):
        """Dump current positioned sms variables."""
        for smsvar, smsvalue in self.setenv().iteritems():
            print '{0:s}="{1:s}"'.format(smsvar, str(smsvalue))

    def binpath(self, path=None):
        """Set and return the binary path to sms tools."""
        if path is not None:
            self._binpath = self._system.path.normpath(path)
        return self._binpath

    def cmdpath(self, cmd):
        """Return a complete binary path to cmd."""
        cmd = cmd.lower()
        if not cmd.startswith('sms'):
            cmd = 'sms' + cmd
        if self.binpath():
            return self._system.path.join(self.binpath(), cmd)
        else:
            return cmd

    def child(self, command, options):
        """Miscellaneous smschild subcommand."""
        args = [ self.cmdpath(command) ]
        if type(options) == list or type(options) == tuple:
            args.extend(options)
        else:
            args.append(options)
        self._env.SMSACTUALPATH = self.binpath()
        rc = self._system.spawn(args, output=False)
        del self._env.SMSACTUALPATH
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
