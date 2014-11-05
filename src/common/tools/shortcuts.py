#!/usr/bin/env python
# -*- coding:Utf-8 -*-

__all__ = [ 'analysis' ]

import re


from vortex import toolbox, sessions
from vortex.tools.date import synop, Date
from vortex.data import geometries
from vortex.syntax import stdattrs


def tbdef(refresh=False):
    """Crude heuristic to setup some defaults footprints values."""
    t = sessions.ticket()
    d = toolbox.defaults
    p = t.sh.getcwd()
    pl = p.lower()

    if refresh:
        thismodel = None
    else:
        thismodel = d.get('model', t.env.get('VORTEX_TBDEF_MODEL', None))

    if thismodel is None:
        for x in stdattrs.models:
            if '/' + x in pl:
                thismodel = x
                break
        else:
            thismodel = 'arpege'

    if refresh:
        thisgeometry = None
    else:
        thisgeometry = d.get('geometry', t.env.get('VORTEX_TBDEF_GEOMETRY', None))

    if thisgeometry is None:
        if thismodel.startswith('aro'):
            thisgeometry = 'frangpsp'
        else:
            thisgeometry = 'globalsp'
    thisgeometry = geometries.getbyname(thisgeometry)

    thisdate = None
    if refresh:
        zcache = re.search('/(\w+)/(\w+)/([A-Z0-9]{4})/(\d{8}T\d{4})([AP])(?:/(\w+))?', p)
        if zcache:
            thisvapp = zcache.group(1)
            thisvconf = zcache.group(2)
            thisexperiment = zcache.group(3)
            thisdate = Date(zcache.group(4))
            thiscutoff = 'production' if zcache.group(5) == 'P' else 'assim'
            if zcache.group(6) is not None:
                thisblock = zcache.group(6)

    if thisdate is None:
        thisdate = synop()

    for k, v in locals().iteritems():
        if k.startswith('this'):
            k = k.replace('this', '')
            print 'Update default', k.ljust(16), '=', v
            d[k] = v

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
