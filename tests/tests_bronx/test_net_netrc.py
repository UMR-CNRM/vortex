#!/usr/bin/env python
# 09/02/2017
# Original version: Python 3.5
#                   Copyright 2001-2017 Python Software Foundation; All Rights Reserved
# Proposed patched applied: https://bugs.python.org/issue11416
# LFM: from test import support -> from test import test_support (for ptyhon2.7)
# LFM: test for quoted password

from __future__ import print_function, absolute_import, unicode_literals, division

import bronx.net.netrc as netrc
import io
import os
import unittest
import sys
import textwrap

try:
    from test import support as test_support
except ImportError:  # For python <= 2.7.13
    from test import test_support

temp_filename = test_support.TESTFN


class NetrcTestCase(unittest.TestCase):

    def make_nrc(self, test_data):
        test_data = textwrap.dedent(test_data)
        mode = 'w'
        if sys.platform != 'cygwin':
            mode += 't'
        with io.open(temp_filename, mode) as fp:
            fp.write(test_data)
        self.addCleanup(os.unlink, temp_filename)
        return netrc.netrc(temp_filename)

    def test_default(self):
        nrc = self.make_nrc("""\
            machine host1.domain.com login log1 password pass1 account acct1
            default login log2 password pass2
            """)
        self.assertEqual(nrc.hosts['host1.domain.com'],
                         ('log1', 'acct1', 'pass1'))
        self.assertEqual(nrc.hosts['default'], ('log2', None, 'pass2'))

    def test_macros(self):
        nrc = self.make_nrc("""\
            macdef macro1
            line1
            line2

            macdef macro2
            line3
            line4
            """)
        self.assertEqual(nrc.macros, {'macro1': ['line1\n', 'line2\n'],
                                      'macro2': ['line3\n', 'line4\n']})

    def _test_passwords(self, nrc, passwd):
        nrc = self.make_nrc(nrc)
        self.assertEqual(nrc.hosts['host.domain.com'], ('log', 'acct', passwd))

    def test_password_with_leading_hash(self):
        self._test_passwords("""\
            machine host.domain.com login log password #pass account acct
            """, '#pass')

    def test_password_with_trailing_hash(self):
        self._test_passwords("""\
            machine host.domain.com login log password pass# account acct
            """, 'pass#')

    def test_password_with_internal_hash(self):
        self._test_passwords("""\
            machine host.domain.com login log password pa#ss account acct
            """, 'pa#ss')

    def test_password_with_quotes(self):
        self._test_passwords("""\
            machine host.domain.com login log password "pa#ss" account acct
            """, 'pa#ss')

    def _test_comment(self, nrc, passwd='pass'):
        nrc = self.make_nrc(nrc)
        self.assertEqual(nrc.hosts['foo.domain.com'], ('bar', None, passwd))
        self.assertEqual(nrc.hosts['bar.domain.com'], ('foo', None, 'pass'))

    def test_comment_before_machine_line(self):
        self._test_comment("""\
            # comment
            machine foo.domain.com login bar password pass
            machine bar.domain.com login foo password pass
            """)

    def test_comment_before_machine_line_no_space(self):
        self._test_comment("""\
            #comment
            machine foo.domain.com login bar password pass
            machine bar.domain.com login foo password pass
            """)

    def test_comment_before_machine_line_hash_only(self):
        self._test_comment("""\
            #
            machine foo.domain.com login bar password pass
            machine bar.domain.com login foo password pass
            """)

    def test_comment_at_end_of_machine_line(self):
        self._test_comment("""\
            machine foo.domain.com login bar password pass # comment
            machine bar.domain.com login foo password pass
            """)

    def test_comment_at_end_of_machine_line_no_space(self):
        self._test_comment("""\
            machine foo.domain.com login bar password pass #comment
            machine bar.domain.com login foo password pass
            """)

    def test_comment_at_end_of_machine_line_pass_has_hash(self):
        self._test_comment("""\
            machine foo.domain.com login bar password #pass #comment
            machine bar.domain.com login foo password pass
            """, '#pass')

    @unittest.skipUnless(os.name == 'posix', 'POSIX only test')
    def test_security(self):
        # This test is incomplete since we are normally not run as root and
        # therefore can't test the file ownership being wrong.
        d = test_support.TESTFN
        os.mkdir(d)
        self.addCleanup(test_support.rmtree, d)
        fn = os.path.join(d, '.netrc')
        with io.open(fn, 'wt') as f:
            f.write("""\
                machine foo.domain.com login bar password pass
                default login foo password pass
                """)
        with test_support.EnvironmentVarGuard() as environ:
            environ.set('HOME', d)
            os.chmod(fn, 0o600)
            nrc = netrc.netrc()
            self.assertEqual(nrc.hosts['foo.domain.com'],
                             ('bar', None, 'pass'))
            os.chmod(fn, 0o622)
            self.assertRaises(netrc.NetrcParseError, netrc.netrc)

    def test_handle_several_accounts_per_host(self):
        nrc = self.make_nrc("""\
            machine host.com login foo password foo account foo
            machine host.com login bar password bar account bar
        """)
        self.assertTupleEqual(nrc.hosts['host.com'], ('bar', 'bar', 'bar'))
        self.assertTupleEqual(nrc.authenticators('host.com'),
                              ('bar', 'bar', 'bar'))
        self.assertTupleEqual(nrc.authenticators('host.com', 'foo'),
                              ('foo', 'foo', 'foo'))
        self.assertIsNone(nrc.authenticators('host.com', lambda: 'foo'))


if __name__ == "__main__":
    unittest.main()
