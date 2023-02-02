import multiprocessing
import time
import os
import signal
import unittest

from bronx.system import interrupt


class TestInterrupt(unittest.TestCase):

    _multiprocess_startdelay = 0.05  # seconds

    def _catch_usr12(self, sleep_again=False):

        with interrupt.SignalInterruptHandler(signals=(signal.SIGUSR1, signal.SIGUSR2),
                                              emitlogs=False):
            try:
                time.sleep(30)
            except interrupt.SignalInterruptError:
                if sleep_again:
                    time.sleep(30)
                else:
                    exit(1)

    def test_interrupt_basics(self):
        # Start all the test subprocesses
        p1 = multiprocessing.Process(target=self._catch_usr12)
        p2 = multiprocessing.Process(target=self._catch_usr12)
        p3 = multiprocessing.Process(target=self._catch_usr12,
                                     kwargs=dict(sleep_again=True))
        p1.start()
        p2.start()
        p3.start()

        # Give some time to the subprocesses to setup the signal handler
        time.sleep(self._multiprocess_startdelay)

        # Start the killings
        # SIGTERM still works
        os.kill(p1.pid, signal.SIGTERM)
        # SIGUSR1 is caught !
        os.kill(p2.pid, signal.SIGUSR1)
        # Harassment...
        os.kill(p3.pid, signal.SIGUSR2)
        time.sleep(self._multiprocess_startdelay)
        os.kill(p3.pid, signal.SIGUSR1)

        # Check...
        p1.join()
        self.assertEqual(p1.exitcode, - signal.SIGTERM)
        p2.join()
        self.assertEqual(p2.exitcode, 1)
        p3.join()
        self.assertEqual(p3.exitcode, - signal.SIGUSR1)


if __name__ == '__main__':
    unittest.main()
