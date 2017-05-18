#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import re
import StringIO

import footprints

import vortex
from vortex.tools.env import Environment
from vortex.tools.net import uriparse
from gco.syntax.stdattrs import GgetId, UgetId

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)

_DATASTORE_KIND = 'uenv_registred_cycle'

_UENV_LINE_RE = re.compile(r'^[^=]+=')


class UenvError(Exception):
    pass


def handler():
    """Return default environment object storing genv items"""
    return vortex.sessions.current().datastore


def contents(cycle, scheme=None, netloc=None):
    """Return definition of a given ``cycle``."""
    p = handler()
    regcycle = None
    if not isinstance(cycle, UgetId):
        cycle = UgetId(cycle)
    if p.check(_DATASTORE_KIND, dict(cycle=cycle)):
        regcycle = p.get(_DATASTORE_KIND, dict(cycle=cycle))
        regcycle = regcycle.clone()
    else:
        if scheme is None or netloc is None:
            raise UenvError("scheme and/or netloc were not provided. Cannot retrieve the cycle.")
        # Get it !
        regcycle = p.insert(_DATASTORE_KIND, dict(cycle=cycle),
                            Environment(active=False, clear=True, history=False))
        uri_s = '{:s}://{:s}/env/{:s}'.format(scheme, netloc, cycle.short)
        tmplocal = StringIO.StringIO()
        localst = footprints.proxy.store(scheme=scheme, netloc=netloc)
        try:
            rc = localst.get(uriparse(uri_s), tmplocal, dict())
        except IOError:
            rc = False
        if not rc:
            raise UenvError("The {:s} cycle was not found".format(uri_s))
        tmplocal.seek(0)
        for i, item in enumerate(tmplocal.readlines()):
            if _UENV_LINE_RE.match(item):
                k, v = item.split('=', 1)
                cycle = v.rstrip("\n").strip('"')
                try:
                    cycle = UgetId(cycle)
                except ValueError:
                    cycle = GgetId(cycle)
                regcycle[k] = cycle
            else:
                raise UenvError('Malformed environement file (line {:d}, "{:s}")'
                                .format(i + 1, item.rstrip("\n")))
    return regcycle


def nicedump(cycle, scheme=None, netloc=None):
    """Return a nice sequence of string, ready to print."""
    if not isinstance(cycle, UgetId):
        cycle = UgetId(cycle)
    ldump = list()
    c = contents(cycle, scheme, netloc)
    if c:
        ldump = ['{0:s}="{1:s}"'.format(k, ' '.join(v if type(v) is list else [v]))
                 for k, v in sorted(c.items())]
    return ldump


def as_rawstr(cycle, scheme=None, netloc=None):
    """Return a raw string of the cycle contents."""
    if not isinstance(cycle, UgetId):
        cycle = UgetId(cycle)
    thisdump = nicedump(cycle, scheme, netloc)
    return "\n".join(thisdump)


def cycles():
    """Return currently defined cycles."""
    p = handler()
    grep = p.grep(_DATASTORE_KIND, dict())
    return [k.cycle for k in grep.keys()]


def clearall():
    """Flush the current environment object storing cycles."""
    p = handler()
    p.grep_delete(_DATASTORE_KIND, dict(), force=True)
