#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import unittest

from bronx.stdtypes.date import Date, Time, Month
import footprints
from footprints.util import rangex

from common.tools.conftools import CouplingOffsetConfPrepareError, \
    CouplingOffsetConfRefillError, CouplingOffsetConfError


class Coupling3DVConfToolTest(unittest.TestCase):
    """Test data from Arome 3D-var France 1hr cycle + with some changes to make it more insane !"""

    _BASE = {'assim': {'00': '18', '01': '00', '02': '00', '03': '00', '04': '00',
                       '05': '00', '06': '00', '07': '06', '08': '06', '09': '06',
                       '10': '06', '11': '06', '12': '06', '13': '12', '14': '12',
                       '15': '12', '16': '12', '17': '12', '18': '12', '19': '18',
                       '20': '18', '21': '18', '22': '18', '23': '18'},
             'production': {'00': '00', '03': '00', '06': '06', '09': '06',
                            '12': '12', '15': '12', '18': '18', '21': '18'}}
    _VAPP = {'assim': {'22': 'arpege', '02': 'arpege', '03': 'arpege',
                       '00': 'arpege', '01': 'arpege', '06': 'arpege',
                       '07': 'arpege', '04': 'arpege', '05': 'arpege',
                       '08': 'arpege', '09': 'arpege', '20': 'arpege',
                       '21': 'arpege', '11': 'arpege', '10': 'arpege',
                       '13': 'arpege', '12': 'arpege', '15': 'arpege',
                       '14': 'arpege', '17': 'arpege', '16': 'arpege',
                       '19': 'arpege', '18': 'arpege', '23': 'arpege'},
             'production': {'03': 'arpege', '00': 'arpege', '12': 'arpege',
                            '15': 'arpege', '21': 'arpege', '18': 'arpege',
                            '09': 'arpege', '06': 'arpege'}}
    _VCONF = {'assim': {'22': '4dvarfr', '02': '4dvarfr', '03': '4dvarfr',
                        '00': '4dvarfr', '01': '4dvarfr', '06': '4dvarfr',
                        '07': '4dvarfr', '04': '4dvarfr', '05': '4dvarfr',
                        '08': '4dvarfr', '09': '4dvarfr', '20': '4dvarfr',
                        '21': '4dvarfr', '11': '4dvarfr', '10': '4dvarfr',
                        '13': '4dvarfr', '12': '4dvarfr', '15': '4dvarfr',
                        '14': '4dvarfr', '17': '4dvarfr', '16': '4dvarfr',
                        '19': '4dvarfr', '18': '4dvarfr', '23': '4dvarfr'},
              'production': {'03': '4dvarfr', '00': 'courtfr', '12': '4dvarfr',
                             '15': '4dvarfr', '21': '4dvarfr', '18': '4dvarfr',
                             '09': '4dvarfr', '06': '4dvarfr'}}
    _CUTOFF = {'assim': {'22': 'production', '02': 'production', '03': 'production',
                         '00': 'assim', '01': 'production', '06': 'assim',
                         '07': 'production', '04': 'production', '05': 'assim',
                         '08': 'production', '09': 'production', '20': 'production',
                         '21': 'production', '11': 'assim', '10': 'production',
                         '13': 'production', '12': 'assim', '15': 'production',
                         '14': 'production', '17': 'assim', '16': 'production',
                         '19': 'production', '18': 'assim', '23': 'assim'},
               'production': {'03': 'production', '00': 'production', '12': 'production',
                              '15': 'production', '21': 'production', '18': 'production',
                              '09': 'production', '06': 'production'}}
    _STEPS = {'assim': {'22': '1-1-1', '02': '1-1-1', '03': '1-1-1', '00': '1-1-1',
                        '01': '1-1-1', '06': '1-1-1', '07': '1-1-1', '04': '1-1-1',
                        '05': '1-1-1', '08': '1-1-1', '09': '1-1-1', '20': '1-1-1',
                        '21': '1-1-1', '11': '1-1-1', '10': '1-1-1', '13': '1-1-1',
                        '12': '1-1-1', '15': '1-1-1', '14': '1-1-1', '17': '1-1-1',
                        '16': '1-1-1', '19': '1-1-1', '18': '1-1-1', '23': '1-1-1'},
              'production': {'03': '1-12-1', '00': '1-42-1', '12': '1-36-1',
                             '15': '1-12-1', '21': '1-12-1', '18': '1-36-1',
                             '09': '1-12-1', '06': '1-36-1'}}

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.wtool = footprints.proxy.conftool(kind='couplingoffset',
                                               cplhhbase=self._BASE, cplvapp=self._VAPP,
                                               cplvconf=self._VCONF, cplcutoff=self._CUTOFF,
                                               cplsteps=self._STEPS, verbose=False)

    def test_weird_coupling_prepare(self):
        self.assertListEqual(self.wtool.prepare_terms('2017010100', 'production', 'arpege', 'courtfr'),
                             list([Time(h) for h in rangex('1-42-1')]))
        self.assertListEqual(self.wtool.prepare_terms('2017010100', 'production', 'arpege', '4dvarfr'),
                             list([Time(h) for h in rangex('2-15-1')]))

    def test_weird_coupling_use(self):
        self.assertEqual(self.wtool.coupling_offset('2017010100', 'production'),
                         Time(0))
        self.assertEqual(self.wtool.coupling_date('2017010100', 'production'),
                         Date('2017010100'))
        self.assertListEqual(self.wtool.coupling_terms('2017010100', 'production'),
                             list([Time(h) for h in rangex('1-42-1', shift=0)]))
        self.assertEqual(self.wtool.coupling_cutoff('2017010100', 'production'),
                         'production')
        self.assertEqual(self.wtool.coupling_vapp('2017010100', 'production'),
                         'arpege')
        self.assertEqual(self.wtool.coupling_vconf('2017010100', 'production'),
                         'courtfr')

        self.assertEqual(self.wtool.coupling_offset('2017010103', 'production'),
                         Time(3))
        self.assertEqual(self.wtool.coupling_date('2017010103', 'production'),
                         Date('2017010100'))
        self.assertListEqual(self.wtool.coupling_terms('2017010103', 'production'),
                             list([Time(h) for h in rangex('1-12-1', shift=3)]))
        self.assertEqual(self.wtool.coupling_cutoff('2017010103', 'production'),
                         'production')
        self.assertEqual(self.wtool.coupling_vapp('2017010103', 'production'),
                         'arpege')
        self.assertEqual(self.wtool.coupling_vconf('2017010103', 'production'),
                         '4dvarfr')

        self.assertEqual(self.wtool.coupling_offset('2017010100', 'assim'),
                         Time(6))
        self.assertEqual(self.wtool.coupling_date('2017010100', 'assim'),
                         Date('2016123118'))
        self.assertListEqual(self.wtool.coupling_terms('2017010100', 'assim'),
                             list([Time(h) for h in rangex('1-1-1', shift=6)]))
        self.assertEqual(self.wtool.coupling_cutoff('2017010100', 'assim'),
                         'assim')
        self.assertEqual(self.wtool.coupling_vapp('2017010100', 'assim'),
                         'arpege')
        self.assertEqual(self.wtool.coupling_vconf('2017010100', 'assim'),
                         '4dvarfr')

    def test_weird_coupling_refill(self):
        self.assertEqual(self.wtool.refill_terms('2016123120', 'assim', 'arpege', '4dvarfr'),
                         {'date': {str(Date(2016, 12, 31, 18, 0)): [Time(6, 0), Time(7, 0)]}})
        self.assertEqual(self.wtool.refill_terms('2016123120', 'production', 'arpege', '4dvarfr'),
                         {'date': {str(Date(2016, 12, 31, 18, 0)): [Time(h) for h in rangex('3-15-1')]}})
        self.assertEqual(self.wtool.refill_terms('2016123123', 'assim', 'arpege', '4dvarfr'),
                         {'date': {str(Date(2016, 12, 31, 18, 0)): [Time(6, 0), Time(7, 0)]}})
        with self.assertRaises(CouplingOffsetConfRefillError):
            self.wtool.refill_terms('2016123123', 'production', 'arpege', '4dvarfr')
        self.assertEqual(self.wtool.refill_terms('2016123122', 'assim', 'arpege', '4dvarfr'),
                         {'date': {str(Date(2016, 12, 31, 18, 0)): [Time(6, 0), Time(7, 0)]}})
        self.assertEqual(self.wtool.refill_terms('2016123122', 'production', 'arpege', '4dvarfr'),
                         {'date': {str(Date(2016, 12, 31, 18, 0)): [Time(5, 0)]}})
        self.assertEqual(self.wtool.refill_terms('2017010100', 'assim', 'arpege', '4dvarfr'),
                         {'date': {str(Date(2016, 12, 31, 18, 0)): [Time(7, 0)],
                                   str(Date(2017, 1, 1, 0, 0)): [Time(6, 0), Time(7, 0)]}})
        self.assertEqual(self.wtool.refill_terms('2017010100', 'production', 'arpege', '4dvarfr'),
                         {'date': {str(Date(2017, 1, 1, 0, 0)): [Time(h) for h in rangex('2-15-1')]}})


