import contextlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from footprints import proxy as fpx

import sandbox
import vortex
from vortex.tools.net import uriparse

assert sandbox
assert vortex

JOBSDIR = os.path.abspath(os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
    'examples', 'jobs', 'DEMO'
))


class _JobIsolationHelper:

    def __init__(self, tmpdir):
        self._tmpdir = tmpdir
        self._cachestore = None
        self._uri_radix = None

    @property
    def tmpdir(self):
        return self._tmpdir

    @property
    def cachestore(self):
        if self._cachestore is None:
            self._cachestore = fpx.store(scheme='vortex',
                                         netloc='vortex-demo.cache.fr',
                                         rootdir=os.path.join(self.tmpdir, 'democache'))
        return self._cachestore

    def cacheuri(self, path):
        if self._uri_radix is None:
            my_app = os.path.dirname(self.tmpdir)
            vconf = os.path.basename(my_app)
            vapp = os.path.basename(os.path.dirname(my_app))
            self._uri_radix = ('vortex://vortex-demo.cache.fr/{:s}/{:s}/'
                               .format(vapp, vconf))
        return uriparse(self._uri_radix + path)

    def _run_stuff(self, cmd):
        env_copy = os.environ.copy()
        env_copy['VORTEX_DEMO_CACHE_PARENTDIR'] = self.tmpdir

        try:
            subprocess.check_output(cmd, stderr=subprocess.STDOUT, env=env_copy)
        except subprocess.CalledProcessError as e:
            print('Captured stdout/stderr:\n' +
                  e.output.decode('utf8', errors='ignore') +
                  '\n')
            print('EXECUTION ERROR. rc={:d} (cmd: {:s})'.format(e.returncode,
                                                                ' '.join(cmd)))
            raise

    def run_mkjob(self, args):
        cmd = [sys.executable,
               os.path.join('..', 'vortex', 'bin', 'mkjob.py'),
               '-j'] + args
        self._run_stuff(cmd)

    def run_jobscript(self, jobname):
        self._run_stuff([sys.executable, jobname])


