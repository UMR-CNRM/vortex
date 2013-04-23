#!/bin/env python
# -*- coding:Utf-8 -*-

__all__ = [ 'analysis' ]

from vortex import toolbox
from vortex.tools.date import synop

from vortex.data.geometries import SpectralGeometry


def fastload(**kw):
    kw.setdefault('cutoff', 'production')
    kw.setdefault('model', 'arpege')
    kw.setdefault('date', synop())
    kw.setdefault('geometry', SpectralGeometry(area='france', truncation=798))
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
        block = 'forecast',
        kind = 'historic',
        experiment = 'A001',
        term = 0,
        tempo=True
    )
    adesc.update(kw)
    return fastload(**adesc)
