#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import io
import re
import tempfile
import unittest

import footprints

import vortex
from vortex.algo.components import TaylorRun
from vortex.tools.parallelism import TaylorVortexWorker

tlog = footprints.loggers.getLogger('taylorism')
vlog = footprints.loggers.getLogger('vortex')
testlogger = footprints.loggers.getLogger(__name__)


class MyTaylorRunAlgo(TaylorRun):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['unittest_taylor_run_1', ]
            ),
            prefix = dict(
            ),
            loopcount = dict(
                type = int,
            ),
            failer = dict(
                default = -1,
                optional = True,
                type = int,
            ),
            ntasks = dict(
                default     = 4,
            ),
            engine = dict(
                optional = True,
                default = 'algo'
            ),
        )
    )

    @property
    def realkind(self):
        return 'unittest_taylor_run'

    def execute(self, rh, opts):

        self._default_pre_execute(rh, opts)
        common_i = self._default_common_instructions(rh, opts)
        # Update the common instructions
        common_i.update(dict(prefix=self.prefix,
                             failingindex=self.failer))

        for i in range(self.loopcount):
            # Give some instructions to the boss
            self._add_instructions(common_i, dict(loopindex=[i, ],
                                                  name=['{:s}_process{:06d}'.format(self.prefix, i), ]))

        self._default_post_execute(rh, opts)


class MyTaylorRunAlgoWorker(TaylorVortexWorker):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['unittest_taylor_run_1', ]
            ),
            prefix = dict(
            ),
            loopindex = dict(
                type = int,
            ),
            failingindex = dict(
                default = -1,
                optional = True,
                type = int,
            ),
        )
    )

    def vortex_task(self, **kwargs):
        print("Test print {:06d}".format(self.loopindex))
        testlogger.info("Test log   {:06d}".format(self.loopindex))
        testlogger.debug("Test debug {:06d}".format(self.loopindex))
        if self.loopindex == self.failingindex:
            raise ValueError('Blurp...')
        with io.open('{0.prefix:s}_{0.loopindex:06d}.result'.format(self), 'w') as fhout:
            fhout.write("Test write {:06d}".format(self.loopindex))


class TestTaylorRunAlgo(unittest.TestCase):

    def setUp(self):
        # Generate a temporary directory
        self.sh = vortex.sessions.current().system()
        self.tmpdir = tempfile.mkdtemp(suffix='_test_ssh')
        self.oldpwd = self.sh.pwd()
        self.sh.cd(self.tmpdir)
        # loglevel...
        self.oldlevelV = vlog.level
        vlog.setLevel('WARNING')
        self.oldlevelT = tlog.level
        tlog.setLevel(999)
        self.oldlevelS = testlogger.level
        testlogger.setLevel('INFO')

    def tearDown(self):
        self.sh.cd(self.oldpwd)
        self.sh.remove(self.tmpdir)
        vlog.setLevel(self.oldlevelV)
        tlog.setLevel(self.oldlevelT)
        testlogger.setLevel(self.oldlevelS)

    def assertOutputs(self, prefix, loopcount):
        for i in range(loopcount):
            with io.open('{:s}_{:06d}.result'.format(prefix, i), 'r') as fhin:
                self.assertEqual(fhin.read(),
                                 "Test write {:06d}".format(i))

    def assertDump(self, prefix, loopcount):
        files = self.sh.ls()
        found = False
        for a_file in files:
            if re.match(r'{:s}_process{:06d}_\d+_stdeo.txt'.format(prefix, loopcount), a_file):
                found = a_file
        self.assertTrue(found)
        with io.open(found, 'r') as fhin:
            alllines = fhin.readlines()
        self.assertRegexpMatches(alllines[0], "^Test print {:06d}$".format(loopcount))
        self.assertRegexpMatches(alllines[1], "^.*Test log   {:06d}".format(loopcount))
        self.assertEqual(len(alllines), 2)  # No DEBUG stuff

    def test_basic_taylorun(self):
        algo = footprints.proxy.component(kind='unittest_taylor_run_1',
                                          prefix='basic1', loopcount=8)
        algo.run()
        self.assertOutputs('basic1', 8)

    def test_failing_taylorun(self):
        algo = footprints.proxy.component(kind='unittest_taylor_run_1',
                                          prefix='failing1', loopcount=8, failer=2)
        with self.assertRaises(ValueError):
            algo.run()
        self.assertDump('failing1', 2)

    def test_verbose_taylorun(self):
        algo = footprints.proxy.component(kind='unittest_taylor_run_1',
                                          prefix='verbose1', loopcount=8,
                                          verbose=True)
        algo.run()
        self.assertOutputs('verbose1', 8)
        for i in range(8):
            self.assertDump('verbose1', i)


if __name__ == '__main__':
    unittest.main()
