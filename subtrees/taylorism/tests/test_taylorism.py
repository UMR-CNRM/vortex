import sys
import time

from unittest import TestCase, main, skipIf

import footprints
import taylorism
from taylorism import examples, schedulers, taylorism_log
from bronx.fancies import loggers
from bronx.system import interrupt  # because subprocesses must be killable properly
from bronx.system import cpus as cpus_tool

try:
    import numpy as np
except ImportError:
    numpy_looks_fine = False
else:
    numpy_looks_fine = True

tloglevel = 'CRITICAL'
tloglevel_taylorism = 'CRITICAL'


def stderr2out_deco(f):
    def wrapped_f(*kargs, **kwargs):
        oldstderr = sys.stderr
        sys.stderr = sys.stdout
        try:
            return f(*kargs, **kwargs)
        finally:
            sys.stderr = oldstderr
    wrapped_f.__name__ = f.__name__
    return wrapped_f


class _TestError(Exception):
    pass


class Succeeder(examples.Sleeper):
    """Does nothing, but succeeds at it."""

    _footprint = dict(
        priority=dict(
            level=footprints.priorities.top.level('debug')
        ),
        info="Suceeds.",
        attr=dict(
            succeed=dict(
                info="Supposed to succeed.",
                type=bool,
                values=[True]
            ),
            bind_test=dict(
                info="Do the bind test.",
                type=bool,
                optional=True,
                default=False,
            )
        )
    )

    def _task(self):
        """Succeed at doing nothing."""
        time.sleep(self.sleeping_time)
        if self.bind_test:
            return ("Succeeded.", self.binding())
        else:
            return ("Succeeded.", )


class Failer(examples.Sleeper):
    """Does nothing, but fails at it."""

    _footprint = dict(
        priority=dict(
            level=footprints.priorities.top.level('debug')
        ),
        info="Fails.",
        attr=dict(
            succeed=dict(
                info="Supposed to fail.",
                type=bool,
                values=[False]
            ),
        )
    )

    def _task(self):
        """Fails (an exception is raised) at doing nothing."""
        time.sleep(self.sleeping_time)
        raise _TestError("Failer: failed")


