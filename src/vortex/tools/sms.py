#!/bin/env python
# -*- coding:Utf-8 -*-

"""
Interface to SMS commands.
"""

__all__ = []

from vortex.autolog import logdefault as logger

from vortex import sessions

class SMSGateway(object):

    def __init__(self, tag='void', system=None, env=None):
        logger.debug('SMS gateway init %s', self)
        self.tag = tag
        self._system = system
        self._binpath = None
        if not system:
            self._system = system or sessions.current().context.system
        self._env = env
        if not self._env:
            self._env = sessions.current().context.env
        if not self._system.which('smschild'):
            logger.warning('No SMS client found at init time <%s>', self.tag)

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
        if path != None:
            self._binpath = self._system.path.normpath(path)
        return self._binpath

    def child(self, command, options):
        """Miscellaneous smschild subcommand."""
        smscmd = 'sms' + command
        smsbin = self.binpath()
        if smsbin:
            smscmd = self._system.path.join(smsbin, smscmd)
        args = [ smscmd ]
        if type(options) == list or type(options) == tuple:
            args.extend(options)
        else:
            args.append(options)
        print 'DEBUG SMS', smscmd
        return self._system.spawn(args, output=False)

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
