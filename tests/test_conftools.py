import unittest

from bronx.fancies import loggers
from bronx.stdtypes.date import Date, Time, Month
import footprints
from footprints.util import rangex

from common.tools.conftools import CouplingOffsetConfPrepareError, \
    CouplingOffsetConfRefillError, CouplingOffsetConfError, \
    TimeSerieInputFinderError

from intairpol.tools.conftools import HHDict, MocageDomainsConfTool, MocageDomainsConfError

tloglevel = 'critical'


# ------------------------------------------------------------------------------
# The generic Arpege/Arome coupling tools

@loggers.unittestGlobalLevel(tloglevel)
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
              'production': {'03': '1-12-1', '00': ['1-21-1', '22-42-1'], '12': '1-36-1',
                             '15': '1-12-1', '21': '1-12-1', '18': '1-36-1',
                             '09': '1-12-1', '06': '1-36-1'}}

    _FINALTERM = None

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.wtool = footprints.proxy.conftool(kind='couplingoffset',
                                               cplhhbase=self._BASE, cplvapp=self._VAPP,
                                               cplvconf=self._VCONF, cplcutoff=self._CUTOFF,
                                               cplsteps=self._STEPS, finalterm=self._FINALTERM,
                                               verbose=False)

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
        # Implicitly: refill_cutoff=assim (default)
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
        with self.assertRaises(CouplingOffsetConfRefillError):
            self.wtool.refill_terms('2017010100', 'production', 'arpege', 'courtfr')
        self.assertEqual(self.wtool.refill_terms('2017010100', 'assim', 'arpege', '4dvarfr'),
                         {'date': {str(Date(2016, 12, 31, 18, 0)): [Time(7, 0)],
                                   str(Date(2017, 1, 1, 0, 0)): [Time(6, 0), Time(7, 0)]}})
        self.assertEqual(self.wtool.refill_terms('2017010100', 'production', 'arpege', '4dvarfr'),
                         {'date': {str(Date(2017, 1, 1, 0, 0)): [Time(h) for h in rangex('2-15-1')]}})

    def test_weird_coupling_refill_a(self):
        self.assertEqual(self.wtool.refill_terms('2016123120', 'assim', 'arpege', '4dvarfr',
                                                 refill_cutoff='all'),
                         {'date': {str(Date(2016, 12, 31, 18, 0)): [Time(6, 0), Time(7, 0)]}})
        self.assertEqual(self.wtool.refill_terms('2016123120', 'production', 'arpege', '4dvarfr',
                                                 refill_cutoff='all'),
                         {'date': {str(Date(2016, 12, 31, 18, 0)): [Time(h) for h in rangex('3-15-1')]}})
        self.assertEqual(self.wtool.refill_terms('2016123123', 'assim', 'arpege', '4dvarfr',
                                                 refill_cutoff='all'),
                         {'date': {str(Date(2016, 12, 31, 18, 0)): [Time(6, 0), Time(7, 0)]}})
        with self.assertRaises(CouplingOffsetConfRefillError):
            self.wtool.refill_terms('2016123123', 'production', 'arpege', '4dvarfr',
                                    refill_cutoff='production')
        self.assertEqual(self.wtool.refill_terms('2016123122', 'assim', 'arpege', '4dvarfr',
                                                 refill_cutoff='all'),
                         {'date': {str(Date(2016, 12, 31, 18, 0)): [Time(6, 0), Time(7, 0)]}})
        self.assertEqual(self.wtool.refill_terms('2016123122', 'production', 'arpege', '4dvarfr',
                                                 refill_cutoff='all'),
                         {'date': {str(Date(2016, 12, 31, 18, 0)): [Time(5, 0)]}})
        self.assertEqual(self.wtool.refill_terms('2017010100', 'production', 'arpege', 'courtfr',
                                                 refill_cutoff='all'),
                         {'date': {str(Date(2017, 1, 1, 0, 0)): [Time(h) for h in rangex('1-42-1')]}})
        self.assertEqual(self.wtool.refill_terms('2017010100', 'assim', 'arpege', '4dvarfr',
                                                 refill_cutoff='all'),
                         {'date': {str(Date(2016, 12, 31, 18, 0)): [Time(7, 0)],
                                   str(Date(2017, 1, 1, 0, 0)): [Time(6, 0), Time(7, 0)]}})
        self.assertEqual(self.wtool.refill_terms('2017010100', 'production', 'arpege', '4dvarfr',
                                                 refill_cutoff='all'),
                         {'date': {str(Date(2017, 1, 1, 0, 0)): [Time(h) for h in rangex('2-15-1')]}})

    def test_weird_coupling_refill_p(self):
        self.assertEqual(self.wtool.refill_terms('2017010100', 'production', 'arpege', 'courtfr',
                                                 refill_cutoff='production'),
                         {'date': {str(Date(2017, 1, 1, 0, 0)): [Time(h) for h in rangex('1-42-1')]}})
        self.assertEqual(self.wtool.refill_terms('2017010100', 'assim', 'arpege', '4dvarfr',
                                                 refill_cutoff='production'),
                         {'date': {str(Date(2017, 1, 1, 0, 0)): [Time(6, 0), Time(7, 0)]}})
        self.assertEqual(self.wtool.refill_terms('2017010100', 'production', 'arpege', '4dvarfr',
                                                 refill_cutoff='production'),
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


class Coupling3DVterConfToolTest(Coupling3DVConfToolTest):
    """Same tests but using the 'default' feature."""

    _VAPP = {'default': 'arpege'}

    _VCONF = {'default': '4dvarfr',
              'production': {'00': 'courtfr', }}

    _CUTOFF = {'default': 'production',
               'assim': {'00': 'assim', '06': 'assim', '05': 'assim',
                         '11': 'assim', '12': 'assim', '17': 'assim',
                         '18': 'assim', '23': 'assim'}, }

    _STEPS = {'assim': {'default': 'finalterm'},
              'production': {'default': '1-finalterm-1'}}

    _FINALTERM = {'assim': {'default': 1},
                  'production': {'03': 12, '00': '42', '12': Time(36),
                                 '15': 12, '21': 12, '18': 36,
                                 '09': '12', '06': '36'}}


@loggers.unittestGlobalLevel(tloglevel)
class Coupling3DVliteConfToolTest(unittest.TestCase):
    """Same tests but using the 'default' feature + XPID."""

    _HHLIST = {'assim': list(range(0, 24)),
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
                                               verbose=False, compute_on_refill=False)

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


@loggers.unittestGlobalLevel(tloglevel)
class Coupling3DVSparseConfToolTest(unittest.TestCase):
    """Same tests but using the 'default' feature + XPID."""

    _HHLIST = {'assim': list(range(0, 24)),
               'production': '12'}  # Compute only the 12h forecast

    _BASE = {'assim': {'00': '18', '01': '00', '02': '00', '03': '00', '04': '00',
                       '05': '00', '06': '00', '07': '06', '08': '06', '09': '06',
                       '10': '06', '11': '06', '12': '06', '13': '12', '14': '12',
                       '15': '12', '16': '12', '17': '12', '18': '12', '19': '18',
                       '20': '18', '21': '18', '22': '18', '23': '18'},
             'production': {'00': '00', '03': '00', '06': '06', '09': '06',
                            '12': '12', '15': '12', '18': '18', '21': '18'}}

    _VAPP = {'default': 'arpege'}

    _VCONF = {'default': '4dvarfr'}

    _XPID = {'default': 'ABCD'}

    _CUTOFF = {'default': 'production', }

    _STEPS = {'default': None,
              'assim': {'00': '1-12-1'}}

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.wtool = footprints.proxy.conftool(kind='couplingoffset',
                                               cplhhlist=self._HHLIST,
                                               cplhhbase=self._BASE, cplvapp=self._VAPP,
                                               cplvconf=self._VCONF, cplcutoff=self._CUTOFF,
                                               cplsteps=self._STEPS, cplxpid=self._XPID,
                                               verbose=False, compute_on_refill=False)

    def test_weird_coupling_prepare(self):
        with self.assertRaises(CouplingOffsetConfPrepareError):
            self.wtool.prepare_terms('2017010100', 'production', 'arpege', '4dvarfr', 'ABCD')
        self.assertListEqual(self.wtool.prepare_terms('2017010118', 'production', 'arpege', '4dvarfr', xpid='ABCD'),
                             list([Time(h) for h in [Time(h) for h in rangex('7-18-1')]]))

    def test_weird_coupling_use(self):
        self.assertListEqual(self.wtool.coupling_terms('2017010112', 'production'), [])
        self.assertListEqual(self.wtool.coupling_terms('2017010100', 'assim'),
                             list([Time(h) for h in rangex('7-18-1')]))
        self.assertListEqual(self.wtool.coupling_terms('2017010106', 'assim'), [])


@loggers.unittestGlobalLevel(tloglevel)
class CouplingAggConfToolTest(unittest.TestCase):
    """Same tests but using the 'default' feature + XPID."""

    _HHLIST = {'assim': list(range(0, 24)),
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

    _STEPS_A2 = {'assim': {'default': None, },
                 'production': {'00': '1-42-1', 'default': None}}

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.wtoolN = footprints.proxy.conftool(kind='couplingoffset',
                                                cplhhlist=self._HHLIST,
                                                cplhhbase=self._BASE, cplvapp=self._VAPP,
                                                cplvconf=self._VCONF, cplcutoff=self._CUTOFF,
                                                cplsteps=self._STEPS, cplxpid=self._XPID,
                                                verbose=False, compute_on_refill=False)
        self.wtoolA1 = footprints.proxy.conftool(kind='couplingoffset',
                                                 cplhhlist=self._HHLIST,
                                                 cplhhbase=self._AL1_BASE, cplvapp=self._VAPP,
                                                 cplvconf=self._AL1_VCONF, cplcutoff=self._CUTOFF,
                                                 cplsteps=self._STEPS, cplxpid=self._XPID,
                                                 verbose=False, compute_on_refill=False)
        self.wtoolA2 = footprints.proxy.conftool(kind='couplingoffset',
                                                 cplhhlist=self._HHLIST,
                                                 cplhhbase=self._AL2_BASE, cplvapp=self._VAPP,
                                                 cplvconf=self._AL1_VCONF, cplcutoff=self._CUTOFF,
                                                 cplsteps=self._STEPS_A2, cplxpid=self._XPID,
                                                 verbose=False, compute_on_refill=False)
        self.wtoolKO = footprints.proxy.conftool(kind='couplingoffset',
                                                 cplhhlist=self._HHLIST,
                                                 cplhhbase=self._BASE, cplvapp=self._VAPP,
                                                 cplvconf=self._VCONF, cplcutoff=self._CUTOFF,
                                                 cplsteps=self._STEPS, cplxpid=self._XPID,
                                                 verbose=False, refill_cutoff='production')
        self.wtoolAggN = footprints.proxy.conftool(kind='aggcouplingoffset',
                                                   nominal=[self.wtoolN, ],
                                                   alternate=[self.wtoolA1, self.wtoolA2],
                                                   use_alternates=False)
        self.wtoolAggA = footprints.proxy.conftool(kind='aggcouplingoffset',
                                                   nominal=[self.wtoolN, ],
                                                   alternate=[self.wtoolA1, self.wtoolA2],
                                                   use_alternates=True)

    def test_agg_consistency(self):
        footprints.proxy.conftool(kind='aggcouplingoffset',
                                  nominal=[self.wtoolN, ],
                                  alternate=[self.wtoolA1, self.wtoolKO],
                                  use_alternates=False)
        with self.assertRaises(CouplingOffsetConfError):
            footprints.proxy.conftool(kind='aggcouplingoffset',
                                      nominal=[self.wtoolN, ],
                                      alternate=[self.wtoolA1, self.wtoolKO],
                                      use_alternates=True)

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


@loggers.unittestGlobalLevel(tloglevel)
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


@loggers.unittestGlobalLevel(tloglevel)
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
                                               cplmodel=self._MODEL, isolated_refill=False,
                                               refill_cutoff='all', verbose=False)

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
                                   str(Date(2016, 12, 30, 12, 0)): [Time(h) for h in rangex('30-42-1')],
                                   }})
        self.assertEqual(self.wtool.refill_terms('2016123118', 'production', 'arpege', '4dvarfr', 'oops'),
                         {'date': {str(Date(2016, 12, 31, 12, 0)): [Time(h) for h in rangex('12-30-1')],
                                   str(Date(2016, 12, 31, 0, 0)): [Time(h) for h in rangex('18-24-1')],
                                   }})
        self.assertEqual(self.wtool.refill_terms('2016123112', 'production', 'arpege', '4dvarfr', 'arpege'),
                         {'date': {str(Date(2016, 12, 31, 0, 0)): [Time(h) for h in rangex('24-126-1')],
                                   str(Date(2016, 12, 30, 12, 0)): [Time(h) for h in rangex('24-48-1')],
                                   }})
        self.assertListEqual(sorted(self.wtool.refill_dates('2016123112', 'production', 'arpege', '4dvarfr')),
                             sorted(['2016-12-30T12:00:00Z', '2016-12-31T00:00:00Z']))
        self.assertListEqual(sorted(self.wtool.refill_months('2016123112', 'production', 'arpege', '4dvarfr')),
                             sorted([Month(12, year=2016), Month(1, year=2017)]))