class Coupling3DVbisConfToolTest(Coupling3DVConfToolTest):
    """Same tests but using the 'default' feature."""

    _VAPP = {'default': 'arpege'}

    _VCONF = {'default': '4dvarfr',
              'production': {'00': 'courtfr', }}

    _CUTOFF = {'default': 'production',
               'assim': {'00': 'assim', '06': 'assim', '05': 'assim',
                         '11': 'assim', '12': 'assim', '17': 'assim',
                         '18': 'assim', '23': 'assim'}, }

    _STEPS = {'assim': {'default': 1},
              'production': {'03': '1-12-1', '00': '1-42-1', '12': '1-36-1',
                             '15': '1-12-1', '21': '1-12-1', '18': '1-36-1',
                             '09': '1-12-1', '06': '1-36-1'}}


class Coupling3DVliteConfToolTest(unittest.TestCase):
    """Same tests but using the 'default' feature + XPID."""

    _HHLIST = {'assim': range(0, 24),
               'production': '12'}  # Compute only the 12h forecast

    _BASE = {'assim': {'00': '18', '01': '00', '02': '00', '03': '00', '04': '00',
                       '05': '00', '06': '00', '07': '06', '08': '06', '09': '06',
                       '10': '06', '11': '06', '12': '06', '13': '12', '14': '12',
                       '15': '12', '16': '12', '17': '12', '18': '12', '19': '18',
                       '20': '18', '21': '18', '22': '18', '23': '18'},
             'production': {'00': '00', '03': '00', '06': '06', '09': '06',
                            '12': '12', '15': '12', '18': '18', '21': '18'}}

    _VAPP = {'default': 'arpege'}

    _VCONF = {'default': '4dvarfr',
              'production': {'00': 'courtfr', }}

    _XPID = {'default': 'ABCD',
             'production': {'00': 'ABCE', },
             'assim': {'00': 'ABCF', }, }

    _CUTOFF = {'default': 'production',
               'assim': {'00': 'assim', '06': 'assim', '05': 'assim',
                         '11': 'assim', '12': 'assim', '17': 'assim',
                         '18': 'assim', '23': 'assim'}, }

    _STEPS = {'assim': {'default': 1},
              'production': {'03': '1-12-1', '00': '1-42-1', '12': '1-36-1',
                             '15': '1-12-1', '21': '1-12-1', '18': '1-36-1',
                             '09': '1-12-1', '06': '1-36-1'}}

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.wtool = footprints.proxy.conftool(kind='couplingoffset',
                                               cplhhlist=self._HHLIST,
                                               cplhhbase=self._BASE, cplvapp=self._VAPP,
                                               cplvconf=self._VCONF, cplcutoff=self._CUTOFF,
                                               cplsteps=self._STEPS, cplxpid=self._XPID,
                                               verbose=False, compute_on_refill = False)

    def test_weird_coupling_prepare(self):
        with self.assertRaises(CouplingOffsetConfPrepareError):
            self.wtool.prepare_terms('2017010100', 'production', 'arpege', 'courtfr', 'ABCE')
        self.assertListEqual(self.wtool.prepare_terms('2017010100', 'production', 'arpege', '4dvarfr', xpid='ABCD'),
                             list([Time(h) for h in rangex('2-5-1')]))
        self.assertListEqual(self.wtool.prepare_terms('2017010112', 'production', 'arpege', '4dvarfr', xpid='ABCD'),
                             list([Time(h) for h in rangex('1-36-1')]))
        self.assertListEqual(self.wtool.prepare_terms('2017010118', 'assim', 'arpege', '4dvarfr', xpid='ABCF'),
                             list([Time(h) for h in ('7', )]))
        self.assertListEqual(self.wtool.prepare_terms('2017010118', 'assim', 'arpege', '4dvarfr', xpid='ABCD'),
                             list([Time(h) for h in ('6', )]))
        self.assertListEqual(self.wtool.prepare_terms('2017010118', 'production', 'arpege', '4dvarfr', xpid='ABCD'),
                             list([Time(h) for h in rangex('2-5-1')]))

    def test_weird_coupling_use(self):
        self.assertEqual(self.wtool.coupling_offset('2017010112', 'production'),
                         Time(0))
        self.assertEqual(self.wtool.coupling_date('2017010112', 'production'),
                         Date('2017010112'))
        self.assertListEqual(self.wtool.coupling_terms('2017010112', 'production'),
                             list([Time(h) for h in rangex('1-36-1', shift=0)]))
        self.assertEqual(self.wtool.coupling_cutoff('2017010112', 'production'),
                         'production')
        self.assertEqual(self.wtool.coupling_vapp('2017010112', 'production'),
                         'arpege')
        self.assertEqual(self.wtool.coupling_vconf('2017010112', 'production'),
                         '4dvarfr')
        self.assertEqual(self.wtool.coupling_xpid('2017010112', 'production'),
                         'ABCD')

        self.assertEqual(self.wtool.coupling_offset('2017010100', 'assim'),
                         Time(6))
        self.assertEqual(self.wtool.coupling_date('2017010100', 'assim'),
                         Date('2016123118'))
        self.assertListEqual(self.wtool.coupling_terms('2017010100', 'assim'),
                             list([Time(h) for h in rangex('1-1-1', shift=6)]))
        self.assertEqual(self.wtool.coupling_cutoff('2017010100', 'assim'),
                         'assim')
        self.assertEqual(self.wtool.coupling_vapp('2017010100', 'assim'),
                         'arpege')
        self.assertEqual(self.wtool.coupling_vconf('2017010100', 'assim'),
                         '4dvarfr')
        self.assertEqual(self.wtool.coupling_xpid('2017010100', 'assim'),
                         'ABCF')

    def test_weird_coupling_refill(self):
        self.assertEqual(self.wtool.refill_terms('2016123120', 'assim', 'arpege', '4dvarfr', xpid='ABCD'),
                         {'date': {str(Date(2016, 12, 31, 18, 0)): [Time(6, 0), ]}})
        self.assertEqual(self.wtool.refill_terms('2016123120', 'assim', 'arpege', '4dvarfr', xpid='ABCF'),
                         {'date': {str(Date(2016, 12, 31, 18, 0)): [Time(7, 0), ]}})
        self.assertEqual(self.wtool.refill_terms('2016123120', 'production', 'arpege', '4dvarfr', xpid='ABCD'),
                         {'date': {str(Date(2016, 12, 31, 18, 0)): [Time(h) for h in rangex('4-5-1')]}})
        self.assertEqual(self.wtool.refill_terms('2016123123', 'assim', 'arpege', '4dvarfr', xpid='ABCF'),
                         {'date': {str(Date(2016, 12, 31, 18, 0)): [Time(7, 0)]}})
        with self.assertRaises(CouplingOffsetConfRefillError):
            self.wtool.refill_terms('2016123123', 'production', 'arpege', '4dvarfr', xpid='ABCD')
        with self.assertRaises(CouplingOffsetConfRefillError):
            self.wtool.refill_terms('2016123122', 'production', 'arpege', '4dvarfr', xpid='ABCD')
        self.assertEqual(self.wtool.refill_terms('2017010100', 'assim', 'arpege', '4dvarfr', xpid='ABCD'),
                         {'date': {str(Date(2017, 1, 1, 0, 0)): [Time(6, 0), Time(7, 0)]}})
        self.assertEqual(self.wtool.refill_terms('2017010100', 'production', 'arpege', '4dvarfr', xpid='ABCD'),
                         {'date': {str(Date(2017, 1, 1, 0, 0)): [Time(h) for h in rangex('2-5-1')]}})


