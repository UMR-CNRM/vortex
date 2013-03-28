#!/bin/env python
# -*- coding:Utf-8 -*-

__all__ = []

import sys, re
from vortex.autolog import logdefault as logger

myself = sys.modules.get(__name__)

class Cycle(object):
    """
    Generic match of a defined regular expression.
    Could be optimised in order to compile the re only when requested.
    """

    def __init__(self, regexp = '.', option = re.IGNORECASE):
        self.cstate = (regexp, option)
        self._recomp = None

    @property
    def regexp(self):
        if not self._recomp:
            self._recomp = re.compile(*self.cstate)
        return self._recomp

    def findall(self, *args):
        return self.regexp.findall(*args)

    def search(self, *args):
        return self.regexp.search(*args)

    def __getstate__(self):
        return self.cstate

    def __setstate__(self, frozendata):
        self.cstate = frozendata


#: Default regular expression to evaluate if a given cycle could be operational or not.
oper = Cycle(regexp = '^(?:cy)?\d{2}t\d_.*op\d')

#: Default regular expression to evaluate if a given cycle could be a bugfix or not.
bugfix = Cycle(regexp = '^(?:cy)?\d{2}(?:t\d)?_.*bf\b')

#: Ordered and formatted list of cycles numbers.
maincycles = [ '{0:02d}'.format(x) for x in range(28,39) ]

#: List of subcycles extensions, such as ``_bf`` or ``t1_op``.
subcycles = [ '', '_bf', 't1', 't1_bf', 't1_op', 't2', 't2_bf', 't2_op' ]

def monocycles():
    """Returns a sorted list combining of :data:`maincycles` and :data:`subcycles`."""
    return sorted([ str(x) + y for y in subcycles for x in maincycles ])

def defined():
    """Returns the cycles-regular expressions currently defined in the namespace of the module."""
    return filter(lambda x: re.match('cy\d{2}', x), myself.__dict__.keys())

def generate():
    """
    Called at the fisrt import but could be called again is data
    :data:`maincycles` and :data:`subcycles` have been alterated.
    """
    for k in defined():
        logger.debug('Remove cycle definition %s', k)
        del myself.__dict__[k]
    for c in monocycles():
        myself.__dict__['cy'+c] = Cycle(regexp = '^(?:cy)?'+c+'$')

generate()
