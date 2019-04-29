#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, unicode_literals, division

from collections import defaultdict, OrderedDict
import io
import tempfile
import unittest

from bronx.fancies.loggers import unittestGlobalLevel
from bronx.patterns.observer import SecludedObserverBoard, Observer
from bronx.stdtypes.date import Date, daterangex

import footprints as fp

import vortex
from vortex import toolbox
from vortex.layout.nodes import ConfigSet, Task, Driver, Family, LoopFamily
from vortex.data import geometries


_JOBCONF1 = """
[DEFAULT]
suitebg            = oper
cycle              = cy42_peace-op2.21
arpege_cycle       = cy42_op2.67
cutoff             = production
geometry           = geometry(global798)
forecast2_{extra:s}_geometry = geometry(global1198)
fc_terms           = dict(production:dict(00:0-6-1 06:0-6-1 12:0-6-1 18:0-6-1))
fp_domains         = EUROC25,GLOB05,EURAT01
nbpert             = 34
nbruns             = 35
members_range      = start:1 end:&{{nbruns}} shift:-1
unitruc            = héhéhé

[job_demo_{extra:s}]
time               = 00:50:00
ntasks             = 10
proc               = 60
nnodes             = 6
openmp             = 8

[forecast1_{extra:s}]
block              = forecast1

[forecast2_{extra:s}]
block              = forecast2
"""

_JOBCONF2 = """
[DEFAULT]
cycle              = cy42_peace-op2.21
cutoff             = production
geometry           = geometry(global798)
nbruns             = 2
members            = rangex(start:1 end:&{nbruns} shift:-1)
physics            = rangex(start:1 end:&{nbruns} shift:99)

[hard_demo]
time               = 00:50:00
ntasks             = 10
proc               = 60
nnodes             = 6
openmp             = 8

[dates]
cutoff             = assim

[update1]
block              = update1

[update2]
block              = update2

[forecast1h]
geometry           = geometry(global1198)

"""

_GLOBAL_OBS = SecludedObserverBoard()

tloglevel = 'CRITICAL'


class TestTask(Task):

    def build(self):
        super(TestTask, self).build()
        _GLOBAL_OBS.notify_new(self, dict(tag=self.tag))

    def complete(self):
        _GLOBAL_OBS.notify_del(self, dict(tag=self.tag))
        super(TestTask, self).complete()

    def refill(self, **kw):
        """Populates the vortex cache with expected input flow data.

        The refill method is systematically called when a task is run. However,
        the refill is not always desirable hence the if statement that checks the
        self.steps attribute's content.
        """
        # This method acts as an example: if a refill is actually needed,
        # it should be overwritten.
        if 'refill' in self.steps:
            _GLOBAL_OBS.notify_upd(self, dict(tag=self.tag, refill=True))

    def process(self):
        """Abstract method: perform the task to do."""
        # This method acts as an example: it should be overwritten.

        actsteps = 0

        if 'early-fetch' in self.steps or 'fetch' in self.steps:
            actsteps |= 0b1

        if 'fetch' in self.steps:
            actsteps |= 0b10

        if 'compute' in self.steps:
            actsteps |= 0b100

        if 'backup' in self.steps or 'late-backup' in self.steps:
            actsteps |= 0b1000

        if 'late-backup' in self.steps:
            actsteps |= 0b10000

        _GLOBAL_OBS.notify_upd(self, dict(tag=self.tag,
                                          steps=actsteps,
                                          conf=dict(self.conf),
                                          defaults=dict(toolbox.defaults),
                                          pwd=self.sh.pwd()))