@loggers.unittestGlobalLevel(tloglevel)
class UtTaylorism(TestCase):

    @stderr2out_deco
    def test_worker_met_an_exception(self):
        """
        Run a Succeeder and a Failer, checks that the Failer exception is
        catched.
        """
        taylorism_log.setLevel(tloglevel_taylorism)
        boss = taylorism.run_as_server(
            common_instructions=dict(),
            individual_instructions=dict(sleeping_time=[0.001, 0.01], succeed=[False, True]),
            scheduler=footprints.proxy.scheduler(limit='threads', max_threads=2),
        )
        with interrupt.SignalInterruptHandler(emitlogs=False):
            with self.assertRaises(_TestError):
                boss.wait_till_finished()

    @stderr2out_deco
    def test_boss_crashes(self):
        """
        Run a Succeeder and a Failer, checks that an error in the Boss
        subprocess is catched.
        """
        taylorism_log.setLevel(tloglevel_taylorism)
        boss = taylorism.run_as_server(
            common_instructions=dict(),
            individual_instructions=dict(sleeping_time=[60, 60], succeed=[True, True]),
            scheduler=footprints.proxy.scheduler(limit='threads', max_threads=2),
        )
        with interrupt.SignalInterruptHandler(emitlogs=False):
            with self.assertRaises(interrupt.SignalInterruptError):
                time.sleep(2)
                boss._process.terminate()
                boss.wait_till_finished()

    def test_servermode(self):
        """Run as server mode, checks appending instructions."""
        # Test both new and legacy schedulers
        taylorism_log.setLevel(tloglevel_taylorism)
        for scheduler in (footprints.proxy.scheduler(limit='threads', max_threads=2),
                          schedulers.MaxThreadsScheduler(max_threads=2)):
            boss = taylorism.run_as_server(
                common_instructions=dict(succeed=True,),
                individual_instructions=dict(sleeping_time=[0.001, 0.001, 0.001]),
                scheduler=scheduler,
            )
            time.sleep(0.2)
            boss.set_instructions(dict(succeed=True,),
                                  individual_instructions=dict(sleeping_time=[0.001, ]))
            boss.wait_till_finished()
            report = boss.get_report()
            self.assertEqual(len(report['workers_report']),
                             4,
                             "4 instructions have been sent, which is not the size of report.")

    @stderr2out_deco
    def test_toomany_instr_after_crash(self):
        """
        Checks that overloading the instructions queue after end of
        subprocess does not lead to deadlock.
        """
        taylorism_log.setLevel(tloglevel_taylorism)
        boss = taylorism.run_as_server(
            common_instructions=dict(),
            individual_instructions=dict(sleeping_time=[0.001, 60], succeed=[False, True]),
            scheduler=footprints.proxy.scheduler(limit='threads', max_threads=2),
        )
        time.sleep(0.5)
        with interrupt.SignalInterruptHandler(emitlogs=False):
            with self.assertRaises(_TestError):
                boss.set_instructions(
                    dict(),
                    individual_instructions=dict(sleeping_time=[1, ], bidon=['a' * 100000000, ])
                )

    def test_binding(self):
        """Checks that the binding works."""
        try:
            li = cpus_tool.LinuxCpusInfo()
            avcpus = cpus_tool.get_affinity()
        except cpus_tool.CpusToolUnavailableError as e:
            raise self.skipTest(str(e))
        if set(li.cpus.keys()) != avcpus:
            raise self.skipTest('The host is not entirely available.')
        taylorism_log.setLevel(tloglevel_taylorism)
        boss = taylorism.run_as_server(
            common_instructions=dict(wakeup_sentence='yo', succeed=True, bind_test=True),
            individual_instructions=dict(sleeping_time=[0.001, 0.001, 0.001]),
            scheduler=footprints.proxy.scheduler(limit='threads', max_threads=2, binded=True),
        )
        boss.wait_till_finished()
        report = boss.get_report()
        self.assertEqual(len(report['workers_report']), 3,
                         "3 instructions have been sent, which is not the size of report.")
        self.assertEqual({r['report'][1][0] for r in report['workers_report']},
                         set(list(li.socketpacked_cpulist())[:2]))

    @stderr2out_deco
    def test_redundant_workers_name(self):
        """
        Checks that a clear error is raised if several workers wear the same
        name.
        """
        taylorism_log.setLevel(tloglevel_taylorism)
        with self.assertRaises(ValueError):
            boss = taylorism.run_as_server(
                common_instructions=dict(),
                individual_instructions=dict(name=['alfred', 'alfred'],
                                             sleeping_time=[60, 60],
                                             succeed=[True, True]),
                scheduler=footprints.proxy.scheduler(limit='threads', max_threads=2),
            )
            boss.wait_till_finished()

    def test_expansion_workers_name(self):
        """Checks that expansion in workers name works fine."""
        taylorism_log.setLevel(tloglevel_taylorism)
        boss = taylorism.run_as_server(
            common_instructions=dict(name='jean-pierre_[sleeping_time]', succeed=True,),
            individual_instructions=dict(sleeping_time=[0.001, 0.01]),
            scheduler=footprints.proxy.scheduler(limit='threads', max_threads=2),
        )
        boss.wait_till_finished()
        report = boss.get_report()
        self.assertEqual(len(report['workers_report']),
                         2,
                         "2 instructions have been sent, which is not the size of report.")

    @skipIf(not numpy_looks_fine, "NumPy is unavailable.")
    def test_sharedmemory_array(self):
        """Checks that sharedmemory mechanism works fine."""
        taylorism_log.setLevel(tloglevel_taylorism)
        vals = [813, 42, 8]
        s = taylorism.util.SharedNumpyArray(np.ones((1,), dtype=int) * vals[0])
        boss = taylorism.run_as_server(
            common_instructions=dict(use_lock=True),
            individual_instructions=dict(value=vals[1:]),
            scheduler=footprints.proxy.scheduler(limit='threads', max_threads=2),
            sharedmemory_common_instructions=dict(shared_sum=s)
        )
        boss.wait_till_finished()
        self.assertEqual(s[0],
                         sum(vals),
                         "sharedmemory array has wrong value:{} instead of expected: {}."
                         .format(s[0], sum(vals)))


if __name__ == '__main__':
    main(verbosity=2)
