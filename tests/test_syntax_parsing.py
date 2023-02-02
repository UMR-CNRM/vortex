import unittest

from bronx.syntax.parsing import str2dict, StringDecoder, StringDecoderSubstError, \
    StringDecoderRemapError


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


class TestStringDecoder(unittest.TestCase):

    _SUBSTACK = dict(
        toto='1',
        titi='dict(a:${toto})',
        tata='int(dict(b:${toto} c:2))',
        impossible='${impossible}',
        nasty='${nasty1} ${nasty2}',
        nasty1='${nasty2}',
        nasty2='${nasty1}',
        notnasty='${nasty4},${nasty3}',
        nasty3='${toto}',
        nasty4='${nasty3}',
    )

    def setUp(self):
        self.cd = StringDecoder()

    def test_litteral_cleaner(self):
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
            self.assertEqual(self.cd._litteral_cleaner(svar), sref)

    def test_sparser(self):
        p = self.cd._sparser
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
        self.assertDictEqual(p('toto:titi', itemsep=' ', keysep=':'),
                             dict(toto='titi'))
        self.assertDictEqual(p('toto:titi blop:blurp', itemsep=' ', keysep=':'),
                             dict(toto='titi', blop='blurp'))
        self.assertDictEqual(p('toto:titi blop:dict(blurp:12 blip:13)', itemsep=' ', keysep=':'),
                             dict(toto='titi', blop='dict(blurp:12 blip:13)'))
        self.assertDictEqual(p('toto:titi blop:dict(blurp:dict(rrr=12 zzz=15) blip:13)', itemsep=' ', keysep=':'),
                             dict(toto='titi', blop='dict(blurp:dict(rrr=12 zzz=15) blip:13)'))
        # Raise Unbalanced parenthesis
        with self.assertRaises(ValueError):
            p('toto:titi(arg', keysep=':', itemsep=' ')
        with self.assertRaises(ValueError):
            p('titi(arg', itemsep=',')
        with self.assertRaises(ValueError):
            p('titi)arg', itemsep=',')

    def test_value_expand(self):

        def _my_vexpand(string, remap=lambda x: x, subs=None):
            l_subs = subs or dict()
            return self.cd._value_expand(string, remap, l_subs)

        # Basics...
        self.assertEqual(_my_vexpand('toto'), 'toto')
        self.assertIs(_my_vexpand('None'), None)
        self.assertEqual(_my_vexpand('toto(scrontch)'), 'toto(scrontch)')
        # Lists...
        self.assertListEqual(_my_vexpand('toto,titi,tata'),
                             ['toto', 'titi', 'tata'])
        self.assertListEqual(_my_vexpand('toto,None,tata'),
                             ['toto', None, 'tata'])
        self.assertListEqual(_my_vexpand('tot(o,tit)i,tata'),
                             ['tot(o,tit)i', 'tata'])
        # Explicit list
        self.assertListEqual(_my_vexpand('list(toto,titi,tata)'),
                             ['toto', 'titi', 'tata'])
        self.assertListEqual(_my_vexpand('list(toto,None,tata)'),
                             ['toto', None, 'tata'])
        self.assertListEqual(_my_vexpand('list(tot(o,tit)i,tata)'),
                             ['tot(o,tit)i', 'tata'])
        self.assertListEqual(_my_vexpand('list(toto)'),
                             ['toto'])
        self.assertListEqual(_my_vexpand('list()'),
                             [])
        # Dictionnaries...
        self.assertDictEqual(_my_vexpand('dict(01:1 02:2)'),
                             {'01': '1', '02': '2'})
        self.assertDictEqual(_my_vexpand('dict(01:(1:26,25) 02:2)'),
                             {'01': '(1:26,25)', '02': '2'})
        self.assertDictEqual(_my_vexpand('dict(assim:dict(01:1 02:2) production:dict(01:4 02:5))'),
                             {'assim': {'01': '1', '02': '2'},
                              'production': {'01': '4', '02': '5'}})
        self.assertDictEqual(_my_vexpand('dict(assim:dict(01:1 02:dict(1:2 2:1)) production:dict(01:4 02:5))'),
                             {'assim': {'01': '1', '02': {'1': '2', '2': '1'}},
                              'production': {'01': '4', '02': '5'}})
        # Dictionnary of lists
        self.assertEqual(_my_vexpand('dict(01:1,26,25 02:2)'),
                         {'01': ['1', '26', '25'], '02': '2'})
        # List of dictionnaries
        self.assertEqual(_my_vexpand('dict(01:1,26,25 02:2),1'),
                         [{'01': ['1', '26', '25'], '02': '2'}, '1'])
        # Remapping
        self.assertDictEqual(_my_vexpand('dict(assim:dict(01:1 02:dict(1:2 2:1)) production:dict(01:4 02:5))', int),
                             {'assim': {'01': 1, '02': {'1': 2, '2': 1}},
                              'production': {'01': 4, '02': 5}})
        self.assertEqual(_my_vexpand('dict(01:1,26,25 02:2),1', int),
                         [{'01': [1, 26, 25], '02': 2}, 1])
        self.assertEqual(_my_vexpand('dict(01:1,None,25 02:2),1', int),
                         [{'01': [1, None, 25], '02': 2}, 1])
        self.assertEqual(_my_vexpand('dict(01:1,True,25 02:2),false', int),
                         [{'01': [1, True, 25], '02': 2}, False])
        self.assertEqual(_my_vexpand('dict(01:1,False,25 02:2),true', int),
                         [{'01': [1, False, 25], '02': 2}, True])
        # Substitute
        self.assertEqual(_my_vexpand('${truc}', subs=dict(truc=1)), 1)
        self.assertEqual(_my_vexpand('dict(a:${truc})', subs=dict(truc=1)),
                         dict(a=1))
        # Xbool
        self.assertTrue(_my_vexpand('xbool(true)'))
        self.assertTrue(_my_vexpand('xbool(1)'))
        self.assertTrue(_my_vexpand('xbool(on)'))
        self.assertTrue(_my_vexpand('xbool(yes)'))
        self.assertTrue(_my_vexpand('xbool(ok)'))
        self.assertFalse(_my_vexpand('xbool(false)'))
        self.assertFalse(_my_vexpand('xbool(0)'))
        self.assertFalse(_my_vexpand('xbool(no)'))
        # Mix of dicts, lists and xbool
        self.assertEqual(_my_vexpand('dict(01:1,xbool(no),25 02:2),xbool(1)'),
                         [{'01': ['1', False, '25'], '02': '2'}, True])

    def test_decode(self):
        # Does nothing
        a = 12589
        self.assertIs(self.cd(a), a)
        # Easy
        tlist = 'toto,titi,tata'
        self.assertListEqual(self.cd(tlist), ['toto', 'titi', 'tata'])
        tdict = 'dict(toto:titi tata:titi)'
        self.assertDictEqual(self.cd(tdict), {'toto': 'titi', 'tata': 'titi'})
        # Remap ?
        tdict2 = 'int(dict(toto:1 tata:2))'
        self.assertDictEqual(self.cd(tdict2), {'toto': 1, 'tata': 2})
        tlist2 = 'float(2.6,2.8)'
        self.assertListEqual(self.cd(tlist2), [2.6, 2.8])
        tdict3 = 'xbool(dict(toto:1 tata:0 titi:ok))'
        self.assertDictEqual(self.cd(tdict3), {'toto': True, 'tata': False, 'titi': True})
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
            self.assertDictEqual(self.cd(sval),
                                 {'toto': ['titi', 'tata'], 'tata': 'titi'})
        with self.assertRaises(StringDecoderRemapError):
            self.cd('toto(1)')

    def test_substitute(self):
        subdict1 = self._SUBSTACK.copy()
        cdbis = StringDecoder(substitution_cb=subdict1.get)
        # Substitutes
        with self.assertRaises(StringDecoderSubstError):
            self.assertEqual(self.cd('${toto}'), dict())
        self.assertEqual(cdbis('arrr${toto}'), 'arrr${toto}')
        self.assertEqual(cdbis('${toto}'), '1')
        self.assertEqual(cdbis('${titi}'), dict(a='1'))
        self.assertDictEqual(cdbis('dict(titi:${titi} tata:${tata})'),
                             dict(titi=dict(a='1'), tata=dict(b='1', c=2)))
        with self.assertRaises(StringDecoderSubstError):
            self.assertEqual(cdbis('${tttt}'), dict())
        with self.assertRaises(StringDecoderSubstError):
            # Cyclic substitution
            cdbis('${impossible}')
        with self.assertRaises(StringDecoderSubstError):
            # Cyclic substitution
            cdbis('${nasty}')
        # Weird but fine
        weird1 = cdbis('int(${notnasty},5,dict(titi:${titi} tata:${tata}))')
        self.assertListEqual(weird1,
                             [['1', '1'], 5, dict(titi=dict(a='1'), tata=dict(b='1', c=2))])
        # Test cache on complex objects
        weird2 = cdbis('int(${notnasty},5,dict(titi:${titi} tata:${tata}))')
        self.assertIs(weird1, weird2)
        subdict1['nasty3'] = '${toto}\n'  # Un-significant change
        weird2 = cdbis('int(${notnasty},5,dict(titi:${titi} tata:${tata}))')
        self.assertIs(weird1, weird2)
        subdict1['nasty3'] = '10'  # Significant change -> The cache should be ignored
        weird2 = cdbis('int(${notnasty},5,dict(titi:${titi} tata:${tata}))')
        self.assertIsNot(weird1, weird2)
        self.assertListEqual(weird2,
                             [['10', '10'], 5, dict(titi=dict(a='1'), tata=dict(b='1', c=2))])
        # Disabling the cache
        cdbis = StringDecoder(substitution_cb=subdict1.get, with_cache=False)
        weird1 = cdbis('int(${notnasty},5,dict(titi:${titi} tata:${tata}))')
        weird2 = cdbis('int(${notnasty},5,dict(titi:${titi} tata:${tata}))')
        self.assertIsNot(weird1, weird2)


if __name__ == "__main__":
    unittest.main()
