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

#: Usual Footprint for a single member (in an algo componnent)
a_algo_member = dict(
    info=("The current member's number " +
          "(may be omitted in deterministic configurations)."),
    optional=True,
    type=int
)

#: Usual Footprint of the ``outputid`` attribute.
algo_member = footprints.Footprint(attr=dict(member=a_algo_member))

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

#: Usual definition of the ``outputid`` attribute
a_outputid = dict(
    info="The identifier for the encoding of post-processed fields.",
    optional=True,
)

#: Usual Footprint of the ``outputid`` attribute.
outputid = footprints.Footprint(attr=dict(outputid=a_outputid))


def _apply_outputid(cls):
    """Decorator that tweak the class in order to add OUTPUTID on the namelist"""
    orig_pnd = getattr(cls, 'prepare_namelist_delta', None)
    if orig_pnd is None:
        raise ImportError('_apply_outputid can not be applied on {!s}'.format(cls))

    def prepare_namelist_delta(self, rh, namcontents, namlocal):
        namw = orig_pnd(self, rh, namcontents, namlocal)
        if self.outputid is not None and any(['OUTPUTID' in nam_b.macros()
                                              for nam_b in namcontents.values()]):
            self._set_nam_macro(namcontents, namlocal, 'OUTPUTID', self.outputid)
            namw = True
        return namw

    cls.prepare_namelist_delta = prepare_namelist_delta
    return cls


#: Decorated footprint for the ``outputid`` attribute
outputid_deco = footprints.DecorativeFootprint(outputid,
                                               decorator=[_apply_outputid, ])


def show():
    """Returns available items and their type."""
    dmod = globals()
    for stda in sorted(filter(lambda x: x.startswith('a_') or type(dmod[x]) == footprints.Footprint, dmod.keys())):
        print('{0} ( {1} ) :\n  {2}\n'.format(stda, type(dmod[stda]).__name__, dmod[stda]))
