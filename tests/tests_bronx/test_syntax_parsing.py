#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import unittest

from bronx.syntax.parsing import str2dict


class Str2DictTest(unittest.TestCase):

    def test_str2dict(self):
        expected = dict(a='toto', b='titi')
        self.assertDictEqual(str2dict('a:toto,b:titi'), expected)
        self.assertDictEqual(str2dict('a=toto,b:titi'), expected)
        self.assertDictEqual(str2dict('a:  toto,   b:titi  '), expected)
        expected = dict(a='toto:knark', b='titi')
        self.assertDictEqual(str2dict('a:toto:knark ,b:titi'), expected)
        expected = dict(a=1, b=2)
        self.assertDictEqual(str2dict('a=1 ,b: 2', try_convert=int), expected)
        expected = dict(a=1, b='adad')
        self.assertDictEqual(str2dict('a=1 ,b: adad', try_convert=int), expected)


if __name__ == "__main__":
    unittest.main()
