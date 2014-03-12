#!/bin/env python
# -*- coding:Utf-8 -*-

__all__ = []

import  re

from vortex.autolog import logdefault as logger


class Cycle(object):
    """
    Generic match of a defined regular expression.
    Could be optimised in order to compile the re only when requested.
    """

    def __init__(self, regexp='.', option=re.IGNORECASE, tag='default'):
        self.cstate = (regexp, option)
        self.tag = str(tag)
        self._recomp = None

    @property
    def regexp(self):
        if not self._recomp:
            self._recomp = re.compile(*self.cstate)
        return self._recomp

    def findall(self, *args):
        return self.regexp.findall(*args)

    def match(self, *args):
        return self.regexp.match(*args)

    def search(self, *args):
        return self.regexp.search(*args)

    def __getstate__(self):
        return (self.cstate, self.tag)

    def __setstate__(self, frozendata):
        self.cstate, self.tag = frozendata
        self._recomp = None

    def __str__(self):
        """Return the current tag."""
        return self.tag

    def __repr__(self):
        """Return a nice view of the current cycle."""
        sr = object.__repr__(self).rstrip('>')
        regexp, option = self.cstate
        return '{0:s} | cycle={1:s} re="{2:s}" options={3:d}>'.format(sr, self.tag, regexp, option)

    def __cmp__(self, other):
        """Compare current object and other as strings."""
        return cmp(str(self), str(other))


#: Default regular expression to evaluate if a given cycle could be operational or not.
oper = Cycle(regexp='^(?:cy)?\d{2}t\d_.*op\d+(?:\.\d+)?', tag='oper')

#: Default regular expression to evaluate if a given cycle could be a bugfix or not.
bugfix = Cycle(regexp='^(?:cy)?\d{2}(?:t\d+)?_.*bf(?:\.\d+)?\b', tag='bugfix')

#: Ordered and formatted list of cycles numbers.
maincycles = [ '{0:02d}'.format(x) for x in range(36, 42) ]

#: List of subcycles extensions, such as ``_bf`` or ``t1_op``.
subcycles = [ '', '_bf', 't1', 't1_bf', 't1_op1', 't1_op2', 't2', 't2_bf', 't2_op1', 't2_op2' ]

def monocycles():
    """Returns a sorted list combining of :data:`maincycles` and :data:`subcycles`."""
    return sorted([ str(x) + y for y in subcycles for x in maincycles ])

def defined():
    """Returns the cycles-regular expressions currently defined in the namespace of the module."""
    myself = globals()
    return filter(lambda x: re.match('cy\d{2}', x), myself.keys())

def generate():
    """
    Called at the fisrt import but could be called again is data
    :data:`maincycles` and :data:`subcycles` have been alterated.
    """
    myself = globals()
    for k in defined():
        logger.debug('Remove cycle definition %s', k)
        del myself[k]
    for c in monocycles():
        cytag = 'cy' + c
        myself[cytag] = Cycle(regexp='^(?:cy)?'+c+'(?:\.\d+)?$', tag=cytag)

generate()
