#!/bin/env python
# -*- coding:Utf-8 -*-

__all__ = [ 'analysis' ]

from vortex import toolbox
from vortex.tools.date import synop

from vortex.data.geometries import SpectralGeometry


def analysis(date=None, suite='oper', cutoff='p', model='arpege', geo=None):
    if not date:
        date = synop()
    if not geo:
        geo = SpectralGeometry(id='Current op', area='france', truncation=798)
    al = toolbox.rload(
        kind='analysis',
        suite=suite,
        cutoff=cutoff,
        model=model,
        igakey='[model]',
        date=date,
        geometry=geo,
        tempo=True,
    )
    if len(al) > 1:
        return al
    else:
        return al[0]
