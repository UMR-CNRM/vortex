#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import footprints

import vortex
from vortex.tools.env import Environment

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)

_DATASTORE_KIND = 'genv_registred_cycle'

genvcmd, genvpath = (None, None)


def actualgenv():
    """Nice try to return a valid full path of the genv command."""
    global genvpath
    global genvcmd
    if genvcmd is None or genvpath is None:
        tg = vortex.sh().target()
        if genvpath is None:
            genvpath = tg.get('gco:genvpath', '')
        if genvcmd is None:
            genvcmd = tg.get('gco:genvcmd', 'genv')
    return vortex.sh().path.join(genvpath, genvcmd)


def handler():
    """Return default environment object storing genv items"""
    return vortex.sessions.current().datastore


def register(**kw):
    """Set key - values for a given ``cycle`` recorded as an ``entry`` (parameters)."""
    p = handler()
    cycle = kw.pop('cycle', 'default')
    if p.check(_DATASTORE_KIND, dict(cycle=cycle)):
        regcycle = p.get(_DATASTORE_KIND, dict(cycle=cycle))
    else:
        logger.debug('Register a new genv cycle: %s', cycle)
        regcycle = p.insert(_DATASTORE_KIND, dict(cycle=cycle),
                            Environment(active=False, clear=True, history=False))
    if kw:
        regcycle.update(kw)
    return regcycle


def contents(**kw):
    """Return definition of a given ``cycle``."""
    p = handler()
    cycle = kw.setdefault('cycle', 'default')
    regcycle = None
    if p.check(_DATASTORE_KIND, dict(cycle=cycle)):
        regcycle = p.get(_DATASTORE_KIND, dict(cycle=cycle))
        regcycle = regcycle.clone()
    return regcycle


def nicedump(**kw):
    """Return a nice sequence of string, ready to print."""
    ldump = list()
    c = contents(**kw)
    if c:
        ldump = [ '{0:s}="{1:s}"'.format(k, ' '.join(v if type(v) is list else [v]))
                  for k, v in sorted(c.items()) ]
    return ldump


def as_rawstr(cycle):
    """Return a raw string of the cycle contents."""
    thisdump = nicedump(cycle=cycle)
    thisdump[0:0] = [ 'CYCLE_NAME="' + cycle  + '"' ]
    return "\n".join(thisdump)


def cycles():
    """Return curretnly defined cycles."""
    p = handler()
    grep = p.grep(_DATASTORE_KIND, dict())
    return [k.cycle for k in grep.keys()]


def clearall():
    """Flush the current environment object storing cycles."""
    p = handler()
    p.grep_delete(_DATASTORE_KIND, dict(), force=True)


def autofill(cycle, gcout=None, writes_dump=False, cacheroot='.'):
    """Use the ``genv`` external tool to fill the specified cycle."""
    actualcycle = None
    if gcout is None:
        sh = vortex.sh()
        cachefile = sh.path.join(cacheroot, '{:s}_vortex_genv_cache'.format(cycle))
        if sh.path.isfile(cachefile):
            with open(cachefile, 'r') as genvfh:
                gcout = [l.rstrip('\n') for l in genvfh.readlines()]
        else:
            gcout = vortex.sh().spawn([actualgenv(), cycle], output=True)
            if writes_dump:
                with open(cachefile, 'w') as genvfh:
                    genvfh.writelines([l + "\n" for l in gcout])
    if gcout:
        gcdict = dict()
        for item in gcout:
            k, v = item.split('=', 1)
            v = v.strip('"')
            if k == 'CYCLE_NAME':
                actualcycle = v.partition('.gco')[0]
                k, v = 'cycle', actualcycle
            gcdict[k] = v
        register(**gcdict)
    else:
        logger.warning('Could not automatically fetch cycle %s contents', actualcycle)
    return contents(cycle=actualcycle)