@loggers.unittestGlobalLevel(tloglevel)
class TimeSerieConfToolTest(unittest.TestCase):

    def test_timeserie_basics(self):
        ctool = footprints.proxy.conftool(kind='timeserie',
                                          timeserie_begin='2019010100',
                                          timeserie_step='P3D')
        with self.assertRaises(TimeSerieInputFinderError):
            ctool.begindate_i('2018120100', '2018120200')
        self.assertEqual(ctool.begindate_i('2019010100', '2019010200'),
                         Date('2019010100'))
        self.assertEqual(ctool.begindate_i(Date('2019010100'), Date('2019010400')),
                         Date('2019010100'))
        self.assertEqual(ctool.begindate_i('2019010100', '2019010406'),
                         [Date('2019010100'), Date('2019010400')])
        self.assertEqual(ctool.begindate_i('2019010100', '2019010700'),
                         [Date('2019010100'), Date('2019010400')])
        self.assertEqual(ctool.begindate_i('2019060100', '2019060200'),
                         Date('2019053100'))

        self.assertEqual(ctool.enddate_i('2019010100', '2019010200'),
                         Date('2019010400'))
        self.assertEqual(ctool.enddate_i('2019010100', '2019010406'),
                         dict(begindate={Date('2019010100'): Date('2019010400'),
                                         Date('2019010400'): Date('2019010700')}))
        self.assertEqual(ctool.enddate_i('2019060100', '2019060200'),
                         Date('2019060300'))

        self.assertEqual(ctool.term_i('2019010100', '2019010200'), Time(72))
        self.assertEqual(ctool.term_i('2019010100', '2019010406'), Time(72))

        with self.assertRaises(TimeSerieInputFinderError):
            ctool.begindate('2018120100', 'PT24H')
        self.assertEqual(ctool.begindate(Date('2019010100'), Time('PT24H')),
                         Date('2019010100'))
        self.assertEqual(ctool.begindate('2019010100', 'PT72H'),
                         Date('2019010100'))
        self.assertEqual(ctool.begindate('2019010100', 'P3DT6H'),
                         [Date('2019010100'), Date('2019010400')])
        self.assertEqual(ctool.begindate('2019010100', 'P6D'),
                         [Date('2019010100'), Date('2019010400')])
        self.assertEqual(ctool.begindate('2019060100', Time('PT24H')),
                         Date('2019053100'))

        self.assertEqual(ctool.enddate('2019010100', Time('PT24H')),
                         Date('2019010400'))
        self.assertEqual(ctool.enddate('2019010100', 'P3DT6H'),
                         dict(begindate={Date('2019010100'): Date('2019010400'),
                                         Date('2019010400'): Date('2019010700')}))
        self.assertEqual(ctool.enddate('2019060100', 'PT24H'),
                         Date('2019060300'))

        self.assertEqual(ctool.term('2019010100', Time('P1D')), Time(72))
        self.assertEqual(ctool.term('2019010100', 'P3DT6H'), Time(72))

    def test_timeserie_no_upper(self):
        ctool = footprints.proxy.conftool(kind='timeserie',
                                          timeserie_begin='2019010100',
                                          timeserie_step='P3D',
                                          upperbound_included=False)
        self.assertEqual(ctool.begindate_i('2019010100', '2019010200'),
                         Date('2019010100'))
        self.assertEqual(ctool.begindate_i(Date('2019010100'), Date('2019010400')),
                         [Date('2019010100'), Date('2019010400')])
        self.assertEqual(ctool.begindate_i(Date('2019010100'), Date('2019010500')),
                         [Date('2019010100'), Date('2019010400')])

        self.assertEqual(ctool.begindate(Date('2019010100'), Time('PT24H')),
                         Date('2019010100'))
        self.assertEqual(ctool.begindate('2019010100', 'PT72H'),
                         [Date('2019010100'), Date('2019010400')])
        self.assertEqual(ctool.begindate('2019010100', 'P3DT6H'),
                         [Date('2019010100'), Date('2019010400')])

    def test_timeserie_single(self):
        ctool = footprints.proxy.conftool(kind='timeserie',
                                          timeserie_begin='2019010100',
                                          timeserie_step='P3D',
                                          singlefile=True)
        self.assertEqual(ctool.begindate_i('2019010100', '2019010200'),
                         Date('2019010100'))
        with self.assertRaises(TimeSerieInputFinderError):
            ctool.begindate_i(Date('2019010100'), Date('2019010500'))

        self.assertEqual(ctool.begindate(Date('2019010100'), Time('PT24H')),
                         Date('2019010100'))
        with self.assertRaises(TimeSerieInputFinderError):
            ctool.begindate('2019010100', 'PT73H')


