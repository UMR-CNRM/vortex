from unittest import main
import os
import sys

if __name__ == '__main__':
    sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from .test_generic import _BaseDataContentTest

from bronx.fancies import loggers
from bronx.stdtypes.date import Time
from common.data import namelists


XXT_T = """00:15   xxt00000015 select_fp1
00:30   xxt00000030 select_fp1
00:45   xxt00000045 select_fp1
1       xxt00000100 select_fp2
01:15   xxt00000115 select_fp2
01:30   xxt00000130 select_fp2
01:45   xxt00000145 select_fp2
02      xxt00000200 select_fp2
"""


XXT_E = {'0000:30': ['xxt00000030', 'select_fp1'],
         '0002:00': ['xxt00000200', 'select_fp2'],
         '0001:00': ['xxt00000100', 'select_fp2'],
         '0000:45': ['xxt00000045', 'select_fp1'],
         '0000:15': ['xxt00000015', 'select_fp1'],
         '0001:45': ['xxt00000145', 'select_fp2'],
         '0001:15': ['xxt00000115', 'select_fp2'],
         '0001:30': ['xxt00000130', 'select_fp2']}


class UtXXTContent(_BaseDataContentTest):

    _data = (XXT_T, )

    def test_obsmap_basic(self):
        ct = namelists.XXTContent()
        ct.slurp(self.insample[0])
        self.assertEqual(ct.data, XXT_E)
        self.assertEqual(ct.xxtnam(dict(term=Time('01:00')), dict()),
                         'xxt00000100')
        self.assertEqual(ct.xxtnam(dict(term='01:00'), dict()),
                         'xxt00000100')
        self.assertEqual(ct.xxtnam(dict(term=Time('01:30')), dict()),
                         'xxt00000130')
        self.assertEqual(ct.xxtsrc(dict(), dict(term=Time('00:45'))),
                         'select_fp1')
        self.assertEqual(ct.xxtsrc(dict(term='blop'), dict()), None)
        with loggers.contextboundGlobalLevel('critical'):
            self.assertEqual(ct.xxtsrc(dict(term=0), dict()), None)


if __name__ == '__main__':
    main(verbosity=2)
