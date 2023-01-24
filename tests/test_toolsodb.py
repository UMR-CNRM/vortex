import unittest
import logging
logging.basicConfig(level=logging.ERROR)

from bronx.stdtypes import date as bdate

from common.tools import odb


class UtTimeSlots(unittest.TestCase):

    def test_4dvar_centered30(self):
        ts1 = odb.TimeSlots(7, '-PT3H', 'PT6H')
        ts2 = odb.TimeSlots(7, '-PT3H', 'PT6H', chunk=3600)
        ts3 = odb.TimeSlots('7/-PT3H/PT6H')
        ts4 = odb.TimeSlots('7/-PT3H/PT6H/PT60M')
        ts5 = odb.TimeSlots(str(ts4))
        for ts in (ts2, ts3, ts4, ts5):
            self.assertEqual(ts1, ts)
        self.assertEqual(ts1.leftmargin, -180)
        self.assertEqual(ts1.rightmargin, 180)
        self.assertListEqual(ts1.as_bounds('2016010100'),
                             ['20151231210000', '20151231213000',
                              '20151231223000', '20151231233000',
                              '20160101003000', '20160101013000',
                              '20160101023000', '20160101030000'])
        self.assertListEqual(ts1.as_centers_fromstart(),
                             [bdate.Period(p)
                              for p in ('PT0S', 'PT1H', 'PT2H', 'PT3H',
                                        'PT4H', 'PT5H', 'PT6H')])
        self.assertDictEqual(ts1.as_environment(),
                             {'BATOR_CENTER_LEN': 60,
                              'BATOR_SLOT_LEN': 60,
                              'BATOR_WINDOW_LEN': 360,
                              'BATOR_WINDOW_SHIFT': -180})

    def test_4dvar_centered30_prod(self):
        ts1 = odb.TimeSlots(6, '-PT3H', 'PT5H')
        ts2 = odb.TimeSlots(6, '-PT3H', 'PT5H', chunk=3600)
        ts3 = odb.TimeSlots('6/-PT3H/PT5H')
        ts4 = odb.TimeSlots('6/-PT3H/PT5H/PT60M')
        ts5 = odb.TimeSlots(str(ts4))
        for ts in (ts2, ts3, ts5):
            self.assertEqual(ts1, ts)
        self.assertEqual(ts1.leftmargin, -180)
        self.assertEqual(ts1.rightmargin, 120)
        self.assertListEqual(ts1.as_bounds('2016010100'),
                             ['20151231210000', '20151231213000',
                              '20151231223000', '20151231233000',
                              '20160101003000', '20160101013000',
                              '20160101020000'])
        self.assertListEqual(ts1.as_centers_fromstart(),
                             [bdate.Period(p)
                              for p in ('PT0S', 'PT1H', 'PT2H', 'PT3H',
                                        'PT4H', 'PT5H')])
        self.assertDictEqual(ts1.as_environment(),
                             {'BATOR_CENTER_LEN': 60,
                              'BATOR_SLOT_LEN': 60,
                              'BATOR_WINDOW_LEN': 300,
                              'BATOR_WINDOW_SHIFT': -180})

    def test_4dvar_regular(self):
        ts1 = odb.TimeSlots(3, '-PT3H', 'PT6H', center=False)
        ts2 = odb.TimeSlots('3/-PT3H/PT6H/regular')
        ts3 = odb.TimeSlots(str(ts2))
        self.assertEqual(ts1, ts2)
        self.assertEqual(ts1, ts3)
        self.assertEqual(ts1.leftmargin, -180)
        self.assertEqual(ts1.rightmargin, 180)
        self.assertListEqual(ts1.as_bounds('2016010100'),
                             ['20151231210000', '20151231230000',
                              '20160101010000', '20160101030000'])
        self.assertListEqual(ts1.as_centers_fromstart(),
                             [bdate.Period(p)
                              for p in ('PT1H', 'PT3H', 'PT5H')])
        self.assertDictEqual(ts1.as_environment(),
                             {'BATOR_CENTER_LEN': 0,
                              'BATOR_SLOT_LEN': 0,
                              'BATOR_WINDOW_LEN': 360,
                              'BATOR_WINDOW_SHIFT': -180})

    def test_singleslot(self):
        ts1 = odb.TimeSlots(1, '-PT3H', 'PT6H')
        ts2 = odb.TimeSlots(1, '-PT3H', 'PT6H', center=False)
        ts3 = odb.TimeSlots('1/-PT3H/PT6H/regular')
        ts4 = odb.TimeSlots('1/-PT3H/PT6H')
        ts5 = odb.TimeSlots(str(ts4))
        for ts in (ts2, ts3, ts5):
            self.assertEqual(ts1, ts)
        self.assertEqual(ts1.leftmargin, -180)
        self.assertEqual(ts1.rightmargin, 180)
        self.assertListEqual(ts1.as_bounds('2016010100'),
                             ['20151231210000', '20160101030000'])
        self.assertListEqual(ts1.as_centers_fromstart(),
                             [bdate.Period(p)
                              for p in ('PT3H', )])
        self.assertDictEqual(ts1.as_environment(),
                             {'BATOR_CENTER_LEN': 0,
                              'BATOR_SLOT_LEN': 0,
                              'BATOR_WINDOW_LEN': 360,
                              'BATOR_WINDOW_SHIFT': -180})

    def test_singleslot_pi(self):
        ts1 = odb.TimeSlots(1, '-PT20M', 'PT30M')
        ts2 = odb.TimeSlots(1, '-PT20M', 'PT30M', center=False)
        ts3 = odb.TimeSlots('1/-PT20M/PT30M/regular')
        ts4 = odb.TimeSlots('1/-PT20M/PT30M')
        ts5 = odb.TimeSlots(str(ts4))
        for ts in (ts2, ts3, ts5):
            self.assertEqual(ts1, ts)
        self.assertEqual(ts1.leftmargin, -20)
        self.assertEqual(ts1.rightmargin, 10)
        self.assertListEqual(ts1.as_bounds('2016010100'),
                             ['20151231234000', '20160101001000'])
        self.assertListEqual(ts1.as_centers_fromstart(),
                             [bdate.Period(p)
                              for p in ('PT15M', )])
        self.assertDictEqual(ts1.as_environment(),
                             {'BATOR_CENTER_LEN': 0,
                              'BATOR_SLOT_LEN': 0,
                              'BATOR_WINDOW_LEN': 30,
                              'BATOR_WINDOW_SHIFT': -20})


if __name__ == "__main__":
    unittest.main(verbosity=2)