# ------------------------------------------------------------------------------
# A few tests on the ArpIfsForecastTermConfTool

@loggers.unittestGlobalLevel(tloglevel)
class ArpIfsForecastTermConfToolTest(unittest.TestCase):

    _FCTERMS = dict(production={0: 102, 12: 24, "default": 24},
                    assim={"default": 6})
    _HIST_TERMS = dict(production={"default": ["0-47-6", "48-finalterm-12"]},
                       assim={"default": "0,3,6"})
    _SDI_TERMS = dict(production={"default": None, 0: ("1:30", 3, 6)},
                      assim={"default": "3,6"})
    _DIAG_TERMS = dict(default={"default": "0-47-3,48-finalterm-6"})
    _EXTRA_TERMS = dict(
        aero=dict(production={0: "0-48-3"}),
        foo=dict(default={"default": "2,3"})
    )

    def _basic_wtools(self, ** kwargs):
        basic = dict(
            kind='arpifs_fcterms',
            fcterm_unit='hour',
            fcterm_def=self._FCTERMS,
            hist_terms_def=self._HIST_TERMS,
            norm_terms_def=self._SDI_TERMS,
            diag_fp_terms_def=self._DIAG_TERMS,
            extra_fp_terms_def=self._EXTRA_TERMS
        )
        basic.update(kwargs)
        return footprints.proxy.conftool(** basic)

    def test_raise(self):
        with self.assertRaises(ValueError):
            self._basic_wtools(extra_fp_terms_def=dict(diag=1))
        with self.assertRaises(ValueError):
            self._basic_wtools(extra_fp_terms_def=dict(assim=dict(default=0)))
        with self.assertRaises(ValueError):
            self._basic_wtools(secondary_diag_terms_def=dict(diag=1))
        with self.assertRaises(ValueError):
            self._basic_wtools(secondary_diag_terms_def=dict(assim=dict(default=0)))
        with self.assertRaises(ValueError):
            self._basic_wtools(hist_terms_def=dict(assim=0))
        with self.assertRaises(ValueError):
            self._basic_wtools(hist_terms_def=dict(bling={"default": None, 0: "1:30,3,6"},
                                                   assim={"default": "3,6"}))
        with self.assertRaises(ValueError):
            self._basic_wtools(hist_terms_def=dict(production={"default": None, 'aerdf': "1:30,3,6"},
                                                   assim={"default": "3,6"}))
        wtool = self._basic_wtools(hist_terms_def=dict(assim={"default": "abc,3,6"}))
        with self.assertRaises(ValueError):
            wtool.hist_terms('assim', '1:33')
        wtool = self._basic_wtools(fcterm_unit='timestep')
        with self.assertRaises(ValueError):
            # Because SDI terms has minutes in it
            wtool.norm_terms('production', 0)

    def test_inline(self):
        wtool = self._basic_wtools()
        self.assertTrue(isinstance(wtool.fcterm('production', 0), int))
        self.assertEqual(['0001:30', '0003:00', '0006:00'],
                         wtool.norm_terms('production', 0))
        self.assertEqual([],
                         wtool.norm_terms('production', 6))
        self.assertEqual([2, 3],
                         wtool.foo_terms('production', 0))
        self.assertEqual([],
                         wtool.diag_terms_fplist('production', 0))
        self.assertEqual(wtool.inline_terms('production', 0),
                         wtool.no_inline.diag_terms('production', 0))
        self.assertEqual([],
                         wtool.no_inline.inline_terms('production', 0))
        self.assertEqual(rangex("0-47-3,48-102:00-6"),
                         wtool.inline_terms('production', 0))
        self.assertEqual([2, 3, 9, 15, 21, 27, 33, 39, 45],
                         wtool.extra_hist_terms('production', 0))
        self.assertEqual(['aero', 'foo'],
                         wtool.fpoff_items('production', 0))
        self.assertEqual([0, 2, 3, 6, 9, 12, 15, 18, 21, 24, 27, 30, 33, 36, 39, 42, 45, 48],
                         wtool.fpoff_terms('production', 0))
        wtool = self._basic_wtools(
            secondary_diag_terms_def=dict(
                labo=dict(production=dict(default='0-12-3')),
            ))
        self.assertEqual(wtool.inline_terms('production', 0),
                         wtool.no_inline.diag_terms('production', 0))
        self.assertEqual([],
                         wtool.no_inline.inline_terms('production', 0))
        self.assertEqual(rangex("0-47-3,48-102:00-6"),
                         wtool.inline_terms('production', 0))
        wtool = self._basic_wtools(
            secondary_diag_terms_def=dict(
                labo=dict(production=dict(default='0-6-1')),
            ))
        self.assertEqual(wtool.inline_terms('production', 0),
                         wtool.no_inline.diag_terms('production', 0))
        self.assertEqual([],
                         wtool.no_inline.inline_terms('production', 0))
        self.assertEqual(rangex("0-5-1,6-47-3,48-102:00-6"),
                         wtool.inline_terms('production', 0))
        wtool = self._basic_wtools(norm_terms_def=None, fcterm_unit='timestep')
        self.assertTrue(isinstance(wtool.fcterm('production', 0), int))

    def test_offline(self):
        wtool = self._basic_wtools(use_inline_fp=False)
        self.assertEqual([],
                         wtool.inline_terms('production', 0))
        self.assertEqual([2, 3, 9, 15, 21, 27, 33, 39, 45, 54, 66, 78, 90, 102],
                         wtool.extra_hist_terms('production', 0))
        self.assertEqual(footprints.FPList(rangex("0-47-3,48-102:00-6")),
                         wtool.diag_terms_fplist('production', 0))
        self.assertEqual(['aero', 'diag', 'foo'],
                         wtool.fpoff_items('production', 0))
        self.assertEqual(rangex("0,2,3-47-3,48-102:00-6"),
                         wtool.fpoff_terms('production', 0))


