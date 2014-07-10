#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import vortex
from calendar import IllegalMonthError
from datetime import datetime, timedelta
from vortex.tools import date
from unittest import TestCase, main


class utDate(TestCase):

    def test_date_basics(self):
        rv = date.Date("20110726121314")
        self.assertEqual(rv.compact(), "20110726121314")

        dt = datetime(2011, 7, 26, 12, 13, 14)
        rv = date.Date(dt)
        self.assertEqual(rv.compact(), "20110726121314")

        rv = date.Date(2011, 7, 26)
        self.assertEqual(rv.compact(), "20110726000000")

        rv = date.Date(2011, 7, 26, 12)
        self.assertEqual(rv.compact(), "20110726120000")

        rv = date.Date(2011, 7, 26, 12, 13)
        self.assertEqual(rv.compact(), "20110726121300")

        rv = date.Date(2011, 7, 26, 12, 13, 14)
        self.assertEqual(rv.compact(), "20110726121314")

        rv = date.Date("2011-0726121314")
        self.assertEqual(rv.compact(), "20110726121314")

        rv = date.Date("2011-07-26T121314Z")
        self.assertEqual(rv.compact(), "20110726121314")

    def test_date_period(self):
        p = date.Period('PT12S')
        self.assertEqual(str(p), '0:00:12')
        self.assertEqual(p.iso8601(), 'PT12S')
        self.assertEqual(p.days, 0)
        self.assertEqual(p.seconds, 12)

        p = date.Period('-P1DT12S')
        self.assertEqual(str(p), '-2 days, 23:59:48')
        self.assertEqual(p.iso8601(), '-P1DT12S')
        self.assertEqual(p.days, -2)
        self.assertEqual(p.seconds, 86388)

        d = date.Date('2013-04-11T10:57Z')
        self.assertEqual(repr(d), 'Date(2013, 4, 11, 10, 57)')

        d = date.Date('2013-04-11T10:57Z/PT4M')
        self.assertEqual(d.compact(), '20130411110100')

        d = date.Date('2013-04-11T10:57Z/-P1DT2H58M')
        self.assertEqual(d.compact(), '20130410075900')

    def test_date_monthrange(self):
        rv = date.Date("20110726121314")
        self.assertEqual(rv.monthrange(), 31)

        rv = date.Date('19640131')
        self.assertRaises(IllegalMonthError, rv.monthrange, rv.year, 0)
        self.assertRaises(IllegalMonthError, rv.monthrange, rv.year, 13)

    def test_date_easter(self):
        check = {2011: 20110424, 2012: 20120408, 2013: 20130331,
                 2014: 20140420, 2015: 20150405, 2016: 20160327,
                 2017: 20170416, 2018: 20180401, 2019: 20190421 }
        for y, d in check.iteritems():
            self.assertEqual(date.Date(str(d)), date.easter(y))

    def test_date_julian(self):
        rv = date.Date("20110726121314")
        self.assertEqual(rv.julian, '207')

    def test_date_vortex(self):
        rv = date.Date(2013, 04, 15, 9, 27, 18)
        self.assertEqual(rv.vortex(), '20130415T0927P')
        self.assertEqual(rv.vortex('a'), '20130415T0927A')

    def test_date_add(self):
        rv = date.Date("20110831")
        td = timedelta(days=1)

        vd2 = rv + td
        self.assertTrue(isinstance(vd2, date.Date))
        self.assertEqual(vd2.compact(), "20110901000000")

        vd2 = rv + date.Period("P1D")
        self.assertTrue(isinstance(vd2, date.Date))
        self.assertEqual(vd2.compact(), "20110901000000")

    def test_date_substract(self):
        rv = date.Date("20110831")
        td = timedelta(days=1)

        vd2 = rv - td
        self.assertTrue(isinstance(vd2, date.Date))
        self.assertEqual(vd2.compact(), "20110830000000")

        vd2 = rv + date.Period("-P1D")
        self.assertTrue(isinstance(vd2, date.Date))
        self.assertEqual(vd2.compact(), "20110830000000")

    def test_date_replace(self):
        args = [
            { 'month': 12 },
            { 'minute': 21 },
            { 'second': 59 },
            { 'year': 2015, 'second': 01 }
        ]
        expected = [
            date.Date("20111231").compact(),
            date.Date("201108310021").compact(),
            date.Date("20110831000059").compact(),
            date.Date("20150831000001").compact()
        ]
        rv = date.Date("20110831")
        for ind, value in enumerate(args):
            self.assertEqual(rv.replace(**value).compact(), expected[ind])

    def test_date_tocnesjulian(self):
        test_dates = (
            ('19491231', -1),
            ('19500101', 0),
            ('20111026', 22578),
            ('20120101', 22645),
            ('20120229', 22704),
            ('20390101', 32507),
        )
        for d, j in test_dates:
            self.assertEqual(date.Date(d).to_cnesjulian(), j)

    def test_date_fromcnesjulian(self):
        test_dates = (
            (-1, '19491231000000'),
            (0, '19500101000000'),
            (22578, '20111026000000'),
            (22645, '20120101000000'),
            (22704, '20120229000000'),
            (32507, '20390101000000'),
        )
        rv = date.Date('19000101')
        for j, d in test_dates:
            self.assertEqual(rv.from_cnesjulian(j).compact(), d)


