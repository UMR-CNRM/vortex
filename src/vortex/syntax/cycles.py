#!/usr/bin/env python
# -*- coding:Utf-8 -*-

__all__ = []

import re

import footprints
logger = footprints.loggers.getLogger(__name__)


# Module Interface

def get(**kw):
    """Return actual cycle object matching description."""
    return Cycle(**kw)

def keys():
    """Return the list of current cycle names collected."""
    return Cycle.tag_keys()

def values():
    """Return the list of current cycle values collected."""
    return Cycle.tag_values()

def items():
    """Return the items of the cycles table."""
    return Cycle.tag_items()


class Cycle(footprints.util.GetByTag):
    """
    Generic match of a defined regular expression.
    Could be optimised in order to compile the re only when requested.
    """

    def __init__(self, regexp=None, option=re.IGNORECASE):
        if regexp is None:
            regexp = self.tag
        self._cstate = (regexp, option)
        self._recomp = None

    @property
    def short(self):
        return self.tag[:4]

    def compact(self, cyclename=None):
        if cyclename is None:
            cyclename = self.tag
        c = re.sub(r'^[a-z]{2}', '', cyclename)
        c = re.sub(r'_\w+\-', '_', c)
        return c

    @property
    def regexp(self):
        if not self._recomp:
            self._recomp = re.compile(*self._cstate)
        return self._recomp

    @property
    def pattern(self):
        return self._cstate[0]

    def findall(self, *args):
        return self.regexp.findall(*args)

    def match(self, *args):
        return self.regexp.match(*args)

    def search(self, *args):
        return self.regexp.search(*args)

    def __getstate__(self):
        return (self._cstate, self._tag)

    def __setstate__(self, frozendata):
        self._cstate, self._tag = frozendata
        self._recomp = None

    def __str__(self):
        """Return the current tag."""
        return self.tag

    def __cmp__(self, other):
        """Compare current object and other as strings."""
        return cmp(self.compact(), self.compact(str(other)))


#: Default regular expression to evaluate if a given cycle could be operational or not.
oper = Cycle(regexp=r'^(?:cy)?\d{2}t\d_.*op\d+(?:\.\d+)?', tag='oper')

#: Default regular expression to evaluate if a given cycle could be a bugfix or not.
bugfix = Cycle(regexp=r'^(?:cy)?\d{2}(?:t\d+)?_.*bf(?:\.\d+)?\b', tag='bugfix')

#: Ordered and formatted list of cycles numbers.
maincycles = [ '{0:02d}'.format(x) for x in range(38, 42) ]

#: List of subcycles extensions, such as ``_bf`` or ``t1_op``.
subcycles = ['', '_bf', '_op1', '_op2', 't1', 't1_bf', 't1_op1', 't1_op2', 't1_op3', 't2', 't2_bf', 't2_op1', 't2_op2', 't2_op3']


def monocycles():
    """Returns a sorted list combining of :data:`maincycles` and :data:`subcycles`."""
    return sorted([ str(x) + y for y in subcycles for x in maincycles ])


def defined():
    """Returns the cycles-regular expressions currently defined in the namespace of the module."""
    myself = globals()
    return filter(lambda x: re.match(r'cy\d{2}', x), myself.keys())


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
        myself[cytag] = Cycle(regexp=r'^(?:cy)?' + c + r'(?:\.\d+)?$', tag=cytag)

generate()
