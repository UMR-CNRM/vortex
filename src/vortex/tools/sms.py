#!/bin/env python
# -*- coding:Utf-8 -*-

r"""
Interface to SMS commands.
"""

__all__ = []

import logging

from vortex import sessions

class SMSGateway(object):
    
    def __init__(self, tag='void'):
        logging.debug('SMS gateway init %s', self.__class__)
        super(SMSGateway, self).__init__()
        self.tag = tag
        if not sessions.system().which('smschild'):
            logging.warning('No SMS client found at init time <%s>', self.tag)

    def env(self, **kw):
        smsenv = sessions.system().env
        if kw:
            for smsvar in filter(lambda var: var.startswith('SMS'), [x.upper() for x in kw.keys()]):
                smsenv[smsvar] = str(kw[smsvar])
        subenv = dict()
        for smsvar in filter(lambda var: var.startswith('SMS'), smsenv.keys()):
            subenv[smsvar] = smsenv.get(smsvar)
        return subenv

    def info(self):
        for smsvar, smsvalue in self.env().iteritems():
            print '{0:s}="{1:s}"'.format(smsvar, smsvalue)

    def child(self, command, options):
        system = sessions.system()
        args = [ 'sms' + command ]
        if type(options) == list or type(options) == tuple:
            args.extend(options)
        else:
            args.append(options)
        system.spawn(args)

    def abort(self, *opts):
        self.child('abort', opts)

    def complete(self, *opts):
        self.child('complete', opts)

    def event(self, *opts):
        self.child('event', opts)

    def init(self, *opts):
        self.child('init', opts)

    def label(self, *opts):
        self.child('label', opts)

    def meter(self, *opts):
        self.child('meter', opts)
