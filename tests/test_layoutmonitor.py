import collections
import tempfile
import time
import unittest

from bronx.fancies.loggers import unittestGlobalLevel, getLogger
from bronx.stdtypes import date as _date

from footprints import proxy as fpx

import vortex
import common  # @UnusedImport
from vortex.data.handlers import Handler
from vortex.layout.dataflow import stripargs_section, intent, ixo, Section
from vortex.layout import monitor

logger = getLogger(__name__)
tloglevel = 'CRITICAL'


@unittestGlobalLevel(tloglevel)
class TestMonitor(unittest.TestCase):

    # Minimum 3 items in each of the lists below !
    _TERMS = [_date.Time(0), _date.Time(2), _date.Time(3), _date.Time(4)]
    _MEMBERS = range(0, 4)

    @staticmethod
    def _givetag():
        """Return the first available sessions name."""
        i = 1
        while 'test_layout_monitor_session_{:d}'.format(i) in vortex.sessions.keys():
            i += 1
        return 'test_layout_monitor_session_{:d}'.format(i)

    def setUp(self):
        self.cursession = vortex.sessions.current()
        self.oldpwd = self.cursession.system().pwd()
        # Generate a temporary directory and session
        # Note: the session is shared between all tests
        self.t = vortex.sessions.get(tag=self._givetag(),
                                     topenv=vortex.rootenv,
                                     glove=self.cursession.glove)
        self.sh = self.t.system()
        self.tmpdir = tempfile.mkdtemp(suffix='_test_layout_monitor')
        self.sh.cd(self.tmpdir)
        self.t.rundir = self.tmpdir
        self.t.activate()
        self.t.context.cocoon()
        self.sh.env.MTOOLDIR = self.tmpdir
        self._promises = collections.defaultdict(dict)
        self._inputs = collections.defaultdict(dict)
        # Initialise sections
        self._init_sections()
        # Do promises
        for it in self._TERMS:
            for im in self._MEMBERS:
                self.assertTrue(self._promises[it][im].put())

    def _create_section(self, x, ixokind):
        opts, xclean = stripargs_section(**x)
        if ixokind == ixo.OUTPUT:
            opts['intent'] = intent.OUT
        else:
            opts['intent'] = intent.IN
        picked_up = fpx.containers.pickup(  # @UndefinedVariable
            * fpx.providers.pickup_and_cache(  # @UndefinedVariable
                * fpx.resources.pickup_and_cache(xclean)  # @UndefinedVariable
            )
        )
        logger.debug('Resource desc %s', picked_up)
        picked_rh = Handler(picked_up)
        self.assertTrue(picked_rh.complete)
        picked_sec = Section(rh=picked_rh,
                             kind=ixokind,
                             ** opts)
        self.t.context.sequence.add(picked_sec)
        return picked_sec

    def _init_sections(self):
        const_stuff = dict(
            kind='historic',
            date='2019010100',
            cutoff='assim',
            model='arpege',
            geometry='global798',
            nativefmt='fa',
            experiment='monitortest@testuser',
            namespace='vortex.cache.fr',
            block='forecast',
            format='fa'
        )
        for it in self._TERMS:
            for im in self._MEMBERS:
                what = dict(term=it, member=im, promised=True,
                            local='PROMISED_[term::fmth]_mb[member]')
                what.update(const_stuff)
                self._promises[it][im] = self._create_section(what, ixo.OUTPUT)
                what = dict(role='InputStuff',
                            term=it, member=im, expected=True,
                            local='TESTFILE_[term::fmth]_mb[member]')
                what.update(const_stuff)
                self._inputs[it][im] = self._create_section(what, ixo.INPUT)

    def tearDown(self):
        self.t.exit()
        self.cursession.activate()
        self.sh.cd(self.oldpwd)
        self.sh.remove(self.tmpdir)

    def _actual_put(self, term, member):
        ps = self._promises[term][member]
        ps.rh.container.write("THIS IS A FAKE !", mode='wt')
        ps.rh.container.close()
        self.assertTrue(ps.put())
        ps.rh.container.clear()

    def _actual_fail(self, term, member):
        ps = self._promises[term][member]
        self.assertTrue(ps.rh.delete())

    def _actual_get(self, term, member):
        ins = self._inputs[term][member]
        return ins.rh.get()

    @property
    def _monitor_entry_list(self):
        melist = list()
        for it in self._TERMS:
            for im in self._MEMBERS:
                melist.append(monitor.InputMonitorEntry(self._inputs[it][im]))
        return melist

    def assertEqualTimedOut(self, new, ref, timeout=5):
        res = False
        t0 = time.time()
        while not res and time.time() - t0 < timeout:
            res = new() == ref
            if not res:
                time.sleep(0.05)
        self.assertEqual(new(), ref)

    def test_monitor_timeout(self):
        for im in self._MEMBERS:
            self._actual_put(_date.Time(0), im)
        bm = monitor.ManualInputMonitor(self.t.context, self._monitor_entry_list,
                                        caching_freq=0.05, mute=True)
        self.assertFalse(bm.all_done)
        with bm:
            self.assertFalse(bm.is_timedout(timeout=5))
            time.sleep(0.2)
            self.assertTrue(bm.is_timedout(timeout=0.05))

    def test_monitor_simple(self):
        for it in self._TERMS:
            for im in self._MEMBERS:
                self.assertTrue(self._actual_get(it, im))
        bm = monitor.BasicInputMonitor(self.t.context, role='InputStuff',
                                       caching_freq=0.05, mute=True)
        with bm:
            self.assertFalse(bm.all_done)
            self.assertEqualTimedOut(lambda: len(bm.expected),
                                     len(self._TERMS) * len(self._MEMBERS))
            self._actual_put(term=self._TERMS[-1], member=self._MEMBERS[0])
            self.assertEqualTimedOut(lambda: len(bm.available), 1)
            ima = bm.pop_available()
            self.assertEqual(ima.state, monitor.EntrySt.available)
            self.assertIs(ima.section, self._inputs[self._TERMS[-1]][self._MEMBERS[0]])
            self._actual_fail(term=self._TERMS[0], member=self._MEMBERS[-1])
            self.assertEqualTimedOut(lambda: len(bm.failed), 1)
            for im in self._MEMBERS[:-1]:
                self._actual_put(term=self._TERMS[0], member=im)
            self.assertEqualTimedOut(lambda: len(bm.available), len(self._MEMBERS) - 1)
            for it in self._TERMS[1:]:
                for im in self._MEMBERS:
                    self._actual_put(term=it, member=im)
            self.assertEqualTimedOut(lambda: bm.all_done, True)
            self.assertEqualTimedOut(lambda: len(bm.failed), 1)
            self.assertEqualTimedOut(lambda: len(bm.expected), 0)
            self.assertEqualTimedOut(lambda: len(bm.available),
                                     len(self._TERMS) * len(self._MEMBERS) - 2)

    def test_monitor_and_gangs(self):
        for it in self._TERMS:
            for im in self._MEMBERS:
                self.assertTrue(self._actual_get(it, im))
        bm = monitor.BasicInputMonitor(self.t.context, role='InputStuff',
                                       caching_freq=0.05, mute=True)
        mg = monitor.AutoMetaGang()
        mg.autofill(bm, grouping_keys=('term', ), allowmissing=1, waitlimit=0.001)
        with bm:
            self.assertFalse(bm.all_done)
            self.assertFalse(mg.has_collectable())
            self.assertFalse(mg.has_pcollectable())
            for ibg in mg.memberslist:
                self.assertEqual(ibg.state, monitor.GangSt.ufo)
            for im in self._MEMBERS:
                self._actual_put(term=self._TERMS[-1], member=im)
            self.assertEqualTimedOut(lambda: len(bm.available), len(self._MEMBERS))
            self.assertEqual(mg.has_collectable(), 1)
            self.assertEqual(mg.has_pcollectable(), 1)
            ibg = mg.pop_collectable()
            self.assertEqual(ibg.info['term'], self._TERMS[-1])
            self.assertEqual(ibg.state, monitor.GangSt.collectable)
            self.assertEqual(mg.has_collectable(), 0)
            for im in self._MEMBERS[1:]:
                self._actual_put(term=self._TERMS[0], member=im)
            self._actual_fail(term=self._TERMS[0], member=self._MEMBERS[0])
            for im in self._MEMBERS:
                self._actual_fail(term=self._TERMS[1], member=im)
            self.assertEqualTimedOut(lambda: len(bm.available), 2 * len(self._MEMBERS) - 1)
            time.sleep(0.01)
            self.assertEqual(mg.has_collectable(), 0)
            self.assertEqual(mg.has_pcollectable(), 1)
            ibg = mg.pop_pcollectable()
            self.assertEqual(ibg.info['term'], self._TERMS[0])
            self.assertEqual(ibg.state, monitor.GangSt.pcollectable)
            self.assertEqual(mg.has_pcollectable(), 0)
            self.assertEqualTimedOut(lambda: len(bm.failed), len(self._MEMBERS) + 1)
            failed = 0
            for ibg in mg.memberslist:
                failed += int(ibg.state == monitor.GangSt.failed)
            self.assertEqual(failed, 1)
        self.assertFalse(bm.all_done)


if __name__ == "__main__":
    unittest.main(verbosity=2)
