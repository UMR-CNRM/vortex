#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, unicode_literals
import tempfile
import os
import unittest

from bronx.datagrip.misc import read_dict_in_CSV


class TestDictCSV(unittest.TestCase):

    def setUp(self):
        self.testfilename = tempfile.mkstemp()[1]
        with open(self.testfilename, 'w') as f:
            f.write(';\n')
            f.write('main\n')
            f.write('a:1;b:ok\n')
            f.write('a:2;b:not ok;c:why?\n')
            f.close()

    def test_read_dict_in_CSV(self):
        self.assertEqual(read_dict_in_CSV(self.testfilename),
                         ([{u'a': 1, u'b': u'ok'},
                           {u'a': 2, u'c': u'why?', u'b': u'not ok'}],
                          'main')
                         )

    def tearDown(self):
        os.remove(self.testfilename)


if __name__ == "__main__":
    unittest.main(verbosity=2)