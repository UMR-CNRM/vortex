#!/bin/env python
# -*- coding:Utf-8 -*-

import vortex
from calendar import IllegalMonthError
from datetime import datetime, timedelta
from vortex.tools import date
from unittest import TestCase, main


class utDate(TestCase):

    def test_basicdate(self):
        vdate = date.Date("20110726121314")
        self.assertEquals(vdate.compact(), "20110726121314")
        dt = datetime(2011, 7, 26, 12, 13, 14)
        vdate = date.Date(dt)
        self.assertEquals(vdate.compact(), "20110726121314")
        vdate = date.Date(2011, 7, 26)
        self.assertEquals(vdate.compact(), "20110726000000")
        vdate = date.Date(2011, 7, 26, 12)
        self.assertEquals(vdate.compact(), "20110726120000")
        vdate = date.Date(2011, 7, 26, 12, 13)
        self.assertEquals(vdate.compact(), "20110726121300")
        vdate = date.Date(2011, 7, 26, 12, 13, 14)
        self.assertEquals(vdate.compact(), "20110726121314")
        vdate = date.Date("2011-0726121314")
        self.assertEquals(vdate.compact(), "20110726121314")
        vdate = date.Date("2011-07-26T121314Z")
        self.assertEquals(vdate.compact(), "20110726121314")

    def test_basicperiod(self):
        p = date.Period('PT12S')
        self.assertEquals(str(p), '0:00:12')
        self.assertEquals(p.iso8601(), 'PT12S')
        self.assertEquals(p.days, 0)
        self.assertEquals(p.seconds, 12)
        p = date.Period('-P1DT12S')
        self.assertEquals(str(p), '-2 days, 23:59:48')
        self.assertEquals(p.iso8601(), '-P1DT12S')
        self.assertEquals(p.days, -2)
        self.assertEquals(p.seconds, 86388)

    def test_dateperiod(self):
        d = date.Date('2013-04-11T10:57Z')
        self.assertEquals(repr(d), 'Date(2013, 4, 11, 10, 57)')
        d = date.Date('2013-04-11T10:57Z/PT4M')
        self.assertEquals(d.compact(), '20130411110100')
        d = date.Date('2013-04-11T10:57Z/-P1DT2H58M')
        self.assertEquals(d.compact(), '20130410075900')

    def test_monthrange(self):
        vdate = date.Date("20110726121314")
        self.assertEquals(vdate.monthrange(), 31)

    def test_monthrangefail(self):
        vdate = date.Date('19640131')
        self.assertRaises(IllegalMonthError, vdate.monthrange, vdate.year, 0)
        self.assertRaises(IllegalMonthError, vdate.monthrange, vdate.year, 13)

    def test_easter(self):
        check = {2011: 20110424, 2012: 20120408, 2013: 20130331,
                 2014: 20140420, 2015: 20150405, 2016: 20160327,
                 2017: 20170416, 2018: 20180401, 2019: 20190421 }
        for y, d in check.iteritems():
            self.assertEqual(date.Date(str(d)), date.easter(y))
   
    def test_julian(self):
        vdate = date.Date("20110726121314")
        self.assertEquals(vdate.julian, '207')

    def test_datevortex(self):
        d = date.Date(2013, 04, 15, 9, 27, 18)
        self.assertEquals(d.vortex(), '20130415T0927P')
        self.assertEquals(d.vortex('a'), '20130415T0927A')

    def test_add(self):
        vdate = date.Date("20110831")
        td = timedelta(days=1)
        vd2 = vdate + td
        self.assertTrue(isinstance(vd2, date.Date))
        self.assertEquals(vd2.compact(), "20110901000000")
        vd2 = vdate + date.Period("P1D")
        self.assertTrue(isinstance(vd2, date.Date))
        self.assertEquals(vd2.compact(), "20110901000000")

    def test_sub(self):
        vdate = date.Date("20110831")
        td = timedelta(days=1)
        vd2 = vdate - td
        self.assertTrue(isinstance(vd2, date.Date))
        self.assertEquals(vd2.compact(), "20110830000000")
        vd2 = vdate + date.Period("-P1D")
        self.assertTrue(isinstance(vd2, date.Date))
        self.assertEquals(vd2.compact(), "20110830000000")

    def test_replace(self):
        args = [
            { 'month': 12 },
            { 'minute': 21 },
            { 'second': 59 },
            { 'year': 2015, 'second': 01 }
        ]
        res = [
            date.Date("20111231").compact(),
            date.Date("201108310021").compact(),
            date.Date("20110831000059").compact(),
            date.Date("20150831000001").compact()
        ]
        vdate = date.Date("20110831")
        for ind, value in enumerate(args):
            self.assertEquals(vdate.replace(**value).compact(), res[ind])

    def test_to_cnesjulian(self):
        test_dates = (
            ('19491231', -1),
            ('19500101', 0),
            ('20111026', 22578),
            ('20120101', 22645),
            ('20120229', 22704),
            ('20390101', 32507),
        )
        for d, j in test_dates:
            self.assertEquals(date.Date(d).to_cnesjulian(), j)  

    def test_from_cnesjulian(self):
        test_dates = (
            (-1, '19491231000000'),
            (0, '19500101000000'),
            (22578, '20111026000000'),
            (22645, '20120101000000'),
            (22704, '20120229000000'),
            (32507, '20390101000000'),
        )
        do = date.Date('19000101')
        for j, d in test_dates:
            self.assertEquals(do.from_cnesjulian(j).compact(), d)