class CouplingAggConfToolTest(unittest.TestCase):
    """Same tests but using the 'default' feature + XPID."""

    _HHLIST = {'assim': range(0, 24),
               'production': (0, 12)}  # Compute only the 12h forecast

    _BASE = {'assim': {'00': '18', '01': '00', '02': '00', '03': '00', '04': '00',
                       '05': '00', '06': '00', '07': '06', '08': '06', '09': '06',
                       '10': '06', '11': '06', '12': '06', '13': '12', '14': '12',
                       '15': '12', '16': '12', '17': '12', '18': '12', '19': '18',
                       '20': '18', '21': '18', '22': '18', '23': '18'},
             'production': {'00': '00', '03': '00', '06': '06', '09': '06',
                            '12': '12', '15': '12', '18': '18', '21': '18'}}

    _AL1_BASE = {'assim': {'00': '12', '01': '18', '02': '18', '03': '18', '04': '18',
                           '05': '18', '06': '18', '07': '00', '08': '00', '09': '00',
                           '10': '00', '11': '00', '12': '00', '13': '06', '14': '06',
                           '15': '06', '16': '06', '17': '06', '18': '06', '19': '12',
                           '20': '12', '21': '12', '22': '12', '23': '12'},
                 'production': {'00': '00', '03': '18', '06': '00', '09': '00',
                                '12': '06', '15': '06', '18': '12', '21': '12'}}

    _AL2_BASE = {'assim': {'00': '12', '01': '18', '02': '18', '03': '18', '04': '18',
                           '05': '18', '06': '18', '07': '00', '08': '00', '09': '00',
                           '10': '00', '11': '00', '12': '00', '13': '06', '14': '06',
                           '15': '06', '16': '06', '17': '06', '18': '06', '19': '12',
                           '20': '12', '21': '12', '22': '12', '23': '12'},
                 'production': {'00': '18', '03': '18', '06': '00', '09': '00',
                                '12': '06', '15': '06', '18': '12', '21': '12'}}

    _VAPP = {'default': 'arpege'}

    _VCONF = {'default': '4dvarfr',
              'production': {'00': 'courtfr', }}

    _AL1_VCONF = {'default': '4dvarfr', }

    _XPID = {'default': 'ABCD',
             'production': {'00': 'ABCE', },
             'assim': {'00': 'ABCF', }, }

    _CUTOFF = {'default': 'production',
               'assim': {'00': 'assim', '06': 'assim', '05': 'assim',
                         '11': 'assim', '12': 'assim', '17': 'assim',
                         '18': 'assim', '23': 'assim'}, }

    _STEPS = {'assim': {'default': 1},
              'production': {'03': '1-12-1', '00': '1-42-1', '12': '1-36-1',
                             '15': '1-12-1', '21': '1-12-1', '18': '1-36-1',
                             '09': '1-12-1', '06': '1-36-1'}}

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.wtoolN = footprints.proxy.conftool(kind='couplingoffset',
                                                cplhhlist=self._HHLIST,
                                                cplhhbase=self._BASE, cplvapp=self._VAPP,
                                                cplvconf=self._VCONF, cplcutoff=self._CUTOFF,
                                                cplsteps=self._STEPS, cplxpid=self._XPID,
                                                verbose=False, compute_on_refill = False)
        self.wtoolA1 = footprints.proxy.conftool(kind='couplingoffset',
                                                 cplhhlist=self._HHLIST,
                                                 cplhhbase=self._AL1_BASE, cplvapp=self._VAPP,
                                                 cplvconf=self._AL1_VCONF, cplcutoff=self._CUTOFF,
                                                 cplsteps=self._STEPS, cplxpid=self._XPID,
                                                 verbose=False, compute_on_refill = False)
        self.wtoolA2 = footprints.proxy.conftool(kind='couplingoffset',
                                                 cplhhlist=self._HHLIST,
                                                 cplhhbase=self._AL2_BASE, cplvapp=self._VAPP,
                                                 cplvconf=self._AL1_VCONF, cplcutoff=self._CUTOFF,
                                                 cplsteps=self._STEPS, cplxpid=self._XPID,
                                                 verbose=False, compute_on_refill = False)
        self.wtoolKO = footprints.proxy.conftool(kind='couplingoffset',
                                                 cplhhlist=self._HHLIST,
                                                 cplhhbase=self._BASE, cplvapp=self._VAPP,
                                                 cplvconf=self._VCONF, cplcutoff=self._CUTOFF,
                                                 cplsteps=self._STEPS, cplxpid=self._XPID,
                                                 verbose=False, refill_cutoff='production')
        self.wtoolAggN = footprints.proxy.conftool(kind='aggcouplingoffset',
                                                   nominal = [self.wtoolN, ],
                                                   alternate = [self.wtoolA1, self.wtoolA2],
                                                   use_alternates = False)
        self.wtoolAggA = footprints.proxy.conftool(kind='aggcouplingoffset',
                                                   nominal = [self.wtoolN, ],
                                                   alternate = [self.wtoolA1, self.wtoolA2],
                                                   use_alternates = True)

    def test_agg_consistency(self):
        footprints.proxy.conftool(kind='aggcouplingoffset',
                                  nominal = [self.wtoolN, ],
                                  alternate = [self.wtoolA1, self.wtoolKO],
                                  use_alternates = False)
        with self.assertRaises(CouplingOffsetConfError):
            footprints.proxy.conftool(kind='aggcouplingoffset',
                                      nominal = [self.wtoolN, ],
                                      alternate = [self.wtoolA1, self.wtoolKO],
                                      use_alternates = True)

    def test_weird_coupling_prepare_aggn(self):
        self.assertListEqual(self.wtoolAggN.prepare_terms('2017010100', 'production', 'arpege', 'courtfr', xpid='ABCE'),
                             list([Time(h) for h in rangex('1-42-1')]))
        self.assertListEqual(self.wtoolAggN.prepare_terms('2017010100', 'production', 'arpege', '4dvarfr', xpid='ABCD'),
                             list([Time(h) for h in rangex('2-5-1')]))
        self.assertListEqual(self.wtoolAggN.prepare_terms('2017010112', 'production', 'arpege', '4dvarfr', xpid='ABCD'),
                             list([Time(h) for h in rangex('1-36-1')]))
        self.assertListEqual(self.wtoolAggN.prepare_terms('2017010118', 'assim', 'arpege', '4dvarfr', xpid='ABCF'),
                             list([Time(h) for h in ('7', )]))
        self.assertListEqual(self.wtoolAggN.prepare_terms('2017010118', 'assim', 'arpege', '4dvarfr', xpid='ABCD'),
                             list([Time(h) for h in ('6', )]))
        self.assertListEqual(self.wtoolAggN.prepare_terms('2017010118', 'production', 'arpege', '4dvarfr', xpid='ABCD'),
                             list([Time(h) for h in rangex('2-5-1')]))

    def test_weird_coupling_refill_aggn(self):
        self.assertListEqual(self.wtoolAggA.prepare_terms('2017010100', 'production', 'arpege', 'courtfr', xpid='ABCE'),
                             list([Time(h) for h in rangex('1-42-1')]))
        self.assertListEqual(self.wtoolAggA.prepare_terms('2017010100', 'production', 'arpege', '4dvarfr', xpid='ABCE'),
                             list([Time(h) for h in rangex('1-42-1')]))
        self.assertEqual(self.wtoolAggN.refill_terms('2016123120', 'assim', 'arpege', '4dvarfr', xpid='ABCF'),
                         {'date': {str(Date(2016, 12, 31, 18, 0)): [Time(7, 0), ]}})
        self.assertEqual(self.wtoolAggN.refill_terms('2016123120', 'production', 'arpege', '4dvarfr', xpid='ABCD'),
                         {'date': {str(Date(2016, 12, 31, 18, 0)): [Time(h) for h in rangex('4-5-1')]}})
        self.assertEqual(self.wtoolAggN.refill_terms('2016123123', 'assim', 'arpege', '4dvarfr', xpid='ABCF'),
                         {'date': {str(Date(2016, 12, 31, 18, 0)): [Time(7, 0)]}})
        with self.assertRaises(CouplingOffsetConfRefillError):
            self.wtoolAggN.refill_terms('2016123123', 'production', 'arpege', '4dvarfr', xpid='ABCD')
        with self.assertRaises(CouplingOffsetConfRefillError):
            self.wtoolAggN.refill_terms('2016123122', 'production', 'arpege', '4dvarfr', xpid='ABCD')
        self.assertEqual(self.wtoolAggN.refill_terms('2017010100', 'assim', 'arpege', '4dvarfr', xpid='ABCD'),
                         {'date': {str(Date(2017, 1, 1, 0, 0)): [Time(6, 0), Time(7, 0)]}})
        self.assertEqual(self.wtoolAggN.refill_terms('2017010100', 'production', 'arpege', '4dvarfr', xpid='ABCD'),
                         {'date': {str(Date(2017, 1, 1, 0, 0)): [Time(h) for h in rangex('2-5-1')]}})

    def test_weird_coupling_prepare_agga(self):
        self.assertListEqual(self.wtoolAggA.prepare_terms('2017010100', 'production', 'arpege', 'courtfr', xpid='ABCE'),
                             list([Time(h) for h in rangex('1-42-1')]))
        self.assertListEqual(self.wtoolAggA.prepare_terms('2017010100', 'production', 'arpege', '4dvarfr', xpid='ABCD'),
                             list([Time(h) for h in (2, 3, 4, 5, 8, 9, 10, 11)]))
        self.assertListEqual(self.wtoolAggA.prepare_terms('2017010106', 'production', 'arpege', '4dvarfr', xpid='ABCD'),
                             list([Time(h) for h in [2, 3, 4, 5, 7, 8, 9, 10, 11, 12] + rangex('13-42-1')]))
        self.assertListEqual(self.wtoolAggA.prepare_terms('2017010112', 'production', 'arpege', '4dvarfr', xpid='ABCD'),
                             list([Time(h) for h in rangex('1-36-1')]))
        self.assertListEqual(self.wtoolAggA.prepare_terms('2017010118', 'assim', 'arpege', '4dvarfr', xpid='ABCF'),
                             list([Time(h) for h in (7, )]))
        self.assertListEqual(self.wtoolAggA.prepare_terms('2017010118', 'assim', 'arpege', '4dvarfr', xpid='ABCD'),
                             list([Time(h) for h in (6, 12, 13)]))
        self.assertListEqual(self.wtoolAggA.prepare_terms('2017010118', 'production', 'arpege', '4dvarfr', xpid='ABCE'),
                             list([Time(h) for h in rangex('7-48-1')]))

    def test_weird_coupling_refill_agga(self):
        self.assertEqual(self.wtoolAggA.refill_terms('2016123120', 'assim', 'arpege', '4dvarfr', xpid='ABCD'),
                         {'date': {str(Date(2016, 12, 31, 18, 0)): [Time(6, 0), Time(12, 0), Time(13, 0)],
                                   str(Date(2016, 12, 31, 12, 0)): [Time(12, 0), ]}})
        self.assertEqual(self.wtoolAggA.refill_terms('2016123120', 'assim', 'arpege', '4dvarfr', xpid='ABCF'),
                         {'date': {str(Date(2016, 12, 31, 18, 0)): [Time(7, 0), ],
                                   str(Date(2016, 12, 31, 12, 0)): [Time(13, 0), ]}})
        self.assertEqual(self.wtoolAggA.refill_terms('2016123120', 'production', 'arpege', '4dvarfr', xpid='ABCD'),
                         {'date': {str(Date(2016, 12, 31, 18, 0)): [Time(h) for h in (4, 5, 8, 9, 10, 11)],
                                   str(Date(2016, 12, 31, 12, 0)): [Time(h) for h in rangex('10-11-1')]}})
        self.assertEqual(self.wtoolAggA.refill_terms('2016123123', 'assim', 'arpege', '4dvarfr', xpid='ABCF'),
                         {'date': {str(Date(2016, 12, 31, 18, 0)): [Time(7, 0)],
                                   str(Date(2016, 12, 31, 12, 0)): [Time(13, 0)]}})
        self.assertEqual(self.wtoolAggA.refill_terms('2016123123', 'production', 'arpege', '4dvarfr', xpid='ABCD'),
                         {'date': {str(Date(2016, 12, 31, 18, 0)): [Time(h) for h in (8, 9, 10, 11)]}})
        self.assertEqual(self.wtoolAggA.refill_terms('2016123122', 'production', 'arpege', '4dvarfr', xpid='ABCD'),
                         {'date': {str(Date(2016, 12, 31, 18, 0)): [Time(h) for h in (8, 9, 10, 11)]}})
        self.assertEqual(self.wtoolAggA.refill_terms('2017010100', 'assim', 'arpege', '4dvarfr', xpid='ABCD'),
                         {'date': {str(Date(2017, 1, 1, 0, 0)): [Time(h) for h in (6, 7, 12, 13)],
                                   str(Date(2016, 12, 31, 18, 0)): [Time(h) for h in (12, 13)]}})
        self.assertEqual(self.wtoolAggA.refill_terms('2017010100', 'production', 'arpege', '4dvarfr', xpid='ABCD'),
                         {'date': {str(Date(2017, 1, 1, 0, 0)): [Time(h) for h in (2, 3, 4, 5, 8, 9, 10, 11)],
                                   str(Date(2016, 12, 31, 18, 0)): [Time(h) for h in (8, 9, 10, 11)]}})


