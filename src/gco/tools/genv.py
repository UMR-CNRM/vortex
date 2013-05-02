#!/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

from vortex.autolog import logdefault as logger
from copy import copy

from vortex.tools import env

def handler():
    return env.param(tag='genvitems')

def register(**kw):
    p = handler()
    cycle = kw.setdefault('cycle', 'default')
    entry = kw.setdefault('entry', None)
    del kw['cycle']
    del kw['entry']
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
    if kw: regcycle.update(kw)
    return regcycle

def contents(**kw):
    p = handler()
    cycle = kw.setdefault('cycle', 'default')
    regcycle = [ x for x in p.keys() if p[x]['CYCLE'] == cycle ]
    if regcycle:
        items = copy(p[regcycle.pop()])
        del items['CYCLE']
        return items
    else:
        return None

def cycles():
    p = handler()
    return [ p[x]['CYCLE'] for x in p.keys() ]
