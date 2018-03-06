#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Basic examples of how to use the module.

A more advanced example of use can be found in ``epygram``'s epy_conv.py tool.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import time

from footprints import proxy as fpx

from taylorism import Worker, run_as_server


class Sleeper(Worker):
    """
    Sample worker for tutorial or debugging purpose, that sleeps a given time.

    The over-loading of __init__() is not mandatory, but a possibility.
    """

    _footprint = dict(
        info = "Sleeps.",
        attr = dict(
            sleeping_time = dict(
                info     = "Sleeping time in s.",
                values   = [0.001, 0.01, 0.1] + list(range(10)) + list(range(10, 65, 5)),
                type     = float,
            ),
            wakeup_sentence = dict(
                info     = "What to say after sleep.",
                optional = True,
                access   = 'rwx',
                default  = 'Hello !',
            ),
        )
    )

    def _task(self):
        """
        Actual task of the Sleeper is implemented therein.
        Return the report to be sent back to the Boss.
        """
        time.sleep(self.sleeping_time)
        return ' '.join([self.wakeup_sentence, 'Woke up after',
                         str(self.sleeping_time), "s sleep on cpu", str(self.binding())])


def sleepers_generic_program(verbose=True, scheduler=None):
    """Generic example: how to run and control the Boss."""

    boss = run_as_server(
        common_instructions     = dict(wakeup_sentence = 'Hello Dolly !'),
        individual_instructions = dict(sleeping_time   = [4, 9, 2, 1]),
        scheduler               = scheduler,
        verbose                 = verbose,
    )
    time.sleep(5)
    print('Intermediate report:', boss.get_report())
    boss.set_instructions(dict(), individual_instructions=dict(sleeping_time = [3]))
    boss.wait_till_finished()
    report = boss.get_report()
    for r in report['workers_report']:
        print(r)


def sleepers_example_laxist(verbose=True):
    """Example: assuming no selection of strategy for scheduling."""
    sleepers_generic_program(
        verbose = verbose,
        scheduler = fpx.scheduler(nosort=True),
    )


def sleepers_example_threads(verbose=True):
    """Example: scheduling is driven by number of threads."""
    sleepers_generic_program(
        verbose = verbose,
        scheduler = fpx.scheduler(limit='threads', max_threads=3),
    )


def sleepers_example_bindedthreads(verbose=True):
    """Example: scheduling is driven by number of threads and processes are binded."""
    sleepers_generic_program(
        verbose = verbose,
        scheduler = fpx.scheduler(limit='threads', max_threads=3, binded=True),
    )


def sleepers_example_memory(verbose=True):
    """Example: scheduling is driven by memory consumption."""
    sleepers_generic_program(
        verbose = verbose,
        scheduler = fpx.scheduler(limit='memory', memory_per_task=1.8),
    )


def sleepers_example_bindedmemory(verbose=True):
    """Example: scheduling is driven by memory consumption and processes are binded."""
    sleepers_generic_program(
        verbose = verbose,
        scheduler = fpx.scheduler(limit='memory', binded=True),
    )
