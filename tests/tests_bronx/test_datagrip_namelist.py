#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from decimal import Decimal
import six
from unittest import TestCase, main

from bronx.datagrip import namelist
import re


DIRTYNAM = """\
! This is a test namelist
&MySecondOne C=.TRUE./
! Below an extra useless endblock: ignoring it
/
&MyNamelistTest
title = 'Coordinates/t=10',
A= 25,30, ! This is a parameter
x = 300.d0, y=628.318, z=0d0,
B(10 )=1,
c=(0,1), boz=B'11', stest=NBPROC,
B(2)=2, LT=T, LF=F
/
"""

CLEANEDNAM = """\
 &MYNAMELISTTEST
   TITLE='Coordinates/t=10',
   A=25,30,
   X=300.,
   Y=628.318,
   Z=0.,
   B(10 )=1,
   C=(0.,1.),
   BOZ=3,
   STEST=NBPROC,
   B(2)=2,
   LT=.TRUE.,
   LF=.FALSE.,
 /
 &MYSECONDONE
   C=.TRUE.,
 /
"""

CLEANEDNAM_SORTED1 = """\
 &MYNAMELISTTEST
   A=25,30,
   B(2)=2,
   B(10 )=1,
   BOZ=3,
   C=(0.,1.),
   LF=.FALSE.,
   LT=.TRUE.,
   STEST=NBPROC,
   TITLE='Coordinates/t=10',
   X=300.,
   Y=628.318,
   Z=0.,
 /
 &MYSECONDONE
   C=.TRUE.,
 /
"""

CLEANEDNAM_SORTED2 = """\
 &MYNAMELISTTEST
   TITLE='Coordinates/t=10',
   A=25,30,
   X=300.,
   Y=628.318,
   Z=0.,
   B(2)=2,
   B(10 )=1,
   C=(0.,1.),
   BOZ=3,
   STEST=NBPROC,
   LT=.TRUE.,
   LF=.FALSE.,
 /
 &MYSECONDONE
   C=.TRUE.,
 /
"""

NAMBLOCK1 = """\
! This is a test namelist
&MyNamelistTest
M1=$MYMACRO1,
M1b='MYMACRO1',
M1c=__MYMACRO1__,
M1d='__MYMACRO1__',
M2=MYMACRO2,
M3=__SOMETHINGNEW__,
M3b='__SOMETHINGNEW__',
TRAP='SOMETHINGNEW',
A=25,30,15
C=--,
GRUIK=--,
/
"""


