#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import contextlib
from unittest import TestCase, main

from bronx.datagrip import namelist as fortran
from common.data.namelists import NamelistContent, NamelistContentError
import re


DIRTYNAM = """\
! This is a test namelist
&MySecondOne C=.TRUE./
&MyNamelistTest
title = 'Coordinates/t=10',
A= 25,30, ! This is a parameter
x = 300.d0, y=628.318, z=0d0,
B(10 )=1,
c=(0,1), boz=B'11', stest=NBPROC,
B(2)=2,
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
/
"""


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
    
    @contextlib.contextmanager
    def preferred_decoding(self, *kargs, **kwargs):
        yield
    


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
        self.assertSetEqual(set(self.namcontent.keys()), set(('MYNAMELISTTEST', )))
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
        self.assertTrue(re.search('M3=__SOMETHINGNEW__,', self.namcontent.dumps()))


if __name__ == '__main__':
    main(verbosity=2)