# ------------------------------------------------------------------------------
# A few tests on the MOCAGE domain config (NB: Most of the test are performed
# by the doctest).

@loggers.unittestGlobalLevel(tloglevel)
class IntairpolHHDictTest(unittest.TestCase):

    def test_HHDict(self):
        self.assertTrue(issubclass(HHDict, dict))
        hhd = HHDict({Time(0): '00t', Time(12): '12t', 'default': 'other'})
        self.assertEqual(hhd['default'], 'other')
        self.assertEqual(hhd[Time(12)], '12t')
        self.assertEqual(hhd[12], '12t')
        self.assertEqual(hhd['00:00'], '00t')
        self.assertEqual(hhd['01:07'], 'other')


@loggers.unittestGlobalLevel(tloglevel)
class IntairpolMDomainConfToolTest(unittest.TestCase):

    def test_utilities(self):
        # _item_value_tweak
        ivt = MocageDomainsConfTool._item_value_tweak  # (value, validcb, validmsg, cast)
        with self.assertRaises(MocageDomainsConfError):
            ivt(1, lambda x: False, 'Coucou', cast=None)
        with self.assertRaises(MocageDomainsConfError):
            ivt('abcd', None, '', cast=Time)
        self.assertEqual(ivt(1, lambda x: True, 'Error', cast=Time), Time('01:00'))
        self.assertEqual(ivt(1, None, '', cast=Time), Time('01:00'))
        # _item_time_transform
        itt = MocageDomainsConfTool._item_time_transform  # (item, validcb, validmsg, cast)
        self.assertEqual(itt({'00': '00t', '06:15': '06t', 'default': 'other'},
                             None, None, None),
                         HHDict({Time(0): '00t', Time('06:15'): '06t', 'default': 'other'}))
        with self.assertRaises(MocageDomainsConfError):
            itt({'00': '00t', 'foo': '06t', 'default': 'other'}, None, None, None)
        # _item_transform
        it = MocageDomainsConfTool._item_transform  # (item, validcb=None, validmsg='Validation Error', cast=None)
        self.assertEqual(it('Stuff'),
                         dict(assim=HHDict(default='Stuff'), production=HHDict(default='Stuff')))
        self.assertEqual(it('01:00', cast=Time),
                         dict(assim=HHDict(default=Time(1)), production=HHDict(default=Time(1))))
        self.assertEqual(it('01:00', validcb=lambda t: Time(t) < 24, cast=Time),
                         dict(assim=HHDict(default=Time(1)), production=HHDict(default=Time(1))))
        with self.assertRaises(MocageDomainsConfError):
            it('25:00', validcb=lambda t: Time(t) < 24, cast=Time)
        self.assertEqual(it(dict(assim='toto', production='titi')),
                         dict(assim=HHDict(default='toto'), production=HHDict(default='titi')))
        with self.assertRaises(MocageDomainsConfError):
            it(dict(assim='toto', production='titi', other='blop'))
        self.assertEqual(it({'00': 'toto', 'default': 'titi'}),
                         dict(assim=HHDict({Time(0): 'toto', 'default': 'titi'}),
                              production=HHDict({Time(0): 'toto', 'default': 'titi'})))
        self.assertEqual(it(dict(assim={'00': 'toto', 'default': 'titi'},
                                 production='TOTO')),
                         dict(assim=HHDict({Time(0): 'toto', 'default': 'titi'}),
                              production=HHDict({'default': 'TOTO'})))
        # _post_steps_validation
        psv = MocageDomainsConfTool._any_steps_validation  # (value)
        self.assertTrue(psv('0'))
        self.assertTrue(psv('finalterm'))
        self.assertTrue(psv('0-15-1'))
        self.assertTrue(psv('0-finalterm-1'))
        self.assertTrue(psv('0:15-finalterm-1'))
        self.assertTrue(psv('0-6-00:15,6:30-finalterm-1'))
        self.assertFalse(psv('foo'))
        self.assertFalse(psv('abcd-finalterm'))


if __name__ == "__main__":
    unittest.main()