class utSpecial(TestCase):

    def test_date_isleap(self):
        self.assertTrue(date.Date('20001211').isleap())
        self.assertTrue(date.Date('19920523090805').isleap())
        self.assertFalse(date.Date('19000701000001').isleap())

    def test_date_synop(self):
        d = date.synop(base=date.Date('2013-04-11T19:48Z'))
        self.assertEqual(d.iso8601(), '2013-04-11T18:00:00Z')
        d = date.synop(base=date.Date('2013-04-11T11:48Z'))
        self.assertEqual(d.iso8601(), '2013-04-11T06:00:00Z')

    def test_date_round(self):
        basedate = date.Date('2013-04-11T11:48Z')

        rv = date.lastround(3, base=basedate)
        self.assertEqual(rv.iso8601(), '2013-04-11T09:00:00Z')

        rv = date.lastround(12, base=basedate)
        self.assertEqual(rv.iso8601(), '2013-04-11T00:00:00Z')

        rv = date.lastround(1, base=basedate, delta=-3540)
        self.assertEqual(rv.iso8601(), '2013-04-11T10:00:00Z')

        rv = date.lastround(12, base=basedate, delta='-PT15H')
        self.assertEqual(rv.iso8601(), '2013-04-10T12:00:00Z')


class utJeffrey(TestCase):

        def test_period_add(self):
            obj1 = date.Period('PT1S')
            obj2 = date.Period('PT10S')
            result = obj1 + obj2
            self.assertEqual(str(result), '0:00:11')
            self.assertEqual(result.iso8601(), 'PT11S')

        def test_period_substract(self):
            obj1 = date.Period('PT1S')
            obj2 = date.Period('PT10S')
            result = obj2 - obj1
            self.assertEqual(result.iso8601(), 'PT9S')

        def test_period_multiply(self):
            obj = date.Period('PT10S')
            factor = 3
            result = obj * factor
            self.assertEqual(result.iso8601(), 'PT30S')

        def test_date_substractmore(self):
            obj1 = date.Date('2011-07-03T12:20:00Z')
            obj2 = date.Date('2011-07-03T12:20:59Z')
            expect = date.Period('-PT59S')
            result = obj1 - obj2
            self.assertEqual(result.iso8601(), expect.iso8601())
            self.assertEqual(result, expect)

        def test_date_addperiod(self):
            obj1 = date.Date('2011-07-03T12:20:00Z')
            obj2 = date.Period('PT1H')
            expect = date.Date('2011-07-03T13:20:00Z')
            result = obj1 + obj2
            self.assertEqual(result, expect)

        def test_date_substractperiod(self):
            obj1 = date.Date('2011-07-03T12:20:00Z')
            obj2 = date.Period('PT1H')
            expect = date.Date('2011-07-03T11:20:00Z')
            result = obj1 - obj2
            self.assertEqual(result, expect)

