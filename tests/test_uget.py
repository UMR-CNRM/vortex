import contextlib
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import unittest


vortexbase = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


class UgetTestIsolationHelper:

    def __init__(self, tmpdir, debug=False):
        self._tmpdir = tmpdir
        self._debug = debug

    @property
    def tmpdir(self):
        return self._tmpdir

    def _run_stuff(self, cmd):
        env_copy = os.environ.copy()
        env_copy['VORTEX_DEMO_CACHE_PARENTDIR'] = self.tmpdir
        env_copy['VORTEX_DEMO_ARCHIVE_PARENTDIR'] = self.tmpdir
        env_copy['VORTEX_UGET_TESTMODE'] = '1'
        env_copy['HOME'] = self.tmpdir
        try:
            output = subprocess.check_output(cmd, stderr=subprocess.STDOUT, env=env_copy)
        except subprocess.CalledProcessError as e:
            print('Captured stdout/stderr:\n' +
                  e.output.decode('utf8', errors='ignore') +
                  '\n')
            print('EXECUTION ERROR. rc={:d} (cmd: {:s})'.format(e.returncode,
                                                                ' '.join(cmd)))
            raise
        else:
            output = output.decode('utf8', errors='ignore')
            if self._debug:
                print('Captured stdout/stderr:\n' + output + '\n')
        return output

    def run_uget(self, args):
        args = shlex.split(args)
        cmd = [sys.executable, os.path.join(vortexbase, 'bin', 'uget.py')] + args
        return self._run_stuff(cmd)


class TestUget(unittest.TestCase):

    _DEBUG_MODE = False

    @contextlib.contextmanager
    def isolate_uget(self):
        currentdir = os.getcwd()
        tmpdir = tempfile.mkdtemp(prefix='uget_test_')
        try:
            helper = UgetTestIsolationHelper(os.path.abspath(tmpdir), debug=self._DEBUG_MODE)
            os.chdir(tmpdir)
            yield helper
        finally:
            os.chdir(currentdir)
            if self._DEBUG_MODE:
                print('[Uget Test] The tmpdir is: {:s}'.format(tmpdir))
            else:
                shutil.rmtree(tmpdir)

    @property
    def envpath(self):
        return os.path.join('.vortexrc', 'hack', 'uget', 'demo', 'env')

    @property
    def datapath(self):
        return os.path.join('.vortexrc', 'hack', 'uget', 'demo', 'data')

    def assertExists(self, u_helper, *paths):
        looking_for = os.path.join(u_helper.tmpdir, *paths)
        self.assertTrue(os.path.exists(looking_for),
                        msg="Looking for: {:s}".format(looking_for))

    def assertNotExists(self, u_helper, *paths):
        looking_for = os.path.join(u_helper.tmpdir, *paths)
        self.assertFalse(os.path.exists(looking_for),
                         msg="Looking for: {:s}".format(looking_for))

    def _assert_data(self, where, dname, dfinaltext=None):
        self.assertTrue(os.path.exists(where),
                        msg="Looking for: {:s}".format(where))
        dfinaltext = dname if dfinaltext is None else dfinaltext
        with open(where) as fh_d:
            self.assertEqual("Fake data: {:s}".format(dfinaltext),
                             fh_d.read())

    def assertHackData(self, u_helper, dname, dfinaltext=None):
        self._assert_data(os.path.join(u_helper.tmpdir, self.datapath, dname),
                          dname,
                          dfinaltext)

    def assertArchiveData(self, u_helper, sdir, dname, dfinaltext=None):
        self._assert_data(os.path.join(u_helper.tmpdir, 'demoarchive', 'uget', 'data', sdir, dname),
                          dname,
                          dfinaltext)

    def assertArchiveEnv(self, u_helper, sdir, e_name):
        self.assertExists(u_helper, 'demoarchive', 'uget', 'env', sdir, e_name)

    def test_uget(self):
        with self.isolate_uget() as u_helper:
            # Create directories
            u_helper.run_uget('bootstrap_hack demo')
            self.assertExists(u_helper, self.envpath)
            self.assertExists(u_helper, self.datapath)
            # Does not exists
            output = u_helper.run_uget('check data fake@demo')
            self.assertRegex(output, r'Hack\s*:\s*MISSING')
            self.assertRegex(output, r'Archive\s*:\s*MISSING')
            # Fake data
            for dname in ('data1.01', 'data2.01'):
                with open(os.path.join(self.datapath, dname), 'w') as fh_d:
                    fh_d.write("Fake data: {:s}".format(dname))
            output = u_helper.run_uget('check data data1.01@demo')
            self.assertRegex(output, r'Hack\s*:\s*Ok')
            self.assertRegex(output, r'Archive\s*:\s*MISSING')
            # Put data1
            u_helper.run_uget('push data data1.01@demo')
            self.assertArchiveData(u_helper, '8', 'data1.01')
            output = u_helper.run_uget('check data data1.01@demo')
            self.assertRegex(output, r'Hack\s*:\s*Ok')
            self.assertRegex(output, r'Archive\s*:\s*Ok')
            # Fake env
            for dname in ('env1.01', ):
                with open(os.path.join(self.envpath, dname), 'w') as fh_e:
                    fh_e.write("\n".join(["FIRSTKEY=uget:data1.01@demo",
                                          "SECONDKEY=uget:data2.01@demo"]))
            # Put env1
            u_helper.run_uget('push env env1.01@demo')
            self.assertArchiveEnv(u_helper, '6', 'env1.01')
            self.assertArchiveData(u_helper, 'f', 'data2.01')
            # Clean
            u_helper.run_uget('clean_hack')
            self.assertNotExists(u_helper, self.datapath, 'data1.01')
            self.assertNotExists(u_helper, self.datapath, 'data2.01')
            self.assertNotExists(u_helper, self.envpath, 'env1.01')
            # Pull ?
            u_helper.run_uget('set location demo')
            output = u_helper.run_uget('pull env env1.01')
            self.assertRegex(output, r'FIRSTKEY\s*=\s*uget:data1\.01@demo')
            self.assertRegex(output, r'SECONDKEY\s*=\s*uget:data2\.01@demo')
            u_helper.run_uget('pull data data2.01')
            with open('data2.01') as fh_d:
                self.assertEqual('Fake data: data2.01', fh_d.read())
            os.unlink('data2.01')
            # Hack
            u_helper.run_uget('hack env env1.01 into env1.02')
            u_helper.run_uget('hack data data1.01 into data3.01')
            with open(os.path.join(self.envpath, 'env1.02'), 'a') as fh_e:
                fh_e.write("\nTHIRDKEY=uget:data3.01@demo")
            u_helper.run_uget('push env env1.02@demo')
            u_helper.run_uget('clean_hack')
            self.assertNotExists(u_helper, self.datapath, 'data3.01')
            self.assertNotExists(u_helper, self.envpath, 'env1.02')
            self.assertArchiveEnv(u_helper, '6', 'env1.02')
            self.assertArchiveData(u_helper, '7', 'data3.01', 'data1.01')
            # Diff
            output = u_helper.run_uget('diff env env1.02 wrt parent')
            self.assertRegex(
                output,
                r'CREATED ENTRIES:[\s\n]+THIRDKEY\s*=\s*uget:data3.01@demo'
            )
            # List
            output = u_helper.run_uget(r"list env matching 'env\d+\.02'")
            self.assertRegex(output, r'env1\.02')


if __name__ == "__main__":
    unittest.main()
