#!/bin/env python
# -*- coding:Utf-8 -*-

__all__ = [ 'analysis' ]

from vortex import toolbox
from vortex.tools.date import synop

from vortex.data import geometries


def fastload(**kw):
    kw.setdefault('cutoff', 'production')
    kw.setdefault('model', 'arpege')
    kw.setdefault('date', synop())
    kw.setdefault('geometry', geometries.getbyname(kw.pop('geoname', 'globalsp')))
    al = toolbox.rload(**kw)
    if len(al) > 1:
        return al
    else:
        return al[0]

def analysis(**kw):
    adesc = dict(
        suite = 'oper',
        kind = 'analysis',
        igakey = '[model]',
        tempo = True
    )
    adesc.update(kw)
    return fastload(**adesc)

def modelstate(**kw):
    adesc = dict(
        suite = 'oper',
        block = 'forecast',
        kind = 'historic',
        igakey = '[model]',
        term = 0,
        tempo=True
    )
    adesc.update(kw)
    return fastload(**adesc)