class TestConfigSet(unittest.TestCase):

    def test_configsset(self):
        cs = ConfigSet()
        # Easy
        cs.blop = 1
        self.assertEqual(cs.BLOP, 1)
        cs.TLIST = 'toto,titi,tata'
        self.assertListEqual(cs.tlist, ['toto', 'titi', 'tata'])
        cs.tdict = 'dict(toto:titi tata:titi)'
        self.assertDictEqual(cs.tdict, {'toto': 'titi', 'tata': 'titi'})
        cs.tdict2_map = 'toto:titi tata:titi'
        self.assertDictEqual(cs.tdict2, {'toto': 'titi', 'tata': 'titi'})
        for dmap in ('dict(toto:titi tata:titi)',
                     'default(dict(toto:titi tata:titi))'):
            cs.tdict3_map = dmap
            self.assertDictEqual(cs.tdict3_map, {'toto': 'titi', 'tata': 'titi'})
        for geo in ('global798', 'geometry(global798)', 'GEOMETRY(global798)'):
            cs.tgeometry = geo
            self.assertEqual(cs.tgeometry, geometries.get(tag='global798'))
        cs.tgeometries = 'global798,globalsp2'
        self.assertListEqual(cs.tgeometries, [geometries.get(tag='global798'),
                                              geometries.get(tag='globalsp2')])
        cs.tr_range = '1-5-2'
        self.assertListEqual(cs.tr, [1, 3, 5])
        cs.tr_range = 'float(1-5-2)'
        self.assertListEqual(cs.tr, [1., 3., 5.])
        # Remap + dict?
        cs.tdict2_map = 'int(toto:1 tata:2)'
        self.assertDictEqual(cs.tdict2, {'toto': 1, 'tata': 2})
        # What
        self.assertSetEqual(set(cs),
                            set(['blop', 'tlist', 'tdict', 'tdict2', 'tdict3_map', 'tgeometry', 'tgeometries', 'tr']))
        del cs.tdict3_MAP
        self.assertSetEqual(set(cs),
                            set(['blop', 'tlist', 'tdict', 'tdict2', 'tgeometry', 'tgeometries', 'tr']))
        cs.clear()
        self.assertEqual(len(cs), 0)


class TaskSpy(Observer):

    def __init__(self):
        self.events = defaultdict(OrderedDict)
        _GLOBAL_OBS.register(self)

    def quit(self):
        _GLOBAL_OBS.unregister(self)

    def updobsitem(self, item, info):
        linfo = dict(info)
        tag = linfo.pop('tag')
        for k, v in linfo.items():
            self.events[k][tag] = v

    def __getattr__(self, key):
        if not key.startswith('_'):
            return self.events[key]
        else:
            raise AttributeError(key)


