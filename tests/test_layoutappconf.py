import unittest

from vortex.layout.appconf import ConfigSet
from vortex.data import geometries


class TestConfigSet(unittest.TestCase):

    def test_configsset(self):
        cs = ConfigSet()
        # Easy
        cs.blop = 1
        self.assertEqual(cs.BLOP, 1)
        cs.TLIST = 'toto,titi,tata'
        self.assertListEqual(cs.tlist, ['toto', 'titi', 'tata'])
        cs.tdict = 'dict(toto:titi tata:titi)'
        self.assertDictEqual(cs.tdict, {'toto': 'titi', 'tata': 'titi'})
        cs.tdict2_map = 'toto:titi tata:titi'
        self.assertDictEqual(cs.tdict2, {'toto': 'titi', 'tata': 'titi'})
        for dmap in ('dict(toto:titi tata:titi)',
                     'default(dict(toto:titi tata:titi))'):
            cs.tdict3_map = dmap
            self.assertDictEqual(cs.tdict3_map, {'toto': 'titi', 'tata': 'titi'})
        for geo in ('global798', 'geometry(global798)', 'GEOMETRY(global798)'):
            cs.tgeometry = geo
            self.assertEqual(cs.tgeometry, geometries.get(tag='global798'))
        cs.tgeometries = 'global798,globalsp2'
        self.assertListEqual(cs.tgeometries, [geometries.get(tag='global798'),
                                              geometries.get(tag='globalsp2')])
        cs.tr_range = '1-5-2'
        self.assertListEqual(cs.tr, [1, 3, 5])
        cs.tr_range = 'float(1-5-2)'
        self.assertListEqual(cs.tr, [1., 3., 5.])
        # Remap + dict?
        cs.tdict2_map = 'int(toto:1 tata:2)'
        self.assertDictEqual(cs.tdict2, {'toto': 1, 'tata': 2})
        # What
        self.assertSetEqual(set(cs),
                            {'blop', 'tlist', 'tdict', 'tdict2', 'tdict3_map', 'tgeometry', 'tgeometries', 'tr'})
        del cs.tdict3_MAP
        self.assertSetEqual(set(cs),
                            {'blop', 'tlist', 'tdict', 'tdict2', 'tgeometry', 'tgeometries', 'tr'})
        cs.clear()
        self.assertEqual(len(cs), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
