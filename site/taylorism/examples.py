#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Basic examples of how to use the module.

A more advanced example of use can be found in ``epygram``'s epy_conv.py tool.
"""

from __future__ import absolute_import, print_function

import time

from taylorism import Worker, run_as_server
from taylorism.schedulers import MaxThreadsScheduler


class Sleeper(Worker):
    """
    Sample worker for tutorial or debugging purpose, that sleeps a given time.

    The over-loading of __init__() is not mandatory, but a possibility.
    """

    _footprint = dict(
        info="Sleeps.",
        attr=dict(
            sleeping_time=dict(
                info="Sleeping time in s.",
                type=float,
                values=[1, 2, 3, 5, 10, 15, 30, 60]),
            wakeup_sentence=dict(
                info="What to say after sleep.",
                type=str,
                optional=True,
                access='rwx',
                default=None)
            )
        )

    def __init__(self, *args, **kwargs):
        super(Sleeper, self).__init__(*args, **kwargs)
        if self.wakeup_sentence is None:
            self.wakeup_sentence = 'Hello !'

    def _task(self):
        """
        Actual task of the Sleeper is implemented therein.
        Return the report to be sent back to the Boss.
        """
        time.sleep(self.sleeping_time)
        return ' '.join([self.wakeup_sentence, "Woke up after", str(self.sleeping_time), "s sleep."])



def sleepers_example_program(verbose=True):
    """Example: how to run and control the Boss."""

    boss = run_as_server(common_instructions={},
                         individual_instructions={'sleeping_time':[5, 10, 2, 1]},
                         scheduler=MaxThreadsScheduler(max_threads=3),
                         verbose=verbose)
    time.sleep(6)
    print(boss.get_report())
    boss.set_instructions({}, individual_instructions={'sleeping_time':[3, ]})
    boss.wait_till_finished()
    report = boss.get_report()
    for r in report['workers_report']:
        print(r)
