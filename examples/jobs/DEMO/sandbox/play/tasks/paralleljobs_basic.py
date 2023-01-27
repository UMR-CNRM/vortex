"""
Demonstrate the benefits of the subjob feature.
"""

from vortex.layout.nodes import Driver, Family, LoopFamily

from .commons import Beacon


def setup(t, **kw):
    """Create a Driver object."""
    return Driver(
        tag     = 'pjobs_basic_drv',
        ticket  = t,
        nodes   = [
            Family(
                tag='pjobs_basic_f1',
                # pjobs_basic_batch1: will process members 1 to 4
                # pjobs_basic_batch2: will process members 5 to 8
                # pjobs_basic_batch3: will process members 9 to 12
                # pjobs_basic_batch4: will process members 13 to 16
                # (this is configured in the configuration file)
                nodes=[
                    LoopFamily(
                        tag='pjobs_basic_batch1',
                        loopconf='members',
                        nodes=[Beacon(tag='pjobs_t1', ticket=t, **kw)],
                        ticket=t, ** kw),
                    LoopFamily(
                        tag='pjobs_basic_batch2',
                        loopconf='members',
                        nodes=[Beacon(tag='pjobs_t2', ticket=t, **kw)],
                        ticket=t, **kw),
                    LoopFamily(
                        tag='pjobs_basic_batch3',
                        loopconf='members',
                        nodes=[Beacon(tag='pjobs_t3', ticket=t, **kw)],
                        ticket=t, **kw),
                    LoopFamily(
                        tag='pjobs_basic_batch4',
                        loopconf='members',
                        nodes=[Beacon(tag='pjobs_t4', ticket=t, **kw)],
                        ticket=t, **kw),
                ],

                # The `paralleljobs_kind` describes how the family's content should
                # be executed in parallel. 'spawn' is the simplest method: tasks
                # will be launched side-by-side on the current node.
                paralleljobs_kind='spawn',
                # NB: In real life, this is probably not what you want... e.g.
                #     for jobs running with the SLURM scheduler,
                #     `paralleljobs_kind='slurm:ssh'` is probably what you need.
                #     It will launch the family's content on distinct compute
                #     nodes (you are responsible for requesting the appropriate
                #     number of nodes to the SLURM scheduler.

                # Looking at the configuration file (section [pjobs_basic_f1]),
                # you will notice that paralleljobs_limit=2. It imposes a limit
                # on the number of nodes that can run concurrently.

                ticket=t, **kw)
        ],
        options=kw
    )
