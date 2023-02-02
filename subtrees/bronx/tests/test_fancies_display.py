from contextlib import contextmanager
from io import StringIO
import os
import sys
import unittest

from bronx.fancies.display import query_yes_no_quit, printstatus


class FanciesDisplayTest(unittest.TestCase):

    @contextmanager
    def _divert_stdin(self, *lines):
        oldstdin = sys.stdin
        newstdin = StringIO()
        newstdin.writelines([line + '\n' for line in lines])
        newstdin.seek(0)
        sys.stdin = newstdin
        yield
        sys.stdin = oldstdin

    @contextmanager
    def _quiet_stdout(self):
        oldstdout = sys.stdout
        # open would be better but it fails in eclipse/pydev...
        with open(os.devnull, "w") as newstdout:
            sys.stdout = newstdout
            yield
            sys.stdout = oldstdout

    @contextmanager
    def _capture(self, s_list):
        oldstdout = sys.stdout
        newstdout = StringIO()
        sys.stdout = newstdout
        yield
        sys.stdout = oldstdout
        newstdout.seek(0)
        s_list.extend([line.rstrip('\n') for line in newstdout.readlines()])

    def test_query_yes_no(self):
        with self._quiet_stdout():
            for yes in ('yes', 'y', 'Yes', 'yEs', 'Y', '', 'ADDD\nY'):
                with self._divert_stdin(yes):
                    self.assertEqual(query_yes_no_quit('', 'yes'), 'yes')
            for no in ('no', 'n', 'No', 'N', '', 'sdqgqg\nN'):
                with self._divert_stdin(no):
                    self.assertEqual(query_yes_no_quit('', 'no'), 'no')
            for stop in ('\n\n\nq', 'Q', 'quit', 'sdqgqg\nQ'):
                with self._divert_stdin(stop):
                    self.assertEqual(query_yes_no_quit('', None), 'quit')
            for stop in ('\n\n\nq', 'quit', ''):
                with self._divert_stdin(stop):
                    self.assertEqual(query_yes_no_quit('', 'quit'), 'quit')

    def test_printstatus(self):
        s_list = list()
        with self._capture(s_list):
            for i in range(0, 5):
                printstatus(i, 4, refresh_freq=2)
        self.assertListEqual(s_list, ['  0%\b\b\b\b 50%\b\b\b\b100%', ])


if __name__ == "__main__":
    unittest.main()
