#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import unittest

from vortex.data import geometries
from vortex.layout.nodes import ConfigSet


class utConfigSet(unittest.TestCase):

    def test_basics(self):
        cs = ConfigSet()
        cs.Testint = 1
        cs.testString = 'blop'
        self.assertDictEqual(cs, dict(testint=1, teststring='blop'))
        del cs['TestINT']
        self.assertDictEqual(cs, dict(teststring='blop'))

    def test_remap(self):
        # Explicit remap
        cs = ConfigSet()
        cs.testint = 'int(2)'
        self.assertEqual(cs.testint, 2)
        cs.testfloat = 'float(2.5)'
        self.assertEqual(cs.testfloat, 2.5)
        cs.testgeo = 'geometry(globalsp)'
        self.assertIs(cs.testgeo, geometries.get(tag='globalsp'))
        # Implicit reap
        cs.globalgeometry = 'globalsp'
        self.assertIs(cs.globalgeometry, geometries.get(tag='globalsp'))

    def test_list_and_dicts(self):
        cs = ConfigSet()
        # Lists
        tref = list(['1', '5', '8'])
        for tstring in ('1,5,8', '1,5, 8', '1,    5,8', "1,\n5,8"):
            cs.testlist = tstring
            self.assertListEqual(cs.testlist, tref)
        tref = list([1, 5, 8])
        for tstring in ('int(1,5,8)', 'int(1,5, 8)', 'int(1,    5,8)',
                        "int(1,\n5,8)"):
            cs.testlist = tstring
            self.assertListEqual(cs.testlist, tref)
        tref = {'01': '5', '02': '7'}
        # Simple dictionnaries
        for tstring in ('dict(01:5 02:7)', 'dict(01:5   02:7)',
                        'dict(01:5 02: 7)', 'dict(01 :5 02: 7)',
                        'dict(01:5\n02:7)'):
            cs.testdict = tstring
            self.assertDictEqual(cs.testdict, tref)
        tref = {'01': 5, '02': 7}
        for tstring in ('int(dict(01:5 02:7))', 'int(dict(01:5\n02:7))'):
            cs.testdict = tstring
            self.assertDictEqual(cs.testdict, tref)
        # Two tiers dictionnary
        tref = {'production': {'01': 4, '02': 5}, 'assim': {'01': 1, '02': 2}}
        for tstring in ('int(dict(production:dict(01:4 02:5) assim:dict(01:1 02:2)))',
                        "int(dict(production:dict(01:4\n02:5) assim:dict(01:1 02:2)))",
                        "int(dict(production:dict(01: 4\n02:5) assim: dict(01 :1 02:2)))"):
            cs.testdict = tstring
            self.assertDictEqual(cs.testdict, tref)
        


if __name__ == "__main__":
    unittest.main(verbosity=2)
