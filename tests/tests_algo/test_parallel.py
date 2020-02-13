from __future__ import print_function, absolute_import, unicode_literals, division

import io
import logging
import os
import sys
import tempfile
import unittest

from bronx.fancies.loggers import unittestGlobalLevel
import footprints as fp
import vortex
from vortex.algo.mpitools import MpiException
from vortex.algo.components import Parallel, ParallelIoServerMixin, ParallelOpenPalmMixin
from vortex.algo.components import ParallelInconsistencyAlgoComponentError, AlgoComponentError
from vortex.util import config
import common.algo.mpitools  # @UnusedImport

DATAPATHTEST = os.path.join(os.path.dirname(__file__), '..', 'data')

tloglevel = 'CRITICAL'


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


class IoServerTestEngine(Parallel, ParallelIoServerMixin):

    _footprint = dict(
        attr = dict(
            engine = dict(
                values = ['test_parallel_ioengine', ]
            ),
        )
    )


class PalmedTestEngine(Parallel, ParallelOpenPalmMixin):

    _footprint = dict(
        attr = dict(
            engine = dict(
                values = ['test_parallel_palmed_engine', ]
            ),
            openpalm_driver = dict(
                default = 'the_plam_driver.x',
            ),
        ),
    )


@unittestGlobalLevel(tloglevel)
class TestParallel(unittest.TestCase):

    _mpiauto = 'mpiauto --init-timeout-restart 2 --verbose --wrap --wrap-stdeo --wrap-stdeo-pack'

    def setUp(self):
        self.t = vortex.ticket()
        # Tweak the target object
        self.testconf = os.path.join(DATAPATHTEST, 'target-test.ini')
        self.t.sh.target(inifile=self.testconf)
        # Local environement
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
        # Tmp directory
        self._oldpwd = self.t.sh.pwd()
        self._tmpdir = tempfile.mkdtemp(prefix='tmp_test_alog_para')
        self.t.sh.cd(self._tmpdir)

    def tearDown(self):
        self.t.sh.cd(self._oldpwd)
        self.t.sh.rm(self._tmpdir)
        self.locenv.active(False)
        fp.logger.setLevel(self._fp_prev)
        vortex.logger.setLevel(self._v_prev)

    def _fix_algo(self, algo):
        # That's ugly :-(
        algo.ticket = vortex.sessions.current()
        algo.context = algo.ticket.context
        algo.env = algo.ticket.env
        algo.system = algo.ticket.system()
        algo.target = algo.system.default_target
        return algo

    def assertCmdl(self, ref, new, **extras):
        return self.assertEqual(ref.format(pwd=self.t.sh.pwd(), **extras),
                                ' '.join(new))

    def assertWrapper(self, mpirankvar, binpaths,
                      tplname='@mpitools/envelope_wrapper_default.tpl',
                      binargs=()):
        with io.open('./global_envelope_wrapper.py') as fhw:
            wrapper_new = fhw.read()
        wtpl_ref = config.load_template(self.t, tplname, encoding='utf-8')
        wrapper_ref = wtpl_ref.substitute(
            python=sys.executable,
            mpirankvariable=mpirankvar,
            todolist=("\n".join(["  {:d}: ('{:s}', [{:s}]),".
                                 format(i, what,
                                        (binargs[i] if i < len(binargs)
                                         else ', '.join(["'{:s}'".format(a) for a in ('-joke', 'yes')]))
                                        )
                                 for i, what in enumerate(binpaths)]))
        )
        try:
            return self.assertEqual(wrapper_new, wrapper_ref)
        except AssertionError:
            print('REF:\n', wrapper_ref)
            print('GOT:\n', wrapper_new)
            raise

    def test_config_reader(self):
        algo = self._fix_algo(fp.proxy.component(engine='parallel'))
        self.assertEqual(algo._mpitool_attributes(dict()), dict(mpiname='mpiauto'))
        algo = self._fix_algo(fp.proxy.component(engine='parallel', mpiname='mpirun'))
        self.assertEqual(algo._mpitool_attributes(dict()), dict(mpiname='mpirun'))
        algo = self._fix_algo(fp.proxy.component(engine='parallel', mpiconflabel='fullsrun'))
        self.assertEqual(algo._mpitool_attributes(dict()),
                         dict(mpiname='mpiauto', mpilauncher='/truc/mpiauto',
                              sublauncher='srun', bindingmethod='launcherspecific'))
        algo = self._fix_algo(fp.proxy.component(engine='parallel', mpiname='mpirun',
                                                 mpiconflabel='fullsrun'))
        self.assertEqual(algo._mpitool_attributes(dict()), dict(mpiname='mpirun'))
        algo = self._fix_algo(fp.proxy.component(engine='parallel', mpiconflabel='fullsrun'))
        self.assertEqual(algo._mpitool_attributes(dict(mpiauto_mpilauncher='toto')),
                         dict(mpiname='mpiauto', mpilauncher='toto',
                              sublauncher='srun', bindingmethod='launcherspecific'))
        self.assertEqual(algo._mpitool_attributes(dict(mpiauto_mpilauncher=None)),
                         dict(mpiname='mpiauto', mpilauncher=None,
                              sublauncher='srun', bindingmethod='launcherspecific'))
        with self.locenv.delta_context(VORTEX_MPI_LAUNCHER='troll'):
            self.assertEqual(algo._mpitool_attributes(dict(mpiauto_opt_sublauncher=None)),
                             dict(mpiname='mpiauto', mpilauncher='troll',
                                  sublauncher=None, bindingmethod='launcherspecific'))
        with self.locenv.delta_context(VORTEX_MPI_OPTS='--toto'):
            self.assertEqual(algo._mpitool_attributes(dict(mpiauto_opt_sublauncher=None)),
                             dict(mpiname='mpiauto', mpilauncher='/truc/mpiauto',
                                  sublauncher=None, bindingmethod='launcherspecific',
                                  mpiopts='--toto'))
            self.assertEqual(algo._mpitool_attributes(dict(mpiauto_opt_sublauncher=None,
                                                           mpiauto_mpiopts=None)),
                             dict(mpiname='mpiauto', mpilauncher='/truc/mpiauto',
                                  sublauncher=None, bindingmethod='launcherspecific',
                                  mpiopts=None))

    def testOneBin(self):
        bin0 = FakeBinaryRh('fake')
        # MPI partitioning from explicit mpiopts
        algo = self._fix_algo(fp.proxy.component(engine='parallel', mpiname='mpirun'))
        _, args = algo._bootstrap_mpitool(bin0, dict(mpiopts=dict(nn=2, nnp=4, openmp=10)))
        self.assertCmdl('mpirun -npernode 4 -np 8 {pwd:s}/fake -joke yes', args)
        _, args = algo._bootstrap_mpitool(bin0, dict(mpiname='mpiauto',
                                                     mpiopts=dict(nn=2, nnp=4, openmp=10)))
        self.assertCmdl('{base:s} --nn 2 --nnp 4 --openmp 10 -- {pwd:s}/fake -joke yes', args, base=self._mpiauto)
        _, args = algo._bootstrap_mpitool(bin0, dict(mpiname='mpiauto', mpiauto_mpiopts='',
                                                     mpiopts=dict(nn=2, nnp=4, openmp=10)))
        self.assertCmdl('mpiauto --init-timeout-restart 2 --nn 2 --nnp 4 --openmp 10 -- {pwd:s}/fake -joke yes', args)
        _, args = algo._bootstrap_mpitool(bin0, dict(mpiname='mpiauto', mpiauto_mpiopts='',
                                                     mpiauto_opt_sublauncher='srun',
                                                     mpiauto_opt_bindingmethod='launcherspecific',
                                                     mpiopts=dict(nn=2, nnp=4, openmp=10)))
        self.assertCmdl('mpiauto --init-timeout-restart 2 --no-use-arch-bind --use-slurm-bind --use-slurm-mpi ' +
                        '--nn 2 --nnp 4 --openmp 10 -- {pwd:s}/fake -joke yes', args)
        _, args = algo._bootstrap_mpitool(bin0, dict(mpiname='mpiauto', mpiauto_mpiopts='',
                                                     mpiauto_opt_sublauncher='libspecific',
                                                     mpiopts=dict(nn=2, nnp=4, openmp=10)))
        _, args = algo._bootstrap_mpitool(bin0, dict(mpiname='mpiauto', mpiauto_mpiopts='',
                                                     mpiauto_opt_bindingmethod='arch',
                                                     mpiopts=dict(nn=2, nnp=4, openmp=10)))
        self.assertCmdl('mpiauto --init-timeout-restart 2 --use-arch-bind ' +
                        '--nn 2 --nnp 4 --openmp 10 -- {pwd:s}/fake -joke yes', args)
        _, args = algo._bootstrap_mpitool(bin0, dict(mpiname='mpiauto', mpiauto_mpiopts='',
                                                     mpiauto_opt_sublauncher='libspecific',
                                                     mpiauto_opt_bindingmethod='launcherspecific',
                                                     mpiopts=dict(nn=2, nnp=4, openmp=10)))
        self.assertCmdl('mpiauto --init-timeout-restart 2 --no-use-arch-bind --no-use-slurm-mpi ' +
                        '--use-intelmpi-bind --use-openmpi-bind --use-slurm-bind ' +
                        '--nn 2 --nnp 4 --openmp 10 -- {pwd:s}/fake -joke yes', args)
        with self.locenv.clone() as cloned_env:
            cloned_env['MPIAUTOGRUIK'] = 1
            algo = self._fix_algo(fp.proxy.component(engine='parallel', mpiconflabel='fullspecific'))
            mpi, args = algo._bootstrap_mpitool(bin0, dict(mpiopts=dict(nn=2, nnp=4, openmp=10)))
            self.assertCmdl('mpiauto --init-timeout-restart 2 ' +
                            '--no-use-arch-bind --no-use-slurm-mpi --use-intelmpi-bind --use-openmpi-bind --use-slurm-bind ' +
                            '--verbose --wrap --wrap-stdeo --wrap-stdeo-pack ' +
                            '--nn 2 --nnp 4 --openmp 10 -- {pwd:s}/fake -joke yes',
                            args)
            mpi.setup_environment(dict(), conflabel='fullspecific')
            self.assertEqual(cloned_env['FAKEVARIABLE'], 'fullspecific')
            self.assertEqual(cloned_env['MPIAUTOCONFIG'], 'mpiauto.TIME.conf')
            self.assertNotIn('MPIAUTOGRUIK', cloned_env)
        algo = self._fix_algo(fp.proxy.component(engine='parallel', mpiname='mpiauto'))
        _, args = algo._bootstrap_mpitool(bin0, dict(mpiopts=dict(nn=2, nnp=4, openmp=10)))
        self.assertCmdl('{base:s} --nn 2 --nnp 4 --openmp 10 -- {pwd:s}/fake -joke yes', args, base=self._mpiauto)
        algo = self._fix_algo(fp.proxy.component(engine='parallel', mpiname='mpiauto'))
        _, args = algo._bootstrap_mpitool(bin0, dict(mpiopts=dict(envelope=dict(nn=2, nnp=4, openmp=10))))
        self.assertCmdl('{base:s} --nn 2 --nnp 4 --openmp 10 --prefix-command ./global_envelope_wrapper.py -- {pwd:s}/fake',
                        args, base=self._mpiauto)
        binpaths = ['{pwd:s}/fake'.format(pwd=self.t.sh.pwd()), ] * 8
        self.assertWrapper('MPIAUTORANK', binpaths, tplname='@mpitools/envelope_wrapper_mpiauto.tpl')
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
        # envelope = auto requires variables...
        algo = self._fix_algo(fp.proxy.component(engine='parallel', mpiname='mpiauto'))
        with self.assertRaises(ValueError):
            _, args = algo._bootstrap_mpitool(bin0, dict(mpiopts=dict(envelope='auto')))
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
        _, args = algo._bootstrap_mpitool(bin0, dict(mpiopts=dict(envelope='auto')))
        self.assertCmdl('{base:s} --nn 2 --nnp 4 --openmp 10 --prefix-command ./global_envelope_wrapper.py -- {pwd:s}/fake',
                        args, base=self._mpiauto)
        binpaths = ['{pwd:s}/fake'.format(pwd=self.t.sh.pwd()), ] * 8
        self.assertWrapper('MPIAUTORANK', binpaths, tplname='@mpitools/envelope_wrapper_mpiauto.tpl')
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
        with self.locenv.delta_context(VORTEX_MPI_OPTS='', VORTEX_MPI_LAUNCHER='mpiauto_debug'):
            _, args = algo._bootstrap_mpitool(bin0, dict())
        self.assertCmdl('{base:s} --nn 2 --nnp 4 --openmp 10 -- {pwd:s}/fake -joke yes', args, base='mpiauto_debug --init-timeout-restart 2')

        # Let's go for an IO Server...
        algo = self._fix_algo(fp.proxy.component(engine='test_parallel_ioengine', mpiname='mpiauto'))
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
        algo = self._fix_algo(fp.proxy.component(engine='test_parallel_ioengine', iolocation=0))
        _, args = algo._bootstrap_mpitool(bin0, dict())
        self.assertCmdl('{base:s} --nn 1 --nnp 8 --openmp 5 -- {pwd:s}/fake -joke yes -- --nn 1 --nnp 4 --openmp 10 -- {pwd:s}/fake -joke yes',
                        args, base=self._mpiauto)
        # Just check mpirun...
        algo = self._fix_algo(fp.proxy.component(engine='test_parallel_ioengine', mpiname='mpirun', iolocation=0))
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
        with self.assertRaises(AlgoComponentError):
            _, args = algo._bootstrap_mpitool(bins, dict(mpiopts=dict(envelope='auto', np=[8, 8, 8])))
        self.locenv.VORTEX_SUBMIT_NODES = 6
        _, args = algo._bootstrap_mpitool(bins, dict(mpiopts=dict(envelope='auto', np=[8, 8, 8])))
        self.assertCmdl('{base:s} --nn 6 --nnp 4 --openmp 10 --prefix-command ./global_envelope_wrapper.py -- {pwd:s}/fake0',
                        args, base=self._mpiauto)
        binpaths = ['{pwd:s}/fake0'.format(pwd=self.t.sh.pwd()), ] * 8
        binpaths.extend(['{pwd:s}/fake1'.format(pwd=self.t.sh.pwd()), ] * 8)
        binpaths.extend(['{pwd:s}/fake2'.format(pwd=self.t.sh.pwd()), ] * 8)
        self.assertWrapper('MPIAUTORANK', binpaths, tplname='@mpitools/envelope_wrapper_mpiauto.tpl')

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

        mpidescs = [fp.proxy.mpibinary(kind='basicsingle', nodes=2, tasks=4, openmp=10),
                    fp.proxy.mpibinary(kind='basic', nodes=2, tasks=8, openmp=5),
                    fp.proxy.mpibinary(kind='basic', nodes=1, tasks=8, openmp=5),
                    ]
        algo = self._fix_algo(fp.proxy.component(engine='parallel', mpiname='mpirun', binaries=mpidescs))
        _, args = algo._bootstrap_mpitool(bins,
                                          dict(mpiopts=dict(envelope=[dict(nn=2, nnp=4, openmp=10),
                                                                      dict(nn=3, nnp=8, openmp=5), ])))
        self.assertCmdl('mpirun -npernode 4 -np 8 ./global_envelope_wrapper.py : ' +
                        '-npernode 8 -np 24 ./global_envelope_wrapper.py', args)

        binpaths = ['{pwd:s}/fake0'.format(pwd=self.t.sh.pwd()), ] * 8
        binpaths.extend(['{pwd:s}/fake1'.format(pwd=self.t.sh.pwd()), ] * 16)
        binpaths.extend(['{pwd:s}/fake2'.format(pwd=self.t.sh.pwd()), ] * 8)
        self.assertWrapper('MPIRANK', binpaths)

    def testPalmMixin(self):
        self.t.sh.touch('the_plam_driver.x')
        bin0 = FakeBinaryRh('fake0')
        bin1 = FakeBinaryRh('fake1')
        # MPI partitioning from explicit mpiopts: no envelope provided, overcommiting
        algo = self._fix_algo(fp.proxy.component(engine='test_parallel_palmed_engine', mpiname='mpirun',))
        with self.assertRaises(AlgoComponentError):
            algo._bootstrap_mpitool(bin0, dict(mpiopts=dict(nn=3, np=12)))
        _, args = algo._bootstrap_mpitool(bin0, dict(mpiopts=dict(nn=3, nnp=4, openmp=10)))
        self.assertCmdl('mpirun -npernode 5 -np 5 ./global_envelope_wrapper.py : -npernode 4 -np 8 ./global_envelope_wrapper.py', args)
        binpaths = ['the_plam_driver.x'.format(pwd=self.t.sh.pwd()), ] * 1
        binpaths.extend(['{pwd:s}/fake0'.format(pwd=self.t.sh.pwd()), ] * 12)
        self.assertWrapper('MPIRANK', binpaths, binargs=['', ])
        _, args = algo._bootstrap_mpitool(bin0, dict(mpiopts=dict(nn=3, nnp=4)))
        self.assertCmdl('mpirun -npernode 5 -np 5 ./global_envelope_wrapper.py : -npernode 4 -np 8 ./global_envelope_wrapper.py', args)
        self.locenv.VORTEX_SUBMIT_NODES = 3
        self.locenv.VORTEX_SUBMIT_TASKS = 4
        self.locenv.VORTEX_SUBMIT_OPENMP = 10
        _, args = algo._bootstrap_mpitool(bin0, dict())
        self.assertCmdl('mpirun -npernode 5 -np 5 ./global_envelope_wrapper.py : -npernode 4 -np 8 ./global_envelope_wrapper.py', args)
        _, args = algo._bootstrap_mpitool(bin0, dict(mpiopts=dict(nn=1, nnp=4)))
        self.assertCmdl('mpirun -npernode 5 -np 5 ./global_envelope_wrapper.py', args)
        _, args = algo._bootstrap_mpitool([bin0, bin1],
                                          dict(mpiopts=dict(nn=[3, 2], nnp=[4, 8], openmp=[10, 5])))
        self.assertCmdl('mpirun -npernode 5 -np 5 ./global_envelope_wrapper.py : -npernode 4 -np 8 ./global_envelope_wrapper.py : -npernode 8 -np 16 ./global_envelope_wrapper.py', args)
        binpaths = ['the_plam_driver.x'.format(pwd=self.t.sh.pwd()), ] * 1
        binpaths.extend(['{pwd:s}/fake0'.format(pwd=self.t.sh.pwd()), ] * 12)
        binpaths.extend(['{pwd:s}/fake1'.format(pwd=self.t.sh.pwd()), ] * 16)
        self.assertWrapper('MPIRANK', binpaths, binargs=['', ])
        # MPI partitioning from explicit mpiopts: with envelope provided, overcommiting
        algo = self._fix_algo(fp.proxy.component(engine='test_parallel_palmed_engine', mpiname='mpirun',))
        _, args = algo._bootstrap_mpitool([bin0, bin1],
                                          dict(mpiopts=dict(np=[8, 4], envelope='auto')))
        self.assertCmdl('mpirun -npernode 5 -np 5 ./global_envelope_wrapper.py : -npernode 4 -np 8 ./global_envelope_wrapper.py', args)
        binpaths = ['the_plam_driver.x'.format(pwd=self.t.sh.pwd()), ] * 1
        binpaths.extend(['{pwd:s}/fake0'.format(pwd=self.t.sh.pwd()), ] * 8)
        binpaths.extend(['{pwd:s}/fake1'.format(pwd=self.t.sh.pwd()), ] * 4)
        self.assertWrapper('MPIRANK', binpaths, binargs=['', ])
        _, args = algo._bootstrap_mpitool([bin0, ],
                                          dict(mpiopts=dict(envelope=[dict(nn=2, nnp=4, openmp=10),
                                                                      dict(nn=2, nnp=8, openmp=5)])))
        self.assertCmdl('mpirun -npernode 5 -np 5 ./global_envelope_wrapper.py : -npernode 4 -np 4 ./global_envelope_wrapper.py : -npernode 8 -np 16 ./global_envelope_wrapper.py', args)
        binpaths = ['the_plam_driver.x'.format(pwd=self.t.sh.pwd()), ] * 1
        binpaths.extend(['{pwd:s}/fake0'.format(pwd=self.t.sh.pwd()), ] * 24)
        self.assertWrapper('MPIRANK', binpaths, binargs=['', ])
        _, args = algo._bootstrap_mpitool([bin0, ],
                                          dict(mpiopts=dict(envelope=[dict(nn=1, nnp=4, openmp=10),
                                                                      dict(nn=2, nnp=8, openmp=5)])))
        self.assertCmdl('mpirun -npernode 5 -np 5 ./global_envelope_wrapper.py : -npernode 8 -np 16 ./global_envelope_wrapper.py', args)
        binpaths = ['the_plam_driver.x'.format(pwd=self.t.sh.pwd()), ] * 1
        binpaths.extend(['{pwd:s}/fake0'.format(pwd=self.t.sh.pwd()), ] * 20)
        self.assertWrapper('MPIRANK', binpaths, binargs=['', ])
        # MPI partitioning from explicit mpiopts: no envelope provided, dedicated
        self.locenv.VORTEX_SUBMIT_NODES = 4
        self.locenv.VORTEX_SUBMIT_TASKS = 4
        self.locenv.VORTEX_SUBMIT_OPENMP = 10
        algo = self._fix_algo(fp.proxy.component(engine='test_parallel_palmed_engine', mpiname='mpirun',
                                                 openpalm_overcommit=False))
        _, args = algo._bootstrap_mpitool(bin0, dict(mpiopts=dict(nn=3, nnp=4, openmp=10)))
        self.assertCmdl('mpirun -npernode 1 -np 1 the_plam_driver.x : -npernode 4 -np 8 {pwd:s}/fake0 -joke yes', args)
        _, args = algo._bootstrap_mpitool(bin0, dict(mpiopts=dict(nn=3, nnp=4)))
        self.assertCmdl('mpirun -npernode 1 -np 1 the_plam_driver.x : -npernode 4 -np 8 {pwd:s}/fake0 -joke yes', args)
        _, args = algo._bootstrap_mpitool(bin0, dict())
        self.assertCmdl('mpirun -npernode 1 -np 1 the_plam_driver.x : -npernode 4 -np 12 {pwd:s}/fake0 -joke yes', args)
        _, args = algo._bootstrap_mpitool([bin0, bin1],
                                          dict(mpiopts=dict(nn=[3, 2], nnp=[4, 8], openmp=[10, 5])))
        self.assertCmdl('mpirun -npernode 1 -np 1 the_plam_driver.x : -npernode 4 -np 12 {pwd:s}/fake0 -joke yes : -npernode 8 -np 16 {pwd:s}/fake1 -joke yes', args)
        # MPI partitioning from explicit mpiopts: with envelope provided, dedicated
        algo = self._fix_algo(fp.proxy.component(engine='test_parallel_palmed_engine', mpiname='mpirun',
                                                 openpalm_overcommit=False))
        _, args = algo._bootstrap_mpitool([bin0, bin1],
                                          dict(mpiopts=dict(np=[11, 4], envelope='auto')))
        self.assertCmdl('mpirun -npernode 4 -np 16 ./global_envelope_wrapper.py', args)
        binpaths = ['the_plam_driver.x'.format(pwd=self.t.sh.pwd()), ] * 1
        binpaths.extend(['{pwd:s}/fake0'.format(pwd=self.t.sh.pwd()), ] * 11)
        binpaths.extend(['{pwd:s}/fake1'.format(pwd=self.t.sh.pwd()), ] * 4)
        self.assertWrapper('MPIRANK', binpaths, binargs=['', ])
        _, args = algo._bootstrap_mpitool([bin0, ],
                                          dict(mpiopts=dict(envelope=[dict(nn=2, nnp=4, openmp=10),
                                                                      dict(nn=2, nnp=8, openmp=5)])))
        self.assertCmdl('mpirun -npernode 4 -np 8 ./global_envelope_wrapper.py : -npernode 8 -np 16 ./global_envelope_wrapper.py', args)
        binpaths = ['the_plam_driver.x'.format(pwd=self.t.sh.pwd()), ] * 1
        binpaths.extend(['{pwd:s}/fake0'.format(pwd=self.t.sh.pwd()), ] * 23)
        self.assertWrapper('MPIRANK', binpaths, binargs=['', ])
        _, args = algo._bootstrap_mpitool([bin0, ],
                                          dict(mpiopts=dict(envelope=[dict(nn=1, nnp=4, openmp=10),
                                                                      dict(nn=2, nnp=8, openmp=5)])))
        self.assertCmdl('mpirun -npernode 4 -np 4 ./global_envelope_wrapper.py : -npernode 8 -np 16 ./global_envelope_wrapper.py', args)
        binpaths = ['the_plam_driver.x'.format(pwd=self.t.sh.pwd()), ] * 1
        binpaths.extend(['{pwd:s}/fake0'.format(pwd=self.t.sh.pwd()), ] * 19)
        self.assertWrapper('MPIRANK', binpaths, binargs=['', ])
        # Strange tweaking variables
        algo = self._fix_algo(fp.proxy.component(engine='test_parallel_palmed_engine', mpiname='mpirun',))
        self.locenv.VORTEX_OPENPALM_DRV_TASKS = 2
        _, args = algo._bootstrap_mpitool(bin0, dict(mpiopts=dict(nn=3, nnp=4, openmp=10)))
        self.assertCmdl('mpirun -npernode 6 -np 6 ./global_envelope_wrapper.py : -npernode 4 -np 8 ./global_envelope_wrapper.py', args)
        binpaths = ['the_plam_driver.x'.format(pwd=self.t.sh.pwd()), ] * 2
        binpaths.extend(['{pwd:s}/fake0'.format(pwd=self.t.sh.pwd()), ] * 12)
        self.assertWrapper('MPIRANK', binpaths, binargs=['', ''])
        _, args = algo._bootstrap_mpitool(bin0, dict(mpiopts=dict(nn=3, nnp=4, openmp=10), palmdrv_nnp=3))
        self.assertCmdl('mpirun -npernode 7 -np 7 ./global_envelope_wrapper.py : -npernode 4 -np 8 ./global_envelope_wrapper.py', args)
        binpaths = ['the_plam_driver.x'.format(pwd=self.t.sh.pwd()), ] * 3
        binpaths.extend(['{pwd:s}/fake0'.format(pwd=self.t.sh.pwd()), ] * 12)
        self.assertWrapper('MPIRANK', binpaths, binargs=['', '', ''])
        _, args = algo._bootstrap_mpitool([bin0, bin1],
                                          dict(mpiopts=dict(nn=[3, 2], nnp=[4, 8], openmp=[10, 5])))
        self.assertCmdl('mpirun -npernode 6 -np 6 ./global_envelope_wrapper.py : -npernode 4 -np 8 ./global_envelope_wrapper.py : -npernode 8 -np 16 ./global_envelope_wrapper.py', args)
        binpaths = ['the_plam_driver.x'.format(pwd=self.t.sh.pwd()), ] * 2
        binpaths.extend(['{pwd:s}/fake0'.format(pwd=self.t.sh.pwd()), ] * 12)
        binpaths.extend(['{pwd:s}/fake1'.format(pwd=self.t.sh.pwd()), ] * 16)
        self.assertWrapper('MPIRANK', binpaths, binargs=['', '', ])


if __name__ == "__main__":
    unittest.main(verbosity=2)