class utTime(TestCase):

    def test_time_basics(self):
        t = date.Time(0)
        self.assertEqual(str(t), '00:00')

        t = date.Time(128)
        self.assertEqual(str(t), '128:00')

        t = date.Time(16.5)
        self.assertEqual(str(t), '16:30')

        t = date.Time(16, 5)
        self.assertEqual(str(t), '16:05')

        t = date.Time([7, 45])
        self.assertEqual(str(t), '07:45')

        t = date.Time((7, 45))
        self.assertEqual(str(t), '07:45')

        t = date.Time('7:45')
        self.assertEqual(str(t), '07:45')

        t = date.Time('0007:45')
        self.assertEqual(str(t), '07:45')

        t = date.Time(18, 30)
        self.assertEqual(t.isoformat(), '18:30')
        self.assertEqual(t.iso8601(), 'T18:30Z')
        self.assertEqual(t.fmth, '0018')
        self.assertEqual(t.fmthm, '0018:30')
        self.assertEqual(t.fmtraw, '001830')

    def test_time_compute(self):
        t = date.Time('07:45')
        t = t + date.Time(1, 22)
        self.assertEqual(str(t), '09:07')
        t = t - date.Time(9, 5)
        self.assertEqual(str(t), '00:02')
        t = date.Time(18, 45)
        self.assertEqual(int(t), 1125)
        t = date.Time(2, 45)
        d = date.Date(2013,4,23,15,30)
        r = d + t
        self.assertEqual(str(r), '2013-04-23T18:15:00Z')
        r = d - t
        self.assertEqual(str(r), '2013-04-23T12:45:00Z')


    def test_time_compare(self):
        t = date.Time(6)
        self.assertFalse(t is None)
        self.assertTrue(t == 6)
        self.assertFalse(t > 6)
        self.assertFalse(t < 6)
        self.assertTrue(t == '06')
        t = date.Time(6, 30)
        self.assertFalse(t == 6)
        self.assertTrue(t > 6)
        self.assertFalse(t < 6)
        self.assertFalse(t < (6, 30))
        self.assertTrue(t < (6, 31))
        self.assertTrue(t > [6, 29])


class utMonth(TestCase):

    def test_month_basics(self):
        thisyear = date.today().year
        for m in range(1, 13):
            rv = date.Month(m)
            self.assertEqual(int(rv), m)
            self.assertEqual(rv.month, m)
            self.assertEqual(rv.year, thisyear)
            if m > 1:
                self.assertEqual(rv.prevmonth().month, m-1)
            else:
                self.assertEqual(rv.prevmonth().month, 12)
            if m < 12:
                self.assertEqual(rv.nextmonth().month, m+1)
            else:
                self.assertEqual(rv.nextmonth().month, 1)
            self.assertEqual(rv.fmtraw, '{0:04d}{1:02d}'.format(thisyear, m))
            self.assertEqual(rv.fmtym,  '{0:04d}-{1:02d}'.format(thisyear, m))

        rv = date.Month(2, 2014)
        self.assertEqual(rv.month, 2)
        self.assertEqual(rv.year, 2014)

        rv = date.Month(2, year=2014)
        self.assertEqual(rv.month, 2)
        self.assertEqual(rv.year, 2014)

        rv = date.Month(2, year=0)
        self.assertEqual(rv.month, 2)
        self.assertEqual(rv.year, 0)

        rv = date.Month(2, year=-1)
        self.assertEqual(rv.month, 2)
        self.assertEqual(rv.year, 0)

        mb = date.Month('20140101')
        rv = date.Month(mb)
        self.assertEqual(rv.month, 1)
        self.assertEqual(rv.year, 2014)

        rv = date.Month(mb, delta=7)
        self.assertEqual(rv.month, 8)
        self.assertEqual(rv.year, 2014)

        rv = date.Month(2, delta=12)
        self.assertEqual(rv.month, 2)
        self.assertEqual(rv.year, thisyear+1)

        rv = date.Month(2, delta=-3)
        self.assertEqual(rv.month, 11)
        self.assertEqual(rv.year, thisyear-1)

        with self.assertRaises(ValueError):
            rv = date.Month()

        with self.assertRaises(ValueError):
            rv = date.Month(0)

        with self.assertRaises(ValueError):
            rv = date.Month(13)

    def test_month_special(self):
        rv = date.Month('20130131')
        self.assertEqual(rv.fmtraw, '201301')

        rv = date.Month('20130131', 2)
        self.assertEqual(rv.fmtraw, '201303')

        rv = date.Month('20130131', 12)
        self.assertEqual(rv.fmtraw, '201401')

        rv = date.Month('20130331', -2)
        self.assertEqual(rv.fmtraw, '201301')

        rv = date.Month('20130331', -12)
        self.assertEqual(rv.fmtraw, '201203')

        rv = date.Month('20130101:next')
        self.assertEqual(rv.fmtraw, '201302')

        rv = date.Month('20131201:next')
        self.assertEqual(rv.fmtraw, '201401')

        rv = date.Month('20130101:prev')
        self.assertEqual(rv.fmtraw, '201212')

        rv = date.Month('20130301:prev')
        self.assertEqual(rv.fmtraw, '201302')


    def test_month_compute(self):
        m1 = date.Month(7)
        m2 = date.Month(8)
        rv = m1 + 1
        self.assertEqual(rv.month, m2.month)
        rv = m2 - 1
        self.assertEqual(rv.month, m1.month)


if __name__ == '__main__':
    main(verbosity=2)
    vortex.exit()