class utSpecial(TestCase):

    def test_isleap(self):
        args = [
            '20001211',
            '19000701000001',
            '19920523090805'
        ]
        res = [
            True,
            False,
            True]

        for i, val in enumerate(args):
            svdate = date.Date(val)
            self.assertEquals(svdate.isleap(), res[i])

    def test_datesynop(self):
        d = date.synop(base=date.Date('2013-04-11T19:48Z'))
        self.assertEquals(d.iso8601(), '2013-04-11T18:00:00Z')
        d = date.synop(base=date.Date('2013-04-11T11:48Z'))
        self.assertEquals(d.iso8601(), '2013-04-11T06:00:00Z')

    def test_dateround(self):
        basedate = date.Date('2013-04-11T11:48Z')
        d = date.lastround(3, base=basedate)
        self.assertEquals(d.iso8601(), '2013-04-11T09:00:00Z')
        d = date.lastround(12, base=basedate)
        self.assertEquals(d.iso8601(), '2013-04-11T00:00:00Z')
        d = date.lastround(1, base=basedate, delta=-3540)
        self.assertEquals(d.iso8601(), '2013-04-11T10:00:00Z')
        d = date.lastround(12, base=basedate, delta='-PT15H')
        self.assertEquals(d.iso8601(), '2013-04-10T12:00:00Z')

class utJeffrey(TestCase):

        def test_addPeriods(self):
            """ add two time periods together """
            obj1 = date.Period('PT1S')
            obj2 = date.Period('PT10S')
            result = obj1 + obj2
            self.assertEqual(str(result), '0:00:11')
            self.assertEqual(result.iso8601(), 'PT11S')

        def test_subPeriods(self):
            """ subtract one time period from another """
            obj1 = date.Period('PT1S')
            obj2 = date.Period('PT10S')
            result = obj2 - obj1
            self.assertEqual(result.iso8601(), 'PT9S')

        def test_mulPeriod(self):
            """ multiply a time period by an int """
            obj = date.Period('PT10S')
            factor = 3
            result = obj * factor
            self.assertEqual(result.iso8601(), 'PT30S')

        def test_subDates(self):
            """ subtract two dates to get a time period """
            obj1 = date.Date('2011-07-03T12:20:00Z')
            obj2 = date.Date('2011-07-03T12:20:59Z')
            expect = date.Period('-PT59S')
            result = obj1 - obj2
            self.assertEqual(result.iso8601(), expect.iso8601())
            self.assertEqual(result, expect)

        def test_addDatePeriod(self):
            """ add a period of time to a date to get a new date """
            obj1 = date.Date('2011-07-03T12:20:00Z')
            obj2 = date.Period('PT1H')
            expect = date.Date('2011-07-03T13:20:00Z')
            result = obj1 + obj2
            self.assertEqual(result, expect)

        def test_subDatePeriod(self):
            """ subtract a period of time from a date to get a new date """
            obj1 = date.Date('2011-07-03T12:20:00Z')
            obj2 = date.Period('PT1H')
            expect = date.Date('2011-07-03T11:20:00Z')
            result = obj1 - obj2
            self.assertEqual(result, expect)

class utTime(TestCase):

    def test_mkTime(self):
        t = date.Time(0)
        self.assertEquals(str(t), '00:00')
        t = date.Time(128)
        self.assertEquals(str(t), '128:00')
        t = date.Time(16.5)
        self.assertEquals(str(t), '16:30')
        t = date.Time(16, 5)
        self.assertEquals(str(t), '16:05')
        t = date.Time([7,45])
        self.assertEquals(str(t), '07:45')
        t = date.Time((7, 45))
        self.assertEquals(str(t), '07:45')
        t = date.Time('7:45')
        self.assertEquals(str(t), '07:45')
        t = date.Time('0007:45')
        self.assertEquals(str(t), '07:45')
        t = date.Time(18, 30)
        self.assertEquals(t.isoformat(), '18:30')
        self.assertEquals(t.iso8601(), 'T18:30Z')
        self.assertEquals(t.fmth, '0018')
        self.assertEquals(t.fmthm, '0018:30')
        self.assertEquals(t.fmtraw, '001830')

    def test_opTime(self):
        t = date.Time('07:45')
        t = t + date.Time(1, 22)
        self.assertEquals(str(t), '09:07')
        t = t - date.Time(9, 5)
        self.assertEquals(str(t), '00:02')
        t = date.Time(18, 45)
        self.assertEquals(int(t), 18)
        t = date.Time(2, 45)
        d = date.Date(2013,4,23,15,30)
        r = d + t
        self.assertEquals(str(r), '2013-04-23T18:15:00Z')
        r = d - t
        self.assertEquals(str(r), '2013-04-23T12:45:00Z')


    def test_cmpTime(self):
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

if __name__ == '__main__':
    main()
    vortex.exit()

def get_test_class():
    return [ utDate, utSpecial, utJeffrey ]
