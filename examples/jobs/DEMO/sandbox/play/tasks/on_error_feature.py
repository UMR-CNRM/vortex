# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

"""
Demonstrate the "on_error" and "delay_component_errors" features of the Node
objects (e.g Task, Family, ...) + the use of a custom JobAssistant plugin.
"""

from vortex.layout.nodes import Driver, Family

from .commons import Beacon


def setup(t, **kw):
    """Create a Driver object."""
    return Driver(
        tag     = 'on_error_drv',
        ticket  = t,
        nodes   = [
            # The 'on_error1_f1' will fail (failer=True) but, since on_error='continue',
            # this failure will be ignored and the processing will continue as usual.
            # Therefore, the 'on_error2_f1 will be executed, the 'on_error_f1' family will
            # complete and the two following families will be executed.
            Family(tag='on_error_f1',
                   nodes = [
                        Beacon(tag='on_error1_f1', ticket=t, failer=True, on_error='continue', **kw),
                        #                                    ^^^^^^^^^^^  ^^^^^^^^^^^^^^^^^^
                        Beacon(tag='on_error2_f1', ticket=t, **kw),
                   ], ticket=t, **kw),
            # The 'on_error1_f2' task will fail, but since no 'on_error' argument is
            # provided, it will break the execution of the 'on_error_f2' family.
            Family(tag='on_error_f2',
                   nodes=[
                       Beacon(tag='on_error1_f2', ticket=t, failer=True, **kw),
                       #                                    ^^^^^^^^^^^
                       Beacon(tag='on_error2_f2', ticket=t, **kw),
                   ], ticket=t, on_error='delayed_fail', **kw),
            #                   ^^^^^^^^^^^^^^^^^^^^^^^
            # However, since on_error='delayed_fail' on the 'on_error_f2', this
            # won't break the execution sequence of the driver and the following
            # will be executed...
            Beacon(tag='on_error_t3', ticket=t, **kw),
            Beacon(tag='on_error_t4', ticket=t, failer=True,
                   delay_component_errors=True, on_error='delayed_fail', **kw),
            #      ^^^^^^^^^^^^^^^^^^^^^^^^^^^
            # The 'on_error_t4' will fail ('failer=True'). However, since
            # 'delay_component_errors=True', the output file of 'on_error_t4' is
            # archived in cache (since it is produced by the AlgoComponent just
            # before crashing).
        ],
        # At the end of the Driver's run, the error on 'on_error1_f1' is completely ignored
        # but the error on 'on_error_f2' and 'on_error_t4' will cause the Driver to raise
        # an exception since on_error='delayed_fail' (that's why it is called "delayed"
        # fail).
        options=kw
    )
