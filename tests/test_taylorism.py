#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import absolute_import, print_function

import logging
logging.basicConfig(level=logging.ERROR)
import time

from unittest import TestCase, main

import footprints
import taylorism
from taylorism import examples
from opinel import interrupt  # because subprocesses must be killable properly



class _TestError(Exception): pass

class Succeeder(examples.Sleeper):
    """Does nothing, but succeeds at it."""

    _footprint = dict(
        priority=dict(
            level = footprints.priorities.top.level('debug')),
        info="Suceeds.",
        attr=dict(
            succeed=dict(
                info="Supposed to succeed.",
                type=bool,
                values=[True]),
            )
        )
    def _task(self):
        """Succeed at doing nothing."""
        super(Succeeder, self)._task()
        return "Succeeded."
    
class Failer(examples.Sleeper):
    """Does nothing, but fails at it."""

    _footprint = dict(
        priority=dict(
            level = footprints.priorities.top.level('debug')),
        info="Fails.",
        attr=dict(
            succeed=dict(
                info="Supposed to fail.",
                type=bool,
                values=[False]),
            )
        )
    def _task(self):
        """Fails (an exception is raised) at doing nothing."""
        super(Failer, self)._task()
        raise _TestError("Failer: failed")
        return "Failed."

class UtTaylorism(TestCase):
    
    def test_worker_met_an_exception(self):
        """
        Run a Succeeder and a Failer, checks that the Failer exception is
        catched.
        """
          
        boss = taylorism.run_as_server(common_instructions={},
                                       individual_instructions={'sleeping_time':[0.001, 0.01],
                                                                'succeed':[False, True]},
                                       scheduler=taylorism.MaxThreadsScheduler(max_threads=2))
        with interrupt.SignalInterruptHandler():
            with self.assertRaises(_TestError):
                boss.wait_till_finished()
         
    def test_boss_crashes(self):
        """
        Run a Succeeder and a Failer, checks that an error in the Boss
        subprocess is catched.
        """
         
        boss = taylorism.run_as_server(common_instructions={},
                                       individual_instructions={'sleeping_time':[60, 60],
                                                                'succeed':[True, True]},
                                       scheduler=taylorism.MaxThreadsScheduler(max_threads=2))
        with interrupt.SignalInterruptHandler():
            with self.assertRaises(interrupt.SignalInterruptError):
                time.sleep(0.01)
                boss._process.terminate()
                boss.wait_till_finished()
         
    def test_servermode(self):
        """Run as server mode, checks appending instructions."""
          
        boss = taylorism.run_as_server(common_instructions={},
                                       individual_instructions={'sleeping_time':[0.001, 0.001, 0.001]},
                                       scheduler=taylorism.MaxThreadsScheduler(max_threads=2))
        time.sleep(0.1)
        boss.set_instructions({}, individual_instructions={'sleeping_time':[0.001, ]})
        boss.wait_till_finished()
        report = boss.get_report()
        self.assertEqual(len(report['workers_report']), 4, "4 instructions have been sent, which is not the size of report.")

    def test_toomany_instr_after_crash(self):
        """
        Checks that overloading the instructions queue after end of
        subprocess does not lead to deadlock.
        """
        boss = taylorism.run_as_server(common_instructions={},
                                       individual_instructions={'sleeping_time':[0.001, 60],
                                                                'succeed':[False, True]},
                                       scheduler=taylorism.MaxThreadsScheduler(max_threads=2))
        time.sleep(0.1)
        with interrupt.SignalInterruptHandler():
            with self.assertRaises(_TestError):
                boss.set_instructions({}, individual_instructions={'sleeping_time':[1, ],
                                                                   'bidon':['a'*100000000,]})



if __name__ == '__main__':
    main(verbosity=2)

