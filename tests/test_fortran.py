#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from decimal import Decimal
from StringIO import StringIO
from unittest import TestCase, main

from vortex.tools import fortran
from common.data.namelists import NamelistContent, NamelistContentError
import re


DIRTYNAM = """\
! This is a test namelist
&MySecondOne C=.TRUE./
&MyNamelistTest
title = 'Coordinates/t=10',
A= 25,30, ! This is a parameter
x = 300.d0, y=628.318, z=0d0,
c=(0,1), boz=B'11', stest=NBPROC
/
"""

CLEANEDNAM = """\
 &MYNAMELISTTEST
   TITLE ='Coordinates/t=10',
   A=25,30,
   X =300.,
   Y=628.318,
   Z=0.,
   C=(0.,1.),
   BOZ=3,
   STEST=NBPROC,
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
M2=MYMACRO2,
A=25,30,15
C=--,
/
"""


class UtFortran(TestCase):

    def setUp(self):
        self.lp = fortran.LiteralParser()

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
        self._parse_tester(".true._2", True)                # With kind.
        self._parse_tester(".truea", ValueError)

    def test_encode(self):
        self._encode_tester(1, '1')
        self._encode_tester(1243523, '1243523')
        self._encode_tester(1., '1.')
        self._encode_tester(1e-76, '1.0D-76')
        self._encode_tester(1e124, '1.0D+124')
        self._encode_tester(complex(1, 1), '(1.,1.)')
        self._encode_tester("machin", "'machin'")
        self._encode_tester("mach'in", '"mach\'in"')
        self._encode_tester("mach\"in", '\'mach"in\'')
        self._encode_tester("'mach\"in", '"\'mach""in"')
        self._encode_tester(True, ".TRUE.")
        self._encode_tester(False, ".FALSE.")

    def test_namblock(self):
        np = fortran.NamelistParser(macros=('MYMACRO1', 'MYMACRO2'))
        nb_res = np.parse(NAMBLOCK1).as_dict()['MyNamelistTest']
        # Inspect the newly created object
        self.assertEqual(nb_res.name, 'MyNamelistTest')
        self.assertEqual(len(nb_res), 4)
        self.assertEqual(['M1', 'M1B', 'M2', 'A'], list(nb_res))  # Iterator test
        self.assertEqual(['M1', 'M1B', 'M2', 'A'], nb_res.keys())
        self.assertEqual(nb_res.A, [25, 30, 15])
        self.assertEqual(nb_res["A"], [25, 30, 15])
        self.assertEqual(nb_res.M1, '$MYMACRO1')
        self.assertEqual(nb_res.M1b, "'MYMACRO1'")
        nb_res.addmacro('MYMACRO1', 'Toto')
        self.assertListEqual(dict(MYMACRO1=None, MYMACRO2=None).keys(),
                             nb_res.macros())
        # Test add/modify/delete of a namelist variable
        nb_res.B = 1.2
        self.assertEqual(nb_res["B"], 1.2)
        nb_res["B"] = 1.2
        self.assertEqual(nb_res["B"], 1.2)
        self.assertEqual(len(nb_res), 5)
        del nb_res.B
        self.assertFalse('B' in nb_res)
        self.assertIs(nb_res.get('B', None), None)
        # Check that the substitution works
        dumped_ori = """\
 &MYNAMELISTTEST
   M1='Toto',
   M1B='Toto',
   M2=MYMACRO2,
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

    def test_nampaser_full(self):
        np = fortran.NamelistParser(macros=('NBPROC', ))
        ori = StringIO()
        ori.write(DIRTYNAM)
        parse_res = np.parse(ori)
        self.assertSetEqual(set(parse_res.iterkeys()),
                            set(['MyNamelistTest', 'MySecondOne']))
        self.assertEqual(parse_res.dumps(), CLEANEDNAM)


class DummyNamContainer(object):

    def __init__(self, thetxt=DIRTYNAM):
        self.mytxt = thetxt

    def rewind(self):
        pass

    def read(self):
        return self.mytxt

    def close(self):
        pass

    def write(self, thetxt):
        self.mytxt = thetxt


class UtNamelistContent(TestCase):

    def setUp(self):
        self.cont = DummyNamContainer()
        self.namcontent = NamelistContent()
        self.namcontent.slurp(self.cont)

    def test_basics(self):
        self.namcontent.rewrite(self.cont)
        self.assertEqual(self.cont.mytxt, CLEANEDNAM)
        nb = self.namcontent.newblock('MYNEWBLOCK')
        nb.A = 1
        self.assertEqual(self.namcontent['MYNEWBLOCK'].A, 1)
        nb = self.namcontent.newblock()
        nb.A = 1
        self.assertEqual(self.namcontent['AUTOBLOCK001'].A, 1)
        # Default macros
        self.namcontent.setmacro('NBPROC', 9999)
        self.assertTrue(re.search('STEST=9999,', self.namcontent.dumps()))
        # Error
        namcontent2 = NamelistContent()
        cont2 = DummyNamContainer("&NAMGLURP\nMACHIN=EXISTEPAS,\n/")
        with self.assertRaises(NamelistContentError):
            namcontent2.slurp(cont2)
        cont2 = DummyNamContainer("GLURP")
        with self.assertRaises(NamelistContentError):
            namcontent2.slurp(cont2)

    def test_merge(self):
        # Test removes
        self.namcontent.merge({}, rmkeys=('A ', 'z'), rmblocks=('MySecondOne', ))
        self.assertSetEqual(set(self.namcontent.keys()), set(('MyNamelistTest', )))
        self.assertNotIn('A ', self.namcontent['MyNamelistTest'])
        self.assertNotIn('Z', self.namcontent['MyNamelistTest'])
        # Test clear
        self.namcontent.merge({}, clblocks=('MyNamelistTest', ))
        self.assertEqual(len(self.namcontent['MyNamelistTest']), 0)

    def test_mergedelta(self):
        np = fortran.NamelistParser(macros=('MYMACRO1', 'MYMACRO2'))
        nblocks = np.parse(NAMBLOCK1 + ' &ANOTHERBLOCK\n TOTO="Truc"\n/')
        self.namcontent.merge(nblocks)
        self.assertNotIn('C', self.namcontent['MyNamelistTest'])
        self.assertIn('C', self.namcontent['MySecondOne'])
        self.assertEqual(self.namcontent['MyNamelistTest'].A, list((25, 30, 15)))
        self.assertEqual(self.namcontent['ANOTHERBLOCK'].TOTO, 'Truc')
        self.namcontent.setmacro('MYMACRO1', 1)
        self.assertTrue(re.search('M1B=1,', self.namcontent.dumps()))
        self.assertTrue(re.search('M1=1,', self.namcontent.dumps()))
        self.assertTrue(re.search('M2=MYMACRO2,', self.namcontent.dumps()))

if __name__ == '__main__':
    main(verbosity=2)