class CouplingBugConfToolTest(unittest.TestCase):
    """Check that inconsistencies are detected."""

    # Test data from Arome 3D-var France 1hr cycle + with some changes to make it more insane !
    _BASE = {'assim': {'00': '18', '01': '00', '02': '00', '03': '00', '04': '00',
                       '05': '00', '06': '00', '07': '06', '08': '06', '09': '06',
                       '10': '06', '11': '06', '12': '06', '13': '12', '14': '12',
                       '15': '12', '16': '12', '17': '12', '18': '12', '19': '18',
                       '20': '18', '21': '18', '22': '18', '23': '18'},
             'production': {'00': '00', '03': '00', '06': '06', '09': '06',
                            '12': '12', '15': '12', '18': '18', '21': '18'}}

    _VAPP = {'default': 'arpege'}
    _VCONF = {'default': '4dvarfr', }
    _CUTOFF = {'default': 'production', }

    # One of the steps is mising in the production part so it crashes...
    _STEPS = {'assim': {'default': 1},
              'production': {'03': '1-12-1', '00': '1-42-1', '12': '1-36-1',
                             '15': '1-12-1', '21': '1-12-1', '18': '1-36-1',
                             '09': '1-12-1', }}

    def test_weird_coupling_refill(self):
        with self.assertRaises(ValueError):
            self.wtool = footprints.proxy.conftool(kind='couplingoffset',
                                                   cplhhbase=self._BASE, cplvapp=self._VAPP,
                                                   cplvconf=self._VCONF, cplcutoff=self._CUTOFF,
                                                   cplsteps=self._STEPS, verbose=False)


