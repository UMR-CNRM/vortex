"""
Demonstrate the benefits of the active_callback feature.
"""

from vortex.layout.nodes import Driver, LoopFamily

from .commons import Beacon


def setup(t, **kw):
    """Create a Driver object."""
    return Driver(
        tag     = 'active_cb_drv',
        ticket  = t,
        nodes   = [
            # For explanations on the LoopFamily class, see loop_family1.py
            LoopFamily(
                tag='active_cb_members',
                loopconf='members',
                nodes=[
                    Beacon(tag='generic_beacon', ticket=t, **kw),
                    Beacon(tag='even_beacon',
                           # We specify an activation condition based on
                           # the content of `self.conf`
                           active_callback=lambda self: self.conf.member % 2 == 0,
                           ticket=t, **kw),
                ],
                ticket=t, ** kw)
        ],
        options=kw
    )


# You are invited to run this Driver by yourself... but if you are lazy (or
# trustful), the execution would result in the following "Tree" for the
# `active_cb_drv` driver:
#
# active_cb_drv (Driver) -> ready to start
#   active_cb_members (LoopFamily) -> ready to start
#     generic_beacon+member1 (Beacon) -> ready to start
#     even_beacon+member1 (Beacon) -> created
#     generic_beacon+member2 (Beacon) -> ready to start
#     even_beacon+member2 (Beacon) -> ready to start
#     generic_beacon+member3 (Beacon) -> ready to start
#     even_beacon+member3 (Beacon) -> created
#     generic_beacon+member4 (Beacon) -> ready to start
#     even_beacon+member4 (Beacon) -> ready to start
#     generic_beacon+member5 (Beacon) -> ready to start
#     even_beacon+member5 (Beacon) -> created
#
# The even_beacon Task is always created but it will only be started for
# members 2 and 4 !
