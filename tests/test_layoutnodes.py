
import unittest

from vortex.layout.nodes import ConfigSet
from vortex.data import geometries


class TestConfigSet(unittest.TestCase):

    def test_setitem(self):
        cs = ConfigSet()
        # Easy
        cs.tlist = 'toto,titi,tata'
        self.assertListEqual(cs.tlist, ['toto', 'titi', 'tata'])
        cs.tdict = 'dict(toto:titi tata:titi)'
        self.assertDictEqual(cs.tdict, {'toto': 'titi', 'tata': 'titi'})
        for dmap in ('toto:titi tata:titi', 'dict(toto:titi tata:titi)',
                     'default(dict(toto:titi tata:titi))'):
            cs.tdict2_map = dmap
            self.assertDictEqual(cs.tdict2, {'toto': 'titi', 'tata': 'titi'})
        for geo in ('global798', 'geometry(global798)', 'GEOMETRY(global798)'):
            cs.tgeometry = geo
            self.assertEqual(cs.tgeometry, geometries.get(tag='global798'))
        cs.tgeometries = 'global798,globalsp2'
        self.assertListEqual(cs.tgeometries, [geometries.get(tag='global798'),
                                              geometries.get(tag='globalsp2')])
        cs.tr_range = '1-5-2'
        self.assertListEqual(cs.tr, [1, 3, 5])
        # Remap + dict?
        cs.tdict2_map = 'int(toto:1 tata:2)'
        self.assertDictEqual(cs.tdict2, {'toto': 1, 'tata': 2})


if __name__ == "__main__":
    unittest.main(verbosity=2)