class CouplingLargeOffsetConfToolTest(unittest.TestCase):
    """Test with very long offsets (up to 36hrs)."""

    _BASE = {'assim': {0: 12, 6: 12, 12: 12, 18: 0},
             'production': {0: 0, 6: 12, 12: 12, 18: 12}, }
    _DAYOFF = {'assim': {0: 0, 6: 0, 12: 1, 18: 0},
               'production': {0: 1, 6: 0, 12: 1, 18: 1}, }

    _VAPP = {'default': 'arpege'}
    _VCONF = {'default': '4dvarfr', }
    _MODEL = {'assim': {'default': 'oops'},
              'production': {'default': 'arpege'}, }
    _CUTOFF = {'default': 'production', }
    _STEPS = {'default': '0-6-1',
              'production': {0: '0-102-1', 6: '0-12-1', 12: '0-24-1', 18: '0-12-1'}}

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.wtool = footprints.proxy.conftool(kind='couplingoffset',
                                               cplhhbase=self._BASE, cplvapp=self._VAPP,
                                               cplvconf=self._VCONF, cplcutoff=self._CUTOFF,
                                               cplsteps=self._STEPS, cpldayoff=self._DAYOFF,
                                               cplmodel=self._MODEL,
                                               verbose=False)

    def test_weird_coupling_prepare(self):
        self.assertListEqual(self.wtool.prepare_terms('2017010112', 'production', 'arpege', '4dvarfr', 'oops'),
                             list([Time(h) for h in rangex('12-30-1')]))
        self.assertListEqual(self.wtool.prepare_terms('2017010112', 'production', 'arpege', '4dvarfr'),
                             list([Time(h) for h in rangex('18-48-1')]))
        self.assertListEqual(self.wtool.prepare_terms('2017010100', 'production', 'arpege', '4dvarfr', 'oops'),
                             list([Time(h) for h in rangex('18-24-1')]))
        self.assertListEqual(self.wtool.prepare_terms('2017010100', 'production', 'arpege', '4dvarfr', 'arpege'),
                             list([Time(h) for h in rangex('24-126-1')]))

    def test_weird_coupling_use(self):
        self.assertEqual(self.wtool.coupling_offset('2017010100', 'production'),
                         Time(24))
        self.assertEqual(self.wtool.coupling_date('2017010100', 'production'),
                         Date('2016123100'))
        self.assertListEqual(self.wtool.coupling_terms('2017010100', 'production'),
                             list([Time(h) for h in rangex('24-126-1', shift=0)]))
        self.assertEqual(self.wtool.coupling_cutoff('2017010100', 'production'),
                         'production')
        self.assertEqual(self.wtool.coupling_vapp('2017010100', 'production'),
                         'arpege')
        self.assertEqual(self.wtool.coupling_vconf('2017010100', 'production'),
                         '4dvarfr')

        self.assertEqual(self.wtool.coupling_offset('2017010106', 'production'),
                         Time(18))
        self.assertEqual(self.wtool.coupling_date('2017010106', 'production'),
                         Date('2016123112'))
        self.assertEqual(self.wtool.coupling_model('2017010106', 'production'),
                         'arpege')
        self.assertListEqual(self.wtool.coupling_terms('2017010106', 'production'),
                             list([Time(h) for h in rangex('18-30-1', shift=0)]))

    def test_weird_coupling_refill(self):
        self.assertEqual(self.wtool.refill_terms('2016123118', 'production', 'arpege', '4dvarfr', 'arpege'),
                         {'date': {str(Date(2016, 12, 31, 12, 0)): [Time(h) for h in rangex('18-48-1')],
                                   str(Date(2016, 12, 31, 0, 0)): [Time(h) for h in rangex('24-126-1')],
                                   }})
        self.assertEqual(self.wtool.refill_terms('2016123118', 'production', 'arpege', '4dvarfr', 'oops'),
                         {'date': {str(Date(2016, 12, 31, 12, 0)): [Time(h) for h in rangex('12-30-1')],
                                   str(Date(2016, 12, 31, 0, 0)): [Time(h) for h in rangex('18-24-1')],
                                   }})
        self.assertEqual(self.wtool.refill_terms('2016123112', 'production', 'arpege', '4dvarfr', 'arpege'),
                         {'date': {str(Date(2016, 12, 31, 12, 0)): [Time(h) for h in rangex('18-30-1')],
                                   str(Date(2016, 12, 31, 0, 0)): [Time(h) for h in rangex('24-126-1')],
                                   str(Date(2016, 12, 30, 12, 0)): [Time(h) for h in rangex('30-42-1')],
                                   }})
        self.assertListEqual(self.wtool.refill_dates('2016123112', 'production', 'arpege', '4dvarfr'),
                             ['2016-12-30T12:00:00Z', '2016-12-31T12:00:00Z', '2016-12-31T00:00:00Z'])
        self.assertListEqual(self.wtool.refill_months('2016123112', 'production', 'arpege', '4dvarfr'),
                             [Month(12, year=2016), Month(1, year=2017)])


if __name__ == "__main__":
    unittest.main()
