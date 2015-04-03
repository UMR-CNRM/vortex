#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

from copy import copy

import footprints
logger = footprints.loggers.getLogger(__name__)

import vortex

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
    return vortex.tools.env.param(tag='genvitems')


def register(**kw):
    """Set key - values for a given ``cycle`` recorded as an ``entry`` (parameters)."""
    p = handler()
    cycle = kw.pop('cycle', 'default')
    entry = kw.pop('entry', None)
    regcycle = [ x for x in p.keys() if p[x]['CYCLE'] == cycle ]
    if not regcycle:
        if entry:
            nextcycle = entry
        else:
            nextcycle = 'CYCLE{0:03d}'.format(len(p)+1)
        logger.debug('Register a new genv cycle %s', nextcycle)
        p[nextcycle] = dict(CYCLE = cycle)
        regcycle = p[nextcycle]
    else:
        regcycle = p[regcycle.pop()]
    if kw:
        regcycle.update(kw)
    return regcycle


def contents(**kw):
    """Return definition of a given ``cycle``."""
    p = handler()
    cycle = kw.setdefault('cycle', 'default')
    regcycle = [ x for x in p.keys() if p[x]['CYCLE'] == cycle ]
    if regcycle:
        items = copy(p[regcycle.pop()])
        del items['CYCLE']
        return items
    else:
        return None


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
    return [ p[x]['CYCLE'] for x in p.keys() ]


def clearall():
    """Flush the current environment object storing cycles."""
    p = handler()
    p.clear()


def autofill(cycle, gcout=None):
    """Use the ``genv`` external tool to fill the specified cycle."""
    actualcycle = None
    if gcout is None:
        gcout = vortex.sh().spawn([actualgenv(), cycle], output=True)
    if gcout:
        gcdict = dict()
        for item in gcout:
            k, v = item.split('=', 1)
            v = v.strip('"')
            if k == 'CYCLE_NAME':
                actualcycle = v.partition('.gco')[0]
                k, v = 'cycle', actualcycle
            if ' ' in v:
                vlist = v.split(' ')
                gcdict[k] = vlist[0]
                gcdict[k+'_LIST'] = vlist
            else:
                gcdict[k] = v
        register(**gcdict)
    else:
        logger.warning('Could not automaticaly fetch cycle %s contents', actualcycle)
    return contents(cycle=actualcycle)
