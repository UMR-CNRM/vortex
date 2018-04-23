#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import absolute_import, print_function

import logging
logging.basicConfig(level=logging.ERROR)
import time
numpy_looks_fine = True
try:
    import numpy as np
except ImportError:
    numpy_looks_fine = False

from unittest import TestCase, main, skipIf

import footprints
import taylorism
from taylorism import examples, schedulers
from bronx.system import interrupt  # because subprocesses must be killable properly
from bronx.system import cpus as cpus_tool


class _TestError(Exception):
    pass


class Succeeder(examples.Sleeper):
    """Does nothing, but succeeds at it."""

    _footprint = dict(
        priority = dict(
            level = footprints.priorities.top.level('debug')
        ),
        info = "Suceeds.",
        attr = dict(
            succeed = dict(
                info   = "Supposed to succeed.",
                type   = bool,
                values = [True]
            ),
        )
    )

    def _task(self):
        """Succeed at doing nothing."""
        super(Succeeder, self)._task()
        return ("Succeeded.", self.binding())


class Failer(examples.Sleeper):
    """Does nothing, but fails at it."""

    _footprint = dict(
        priority = dict(
            level = footprints.priorities.top.level('debug')
        ),
        info = "Fails.",
        attr = dict(
            succeed = dict(
                info   = "Supposed to fail.",
                type   = bool,
                values = [False]
            ),
        )
    )

    def _task(self):
        """Fails (an exception is raised) at doing nothing."""
        super(Failer, self)._task()
        raise _TestError("Failer: failed")
        return ("Failed.", self.binding())


class UtTaylorism(TestCase):

    def test_worker_met_an_exception(self):
        """
        Run a Succeeder and a Failer, checks that the Failer exception is
        catched.
        """

        boss = taylorism.run_as_server(
            common_instructions     = dict(),
            individual_instructions = dict(sleeping_time=[0.001, 0.01], succeed=[False, True]),
            scheduler               = footprints.proxy.scheduler(limit='threads', max_threads=2),
        )
        with interrupt.SignalInterruptHandler():
            with self.assertRaises(_TestError):
                boss.wait_till_finished()

    def test_boss_crashes(self):
        """
        Run a Succeeder and a Failer, checks that an error in the Boss
        subprocess is catched.
        """

        boss = taylorism.run_as_server(
            common_instructions     = dict(),
            individual_instructions = dict(sleeping_time=[60, 60], succeed=[True, True]),
            scheduler               = footprints.proxy.scheduler(limit='threads', max_threads=2),
        )
        with interrupt.SignalInterruptHandler():
            with self.assertRaises(interrupt.SignalInterruptError):
                time.sleep(0.01)
                boss._process.terminate()
                boss.wait_till_finished()

    def test_servermode(self):
        """Run as server mode, checks appending instructions."""
        # Test both new and legacy schedulers
        for scheduler in (footprints.proxy.scheduler(limit='threads', max_threads=2),
                          schedulers.MaxThreadsScheduler(max_threads=2)):
            boss = taylorism.run_as_server(
                common_instructions     = dict(),
                individual_instructions = dict(sleeping_time=[0.001, 0.001, 0.001]),
                scheduler               = scheduler,
            )
            time.sleep(0.1)
            boss.set_instructions(dict(), individual_instructions=dict(sleeping_time=[0.001, ]))
            boss.wait_till_finished()
            report = boss.get_report()
            self.assertEqual(len(report['workers_report']), 4, "4 instructions have been sent, which is not the size of report.")

    def test_toomany_instr_after_crash(self):
        """
        Checks that overloading the instructions queue after end of
        subprocess does not lead to deadlock.
        """
        boss = taylorism.run_as_server(
            common_instructions     = dict(),
            individual_instructions = dict(sleeping_time=[0.001, 60], succeed=[False, True]),
            scheduler               = footprints.proxy.scheduler(limit='threads', max_threads=2),
        )
        time.sleep(0.1)
        with interrupt.SignalInterruptHandler():
            with self.assertRaises(_TestError):
                boss.set_instructions(
                    dict(),
                    individual_instructions = dict(sleeping_time=[1, ], bidon=['a' * 100000000, ])
                )

    def test_binding(self):
        """Checks that the binding works."""
        boss = taylorism.run_as_server(
            common_instructions     = dict(wakeup_sentence='yo', succeed=True),
            individual_instructions = dict(sleeping_time=[0.001, 0.001, 0.001]),
            scheduler               = footprints.proxy.scheduler(limit='threads', max_threads=2, binded=True),
        )
        try:
            boss.wait_till_finished()
        except cpus_tool.CpusToolUnavailableError as e:
            raise self.skipTest(str(e))
        report = boss.get_report()
        self.assertEqual(len(report['workers_report']), 3, "3 instructions have been sent, which is not the size of report.")
        self.assertEqual(set([r['report'][1][0] for r in report['workers_report']]), set([0, 1]))

    def test_redundant_workers_name(self):
        """
        Checks that a clear error is raised if several workers wear the same
        name.
        """
        with self.assertRaises(ValueError):
            boss = taylorism.run_as_server(
                common_instructions     = dict(),
                individual_instructions = dict(name=['alfred', 'alfred'], sleeping_time=[60, 60], succeed=[True, True]),
                scheduler               = footprints.proxy.scheduler(limit='threads', max_threads=2),
            )
            boss.wait_till_finished()

    def test_expansion_workers_name(self):
        """Checks that expansion in workers name works fine."""
        boss = taylorism.run_as_server(
            common_instructions     = dict(name='jean-pierre_[sleeping_time]'),
            individual_instructions = dict(sleeping_time = [0.001, 0.01]),
            scheduler               = footprints.proxy.scheduler(limit='threads', max_threads=2),
        )
        boss.wait_till_finished()
        report = boss.get_report()
        self.assertEqual(len(report['workers_report']), 2, "2 instructions have been sent, which is not the size of report.")

    @skipIf(not numpy_looks_fine)
    def test_sharedmemory_array(self):
        """Checks that sharedmemory mechanism works fine."""
        vals = [813, 42, 8]
        s = taylorism.util.SharedNumpyArray(np.ones((1,), dtype=int) * vals[0])
        boss = taylorism.run_as_server(
            common_instructions     = dict(use_lock=True),
            individual_instructions = dict(value=vals[1:]),
            scheduler               = footprints.proxy.scheduler(limit='threads', max_threads=2),
            sharedmemory_common_instructions = dict(shared_sum=s)
        )
        boss.wait_till_finished()
        self.assertEqual(s[0], sum(vals), "sharedmemory array has wrong value:{} instead of expected: {}.".format(s[0], sum(vals)))


if __name__ == '__main__':
    main(verbosity=2)
