#!/bin/env python
# -*- coding:Utf-8 -*-

__all__ = [ 'analysis' ]

from vortex import toolbox
from vortex.tools.date import synop

from vortex.data import geometries


def fastload(**kw):
    """
    Generic load of some resource handler according to current description.
    If not provided, these parameters are set:
      * cutoff = production
      * model = arpege
      * date = last synoptic hour
      * geometry = global spectral default geometry
    """
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
    """
    Return a analysis according to a standard description and/or some additional information.
    Defaults are:
      * kind = analysis
      * suite = oper
      * igakey = same as model
      * tempo = True
    """
    adesc = dict(
        suite = 'oper',
        kind = 'analysis',
        igakey = '[model]',
        tempo = True
    )
    adesc.update(kw)
    return fastload(**adesc)

def modelstate(**kw):
    """
    Return a model state according to a standard description and/or some additional information.
    Defaults are:
      * kind = historic
      * suite = oper
      * block = forecast
      * igakey = same as model
      * term = 0
      * tempo = True
    """
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
