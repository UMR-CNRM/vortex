#!/usr/bin/env python
# -*- coding:Utf-8 -*-

__all__ = ['analysis']

import re


from vortex import toolbox, sessions
from vortex.tools.date import synop, Date
from vortex.data import geometries
from vortex.syntax import stdattrs


def tbdef(refresh=False):
    """Crude heuristic to setup some defaults footprints values."""
    t = sessions.current()
    d = toolbox.defaults
    p = t.sh.getcwd()
    pl = p.lower()

    thisdef = dict()
    for attr in ('model', 'date', 'cutoff', 'geometry'):
        if refresh:
            thisdef[attr] = None
        else:
            thisdef[attr] = d.get(attr, t.env.get('VORTEX_TBDEF_' + attr.upper(), None))

    if thisdef['model'] is None:
        for x in stdattrs.models:
            if '/' + x in pl:
                thisdef['model'] = x
                break
        else:
            thisdef['model'] = 'arpege'

    if thisdef['geometry'] is None:
        if thisdef['model'].startswith('aro'):
            thisdef['geometry'] = 'frangpsp'
        else:
            thisdef['geometry'] = 'globalsp'
    if not hasattr(thisdef['geometry'], 'tag'):
        thisdef['geometry'] = geometries.get(tag=thisdef['geometry'])

    if refresh:
        zcache = re.search('/(\w+)/(\w+)/([A-Z0-9]{4})/(\d{8}T\d{4})([AP])(?:/(\w+))?', p)
        if zcache:
            thisdef['vapp']       = zcache.group(1)
            thisdef['vconf']      = zcache.group(2)
            thisdef['experiment'] = zcache.group(3)
            thisdef['date']       = Date(zcache.group(4))
            thisdef['cutoff']     = 'production' if zcache.group(5) == 'P' else 'assim'
            if zcache.group(6) is not None:
                thisdef['block'] = zcache.group(6)


    if thisdef['cutoff'] is None:
        thisdef['cutoff'] = 'production'

    if thisdef['date'] is None:
        thisdef['date'] = synop()

    for k, v in { a:b for a, b in thisdef.items() if b is not None }.items():
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
    kw.setdefault('geometry', geometries.get(tag=kw.pop('geoname', 'globalsp')))
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
        suite  = 'oper',
        kind   = 'analysis',
        igakey = '[model]',
        local  = 'toto.toy'
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
        suite  = 'oper',
        block  = 'forecast',
        kind   = 'historic',
        igakey = '[model]',
        term   = 0,
        local  = 'toto.toy'
    )
    adesc.update(kw)
    return fastload(**adesc)
