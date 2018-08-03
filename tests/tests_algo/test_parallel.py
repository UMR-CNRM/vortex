from __future__ import print_function, absolute_import, unicode_literals, division

import logging
import unittest

import footprints as fp
import vortex
from vortex.algo.mpitools import MpiException
from vortex.algo.components import ParallelInconsistencyAlgoComponentError
import common.algo.mpitools  # @UnusedImport


# Fake objects for test purposes only
class FakeResource(object):

    def command_line(self, **kwargs):
        return '-joke yes'


class FakeContainer(object):

    def __init__(self, name):
        self._name = name

    def localpath(self):
        return self._name


class FakeBinaryRh(object):

    def __init__(self, name):
        self.container = FakeContainer(name)
        self.resource = FakeResource()


class TestParallel(unittest.TestCase):

    _mpiauto = 'mpiauto --wrap --wrap-stdeo-pack --wrap-stdeo --verbose --init-timeout-restart 2'

    def setUp(self):
        self.t = vortex.ticket()
        self.locenv = self.t.env.clone()
        # Clean things up
        trash = [k for k in self.locenv.keys() if k.startswith('VORTEX_')]
        for k in trash:
            del self.locenv[k]
        self.locenv.active(True)
        self._fp_prev = fp.logger.level
        fp.logger.setLevel(logging.ERROR)
        self._v_prev = vortex.logger.level
        vortex.logger.setLevel(logging.ERROR)

    def tearDown(self):
        self.locenv.active(False)
        fp.logger.setLevel(self._fp_prev)
        vortex.logger.setLevel(self._v_prev)

    def _fix_algo(self, algo):
        # That's ugly :-(
        algo.ticket  = vortex.sessions.current()
        algo.context = algo.ticket.context
        algo.env  = algo.ticket.env
        algo.system  = algo.ticket.system()
        algo.target = algo.system.target()
        return algo

    def assertCmdl(self, ref, new, **extras):
        return self.assertEqual(ref.format(pwd=self.t.sh.pwd(), **extras),
                                ' '.join(new))

    def testOneBin(self):
        bin0 = FakeBinaryRh('fake')
        # MPI partitioning from explicit mpiopts
        algo = self._fix_algo(fp.proxy.component(engine='parallel', mpiname='mpirun'))
        _, args = algo._bootstrap_mpitool(bin0, dict(mpiopts=dict(nn=2, nnp=4, openmp=10)))
        self.assertCmdl('mpirun -npernode 4 -np 8 {pwd:s}/fake -joke yes', args)
        algo = self._fix_algo(fp.proxy.component(engine='parallel', mpiname='mpiauto'))
        _, args = algo._bootstrap_mpitool(bin0, dict(mpiopts=dict(nn=2, nnp=4, openmp=10)))
        self.assertCmdl('{base:s} --nn 2 --nnp 4 --openmp 10 -- {pwd:s}/fake -joke yes', args, base=self._mpiauto)
        algo = self._fix_algo(fp.proxy.component(engine='parallel', mpiname='mpiauto'))
        _, args = algo._bootstrap_mpitool(bin0, dict(mpiopts=dict(nn=2, nnp=4, np=8, openmp=10)))
        self.assertCmdl('{base:s} --nn 2 --nnp 4 --openmp 10 -- {pwd:s}/fake -joke yes', args, base=self._mpiauto)
        # Strange stuff: ask for a total of only 7 tasks (not recommended !)
        algo = self._fix_algo(fp.proxy.component(engine='parallel', mpiname='mpiauto'))
        _, args = algo._bootstrap_mpitool(bin0, dict(mpiopts=dict(nn=2, nnp=4, np=7)))
        self.assertCmdl('{base:s} --mpi-allow-odd-dist --nn 2 --nnp 4 --np 7 -- {pwd:s}/fake -joke yes', args, base=self._mpiauto)
        with self.assertRaises(MpiException):
            algo = self._fix_algo(fp.proxy.component(engine='parallel', mpiname='mpiauto'))
            _, args = algo._bootstrap_mpitool(bin0, dict(mpiopts=dict(nn=7, np=1)))
        # mpiauto prefix command...
        algo = self._fix_algo(fp.proxy.component(engine='parallel', mpiname='mpiauto'))
        _, args = algo._bootstrap_mpitool(bin0, dict(mpiopts=dict(nn=2, nnp=4, openmp=10,
                                                                  prefixcommand='toto')))
        self.assertCmdl('{base:s} --nn 2 --nnp 4 --openmp 10 --prefix-command toto -- {pwd:s}/fake -joke yes', args, base=self._mpiauto)
        # MPI partitioning from environment
        self.locenv.VORTEX_SUBMIT_NODES = 2
        self.locenv.VORTEX_SUBMIT_TASKS = 4
        self.locenv.VORTEX_SUBMIT_OPENMP = 10
        algo = self._fix_algo(fp.proxy.component(engine='parallel', mpiname='mpirun'))
        _, args = algo._bootstrap_mpitool(bin0, dict())
        self.assertCmdl('mpirun -npernode 4 -np 8 {pwd:s}/fake -joke yes', args)
        algo = self._fix_algo(fp.proxy.component(engine='parallel', mpiname='mpiauto'))
        _, args = algo._bootstrap_mpitool(bin0, dict())
        self.assertCmdl('{base:s} --nn 2 --nnp 4 --openmp 10 -- {pwd:s}/fake -joke yes', args, base=self._mpiauto)
        # Strange stuff: ask for a total of only 7 tasks (not recommended !)
        algo = self._fix_algo(fp.proxy.component(engine='parallel', mpiname='mpiauto'))
        _, args = algo._bootstrap_mpitool(bin0, dict(mpiopts=dict(np=7)))
        self.assertCmdl('{base:s} --mpi-allow-odd-dist --nn 2 --nnp 4 --np 7 --openmp 10 -- {pwd:s}/fake -joke yes', args, base=self._mpiauto)
        # Tweaking mpiname
        algo = self._fix_algo(fp.proxy.component(engine='parallel'))
        self.locenv.VORTEX_MPI_NAME = 'mpiauto'
        _, args = algo._bootstrap_mpitool(bin0, dict())
        self.assertCmdl('{base:s} --nn 2 --nnp 4 --openmp 10 -- {pwd:s}/fake -joke yes', args, base=self._mpiauto)
        # Tweaking mpiopts/mpilauncher
        self.locenv.VORTEX_MPI_OPTS = ''
        self.locenv.VORTEX_MPI_LAUNCHER = 'mpiauto_debug'
        _, args = algo._bootstrap_mpitool(bin0, dict())
        self.assertCmdl('{base:s} --nn 2 --nnp 4 --openmp 10 -- {pwd:s}/fake -joke yes', args, base='mpiauto_debug --init-timeout-restart 2')
        del self.locenv.VORTEX_MPI_OPTS
        del self.locenv.VORTEX_MPI_LAUNCHER
        # Let's go for an IO Server...
        self.locenv.VORTEX_IOSERVER_NODES = 1
        _, args = algo._bootstrap_mpitool(bin0, dict())
        self.assertCmdl('{base:s} --nn 1 --nnp 4 --openmp 10 -- {pwd:s}/fake -joke yes -- --nn 1 --nnp 4 --openmp 10 -- {pwd:s}/fake -joke yes',
                        args, base=self._mpiauto)
        _, args = algo._bootstrap_mpitool(bin0, dict(io_nnp=8, io_openmp=5))
        self.assertCmdl('{base:s} --nn 1 --nnp 4 --openmp 10 -- {pwd:s}/fake -joke yes -- --nn 1 --nnp 8 --openmp 5 -- {pwd:s}/fake -joke yes',
                        args, base=self._mpiauto)
        self.locenv.VORTEX_IOSERVER_TASKS = 8
        self.locenv.VORTEX_IOSERVER_OPENMP = 5
        _, args = algo._bootstrap_mpitool(bin0, dict())
        self.assertCmdl('{base:s} --nn 1 --nnp 4 --openmp 10 -- {pwd:s}/fake -joke yes -- --nn 1 --nnp 8 --openmp 5 -- {pwd:s}/fake -joke yes',
                        args, base=self._mpiauto)
        # Send the IO server at the begining of the arguments list
        algo = self._fix_algo(fp.proxy.component(engine='parallel', iolocation=0))
        _, args = algo._bootstrap_mpitool(bin0, dict())
        self.assertCmdl('{base:s} --nn 1 --nnp 8 --openmp 5 -- {pwd:s}/fake -joke yes -- --nn 1 --nnp 4 --openmp 10 -- {pwd:s}/fake -joke yes',
                        args, base=self._mpiauto)
        # Just check mpirun...
        algo = self._fix_algo(fp.proxy.component(engine='parallel', mpiname='mpirun', iolocation=0))
        _, args = algo._bootstrap_mpitool(bin0, dict())
        self.assertCmdl('mpirun -npernode 8 -np 8 {pwd:s}/fake -joke yes : -npernode 4 -np 4 {pwd:s}/fake -joke yes', args)
        # Zero IO server nodes...
        self.locenv.VORTEX_IOSERVER_NODES = 0
        _, args = algo._bootstrap_mpitool(bin0, dict())
        self.assertCmdl('mpirun -npernode 4 -np 8 {pwd:s}/fake -joke yes', args)

    def testThreeBins(self):
        bin0 = FakeBinaryRh('fake0')
        bin1 = FakeBinaryRh('fake1')
        bin2 = FakeBinaryRh('fake2')
        bins = [bin0, bin1, bin2]
        algo = self._fix_algo(fp.proxy.component(engine='parallel', mpiname='mpirun'))
        # Not enough informations
        with self.assertRaises(MpiException):
            algo._bootstrap_mpitool(bins, dict())
        # Malformed MPI opts
        with self.assertRaises(ValueError):
            algo._bootstrap_mpitool(bins, dict(mpiopts=dict(nn=1, openmp=1, nnp=1)))
        with self.assertRaises(ParallelInconsistencyAlgoComponentError):
            algo._bootstrap_mpitool(bins, dict(mpiopts=dict(nn=[1, 1], openmp=[1, 0], nnp=[1, 0])))
        _, args = algo._bootstrap_mpitool(bins, dict(mpiopts=dict(nn=[2, 2, 1], openmp=[10, 5, 5], nnp=[4, 8, 8])))
        self.assertCmdl('mpirun -npernode 4 -np 8 {pwd:s}/fake0 -joke yes : ' +
                        '-npernode 8 -np 16 {pwd:s}/fake1 -joke yes : ' +
                        '-npernode 8 -np 8 {pwd:s}/fake2 -joke yes', args)
        # Manual mpi_description names
        algo = self._fix_algo(fp.proxy.component(engine='parallel', mpiname='mpirun',
                                                 binarymulti=['basicsingle', 'basic']))
        with self.assertRaises(ParallelInconsistencyAlgoComponentError):
            _, args = algo._bootstrap_mpitool(bins, dict(mpiopts=dict(nn=[2, 2, 1], openmp=[10, 5, 5], nnp=[4, 8, 8])))
        algo = self._fix_algo(fp.proxy.component(engine='parallel', mpiname='mpirun',
                                                 binarymulti=['basicsingle', 'basic', 'nwpioserv']))
        _, args = algo._bootstrap_mpitool(bins, dict(mpiopts=dict(nn=[2, 2, 1], openmp=[10, 5, 5], nnp=[4, 8, 8])))
        self.assertCmdl('mpirun -npernode 4 -np 8 {pwd:s}/fake0 -joke yes : ' +
                        '-npernode 8 -np 16 {pwd:s}/fake1 -joke yes : ' +
                        '-npernode 8 -np 8 {pwd:s}/fake2 -joke yes', args)
        # Something with MPIauto and variables...
        algo = self._fix_algo(fp.proxy.component(engine='parallel', mpiname='mpiauto'))
        self.locenv.VORTEX_SUBMIT_NODES = 2
        self.locenv.VORTEX_SUBMIT_TASKS = 4
        self.locenv.VORTEX_SUBMIT_OPENMP = 10
        _, args = algo._bootstrap_mpitool(bins, dict())
        self.assertCmdl('{base:s} --nn 2 --nnp 4 --openmp 10 -- {pwd:s}/fake0 -joke yes -- ' +
                        '--nn 2 --nnp 4 --openmp 10 -- {pwd:s}/fake1 -joke yes -- ' +
                        '--nn 2 --nnp 4 --openmp 10 -- {pwd:s}/fake2 -joke yes', args, base=self._mpiauto)

    def testFullManual(self):
        bin0 = FakeBinaryRh('fake0')
        bin1 = FakeBinaryRh('fake1')
        bin2 = FakeBinaryRh('fake2')
        bins = [bin0, bin1, bin2]
        mpidescs = [fp.proxy.mpibinary(kind='basicsingle', nodes=2, tasks=4, openmp=10),
                    fp.proxy.mpibinary(kind='basic', nodes=2, tasks=8, openmp=5),
                    fp.proxy.mpibinary(kind='basic', nodes=1, tasks=8, openmp=5),
                    ]
        algo = self._fix_algo(fp.proxy.component(engine='parallel', mpiname='mpirun', binaries=mpidescs))
        _, args = algo._bootstrap_mpitool(bins, dict())
        self.assertCmdl('mpirun -npernode 4 -np 8 {pwd:s}/fake0 -joke yes : ' +
                        '-npernode 8 -np 16 {pwd:s}/fake1 -joke yes : ' +
                        '-npernode 8 -np 8 {pwd:s}/fake2 -joke yes', args)


if __name__ == "__main__":
    unittest.main(verbosity=2)
