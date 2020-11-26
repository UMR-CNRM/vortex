#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This module provides some pre-defined attributes descriptions or combined sets
of attributes description that could be used in the footprint definition of any
class which follow the :class:`footprints.Footprint` syntax.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.stdtypes.date import Time
import footprints

#: Export a set of attributes :data:`a_run`, etc..
__all__ = []

#: Usual definition of the ``run`` attribute for OOPS binaries.
a_oops_run = dict(
    info="The OOPS run (== task).",
    optional=False,
)
#: Usual Footprint of the ``run`` attribute for OOPS binaries.
oops_run = footprints.Footprint(info='OOPS kind of run', attr=dict(run=a_oops_run))

#: Usual definition of the ``test_type`` attribute.
a_oops_test_type = dict(
    info='Sub-test or family of sub-tests to be ran.',
    optional=False,
)
#: Usual Footprint of the ``test_type`` attribute.
oops_test_type = footprints.Footprint(info='OOPS type of test', attr=dict(test_type=a_oops_test_type))

#: Usual definition of the ``expected_target`` attribute.
an_oops_expected_target = dict(
    info=('Expected target for the test success'),
    type=footprints.FPDict,
    optional=True,
    default=None
)
#: Usual Footprint of the ``expected_target`` attribute.
oops_expected_target = footprints.Footprint(attr=dict(expected_target=an_oops_expected_target))

#: Usual Footprint of a combined lists of members and terms
oops_members_terms_lists = footprints.Footprint(
    info="Abstract footprint for a members/terms list.",
    attr=dict(
        members=dict(
            info='A list of members.',
            type=footprints.FPList,
        ),
        terms=dict(
            info='A list of effective terms.',
            type=footprints.FPList,
            optional=True,
            default=footprints.FPList([Time(0), ])
        ),
    )
)


def show():
    """Returns available items and their type."""
    dmod = globals()
    for stda in sorted(filter(lambda x: x.startswith('a_') or type(dmod[x]) == footprints.Footprint, dmod.keys())):
        print('{0} ( {1} ) :\n  {2}\n'.format(stda, type(dmod[stda]).__name__, dmod[stda]))
