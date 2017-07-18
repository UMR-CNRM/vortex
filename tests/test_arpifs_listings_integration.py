#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from contextlib import contextmanager
import os
import six
import sys
import unittest

import arpifs_listings

import footprints
import vortex
from vortex.tools import listings

DATADIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))

_NODIFFS = """\
Norms   check succeeded for all steps.
JoTable check succeeded for: SCREENING JOB    T1198 NCONF=     1 NSIM4D=     0 NUPTRA=     0
"""

_BIGDIFFS = """\
Norms   check succeeded for steps:
  (NSIM4D=None, subroutine=OPENFA, NSTEP=None)
  (NSIM4D=None, subroutine=STEPO, NSTEP=0, CDCONF=T00000000)
  (NSIM4D=None, subroutine=OPENFA, NSTEP=60)
  (NSIM4D=0, subroutine=CNT4, NSTEP=0 (None))
Norms   check FAILED    for steps:
  (NSIM4D=None, subroutine=STEPO, NSTEP=30, CDCONF=AAAA0VDAA)
  (NSIM4D=0, subroutine=STEPO, NSTEP=0, CDCONF=A00000000)
JoTable check FAILED    for: SCREENING JOB    T1198 NCONF=     1 NSIM4D=     0 NUPTRA=     0
  > SYNOP, Land stations and ships   > French RADOME                    > U    : d_n=-1         d_jo=-1.000000
  > SYNOP, Land stations and ships   > French RADOME                    > U10  : d_n=-1         d_jo=-3.000000
  > SYNOP, Land stations and ships   > French RADOME                    > Q    : d_n=-1         d_jo=-1.000000
  > DRIBU, Drifing Buoys             > DRIBU Buoy Report                > U10  : d_n=-2         d_jo=-2.000000
  > SATEM, Satellite sounding data   > JPSS     0   224 SENSOR=ATMS     > RAD  : d_n=-1031184   d_jo=-444350.465813
  > SATEM, Satellite sounding data   > HIMAWARI 8   173 SENSOR=AHI      > RAD  : d_n=2491340    d_jo=3395197.925141
"""

L1SIZE = 3000


def _find_testfile(fname):
        return os.path.join(DATADIR, fname)


@contextmanager
def capture(command, *args, **kwargs):
    out, sys.stdout = sys.stdout, six.StringIO()
    try:
        command(*args, **kwargs)
        sys.stdout.seek(0)
        yield sys.stdout.read()
    finally:
        sys.stdout = out


class TestArpIfsIntegration(unittest.TestCase):

    def test_addons_diff(self):
        addon = listings.ArpIfsListingsTool(kind='arpifs_listings',
                                            sh=vortex.ticket().system())
        # Listings are equal
        rc = addon.arpifslist_diff(_find_testfile('listing_screen_li1'),
                                   _find_testfile('listing_screen_li1'))
        self.assertTrue(rc)
        self.assertRegexpMatches(str(rc), r"rc=1")
        self.assertRegexpMatches(str(rc.result), r"NormsOk=1 JoTablesOk=1")
        with capture(rc.result.differences) as output:
            self.assertEqual(output, _NODIFFS)
        # Listings are different
        rc = addon.arpifslist_diff(_find_testfile('listing_screen_li1'),
                                   _find_testfile('listing_screen_li2'))
        self.assertFalse(rc)
        self.assertRegexpMatches(str(rc), r"rc=0")
        self.assertRegexpMatches(str(rc.result), r"NormsOk=0 JoTablesOk=0")
        with capture(rc.result.differences) as output:
            self.assertEqual(output, _BIGDIFFS)

    def test_adapter(self):
        adapt = footprints.proxy.dataformat(filename=_find_testfile('listing_screen_li1'),
                                            format='ARPIFSLIST')
        self.assertEqual(len(adapt), L1SIZE)
        self.assertTrue(adapt.end_is_reached)
        self.assertIsInstance(adapt.normset, arpifs_listings.norms.NormsSet)
        self.assertEqual(len(adapt.normset), 7)
        self.assertIsInstance(adapt.jotables, arpifs_listings.jo_tables.JoTables)
        self.assertEqual(len(adapt.jotables), 1)

if __name__ == "__main__":
    unittest.main()
