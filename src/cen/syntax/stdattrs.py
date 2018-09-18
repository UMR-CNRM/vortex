#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module provides some pre-defined attributes descriptions or combined sets
of attributes description that could be used in the footprint definition of any
class which follow the :class:`footprints.Footprint` syntax.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.stdtypes.date import Date
import footprints

from vortex.syntax.stddeco import namebuilding_insert, generic_pathname_insert


#: Usual definition of a date period for CEN resources.

cendateperiod = footprints.Footprint(info = 'Abstract date period',
                                     attr = dict(begindate = dict(info = "The resource's begin date.",
                                                                  alias = ('datebegin', ),
                                                                  type = Date,
                                                                  optional = False),
                                                 enddate = dict(info = "The resource's end date.",
                                                                alias = ('dateend', ),
                                                                type = Date,
                                                                optional = False),
                                                 ))

cendateperiod_deco = footprints.DecorativeFootprint(
    cendateperiod,
    decorator = [namebuilding_insert('cen_period', lambda self: [self.begindate.ymdh, self.enddate.ymdh]),
                 generic_pathname_insert('begindate', lambda self: self.begindate, setdefault=True),
                 generic_pathname_insert('enddate', lambda self: self.enddate, setdefault=True)])


def show():
    """Returns available items and their type."""
    dmod = globals()
    for stda in sorted(filter(lambda x: x.startswith('a_') or type(dmod[x]) == footprints.Footprint, dmod.keys())):
        print('{0} ( {1} ) :\n  {2}\n'.format(stda, type(dmod[stda]).__name__, dmod[stda]))