class TestJobExamples(unittest.TestCase):

    _DEBUG_MODE = False

    def setUp(self):
        self._cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self._cwd)

    @contextlib.contextmanager
    def isolate_job(self, my_appdir):
        os.chdir(my_appdir)
        tmpdir = tempfile.mkdtemp(prefix='jobs_', dir='.')
        try:
            helper = _JobIsolationHelper(os.path.abspath(tmpdir))
            os.chdir(tmpdir)
            yield helper
        finally:
            os.chdir(my_appdir)
            # Empty the abort dir
            abortdir = os.path.join('run', 'abort')
            if os.path.exists(abortdir):
                todo = os.listdir(abortdir)
                for what in todo:
                    if os.path.isdir(os.path.join(abortdir, what)):
                        if self._DEBUG_MODE:
                            print('[{:s}] Existing abort directory: {:s}'
                                  .format(my_appdir, os.path.join(abortdir, what)))
                        else:
                            shutil.rmtree(os.path.join(abortdir, what))
            if self._DEBUG_MODE:
                print('[{:s}] The tmpdir is: {:s}'.format(my_appdir, tmpdir))
            else:
                shutil.rmtree(tmpdir)

    def assertInCache(self, i_helper, path):
        self.assertTrue(i_helper.cachestore.check(i_helper.cacheuri(path), dict()))

    def assertNotInCache(self, i_helper, path):
        self.assertFalse(i_helper.cachestore.check(i_helper.cacheuri(path), dict()))

    def _test_jobs_stdpost_examples_assert_date(self, i_helper, sdate):
        for what in ('mb000/forecast/grid.arpege-forecast.glob05+0000:00.md5.ascii',
                     'mb000/forecast/grid.arpege-forecast.glob05+0003:00.md5.ascii',
                     'mb000/forecast/grid.arpege-forecast.glob05+0006:00.md5.ascii',
                     'mb000/forecast/grid.arpege-forecast.glob05+0009:00.md5.ascii',
                     'mb000/forecast/grid.arpege-forecast.glob05+0012:00.md5.ascii',
                     'mb001/forecast/grid.arpege-forecast.glob05+0000:00.md5.ascii',
                     'mb001/forecast/grid.arpege-forecast.glob05+0003:00.md5.ascii',
                     'mb001/forecast/grid.arpege-forecast.glob05+0006:00.md5.ascii',
                     'mb001/forecast/grid.arpege-forecast.glob05+0009:00.md5.ascii',
                     'mb001/forecast/grid.arpege-forecast.glob05+0012:00.md5.ascii',
                     'mb002/forecast/grid.arpege-forecast.glob05+0000:00.md5.ascii',
                     'mb002/forecast/grid.arpege-forecast.glob05+0003:00.md5.ascii',
                     'mb002/forecast/grid.arpege-forecast.glob05+0006:00.md5.ascii',
                     'mb002/forecast/grid.arpege-forecast.glob05+0009:00.md5.ascii',
                     'mb002/forecast/grid.arpege-forecast.glob05+0012:00.md5.ascii',
                     'forecast/gribinfos.arpege.json'):
            self.assertInCache(i_helper, 'DEMO/{:s}/{:s}'.format(sdate, what))

    def test_jobs_stdpost_examples(self):
        my_appdir = os.path.join(JOBSDIR, 'arpege', 'stdpost')
        with self.isolate_job(my_appdir) as i_helper:
            i_helper.run_mkjob(['name=single_b_job', 'task=single_b_stdpost',
                                'rundate=2020102918', 'profile=void'])
            i_helper.run_jobscript('./single_b_job.py')
            self._test_jobs_stdpost_examples_assert_date(i_helper, '20201029T1800P')
        with self.isolate_job(my_appdir) as i_helper:
            i_helper.run_mkjob(['name=single_bp_multidate_job',
                                'task=single_bp_multidate_stdpost',
                                'rundates=2020102912-2020102918-PT6H',
                                'profile=void'])
            i_helper.run_jobscript('./single_bp_multidate_job.py')
            self._test_jobs_stdpost_examples_assert_date(i_helper, '20201029T1200P')
            self._test_jobs_stdpost_examples_assert_date(i_helper, '20201029T1800P')
        with self.isolate_job(my_appdir) as i_helper:
            i_helper.run_mkjob(['name=single_s_para_job', 'task=single_s_stdpost',
                                'rundate=2020102918', 'profile=void'])
            i_helper.run_jobscript('./single_s_para_job.py')
            self._test_jobs_stdpost_examples_assert_date(i_helper, '20201029T1800P')

    def test_jobs_play_examples(self):
        my_appdir = os.path.join(JOBSDIR, 'sandbox', 'play')
        with self.isolate_job(my_appdir) as i_helper:
            i_helper.run_mkjob(['name=on_error_feature_job', 'task=on_error_feature',
                                'rundate=2020102918'])
            with self.assertRaises(subprocess.CalledProcessError):
                i_helper.run_jobscript('./on_error_feature_job.py')
            self.assertNotInCache(i_helper, 'DEMO/20201029T1800P/on_error1_f1/beacon.arpege.json')
            self.assertInCache(i_helper, 'DEMO/20201029T1800P/on_error2_f1/beacon.arpege.json')
            self.assertNotInCache(i_helper, 'DEMO/20201029T1800P/on_error1_f2/beacon.arpege.json')
            self.assertNotInCache(i_helper, 'DEMO/20201029T1800P/on_error2_f2/beacon.arpege.json')
            self.assertInCache(i_helper, 'DEMO/20201029T1800P/on_error_t3/beacon.arpege.json')
            self.assertInCache(i_helper, 'DEMO/20201029T1800P/on_error_t4/beacon.arpege.json')
        with self.isolate_job(my_appdir) as i_helper:
            i_helper.run_mkjob(['name=loop_family_job1', 'task=loop_family1',
                                'rundates=2020102918-2020103118-PT24H',
                                'members=rangex(1-2)'])
            i_helper.run_jobscript('./loop_family_job1.py')
            for date in ('20201029T1800P', '20201030T1800P'):
                for member in range(1, 3):
                    self.assertInCache(i_helper,
                                       'DEMO/{:s}/mb{:03d}/lfamily1_beacon/beacon.arpege.json'
                                       .format(date, member))
            # Be sure that loopneednext works...
            for date in ('20201031T1800P', ):
                for member in range(1, 3):
                    self.assertNotInCache(i_helper,
                                          'DEMO/{:s}/mb{:03d}/lfamily1_beacon/beacon.arpege.json'
                                          .format(date, member))
        with self.isolate_job(my_appdir) as i_helper:
            i_helper.run_mkjob(['name=active_cb_job', 'task=active_cb',
                                'rundate=2020102918'])
            i_helper.run_jobscript('./active_cb_job.py')
            for member in range(1, 5):
                self.assertInCache(i_helper,
                                   'DEMO/20201029T1800P/mb{:03d}/generic_beacon/beacon.arpege.json'
                                   .format(member))
            for member in (1, 3, 5):
                self.assertNotInCache(i_helper,
                                      'DEMO/20201029T1800P/mb{:03d}/even_beacon/beacon.arpege.json'
                                      .format(member))
            for member in (2, 4):
                self.assertInCache(i_helper,
                                   'DEMO/20201029T1800P/mb{:03d}/even_beacon/beacon.arpege.json'
                                   .format(member))
        with self.isolate_job(my_appdir) as i_helper:
            i_helper.run_mkjob(['name=paralleljobs_basic_job', 'task=paralleljobs_basic',
                                'rundate=2020102918'])
            i_helper.run_jobscript('./paralleljobs_basic_job.py')
            for batch in range(0, 4):
                for member in range(1, 5):
                    self.assertInCache(i_helper,
                                       'DEMO/20201029T1800P/mb{:03d}/pjobs_t{:d}/beacon.arpege.json'
                                       .format(member + batch * 4, batch + 1))
        with self.isolate_job(my_appdir) as i_helper:
            i_helper.run_mkjob(['name=paralleljobs_workshares_job', 'task=paralleljobs_workshares',
                                'rundate=2020102918', 'allmembers=rangex(1-4)'])
            i_helper.run_jobscript('./paralleljobs_workshares_job.py')
            for member in range(1, 5):
                self.assertInCache(i_helper,
                                   'DEMO/20201029T1800P/mb{:03d}/pjobs_t/beacon.arpege.json'
                                   .format(member))
            self.assertNotInCache(i_helper,
                                  'DEMO/20201029T1800P/mb{:03d}/pjobs_t/beacon.arpege.json'
                                  .format(5))


if __name__ == "__main__":
    unittest.main()
