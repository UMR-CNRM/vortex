#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import os
import shutil
import subprocess
import sys
import tempfile
import unittest


JOBSDIR = os.path.abspath(os.path.join(
    os.path.dirname(os.path.dirname(os.path.realpath(__file__))),
    'examples', 'jobs', 'DEMO'
))


class TestJobExamples(unittest.TestCase):

    def setUp(self):
        self._cwd = os.getcwd()

    def tearDown(self):
        os.chdir(self._cwd)

    def _run_stuff(self, cmd):
        try:
            subprocess.check_output(cmd, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            print('Captured stdout/stderr:\n' +
                  e.output.decode('utf8', errors='ignore') +
                  '\n')
            print('EXECUTION ERROR. rc={:d} (cmd: {:s})'.format(e.returncode,
                                                                ' '.join(cmd)))
            raise

    def _run_mkjob(self, args):
        cmd = [sys.executable,
               os.path.join('..', 'vortex', 'bin', 'mkjob.py'),
               '-j', 'profile=void'] + args
        self._run_stuff(cmd)

    def _run_jobscript(self, jobname):
        self._run_stuff([sys.executable, jobname])

    def test_jobs_stdpost_examples(self):
        my_appdir = os.path.join(JOBSDIR, 'arpege', 'stdpost')
        os.chdir(os.path.join(JOBSDIR, 'arpege', 'stdpost'))
        tmpdir = tempfile.mkdtemp(prefix='jobs_', dir='.')
        try:
            os.chdir(tmpdir)
            self._run_mkjob(['name=single_b_job', 'task=single_b_stdpost',
                             'rundate=2020102918'])
            self._run_jobscript('./single_b_job.py')
            self._run_mkjob(['name=single_bp_multidate_job',
                             'task=single_bp_multidate_stdpost',
                             'rundates=2020102912-2020102918-PT6H'])
            self._run_jobscript('./single_bp_multidate_job.py')
            self._run_mkjob(['name=single_s_para_job', 'task=single_s_stdpost',
                             'rundate=2020102918'])
            self._run_jobscript('./single_s_para_job.py')
        finally:
            os.chdir(my_appdir)
            # Empty the abort dir
            abortdir = os.path.join('run', 'abort')
            if os.path.exists(abortdir):
                todo = os.listdir(abortdir)
                for what in todo:
                    if os.path.isdir(os.path.join(abortdir, what)):
                        shutil.rmtree(os.path.join(abortdir, what))
            shutil.rmtree(tmpdir)


if __name__ == "__main__":
    unittest.main()
