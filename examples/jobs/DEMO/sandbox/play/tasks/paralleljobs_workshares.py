# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

"""
Demonstrate the benefits of the subjob feature.
"""

from vortex.layout.nodes import Driver, WorkshareFamily, LoopFamily

from .commons import Beacon


def setup(t, **kw):
    """Create a Driver object."""
    return Driver(
        tag     = 'pjobs_ws_drv',
        ticket  = t,
        nodes   = [
            # In the parelleljobs_basic.py, it was not very handy: to allow
            # some parallelism, we add to manually create several LoopFamilies
            # that each work on a sub-ensemble of the members.
            # What we really want is a Family that takes a full list of members,
            # slice it in portions, and create the necessary nodes to deal with
            # them. That's the purpose of the WorkshareFamily.
            WorkshareFamily(
                tag='pjobs_ws_f1',

                # Lets consider the `self.conf.allmembers` full list of members
                workshareconf='allmembers',
                # This list wil be sliced and each slice will be named
                # `self.conf.members` in the duplicated nodes.
                worksharename='members',

                # `worksharelimit` tells the WorkshareFamily that the number of slices
                # should be equal to the number of parallel tasks (given by
                # `self.conf.paralleljobs_limit`).
                worksharelimit='paralleljobs_limit',

                # NB: `worksharesize` could also be specified. It specifies
                #     a lower limit to the number of items in each of the slices.

                nodes=[
                    LoopFamily(
                        tag='pjobs_ws_batch',
                        loopconf='members',
                        nodes=[Beacon(tag='pjobs_t', ticket=t, **kw)],
                        ticket=t, ** kw),
                ],

                # See parelleljobs_basic.py for details on the parelleljobs_*
                # arguments
                paralleljobs_kind='spawn',

                ticket=t, **kw)
        ],
        options=kw
    )
