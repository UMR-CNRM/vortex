#!/usr/bin/env python
# -*- coding:Utf-8 -*-

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
        self.assertTrue(rv.is_synoptic())

        rv = date.Date(2011, 7, 26, 12, 13)
        self.assertEqual(rv.compact(), "20110726121300")

        rv = date.Date(2011, 7, 26, 12, 13, 14)
        self.assertEqual(rv.compact(), "20110726121314")

        rv = date.Date((2011, 7, 26, 12, 13, 14))
        self.assertEqual(rv.compact(), "20110726121314")

        rv = date.Date(year=2011, month=7, day=26,
                       hour=12, minute=13, second=14)
        self.assertEqual(rv.compact(), "20110726121314")

        rv = date.Date("2011-0726121314")
        self.assertEqual(rv.compact(), "20110726121314")

        rv = date.Date("2011-07-26T121314Z")
        self.assertEqual(rv.compact(), "20110726121314")

        rv = date.Date("20110726T12")
        self.assertEqual(rv.compact(), "20110726120000")

        rv = date.Date("yesterday", base=date.Date("20110726T12"))
        self.assertEqual(rv.compact(), "20110725120000")

        rv = date.Date(float(1))
        self.assertEqual(rv.compact(), "19700101000001")

    def test_date_format(self):
        rv = date.Date("2011-07-26T021314Z")
        self.assertEqual(rv.ymd, "20110726")
        self.assertEqual(rv.ymdh, "2011072602")
        self.assertEqual(rv.ymdhm, "201107260213")
        self.assertEqual(rv.ymdhms, "20110726021314")
        self.assertEqual(rv.hm, "0213")
        self.assertEqual(rv.hh, "02")

    def test_date_time(self):
        rv = date.Date("2011-07-26T021314Z")
        self.assertEqual(rv.time(), date.Time("2:13"))

    def test_date_bounds(self):
        rv = date.Date("2011-07-26T021314Z")
        self.assertEqual(rv.bounds(), (date.Date("20110701"),
                                       date.Date("201107312359")))
        self.assertEqual(rv.outbound, "20110801")
        rv = date.Date("2011-07-01T021314Z")
        self.assertEqual(rv.outbound, "20110630")
        self.assertEqual(rv.midcross, "20110630")
        rv = date.Date("2011-07-16T115900Z")
        self.assertEqual(rv.outbound, "20110630")
        self.assertEqual(rv.midcross, "20110801")
        rv = date.Date("2011-07-16T120100Z")
        self.assertEqual(rv.outbound, "20110801")

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

        d = date.Date('2013-04-11T10:57Z/PT4M/PT4M')
        self.assertEqual(d.compact(), '20130411110500')

        d = date.Date('2013-04-11T10:57Z/-PT1H/-PT3H')
        self.assertEqual(d.compact(), '20130411065700')

        d = date.Date('2013-04-11T10:57Z/-P1DT2H58M')
        self.assertEqual(d.compact(), '20130410075900')

        d = date.Date('2013-04-11T10:57Z/-P1DT2H58M/+P2D')
        self.assertEqual(d.compact(), '20130412075900')

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
            ((2039, 1, 1), 32507),
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

    def test_date_compare(self):
        d = date.Date('201507091233')
        e = date.now()
        self.assertTrue(d == d)
        self.assertTrue(d < e)
        self.assertTrue(d <= e)
        self.assertFalse(d > e)
        self.assertTrue(d == d.compact())
        self.assertTrue(d > '2015')
        self.assertTrue(d > 2015)
        self.assertTrue(d > 201507)
        self.assertTrue(d > 20150709)
        self.assertTrue(d >= '2015')
        self.assertTrue(d >= 2015)
        self.assertTrue(d >= 201507)
        self.assertTrue(d >= 20150709)
        self.assertTrue(d < '2016')
        self.assertTrue(d < 2016)
        self.assertTrue(d < 201601)
        self.assertTrue(d < 20160101)
        self.assertTrue(d < 201507091234)
        self.assertTrue(d <= '2016')
        self.assertTrue(d <= 2016)
        self.assertTrue(d <= 201601)
        self.assertTrue(d <= 20160101)
        self.assertTrue(d <= 201507091234)

    def test_date_utilities(self):
        rv = date.Date("20110726121314")
        self.assertEqual(date.yesterday(rv), "20110725121314")
        rv = date.Date("20110726121314")
        self.assertEqual(date.tomorrow(rv), "20110727121314")
        rv = date.at_second()
        self.assertEqual(rv.microsecond, 0)
        rv = date.at_hour()
        self.assertEqual(rv.microsecond, 0)
        self.assertEqual(rv.second, 0)
        self.assertEqual(rv.minute, 0)
        rv = date.guess('20130509T00')
        self.assertIsInstance(rv, date.Date)
        rv = date.guess('PT6H')
        self.assertIsInstance(rv, date.Period)
        with self.assertRaises(ValueError):
            rv = date.guess('20130631T00')
        self.assertEqual([x for x in date.daterange('20150101', 
                                                    end='20150103')],
                         [date.Date('20150101'), date.Date('20150102'),
                          date.Date('20150103')])


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
        d = date.synop(base=date.Date('2013-04-11T11:48Z'), time=0)
        self.assertEqual(d.iso8601(), '2013-04-11T00:00:00Z')
        with self.assertRaises(ValueError):
            d = date.synop(base=date.Date('2013-04-11T11:48Z'), time=1, step=2)

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

        def test_period_ini(self):
            res_exp = date.Period('PT6H3M2S')
            self.assertEqual(res_exp.total_seconds(), 21782)
            obj = date.Period(hours=6, minutes=3, seconds=2)
            self.assertEqual(obj, res_exp)
            res_exp = date.Period(date.Time('06:03'))
            self.assertEqual(res_exp.total_seconds(), 21780)
            obj = date.Period(0, 21780)
            self.assertEqual(obj, res_exp)

        def test_period_utilities(self):
            obj_sec = 86410
            obj = date.Period(obj_sec)
            self.assertEqual(len(obj), obj_sec)
            self.assertEqual(obj.length, obj_sec)
            self.assertEqual(int(obj.time()), obj_sec / 60)  # 24h

        def test_period_add(self):
            obj1 = date.Period('PT1S')
            obj2 = date.Period('PT10S')
            result = obj1 + obj2
            self.assertEqual(str(result), '0:00:11')
            self.assertEqual(result.iso8601(), 'PT11S')
            result = obj1 + 'PT10S'
            self.assertEqual(result.iso8601(), 'PT11S')

        def test_period_substract(self):
            obj1 = date.Period('PT1S')
            obj2 = date.Period('PT10S')
            result = obj2 - obj1
            self.assertEqual(result.iso8601(), 'PT9S')
            result = obj2 - 'PT1S'
            self.assertEqual(result.iso8601(), 'PT9S')

        def test_period_multiply(self):
            obj = date.Period('PT10S')
            factor = 3
            result = obj * factor
            self.assertEqual(result.iso8601(), 'PT30S')
            factor = '3'
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

        t = date.Time(hour=16, minute=5)
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

        a = date.Time(48,       0)
        b = date.Time( 0, 48 * 60)
        self.assertEqual(a, b)

    def test_time_compute(self):
        t = date.Time('07:45')
        t = t + date.Time(1, 22)
        self.assertEqual(str(t), '09:07')
        t = t - date.Time(0, 10)
        self.assertEqual(str(t), '08:57')
        t = t - date.Time(8, 55)
        self.assertEqual(str(t), '00:02')
        t = date.Time(18, 45)
        self.assertEqual(int(t), 1125)
        t = date.Time(2, 45)
        d = date.Date(2013, 4, 23, 15, 30)
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


