#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module provides some pre-defined attributes descriptions or combined sets
of attributes description that could be used in the footprint definition of any
class which follow the :class:`footprints.Footprint` syntax.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import footprints


#: Export a set of attributes :data:`a_run`, etc..
__all__ = []

#: Usual definition of the ``run`` attribute.
a_run = dict(
    info     = "The OOPS run (== task).",
    optional = False,
)

run = footprints.Footprint(info = 'OOPS kind of run', attr = dict(run = a_run))


#: Usual definition of the ``test_type`` attribute.
a_test_type = dict(
    info = 'Sub-test or family of sub-tests to be ran.',
    optional = False,
)
test_type = footprints.Footprint(info = 'OOPS type of test', attr = dict(test_type = a_test_type))


#: Usual definition of the ``expected_target`` attribute.
an_expected_target = dict(
    info = ('Expected target for the test success'),
    type = footprints.FPDict,
    optional = True,
    default = None
)
expected_target = footprints.Footprint(attr = dict(expected_target = an_expected_target))


#: Usual definition of the ``select_expected_target`` attribute.
a_select_expected_target = dict(
    info = ("Ordered keys to select expected target for the test " +
            "success, within the dict from 'expected_target' or " +
            "resource Role: Expected Target"),
    type = footprints.FPList,
    optional = True,
    default = None
)
select_expected_target = footprints.Footprint(attr = dict(select_expected_target = a_select_expected_target))


def show():
    """Returns available items and their type."""
    dmod = globals()
    for stda in sorted(filter(lambda x: x.startswith('a_') or type(dmod[x]) == footprints.Footprint, dmod.keys())):
        print('{0} ( {1} ) :\n  {2}\n'.format(stda, type(dmod[stda]).__name__, dmod[stda]))
