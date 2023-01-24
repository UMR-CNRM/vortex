import os
import tempfile
import unittest
from unittest import TestCase

import vortex

from vortex.util.config import load_template

try:
    import jinja2  # @UnusedImport
except ImportError:
    jinja2_ok = False
else:
    jinja2_ok = True


SITEROOT_PATH = os.path.join(os.path.dirname(__file__), 'siteroot')
CONFIGRC_PATH = os.path.join(os.path.dirname(__file__), 'configrc')

JINJA2_RESULT = """Header line.
This is jinja2 tpl. Line 01. Input foo.
This is jinja2 tpl. Line 02. Input bar.
Footer line."""


class UtLoadTemplate(TestCase):

    def setUp(self):
        self.cursession = vortex.sessions.current()
        self.oldpwd = self.cursession.system().pwd()
        # Generate a temporary directory and session
        # Note: the session is shared between all tests
        self.glove = vortex.sessions.getglove(
            profile='utest',
            test_siteroot=SITEROOT_PATH,
            test_configrc=CONFIGRC_PATH,
        )
        self.t = vortex.sessions.get(tag='vortex_templating_test_session',
                                     topenv=vortex.rootenv,
                                     glove=self.glove)
        self.sh = self.t.system()
        self.tmpdir = tempfile.mkdtemp(suffix='_test_templating')
        self.sh.cd(self.tmpdir)
        self.t.rundir = self.tmpdir
        self.t.activate()

    def tearDown(self):
        self.cursession.activate()
        self.sh.cd(self.oldpwd)
        self.sh.remove(self.tmpdir)

    def test_legacy_and_configrc(self):
        tpl = load_template(self.t, '@legacy.tpl')
        tpl_dict = dict(foo='Hello')
        expected_res = "This is the legacy tpl. Sub=Hello."
        self.assertEqual(tpl(** tpl_dict), expected_res)
        self.assertEqual(tpl.substitute(**tpl_dict), expected_res)
        self.assertEqual(tpl.safe_substitute(**tpl_dict), expected_res)
        self.assertEqual(tpl.substitute(tpl_dict), expected_res)
        self.assertEqual(tpl.safe_substitute(tpl_dict), expected_res)
        self.assertEqual(tpl.substitute(dict(foo='ko'), **tpl_dict), expected_res)
        tpl = load_template(self.t, '@legacy.tpl', default_templating='twopasslegacy')
        self.assertEqual(tpl(**tpl_dict), expected_res)

    def test_auto_encoding(self):
        tpl = load_template(self.t, '@legacy_encoding.tpl', encoding='script')
        tpl_dict = dict(foo='à')
        expected_res = "This is the legacy tpl with éè. Sub=à."
        self.assertEqual(tpl(**tpl_dict), expected_res)

    def test_auto_twopass(self):
        tpl = load_template(self.t, '@twopass.tpl')
        tpl_dict = dict(foo='$other', other='Hello')
        expected_res = "This is the twopass-legacy tpt. Sub=Hello."
        self.assertEqual(tpl(**tpl_dict), expected_res)

    @unittest.skipUnless(jinja2_ok, "The jinja2 package is unavailable")
    def test_jinja2(self):
        tpl = load_template(self.t, '@jinja2.tpl', encoding='script')
        tpl_dict = dict(listvar=['foo', 'bar'])
        self.assertEqual(tpl(**tpl_dict), JINJA2_RESULT)
        tpl = load_template(self.t, '@jinja2_bis.tpl', encoding='script')
        tpl_dict = dict(listvar=['FOO', 'Bar'])
        self.assertEqual(tpl(**tpl_dict), JINJA2_RESULT)


if __name__ == '__main__':
    unittest.main(verbosity=2)