class UtFortranNamelist(TestCase):

    def setUp(self):
        self.lp = namelist.LiteralParser()

    def _parse_tester(self, string, expected, parser=None):
        parse = self.lp.parse
        if parser:
            parse = getattr(self.lp, 'parse_' + parser)
        try:
            parsed = parse(string)
        except ValueError as e:
            self.assertIsInstance(e, expected)
        else:
            self.assertEqual(parsed, expected)

    def _encode_tester(self, string, expected):
        parsed = self.lp.encode(string)
        self.assertEqual(parsed, expected)

    def test_parse(self):
        self._parse_tester("1", 1)
        self._parse_tester("+0", 0)
        self._parse_tester("-2", -2)
        self._parse_tester("+46527_8", 46527)               # With kind.
        self._parse_tester("1.", ValueError, 'integer')     # To avoid confusion with real.
        self._parse_tester("B'1010'", 10)
        self._parse_tester("O'76'", 62)
        self._parse_tester("Z'ABC'", 2748)
        self._parse_tester("B'012'", ValueError)            # Meaningless digit.
        self._parse_tester("1.", 1)
        self._parse_tester("-.1", Decimal('-0.1'))
        self._parse_tester("+1E23", Decimal('1e+23'))
        self._parse_tester("2.e4_8", 2e+4)                  # With kind.
        self._parse_tester(".45D2", 45)
        self._parse_tester("10", ValueError, 'real')        # To avoid confusion with integer
        self._parse_tester("(1.,0.)", complex(1, 0))
        self._parse_tester("(0,1)", complex(0, 1))
        self._parse_tester("(0,1d0)", complex(0, 1))
        self._parse_tester("'Foo'", 'Foo')
        self._parse_tester('"baR"', 'baR')
        self._parse_tester('2_"kind"', 'kind')              # With kind.
        self._parse_tester("'T_machin'", 'T_machin')        # Underscore in the string.
        self._parse_tester('foo', ValueError)
        self._parse_tester(".TRUE.", True)
        self._parse_tester(".False.", False)
        self._parse_tester("T", True)
        self._parse_tester("F", False)
        self._parse_tester("G", ValueError)
        self._parse_tester(".true._2", True)                # With kind.
        self._parse_tester(".truea", ValueError)

    def test_encode(self):
        self._encode_tester(1, '1')
        self._encode_tester(1243523, '1243523')
        self._encode_tester(1.0, '1.')
        self._encode_tester(1., '1.')
        self._encode_tester(1e-76, '1.0D-76')
        self._encode_tester(1e124, '1.0D+124')
        self._encode_tester(222.5125, '222.5125')
        self._encode_tester(1.2345432123454321e-06, '1.23454321234543D-06')
        self._encode_tester(0.0000012345432123454321, '1.23454321234543D-06')
        self._encode_tester(complex(1, 1), '(1.,1.)')
        self._encode_tester("machin", "'machin'")
        self._encode_tester("mach'in", '"mach\'in"')
        self._encode_tester("mach\"in", '\'mach"in\'')
        self._encode_tester("'mach\"in", '"\'mach""in"')
        self._encode_tester(True, ".TRUE.")
        self._encode_tester(False, ".FALSE.")

    def test_namblock(self):
        np = namelist.NamelistParser(macros=('MYMACRO1', 'MYMACRO2'))
        nb_res = np.parse(NAMBLOCK1).as_dict()['MyNamelistTest']
        # Inspect the newly created object
        self.assertEqual(nb_res.name, 'MyNamelistTest')
        self.assertEqual(len(nb_res), 9)
        self.assertEqual(['M1', 'M1B', 'M1C', 'M1D', 'M2', 'M3', 'M3B', 'TRAP', 'A'],
                         list(nb_res))  # Iterator test
        self.assertEqual(['M1', 'M1B', 'M1C', 'M1D', 'M2', 'M3', 'M3B', 'TRAP', 'A'],
                         list(nb_res.keys()))
        self.assertEqual(nb_res.A, [25, 30, 15])
        self.assertEqual(nb_res["A"], [25, 30, 15])
        self.assertEqual(nb_res.M1, '$MYMACRO1')
        self.assertEqual(nb_res.M1b, "'MYMACRO1'")
        self.assertSetEqual(nb_res.rmkeys(), set(['C', 'GRUIK']))
        nb_res.addmacro('MYMACRO1', 'Toto')
        self.assertSetEqual(set(dict(MYMACRO1='Toto', MYMACRO2=None, SOMETHINGNEW=None).keys()),
                             set(nb_res.macros()))
        # Test add/modify/delete of a namelist variable
        nb_res.B = 1.2
        self.assertEqual(nb_res["B"], 1.2)
        nb_res["B"] = 1.2
        self.assertEqual(nb_res["B"], 1.2)
        self.assertEqual(len(nb_res), 10)
        del nb_res.B
        self.assertFalse('B' in nb_res)
        self.assertIs(nb_res.get('B', None), None)
        # Check that the substitution works
        dumped_ori = """\
 &MYNAMELISTTEST
   M1='Toto',
   M1B='Toto',
   M1C='Toto',
   M1D='Toto',
   M2=MYMACRO2,
   M3=__SOMETHINGNEW__,
   M3B='__SOMETHINGNEW__',
   TRAP='SOMETHINGNEW',
   A=25,30,15,
 /
"""
        self.assertEqual(nb_res.dumps(), dumped_ori)
        nb_res.addmacro('SOMETHINGNEW', 1)
        # Check that the substitution works
        dumped_ori = """\
 &MYNAMELISTTEST
   M1='Toto',
   M1B='Toto',
   M1C='Toto',
   M1D='Toto',
   M2=MYMACRO2,
   M3=1,
   M3B=1,
   TRAP='SOMETHINGNEW',
   A=25,30,15,
 /
"""
        self.assertEqual(nb_res.dumps(), dumped_ori)
        # Check merge
        ori2 = """\
! This is another test namelist
&MyNamelistTest
C='Trash',
/
"""
        nb_res2 = np.parse(ori2).as_dict()['MyNamelistTest']
        nb_res2.merge(nb_res)
        # 'C' should have been deleted...
        self.assertNotIn('C', nb_res2)
        self.assertTrue(re.search("M1B='Toto',", str(nb_res2)))
        self.assertTrue(re.search("M2=MYMACRO2,", str(nb_res2)))
        nb_res2.C = 5
        self.assertNotIn('C', nb_res2.rmkeys())
        # Test the clear function
        nb_res2.clear(rmkeys=('C',))
        self.assertTrue(re.search("M1B='Toto',", str(nb_res2)))
        self.assertTrue(re.search("M2=MYMACRO2,", str(nb_res2)))
        self.assertNotIn('C', nb_res2)
        nb_res2.clear()
        self.assertEqual(len(nb_res2), 0)

    def test_namparser_namset_basics(self):
        np = namelist.NamelistParser(macros=('NBPROC', ))
        ori = six.StringIO()
        ori.write(DIRTYNAM)
        parse_res = np.parse(ori)
        self.assertSetEqual(set(six.iterkeys(parse_res)),
                            set(['MyNamelistTest', 'MySecondOne']))
        self.assertEqual(parse_res.dumps(), CLEANEDNAM)
        self.assertEqual(parse_res.dumps(sorting=namelist.FIRST_ORDER_SORTING),
                         CLEANEDNAM_SORTED1)
        self.assertEqual(parse_res.dumps(sorting=namelist.SECOND_ORDER_SORTING),
                         CLEANEDNAM_SORTED2)
        with self.assertRaises(AssertionError):
            parse_res.mvblock('MyNamelistTest', 'MySecondOne')
        parse_res.mvblock('MyNamelistTest', 'MyThirdOne')
        self.assertSetEqual(set(parse_res.keys()),
                            set(['MyThirdOne', 'MySecondOne']))
        nset2 = namelist.NamelistSet(parse_res)
        self.assertEqual(parse_res.keys(), nset2.keys())

    def test_namset_newblock(self):
        np = namelist.NamelistParser(macros=('NBPROC', ))
        nset = np.parse(DIRTYNAM)
        nb = nset.newblock('MYNEWBLOCK')
        nb.A = 1
        self.assertEqual(nset['MYNEWBLOCK'].A, 1)
        nbbis = nset.newblock('MYNEWBLOCK')
        self.assertIs(nb, nbbis)
        nb = nset.newblock()
        nb.A = 1
        self.assertEqual(nset['AUTOBLOCK001'].A, 1)
        nb = nset.newblock('AUTOBLOCK002')
        nb = nset.newblock()
        nb.A = 1
        self.assertEqual(nset['AUTOBLOCK003'].A, 1)
        # Default macros
        nset.setmacro('NBPROC', 9999)
        self.assertTrue(re.search('STEST=9999,', nset.dumps()))

    def test_merge_nothing(self):
        np = namelist.NamelistParser(macros=('NBPROC', ))
        nset = np.parse(DIRTYNAM)
        # Test removes
        nset.merge({}, rmkeys=('A ', 'z'), rmblocks=('MySecondOne', ))
        self.assertSetEqual(set(nset.keys()), set(('MyNamelistTest', )))
        self.assertNotIn('A ', nset['MyNamelistTest'])
        self.assertNotIn('Z', nset['MyNamelistTest'])
        # Test clear
        nset.merge({}, clblocks=('MyNamelistTest', ))
        self.assertEqual(len(nset['MyNamelistTest']), 0)

    def test_merge_delta(self):
        np = namelist.NamelistParser(macros=('NBPROC', ))
        nset = np.parse(DIRTYNAM)
        np_d = namelist.NamelistParser(macros=('MYMACRO1', 'MYMACRO2'))
        nset_d = np_d.parse(NAMBLOCK1 + ' &ANOTHERBLOCK\n TOTO="Truc"\n/')
        nset.merge(nset_d)
        self.assertNotIn('C', nset['MyNamelistTest'])
        self.assertIn('C', nset['MySecondOne'])
        self.assertSetEqual(nset['MyNamelistTest'].rmkeys(), set(['C', 'GRUIK']))
        self.assertEqual(nset['MyNamelistTest'].A, list((25, 30, 15)))
        self.assertEqual(nset['ANOTHERBLOCK'].TOTO, 'Truc')
        nset.setmacro('MYMACRO1', 1)
        self.assertTrue(re.search('M1B=1,', nset.dumps()))
        self.assertTrue(re.search('M1=1,', nset.dumps()))
        self.assertTrue(re.search('M2=MYMACRO2,', nset.dumps()))
        self.assertTrue(re.search('M3=__SOMETHINGNEW__,', nset.dumps()))


if __name__ == '__main__':
    main(verbosity=2)
