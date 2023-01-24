import tempfile
from unittest import TestCase, main

from bronx.fancies import loggers

import vortex
from vortex import sessions

tloglevel = 'critical'


@loggers.unittestGlobalLevel(tloglevel)
class UtSession(TestCase):

    @staticmethod
    def _givetag(guess='faketest-1'):
        """Return the first available sessions name."""
        i = int(guess[8:]) + 1
        while 'faketest{:d}'.format(i) in sessions.keys():
            i += 1
        return 'faketest{:d}'.format(i)

    def setUp(self):
        self.rootsession = sessions.current()
        self.sh = self.rootsession.system()
        self.tmpdir = self.sh.path.realpath(tempfile.mkdtemp(prefix='test_sessions_stuff_'))
        self.sh.cd(self.sh.path.dirname(self.tmpdir))
        self.oldpwd = self.sh.pwd()
        # Always create two new sessions for this test...
        self.tag0 = self._givetag()
        self.tag1 = self._givetag(self.tag0)

    def tearDown(self):
        self.rootsession.activate()
        self.sh.cd(self.oldpwd)
        self.sh.remove(self.tmpdir)

    def test_session_create(self):
        topenv = vortex.rootenv
        curglove = self.rootsession.glove
        # Create your main test session
        cursession = sessions.get(tag=self.tag0,
                                  topenv=topenv,
                                  glove=curglove)
        cursession.activate()
        curenv = cursession.context.env
        # Create the new session (that remains unactive)
        newsession = sessions.get(tag=self.tag1,
                                  topenv=topenv,
                                  glove=curglove)
        self.assertTrue(cursession.active)
        self.assertFalse(newsession.active)
        self.assertEqual(newsession.context.path, '/{0:s}/{0:s}'.format(self.tag1))
        # The new context is not yet active
        self.assertTrue(cursession.context.active)
        self.assertFalse(newsession.context.active)
        # Check that environment are different but derive from the topenv
        self.assertIsNot(cursession.context.env, newsession.context.env)
        self.assertIs(cursession.context.env.osstack()[-1], topenv)
        self.assertIs(newsession.context.env.osstack()[-1], topenv)
        self.assertTrue(cursession.context.env.active())
        nenv = newsession.context.env
        self.assertFalse(newsession.context.env.active())
        # It's not possible to switch to the new context before switching to the
        # new session
        with self.assertRaises(RuntimeError):
            newsession.context.activate()
        self.assertTrue(cursession.active)
        # It's not possible to switch to an Environment that does not belongs
        # to the current Context
        with self.assertRaises(RuntimeError):
            nenv.active(True)
        self.assertTrue(cursession.context.env.active())
        # The same goes for Cocooning
        with self.assertRaises(RuntimeError):
            newsession.context.cocoon()
        # Now activate the new one !
        newsession.activate()
        self.assertFalse(cursession.active)
        self.assertTrue(newsession.active)
        # The context has switched (as for the Environment)
        self.assertFalse(cursession.context.active)
        self.assertTrue(newsession.context.active)
        self.assertFalse(curenv.active())
        self.assertTrue(newsession.context.env.active())
        # Now we can create a subcontext...
        nsubctx = newsession.context.newcontext('scrontch', focus=True)
        # It's not possible to create two contexts with the same tag
        with self.assertRaises(RuntimeError):
            newsession.context.newcontext('scrontch')
        # Check that the active session is the one we are expecting
        self.assertEqual(newsession.context.path, '/{0:s}/{0:s}/scrontch'.format(self.tag1))
        nsubenv = newsession.context.env
        self.assertIsNot(newsession.context.env, nenv)
        # It derives from curenv (that was the previous active env)
        self.assertIs(newsession.context.env.osstack()[-1], nenv)
        # Coocooning
        newsession.rundir = self.tmpdir
        newsession.context.cocoon()
        self.assertEqual(newsession.context.rundir,
                         self.sh.path.join(self.tmpdir, '{:s}/scrontch'.format(self.tag1)))
        newsession.system().mkdir('toto')
        newsession.system().cd('toto')
        # Switch back to the original session
        cursession.activate()
        self.assertTrue(cursession.active)
        self.assertFalse(newsession.active)
        self.assertTrue(cursession.context.active)
        self.assertFalse(newsession.context.active)
        self.assertTrue(cursession.context.env.active())
        self.assertTrue(curenv.active())
        self.assertFalse(newsession.context.env.active())
        # Change of directory (just to mess things up)
        self.sh.cd(self.oldpwd)
        # Switch back to the newsession... everything should be as they were before...
        newsession.activate()
        self.assertFalse(cursession.active)
        self.assertTrue(newsession.active)
        # The context has switch (as for the Environment)
        self.assertFalse(cursession.context.active)
        self.assertIs(newsession.context, nsubctx)
        self.assertTrue(newsession.context.active)
        self.assertFalse(curenv.active())
        self.assertIs(newsession.context.env, nsubenv)
        self.assertTrue(newsession.context.env.active())
        # The working directory was restored
        self.assertEqual(self.sh.path.realpath(self.sh.pwd()),
                         self.sh.path.join(self.tmpdir, '{:s}/scrontch/toto'.format(self.tag1)))


if __name__ == '__main__':
    main(verbosity=2)
