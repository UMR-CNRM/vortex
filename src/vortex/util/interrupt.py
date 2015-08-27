#!/usr/bin/env python
# -*- coding: utf-8 -*-

import signal

import footprints
logger = footprints.loggers.getLogger(__name__)


class SignalInterruptError(Exception):
    '''Exception raised when a system signal is caught.'''
    pass


class SignalInterruptHandler(object):
    '''
    Handler to deal with system signals.

    For each of the signals specified to the class constructor, this
    signal handler is able to swith on and off a customise signal
    handler that will raise a SignalInterruptError exception when
    the signal is received by the python shell.

    An exception is made with SIGINT that will trigger the usual
    Python's KeyboardInterrupt exception.
    '''

    def __init__(self, signals=(signal.SIGHUP, signal.SIGINT, signal.SIGQUIT,
                                signal.SIGTRAP, signal.SIGABRT, signal.SIGFPE,
                                signal.SIGUSR1, signal.SIGUSR2, signal.SIGTERM
                                )):
        '''
        Handler to deal with system signals.

        :param signals: list/tupple of signals that will be caught
        '''

        self._signals = signals
        self._original_handlers = {}
        self._active = False

    def __enter__(self):
        self.activate()
        return self

    def __exit__(self, exctype, excvalue, exctb):
        self.deactivate()

    @property
    def signals(self):
        '''List of the signals catched by the signal handlers.'''
        return list(self._signals)

    @property
    def active(self):
        '''Are the singal handlers active ?'''
        return self._active

    def activate(self):
        '''Activate the signal handlers.'''
        if not self._active:
            def handler(signum, frame):
                self.deactivate()
                logger.error('Signal {:d} was caught.'.format(signum))
                if signum == signal.SIGINT:
                    raise KeyboardInterrupt()
                else:
                    raise SignalInterruptError('Signal {:d} was caught.'.format(signum))
            for sig in self.signals:
                self._original_handlers[sig] = signal.signal(sig, handler)
                logger.info('Customised signal handler installed for signal {:d}'.format(sig))
        self._active = True

    def deactivate(self):
        '''Deactivate the signal handlers and restore the previous ones.'''
        if self._active:
            for sig in self.signals:
                signal.signal(sig, self._original_handlers[sig])
                logger.info('Original signal handler restored for signal {:d}'.format(sig))
        self._active = False