@unittestGlobalLevel(tloglevel)
class TestHeavyNodesStuff(unittest.TestCase):

    @staticmethod
    def _givetag():
        """Return the first available sessions name."""
        i = 1
        while 'test_heavy_nodes_{:d}'.format(i) in vortex.sessions.keys():
            i += 1
        return 'test_heavy_nodes_{:d}'.format(i)

    def setUp(self):
        self.cursession = vortex.sessions.current()
        self.oldpwd = self.cursession.system().pwd()
        self.olddefaults = dict(fp.setup.defaults)
        # Generate a temporary directory and session
        # Note: the session is shared between all tests
        self.t = vortex.sessions.get(tag=self._givetag(),
                                     topenv=vortex.rootenv,
                                     glove=self.cursession.glove)
        self.sh = self.t.system()
        self.tmpdir = tempfile.mkdtemp(suffix='_test_heavynodes')
        self.sh.cd(self.tmpdir)
        self.t.rundir = self.tmpdir
        self.t.activate()
        # Test variables
        self.jobconfig = self.sh.path.join(self.tmpdir, 'jobconfig.ini')
        self.registered = set()
        self.spy = TaskSpy()

    def tearDown(self):
        self.spy.quit()
        self.cursession.activate()
        self.sh.cd(self.oldpwd)
        fp.setup.defaults = self.olddefaults
        self.sh.remove(self.tmpdir)

    def dumpconfig(self, what):
        with io.open(self.jobconfig, 'w', encoding='utf-8') as fhc:
            fhc.write(what)

    def _void_register(self, cycle):
        self.registered.add(cycle)

    def assertOrderedDictEqual(self, item, ref):
        if isinstance(ref, (list, tuple)):
            self.assertSequenceEqual(list(item.items()), ref)
        else:
            self.assertSequenceEqual(list(item.items()), list(ref.items()))

    def assertTaskPwd(self, got, expected):
        self.assertEqual(self.sh.path.realpath(got),
                         self.sh.path.realpath(self.sh.path.join(self.t.rundir, self.t.tag, expected)))

    def _test_nodes_simple(self, extra, refill=False, play=False, steps=()):
        self.dumpconfig(_JOBCONF1.format(extra=extra))
        with self.sh.env.clone() as lenv:
            lenv.rd_iniconf = self.jobconfig
            lenv.rd_jobname = 'job_demo'
            lenv.rd_rundate = Date('2018010100')
            lenv.rd_xpid = 'BLOP'
            lenv.rd_vapp = 'arpege'
            lenv.rd_vconf = '4dvarfr'
            lenv.rd_truc = 'toto'
            if refill:
                lenv.rd_refill = refill
            opts = dict(special_prefix='rd_',
                        register_cycle_prefix=self._void_register,
                        play=play)
            if steps:
                opts['steps'] = steps
            dr = Driver(tag='job_demo_drv_' + extra, ticket=self.t,
                        nodes=[TestTask(tag='forecast1_' + extra, ticket=self.t, **opts),
                               TestTask(tag='forecast2_' + extra, ticket=self.t, **opts)],
                        options = opts,
                        iniencoding='utf-8')
            dr.setup()
            dr.run()
            # Config
            self.assertEqual(self.spy.conf['forecast1_' + extra]['block'], 'forecast1')
            self.assertEqual(self.spy.conf['forecast1_' + extra]['geometry'].tag, 'global798')
            self.assertEqual(self.spy.conf['forecast2_' + extra]['block'], 'forecast2')
            self.assertEqual(self.spy.conf['forecast2_' + extra]['geometry'].tag, 'global1198')
            for tid in ['forecast1_' + extra, 'forecast2_' + extra]:
                self.assertEqual(self.spy.conf[tid]['xpid'], 'BLOP')
                self.assertEqual(self.spy.conf[tid]['truc'], 'toto')
                self.assertEqual(self.spy.conf[tid]['unitruc'], 'héhéhé')
            # PWD
            self.assertTaskPwd(self.spy.pwd['forecast1_' + extra], 'forecast1_' + extra)
            self.assertTaskPwd(self.spy.pwd['forecast2_' + extra], 'forecast2_' + extra)
            # Defaults
            self.assertEqual(self.spy.defaults['forecast1_' + extra]['geometry'].tag, 'global798')
            self.assertEqual(self.spy.defaults['forecast2_' + extra]['geometry'].tag, 'global1198')
            for tid in ['forecast1_' + extra, 'forecast2_' + extra]:
                self.assertEqual(self.spy.defaults[tid]['date'], Date('2018010100'))
                self.assertEqual(self.spy.defaults[tid]['model'], self.t.glove.vapp)
                self.assertEqual(self.spy.defaults[tid]['namespace'], 'vortex.cache.fr')
                self.assertEqual(self.spy.defaults[tid]['gnamespace'], 'gco.multi.fr')
                self.assertEqual(self.spy.defaults[tid]['cutoff'], 'production')
                self.assertEqual(self.spy.defaults[tid]['cycle'], 'cy42_peace-op2.21')
            # Cycles
            self.assertSetEqual(self.registered, set(['cy42_peace-op2.21', 'cy42_op2.67']))
            # No refills
            if not refill:
                self.assertTrue(len(self.spy.refill) == 0)
                if steps == ('compute', ):
                    self.assertOrderedDictEqual(self.spy.steps,
                                                [('forecast1_' + extra, 0b100),
                                                 ('forecast2_' + extra, 0b100)])
                else:
                    if play:
                        self.assertOrderedDictEqual(self.spy.steps,
                                                    [('forecast1_' + extra, 0b11111),
                                                     ('forecast2_' + extra, 0b11111)])
                    else:
                        self.assertOrderedDictEqual(self.spy.steps,
                                                    [('forecast1_' + extra, 0b11),
                                                     ('forecast2_' + extra, 0b11)])
            else:
                self.assertOrderedDictEqual(self.spy.refill,
                                            [('forecast1_' + extra, True),
                                             ('forecast2_' + extra, True)])

    def test_nodes_play(self):
        self._test_nodes_simple('play', play=True)

    def test_nodes_refill(self):
        self._test_nodes_simple('refill', refill=True)

    def test_nodes_compute(self):
        self._test_nodes_simple('compute', steps=('compute', ))

    def test_nodes_bare(self):
        self._test_nodes_simple('bare')

    def test_nodes_hard(self):
        self.dumpconfig(_JOBCONF2)
        with self.sh.env.clone() as lenv:
            lenv.rd_iniconf = self.jobconfig
            lenv.rd_jobname = 'hard_demo'
            lenv.rd_rundates = daterangex('2018010100-2018010200-PT12H')
            lenv.rd_xpid = 'BLOP'
            opts = dict(special_prefix='rd_',
                        register_cycle_prefix=self._void_register,
                        play=True,
                        anystuff='truc')
            dr = Driver(tag='job_demo_drv', ticket=self.t,
                        nodes = [[LoopFamily(
                            tag='dates',
                            ticket=self.t,
                            loopconf='rundates',
                            loopsuffix='+d{.ymdh:s}',
                            loopneednext=True,
                            nodes = [LoopFamily(
                                tag='members',
                                ticket=self.t,
                                loopconf='members,physics',
                                nodes = [
                                    Family(tag='update1', ticket=self.t,
                                           nodes=[
                                               TestTask(tag='forecast1h', ticket=self.t, **opts)
                                           ], **opts),
                                    Family(tag='update2', ticket=self.t,
                                           active_callback=lambda s: s.conf.member == 0,
                                           nodes=[
                                               TestTask(tag='forecast2h', ticket=self.t, **opts)
                                           ], **opts),
                                ], **opts),
                            ], **opts),
                        ], ], options = opts)
            dr.setup(verbose=False)
            dr.run()
            # Config
            alltasks = ['forecast1h+d2018010100+member0',
                        'forecast2h+d2018010100+member0',
                        'forecast1h+d2018010100+member1',
                        'forecast1h+d2018010112+member0',
                        'forecast2h+d2018010112+member0',
                        'forecast1h+d2018010112+member1', ]
            self.assertListEqual(list(self.spy.steps.keys()), alltasks)
            for t in alltasks:
                self.assertEqual(self.spy.conf[t]['cutoff'], 'assim')
                self.assertEqual(self.spy.conf[t]['anystuff'], 'truc')

            self.assertEqual(self.spy.conf['forecast1h+d2018010100+member0']['rundate'], Date('2018010100'))
            self.assertEqual(self.spy.conf['forecast1h+d2018010112+member0']['rundate'], Date('2018010112'))
            self.assertEqual(self.spy.conf['forecast1h+d2018010100+member0']['rundate_next'], Date('2018010112'))
            self.assertEqual(self.spy.conf['forecast1h+d2018010112+member0']['rundate_next'], Date('2018010200'))
            self.assertEqual(self.spy.conf['forecast1h+d2018010100+member0']['rundate_prev'], None)
            self.assertEqual(self.spy.conf['forecast1h+d2018010112+member0']['rundate_prev'], Date('2018010100'))

            self.assertEqual(self.spy.conf['forecast2h+d2018010100+member0']['member'], 0)
            self.assertEqual(self.spy.conf['forecast2h+d2018010100+member0']['member_prev'], None)
            self.assertEqual(self.spy.conf['forecast2h+d2018010100+member0']['member_next'], 1)
            self.assertEqual(self.spy.conf['forecast2h+d2018010100+member0']['physic'], 100)
            self.assertEqual(self.spy.conf['forecast2h+d2018010100+member0']['physic_prev'], None)
            self.assertEqual(self.spy.conf['forecast2h+d2018010100+member0']['physic_next'], 101)
            self.assertEqual(self.spy.conf['forecast1h+d2018010100+member1']['member'], 1)
            self.assertEqual(self.spy.conf['forecast1h+d2018010100+member1']['member_prev'], 0)
            self.assertEqual(self.spy.conf['forecast1h+d2018010100+member1']['member_next'], None)
            self.assertEqual(self.spy.conf['forecast1h+d2018010100+member1']['physic'], 101)
            self.assertEqual(self.spy.conf['forecast1h+d2018010100+member1']['physic_prev'], 100)
            self.assertEqual(self.spy.conf['forecast1h+d2018010100+member1']['physic_next'], None)

            self.assertEqual(self.spy.conf['forecast1h+d2018010112+member0']['geometry'].tag, 'global1198')
            self.assertEqual(self.spy.conf['forecast2h+d2018010112+member0']['geometry'].tag, 'global798')
            self.assertEqual(self.spy.conf['forecast1h+d2018010112+member0']['block'], 'update1')
            self.assertEqual(self.spy.conf['forecast2h+d2018010112+member0']['block'], 'update2')


if __name__ == "__main__":
    unittest.main(verbosity=2)
