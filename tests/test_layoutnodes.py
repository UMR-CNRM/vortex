
import unittest

from vortex.layout.nodes import ConfigSet
from vortex.data import geometries


class TestConfigSet(unittest.TestCase):

    def test_litteral_cleaner(self):
        cs = ConfigSet()
        sref = 'blop(uit:1 tri:2) rtui,trop'
        for svar in ('  blop(uit:1 tri:2) rtui,trop ',
                     'blop( uit:1 tri:2 ) rtui,trop',
                     'blop( uit:1 tri:2)   rtui,trop',
                     'blop(uit:1 tri:2) rtui,  trop',
                     'blop(uit:1 tri:2) rtui ,trop',
                     "blop(uit:1\ntri:2) rtui ,trop",
                     "blop(uit:1 \ntri:2) rtui ,trop",
                     'blop(uit:  1  tri:2) rtui ,trop',
                     ):
            self.assertEqual(cs._litteral_cleaner(svar), sref)

    def test_sparser(self):
        cs = ConfigSet()
        p = cs._sparser
        # Does nothing
        self.assertListEqual(p('blop(123)'), ['blop(123)', ])
        self.assertListEqual(p('bdict(123)'), ['bdict(123)', ])
        # Raise ?
        with self.assertRaises(ValueError):
            p('toto', keysep=':')
        with self.assertRaises(ValueError):
            p('toto', keysep=':', itemsep=' ')
        with self.assertRaises(ValueError):
            p('toto:titi tata', keysep=':', itemsep=' ')
        # Item separator only
        self.assertListEqual(p('1', itemsep=','), ['1', ])
        self.assertListEqual(p('1,2,3', itemsep=','), ['1', '2', '3'])
        self.assertListEqual(p('1,(2,5,6),3', itemsep=','),
                             ['1', '(2,5,6)', '3'])
        self.assertListEqual(p('1,machin(2,5,6),3', itemsep=','),
                             ['1', 'machin(2,5,6)', '3'])
        self.assertListEqual(p('1(fgt,jt)a,machin', itemsep=','),
                             ['1(fgt,jt)a', 'machin'])
        # Key/value separators
        self.assertListEqual(p('toto:titi', itemsep=' ', keysep=':'),
                             ['toto', 'titi'])
        self.assertListEqual(p('toto:titi blop:blurp', itemsep=' ', keysep=':'),
                             ['toto', 'titi', 'blop', 'blurp'])
        self.assertListEqual(p('toto:titi blop:dict(blurp:12 blip:13)', itemsep=' ', keysep=':'),
                             ['toto', 'titi', 'blop', 'dict(blurp:12 blip:13)'])
        self.assertListEqual(p('toto:titi blop:dict(blurp:dict(rrr=12 zzz=15) blip:13)', itemsep=' ', keysep=':'),
                             ['toto', 'titi', 'blop', 'dict(blurp:dict(rrr=12 zzz=15) blip:13)'])
        # Raise Unbalanced parenthesis
        with self.assertRaises(ValueError):
            p('toto:titi(arg', keysep=':', itemsep=' ')
        with self.assertRaises(ValueError):
            p('titi(arg', itemsep=',')
        with self.assertRaises(ValueError):
            p('titi)arg', itemsep=',')

    def test_value_expand(self):
        cs = ConfigSet()
        # Basics...
        self.assertEqual(cs._value_expand('toto', lambda x: x),
                         'toto')
        self.assertIs(cs._value_expand('None', lambda x: x),
                      None)
        self.assertEqual(cs._value_expand('toto(scrontch)', lambda x: x),
                         'toto(scrontch)')
        # Lists...
        self.assertListEqual(cs._value_expand('toto,titi,tata', lambda x: x),
                             ['toto', 'titi', 'tata'])
        self.assertListEqual(cs._value_expand('toto,None,tata', lambda x: x),
                             ['toto', None, 'tata'])
        self.assertListEqual(cs._value_expand('tot(o,tit)i,tata', lambda x: x),
                             ['tot(o,tit)i', 'tata'])
        # Dictionnaries...
        self.assertDictEqual(cs._value_expand('dict(01:1 02:2)', lambda x: x),
                             {'01': '1', '02': '2'})
        self.assertDictEqual(cs._value_expand('dict(01:(1:26,25) 02:2)', lambda x: x),
                             {'01': '(1:26,25)', '02': '2'})
        self.assertDictEqual(cs._value_expand('dict(assim:dict(01:1 02:2) production:dict(01:4 02:5))', lambda x: x),
                             {'assim': {'01': '1', '02': '2'},
                              'production': {'01': '4', '02': '5'}})
        self.assertDictEqual(cs._value_expand('dict(assim:dict(01:1 02:dict(1:2 2:1)) production:dict(01:4 02:5))', lambda x: x),
                             {'assim': {'01': '1', '02': {'1': '2', '2': '1'}},
                              'production': {'01': '4', '02': '5'}})
        # Dictionnary of lists
        self.assertEqual(cs._value_expand('dict(01:1,26,25 02:2)', lambda x: x),
                         {'01': ['1', '26', '25'], '02': '2'})
        # List of dictionnaries
        self.assertEqual(cs._value_expand('dict(01:1,26,25 02:2),1', lambda x: x),
                         [{'01': ['1', '26', '25'], '02': '2'}, '1'])
        # Remapping
        self.assertDictEqual(cs._value_expand('dict(assim:dict(01:1 02:dict(1:2 2:1)) production:dict(01:4 02:5))', int),
                             {'assim': {'01': 1, '02': {'1': 2, '2': 1}},
                              'production': {'01': 4, '02': 5}})
        self.assertEqual(cs._value_expand('dict(01:1,26,25 02:2),1', int),
                         [{'01': [1, 26, 25], '02': 2}, 1])
        self.assertEqual(cs._value_expand('dict(01:1,None,25 02:2),1', int),
                         [{'01': [1, None, 25], '02': 2}, 1])

    def test_setitem(self):
        cs = ConfigSet()
        # Easy
        cs.tlist = 'toto,titi,tata'
        self.assertListEqual(cs.tlist, ['toto', 'titi', 'tata'])
        cs.tdict = 'dict(toto:titi tata:titi)'
        self.assertDictEqual(cs.tdict, {'toto': 'titi', 'tata': 'titi'})
        cs.tdict2_map = 'toto:titi tata:titi'
        self.assertDictEqual(cs.tdict2, {'toto': 'titi', 'tata': 'titi'})
        cs.tgeometry = 'globalsp'
        self.assertEqual(cs.tgeometry, geometries.get(tag='globalsp'))
        cs.tgeometries = 'globalsp,globalsp2'
        self.assertListEqual(cs.tgeometries, [geometries.get(tag='globalsp'),
                                              geometries.get(tag='globalsp2')])
        cs.tr_range = 'int(1,5,2)'
        self.assertListEqual(cs.tr, [1, 3, 5])
        cs.tr_range = '1-5-2'
        self.assertListEqual(cs.tr, [1, 3, 5])
        # Remap ?
        cs.tdict2_map = 'int(toto:1 tata:2)'
        self.assertDictEqual(cs.tdict2, {'toto': 1, 'tata': 2})
        cs.tlist = 'float(2.6,2.8)'
        self.assertListEqual(cs.tlist, [2.6, 2.8])
        cs.tlist = 'float(2.6, None)'
        self.assertListEqual(cs.tlist, [2.6, None])
        # Strange case
        for sval in ('dict(toto:titi,tata tata:titi)',
                     "dict(toto:titi,tata \n\ntata:titi)",
                     "dict(toto:titi,\ntata tata:titi)",
                     'dict(toto:  titi,tata   tata:titi)',
                     '   dict(toto:titi,tata tata:titi)  ',
                     'dict(toto:titi ,  tata tata:titi)',
                     'dict(  toto:titi,tata tata:titi)',
                     'dict(toto:titi,tata tata:titi  )',
                     ):
            cs.tdict3 = sval
            self.assertDictEqual(cs.tdict3, {'toto': ['titi', 'tata'], 'tata': 'titi'})

if __name__ == "__main__":
    unittest.main(verbosity=2)
