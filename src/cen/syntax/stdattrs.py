#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module provides some pre-defined attributes descriptions or combined sets
of attributes description that could be used in the footprint definition of any
class which follow the :class:`footprints.Footprint` syntax.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import footprints

from vortex.syntax.stdattrs import a_term, term
from vortex.syntax.stddeco import namebuilding_insert


#: Usual definition of the ``term`` attribute.

a_centerm = a_term

centerm = term

centerm_deco = footprints.DecorativeFootprint(
    centerm,
    decorator = [namebuilding_insert('term',
                                     lambda self: None if self.term is None else self.term.fmthour,
                                     none_discard=True), ])


def show():
    """Returns available items and their type."""
    dmod = globals()
    for stda in sorted(filter(lambda x: x.startswith('a_') or type(dmod[x]) == footprints.Footprint, dmod.keys())):
        print('{0} ( {1} ) :\n  {2}\n'.format(stda, type(dmod[stda]).__name__, dmod[stda]))
