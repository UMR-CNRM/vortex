# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

"""
Demonstrate the benefits of the LoopFamily task.
"""

from vortex.layout.nodes import Driver, LoopFamily

from .commons import Beacon


def setup(t, **kw):
    """Create a Driver object."""
    return Driver(
        tag     = 'lfamily1_drv',
        ticket  = t,
        nodes   = [
            LoopFamily(
                tag='lfamily1_dates',

                # Look for a `rundates` entry in `self.conf` (this entry has
                # to be a list): we will loop on this entry.
                loopconf='rundates',

                # When iterating, a `rundate` entry will be added to `self.conf`
                # (this is the "control variable" of the loop). The name of such
                # a control variable is prescribed by `loopvariable`. In this
                # example `loopvariable` could actually be omitted because the
                # default behaviour is to use the value of `loopconf` without
                # the final "s" (i.e. `loopconf` should be a plural form).
                loopvariable='rundate',

                # Below the hood, the LoopFamily class will create clones of its
                # `nodes` argument content. However, since each tag needs to be
                # unique, the clone will be tagged with the original tag name
                # plus an additional string that can be customised using `loopsuffix`
                loopsuffix='+d{0.ymdh:s}',  # This string will be formatted using
                                            # the loop control variable as a first
                                            # and unique argument
                # NB: The default is loopsuffix='+X{0!s}' where X is the
                #     `loopvariable` name. Depending on your needs, it might
                #     be decent enough (although it's a bit long).

                # When iterating, a `rundate` entry is added to `self.conf`.
                # Actually, `rundate_prev` and `rundate_next` will also be added.
                # By default, for the first (resp. last) item of the loop,
                # `rundate_prev=None` (resp. `rundate_next=None`). Sometimes, it
                # is desirable to change this behaviour and to force the LoopFamily
                # to keep the first (resp. last) element of `loopconf` in "spare" in
                # order to properly initialise `rundate_prev` (resp. `rundate_next`).
                # That's what the `loopneedprev` and `loopneednext` arguments are for.
                loopneednext=True,
                # Because loopneednext=`True`, in this example we won't iterate on
                # the last element of the `rundates` list, which ensures that the
                # `self.conf.rundate_next` always has a well defined value.

                nodes=[
                    LoopFamily(
                        tag='lfamily1_members',

                        # We just say we want to loop on the `members` list.
                        loopconf='members',

                        # The default values for `loopvariable` and `loopsuffix`
                        # are fine...

                        nodes=[
                            Beacon(tag='lfamily1_beacon', ticket=t, **kw),
                        ],
                        ticket=t, ** kw)
                ],
                ticket=t, **kw
            )
        ],
        options=kw
    )


# You are invited to run this Driver by yourself... but if you are lazy (or
# trustful), the execution would result in the following "Tree" for the
# `lfamily1_drv` driver:
#
# lfamily1_drv (Driver) -> ready to start
#   lfamily1_dates (LoopFamily) -> ready to start
#     lfamily1_members+d2020102918 (LoopFamily) -> ready to start
#       lfamily1_beacon+d2020102918+member1 (Beacon) -> ready to start
#       lfamily1_beacon+d2020102918+member2 (Beacon) -> ready to start
#       lfamily1_beacon+d2020102918+member3 (Beacon) -> ready to start
#       lfamily1_beacon+d2020102918+member4 (Beacon) -> ready to start
#       lfamily1_beacon+d2020102918+member5 (Beacon) -> ready to start
#     lfamily1_members+d2020103018 (LoopFamily) -> ready to start
#       lfamily1_beacon+d2020103018+member1 (Beacon) -> ready to start
#       lfamily1_beacon+d2020103018+member2 (Beacon) -> ready to start
#       lfamily1_beacon+d2020103018+member3 (Beacon) -> ready to start
#       lfamily1_beacon+d2020103018+member4 (Beacon) -> ready to start
#       lfamily1_beacon+d2020103018+member5 (Beacon) -> ready to start
#     lfamily1_members+d2020103118 (LoopFamily) -> ready to start
#       lfamily1_beacon+d2020103118+member1 (Beacon) -> ready to start
#       lfamily1_beacon+d2020103118+member2 (Beacon) -> ready to start
#       lfamily1_beacon+d2020103118+member3 (Beacon) -> ready to start
#       lfamily1_beacon+d2020103118+member4 (Beacon) -> ready to start
#       lfamily1_beacon+d2020103118+member5 (Beacon) -> ready to start
