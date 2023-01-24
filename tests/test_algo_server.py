import signal
import tempfile

import footprints as fp

from bronx.fancies import loggers
from bronx.system import interrupt

import unittest

import vortex
from vortex import toolbox as tb
from vortex.algo import components, serversynctools

logger = loggers.getLogger(__name__)
tloglevel = 9999  # Extremely quiet....


class ServerSyncToolQuick(serversynctools.ServerSyncSimpleSocket):
    """For test purposes: it just accelerate things by reducing the timeout."""
    _footprint = dict(
        attr = dict(
            checkinterval = dict(
                type        = int,
                optional    = True,
                default     = 1,
            ),
        ),
        priority = dict(
            level = fp.priorities.top.TOOLBOX  # @UndefinedVariable
        )
    )


class ExpressoServer(components.Expresso):
    """Just a fake algo component that simulate some crashes."""
    _footprint = dict(
        attr = dict(
            server_run = dict(
                values = [True, False],
            ),
            niter = dict(
                optional = True,
                type = int,
                default = 3,
            ),
            simulatecrash = dict(
                optional = True,
                type = bool,
                default = False
            ),
            tickingbomb = dict(
                optional = True,
                type = int,
            )
        )
    )

    def boum(self, signum, frame):
        raise interrupt.SignalInterruptError("Surprise !!!")

    def execute(self, rh, opts):
        for i in range(self.niter):
            logger.info('Prepare  iteration number %d', i + 1)
            logger.info('Starting iteration number %d', i + 1)
            if self.tickingbomb is not None:  # Fake a SIGTERM after a few seconds
                signal.signal(signal.SIGALRM, self.boum)
                signal.alarm(self.tickingbomb)
            super().execute(rh, opts)
            if self.simulatecrash:
                raise ValueError("Who knows what might happened ?")
            logger.info('Dealing with results of iteration number %d', i + 1)

    def spawn_pre_dirlisting(self):
        pass

    def postfix_post_dirlisting(self):
        pass


@loggers.unittestGlobalLevel(tloglevel)
class TestExpressoServer(unittest.TestCase):

    def setUp(self):
        self.t = vortex.sessions.current()
        self.sh = self.t.system()

        # Work in a dedicated directory
        self.tmpdir = tempfile.mkdtemp(suffix='test_expresso_server')
        self.oldpwd = self.sh.pwd()
        self.sh.cd(self.tmpdir)

        self.rpath = self.sh.path.join(self.t.glove.siteroot,
                                       'tests', 'data', 'server_decoy.py')
        self.syncscript = './decoy_sync.py'
        self.shandler = interrupt.SignalInterruptHandler(emitlogs=False)
        self.shandler.activate()

    def tearDown(self):
        self.sh.cd(self.oldpwd)
        self.sh.remove(self.tmpdir)
        self.shandler.deactivate()

    def _get_fake_server(self, *kargs, **kwargs):
        rhScript = tb.rh(language='python',
                         local='server_decoy_script.py',
                         remote=self.rpath,
                         **kwargs)
        rhScript.get()
        return rhScript

    def _run_algo(self, rhScript, niter, *kargs, **kwargs):
        algo = fp.proxy.component(engine='exec', interpreter='current',
                                  niter=niter, server_run=True,
                                  serversync_method='simple_socket',
                                  serversync_medium=self.syncscript,
                                  **kwargs)
        with self.sh.env.clone() as lenv:
            del lenv['PYTHONPATH']
            algo.run(rhScript)

    def test_server_fine(self):
        """When everything works as expected."""

        rhScript = self._get_fake_server(rawopts='--sleep 0.1')

        niter = 3
        self._run_algo(rhScript, niter)
        for i in range(niter):
            self.assertTrue(self.sh.path.exists('server_decoy_processing_{:d}'.format(i + 1),),
                            'Checking fake processing')

    def test_server_crash(self):
        """Simulate a crash in the server."""

        rhScript = self._get_fake_server(rawopts='--sleep 10 --crash')

        niter = 2
        with self.assertRaises(components.AlgoComponentError):
            self._run_algo(rhScript, niter)

    def test_mainscript_fails(self):
        """Simulate an exception in the main script."""

        rhScript = self._get_fake_server(rawopts='--sleep 0.5')

        niter = 2
        with self.assertRaises(ValueError):
            self._run_algo(rhScript, niter, simulatecrash=True)
        self.assertTrue(self.sh.path.exists('server_decoy_processing_1',),
                        'Checking fake processing')
        self.sh.sleep(1)
        self.assertFalse(self.sh.path.exists('server_decoy_processing_2',),
                         'Checking fake processing')

    def test_mainscript_sigterm(self):
        """Simulate a sigterm in the main script when the processing is in progress."""

        rhScript = self._get_fake_server(rawopts='--sleep 3')

        niter = 2
        with self.assertRaises(interrupt.SignalInterruptError):
            self._run_algo(rhScript, niter, tickingbomb=1)
        self.sh.sleep(2.5)  # If the subprocess still runs it might produce a file after 3 seconds
        self.assertFalse(self.sh.path.exists('server_decoy_processing_1',),
                         'Checking fake processing')


if __name__ == '__main__':
    unittest.main()