# noinspection PyUnusedLocal
class utMonth(TestCase):

    def test_month_basics(self):
        thisyear = date.today().year
        for m in range(1, 13):
            rv = date.Month(m)
            self.assertEqual(int(rv), m)
            self.assertEqual(rv.month, m)
            self.assertEqual(rv.year, thisyear)
            if m > 1:
                self.assertEqual(rv.prevmonth().month, m - 1)
            else:
                self.assertEqual(rv.prevmonth().month, 12)
            if m < 12:
                self.assertEqual(rv.nextmonth().month, m + 1)
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
        self.assertEqual(rv.year, thisyear + 1)

        rv = date.Month(2, delta=-3)
        self.assertEqual(rv.month, 11)
        self.assertEqual(rv.year, thisyear - 1)

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

        rv = date.Month('20130301:closest')
        self.assertEqual(rv.fmtraw, '201302')

        rv = date.Month('20130315:closest')
        self.assertEqual(rv.fmtraw, '201302')

        rv = date.Month('20130316:closest')
        self.assertEqual(rv.fmtraw, '201304')

        rv = date.Month('20130327:closest')
        self.assertEqual(rv.fmtraw, '201304')

    def test_month_compute(self):
        m1 = date.Month(7)
        m2 = date.Month(8)
        rv = m1 + 1
        self.assertEqual(rv.month, m2.month)
        rv = m1 + 'P1M'
        self.assertEqual(rv.month, m2.month)
        rv = m2 - 1
        self.assertEqual(rv.month, m1.month)
        rv = m2 - 'P1M'
        self.assertEqual(rv.month, m1.month)

    def test_month_compare(self):
        m1 = date.Month(7)
        m2 = date.Month(8)
        self.assertGreater(m2, m1)
        self.assertGreater(m2, 7)
        self.assertLess(m1, m2)
        m1 = date.Month(12, 2015)
        m2 = date.Month(1, 2016)
        self.assertGreater(m2, m1)
        self.assertGreater(m2, (12, 2015))
        self.assertEqual(m2, (1, 2016))
        self.assertEqual(m2, (1, 0))

if __name__ == '__main__':
    main(verbosity=2)
