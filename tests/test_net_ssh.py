import os
import platform
import stat
import subprocess
import tempfile
import unittest
import uuid

from bronx.fancies import loggers
from bronx.system import interrupt

import vortex
from vortex.tools.net import Ssh, AssistedSsh

test_host = 'localhost'
fake_host = 'this-hostname-should-not-exist-in-your-network'

DATAPATHTEST = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                            'data')

tloglevel = 9999  # Extremely quiet...


def check_localssh():
    """Check if it's possible to connect to SSH using a key based authentication."""
    try:
        subprocess.check_output(['ssh', '-x',
                                 '-oNumberOfPasswordPrompts=0',
                                 '-oConnectTimeout=1',
                                 '-oNoHostAuthenticationForLocalhost=true',
                                 test_host, 'true'], stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError:
        return False
    else:
        return True


LOCALSSH_OK = check_localssh()


@unittest.skipUnless(LOCALSSH_OK,
                     'It is not possible to connect to {} using SSH.'.format(test_host))
@loggers.unittestGlobalLevel(tloglevel)
class _SshTestBase(unittest.TestCase):

    def setUp(self):
        # Generate a temporary directory
        self.t = vortex.sessions.current()
        self.sh = self.t.system()
        self.user = self.t.glove.user
        self.tmpdir = tempfile.mkdtemp(suffix='_test_ssh')
        self.oldpwd = self.sh.pwd()
        self.sh.cd(self.tmpdir)
        self.shandler = interrupt.SignalInterruptHandler(emitlogs=False)
        self.shandler.activate()
        # and temporary files
        self.ref1 = self.sh.path.join(self.tmpdir, 'refdata1')
        self.ref2 = self.sh.path.join(self.tmpdir, 'refdata2')
        self.ref1_ct = uuid.uuid4().bytes
        self.ref2_ct = uuid.uuid4().bytes
        with open(self.ref1, 'wb') as fh1:
            fh1.write(self.ref1_ct)
        with open(self.ref2, 'wb') as fh2:
            fh2.write(self.ref2_ct)

    def _check_against(self, ref, newfile):
        with open(newfile, 'rb') as fhN:
            newdata = fhN.read()
        self.assertEqual(ref, newdata)

    def assertIsCopy1(self, newfile):
        self._check_against(self.ref1_ct, newfile)

    def assertIsCopy2(self, newfile):
        self._check_against(self.ref2_ct, newfile)

    def tearDown(self):
        self.sh.cd(self.oldpwd)
        self.sh.remove(self.tmpdir)
        self.shandler.deactivate()


class TestSsh(_SshTestBase):

    _SSH_CLASS = Ssh
    _SSH_EXTRA_ARGS = dict()

    def setUp(self):
        super().setUp()
        self.ssh = self._SSH_CLASS(self.sh, test_host, logname=self.user,
                                   **self._SSH_EXTRA_ARGS)

    def test_ssh_commands(self):
        self.assertEqual(self.ssh.remote, '{:s}@{:s}'.format(self.user, test_host))
        self.assertTrue(self.ssh.check_ok())
        self.assertFalse(self.ssh.execute(False))
        self.assertFalse(self.ssh.execute('false'))
        self.assertEqual(self.ssh.execute('hostname'), [self.sh.hostname, ])
        self.assertTrue(self.ssh.cocoon(''))
        cocoonbase = self.sh.path.join(self.tmpdir, 'cocoon')
        cocoonfile = self.sh.path.join(cocoonbase, 'testsubdir', 'truc')
        self.assertTrue(self.ssh.cocoon(cocoonfile))
        self.assertTrue(self.sh.path.isdir(self.sh.path.dirname(cocoonfile)))
        self.assertTrue(self.ssh.cocoon(cocoonfile))
        self.assertTrue(self.ssh.remove(cocoonfile))
        self.assertTrue(self.ssh.remove(cocoonbase))
        self.assertFalse(self.sh.path.isdir(cocoonbase))

    def test_scpput(self):
        # copy to a subdir
        dest_cp1 = self.sh.path.join(self.tmpdir, 'subcp1')
        self.assertTrue(self.ssh.scpput(self.ref1, dest_cp1 + '/'))
        self.assertIsCopy1(self.sh.path.join(dest_cp1, self.sh.path.basename(self.ref1)))

        # same with a relative path for the source
        dest_cp1bis = self.sh.path.join(self.tmpdir, 'subrel1')
        self.assertTrue(self.ssh.scpput(self.sh.path.basename(self.ref1), dest_cp1bis + '/'))
        self.assertIsCopy1(self.sh.path.join(dest_cp1bis, self.sh.path.basename(self.ref1)))

        # copy a file to a file
        dest_cp2 = self.sh.path.join(self.tmpdir, 'toto')
        self.assertTrue(self.ssh.scpput(self.ref1, dest_cp2))
        self.assertIsCopy1(dest_cp2)

        # Forbidden
        with self.assertRaises(ValueError):
            self.ssh.scpput(self.ref1, self.sh.path.join(self.tmpdir, '..', 'failer'))

        # Directory copy
        dest_cp3 = self.sh.path.join(self.tmpdir, 'subcp3')
        self.assertTrue(self.ssh.scpput(dest_cp1, dest_cp3))
        self.assertIsCopy1(self.sh.path.join(dest_cp3, self.sh.path.basename(self.ref1)))

        # same to a subdirectory
        dest_cp3bis = self.sh.path.join(self.tmpdir, 'subcp3/')
        self.assertTrue(self.ssh.scpput(dest_cp1, dest_cp3bis))
        self.assertIsCopy1(self.sh.path.join(dest_cp3bis, self.sh.path.basename(self.ref1)))

        # Streaming !
        with open(self.ref2, 'rb') as fh2:
            self.assertTrue(self.ssh.scpput_stream(fh2, dest_cp2, permissions=0o400))
        self.assertIsCopy2(dest_cp2)
        self.assertEqual(stat.S_IMODE(self.sh.stat(dest_cp2).st_mode), 0o400)

        # Nasty characters
        dest_cp5 = self.sh.path.join(self.tmpdir, 'toto+titi')
        self.assertTrue(self.ssh.scpput(self.ref1, dest_cp5))
        self.assertIsCopy1(dest_cp5)

    def test_scpget(self):
        dest_cp1 = self.sh.path.join(self.tmpdir, 'subcp1')
        self.assertTrue(self.ssh.scpget(self.ref1, dest_cp1 + '/'))
        self.assertIsCopy1(self.sh.path.join(dest_cp1, self.sh.path.basename(self.ref1)))
        dest_cp2 = self.sh.path.join(self.tmpdir, 'toto')
        self.assertTrue(self.ssh.scpget(self.ref1, dest_cp2))
        self.assertIsCopy1(dest_cp2)
        dest_cp3 = self.sh.path.join(self.tmpdir, 'subcp3')
        self.assertFalse(self.ssh.scpget(dest_cp1, dest_cp3))
        self.assertTrue(self.ssh.scpget(dest_cp1, dest_cp3, isadir=True))
        self.assertIsCopy1(self.sh.path.join(dest_cp3, self.sh.path.basename(self.ref1)))
        # Streaming !
        dest_cp2bis = self.sh.path.join(self.tmpdir, 'titi')
        with open(dest_cp2bis, 'wb') as fh2:
            self.assertTrue(self.ssh.scpget_stream(dest_cp2, fh2))
        self.assertIsCopy1(dest_cp2bis)
        # Nasty characters
        dest_cp4 = self.sh.path.join(self.tmpdir, 'large toto')
        self.assertTrue(self.ssh.scpget(self.ref1, dest_cp4))
        self.assertIsCopy1(dest_cp4)
        # Failing on mageia 7 (openssh v8.0p1)
        # self.assertTrue(self.ssh.scpget(dest_cp4, dest_cp4 + '.bis'))
        # self.assertIsCopy1(dest_cp4 + '.bis')

    @unittest.skipUnless(platform.system() == 'Linux', 'Linux system check')
    def test_tunnel(self):
        # Obviously, port #22 is already in use !
        self.assertFalse(self.ssh.tunnel(test_host, 22, 22, maxwait=1., checkdelay=0.1))
        # Doing a tunnel to myself... pretty useless but it's a test
        tunnel = self.ssh.tunnel(test_host, 22, checkdelay=0.1)
        self.assertTrue(tunnel.opened)
        self.assertEqual(tunnel.finaldestination, test_host)
        self.assertEqual(tunnel.finalport, 22)
        with tunnel:
            # Create a new SSH instance that goes through the tunnel
            sshbis = self._SSH_CLASS(self.sh, test_host, logname=self.user,
                                     sshopts='-p {:d}'.format(tunnel.entranceport),
                                     **self._SSH_EXTRA_ARGS)
            self.assertTrue(sshbis.check_ok())
            self.assertFalse(sshbis.execute('false'))
        self.assertFalse(tunnel.opened)


# The AssistedSsh class should be compatible with the Ssh one...
class TestAssistedSshCompatibility(TestSsh):

    _SSH_CLASS = AssistedSsh
    _SSH_EXTRA_ARGS = dict(triesdelay=0.1)


class TestAssistedSsh(_SshTestBase):

    def setUp(self):
        super().setUp()
        self.testconf = os.path.join(DATAPATHTEST, 'target-test.ini')
        self.tg = self.sh.target(hostname='unittestlogin001',
                                 inetname='unittest',
                                 sysname='Linux',
                                 inifile=self.testconf)

    def ssh(self, *kargs, **kwargs):
        kwargs.setdefault('triesdelay', 0.1)
        return AssistedSsh(self.sh, *kargs, **kwargs)

    def test_ssh(self):
        # Host testing...
        ssh = self.ssh([fake_host, test_host], logname=self.user, permut=False)
        self.assertListEqual(ssh.targets,
                             [self.user + '@' + x for x in (fake_host, test_host)])
        self.assertEqual(ssh.remote, self.user + '@' + test_host)
        ssh = self.ssh([fake_host, test_host])
        self.assertEqual(ssh.remote, test_host)
        ssh = self.ssh([fake_host, test_host], permut=False, mandatory_hostcheck=False)
        self.assertEqual(ssh.remote, fake_host)
        self.assertEqual(ssh.remote, test_host)
        ssh = self.ssh(fake_host)
        self.assertEqual(ssh.remote, fake_host)
        # Failing and retrying ?
        ssh = self.ssh(fake_host, fatal=True, maxtries=2)
        with self.assertRaises(RuntimeError):
            ssh.check_ok()
        self.assertEqual(ssh.retries, 2)
        # virtualnodes ?
        with self.assertRaises(ValueError):
            self.ssh([fake_host, test_host], virtualnode=True)
        ssh = self.ssh('unittest', virtualnode=True, permut=False)
        self.assertListEqual(ssh.targets, [test_host, fake_host])
        # This should ensure that the metaclass works...
        ssh = self.ssh(fake_host, fatal=True, maxtries=2)
        with self.assertRaises(RuntimeError):
            ssh.check_ok()
        self.assertEqual(ssh.retries, 2)
        ssh = self.ssh(test_host, fatal=True, maxtries=2)
        with self.assertRaises(RuntimeError):
            ssh.execute('false')
        self.assertEqual(ssh.retries, 2)
        # Virtual nodes proper selection
        ssh = self.ssh([fake_host, test_host], logname=self.user, permut=False,
                       mandatory_hostcheck=False)
        self.assertTrue(ssh.check_ok())
        self.assertEqual(ssh.retries, 2)


if __name__ == '__main__':
    unittest.main()
