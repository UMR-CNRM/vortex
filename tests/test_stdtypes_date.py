from calendar import IllegalMonthError
from datetime import datetime, timedelta
import pickle
from unittest import TestCase, main

from bronx.stdtypes import date


class utDate(TestCase):

    def test_date_basics(self):
        rv = date.Date("20110726121314")
        self.assertEqual(rv.compact(), "20110726121314")

        rv = date.Date("YYYY0201", year=1995)
        self.assertEqual(rv.compact(), "19950201000000")
        rv = date.Date("yyyy0201", year=1995)
        self.assertEqual(rv.compact(), "19950201000000")
        rv = date.Date("yyyy0201")
        self.assertEqual(rv.compact(),
                         "{:4d}0201000000".format(date.today().year))

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

        rv = date.Date("20110726 010203")
        self.assertEqual(rv.compact(), "20110726010203")

        rv = date.Date("20110726H010203")
        self.assertEqual(rv.compact(), "20110726010203")

        rv = date.Date("2011-07-26 010203 UTC")
        self.assertEqual(rv.compact(), "20110726010203")

        rv = date.Date("2011-07-26 010203 GMT")
        self.assertEqual(rv.compact(), "20110726010203")

        rv = date.Date("2011-07-26 01:02:03")
        self.assertEqual(rv.compact(), "20110726010203")

        rv = date.Date("yesterday", base=date.Date("20110726T12"))
        self.assertEqual(rv.compact(), "20110725120000")

        rv = date.Date(float(1))
        self.assertEqual(rv.compact(), "19700101000001")

        self.assertEqual(pickle.loads(pickle.dumps(rv)), rv)

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
        self.assertEqual(str(p), 'PT12S')
        self.assertEqual(p.iso8601(), 'PT12S')
        self.assertEqual(p.days, 0)
        self.assertEqual(p.seconds, 12)

        p = date.Period('-P1DT12S')
        self.assertEqual(str(p), '-P1DT12S')
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
                 2017: 20170416, 2018: 20180401, 2019: 20190421}
        for y, d in check.items():
            self.assertEqual(date.Date(str(d)), date.easter(y))

    def test_date_julian(self):
        rv = date.Date("20110726121314")
        self.assertEqual(rv.julian, '207')

    def test_date_vortex(self):
        rv = date.Date(2013, 4, 15, 9, 27, 18)
        self.assertEqual(rv.vortex(), '20130415T0927P')
        self.assertEqual(rv.vortex('a'), '20130415T0927A')

    def test_date_add(self):
        rv = date.Date("20110831")
        td = timedelta(days=1)

        for vd2 in (rv + td, rv + 'P1D',
                    rv + date.Period("P1D"), 'P1D' + rv):
            self.assertTrue(isinstance(vd2, date.Date))
            self.assertEqual(vd2.compact(), "20110901000000")

    def test_date_substract(self):
        rv = date.Date("20110831")
        # Date/Period operation
        vd2 = rv - timedelta(days=1)
        self.assertTrue(isinstance(vd2, date.Date))
        self.assertEqual(vd2.compact(), "20110830000000")
        vd2 = rv - date.Period("P1D")
        self.assertTrue(isinstance(vd2, date.Date))
        self.assertEqual(vd2.compact(), "20110830000000")
        vd2 = rv - "P1D"
        self.assertTrue(isinstance(vd2, date.Date))
        self.assertEqual(vd2.compact(), "20110830000000")
        # Date/Date Operation
        rv = date.Date("20110831")
        vd2 = rv - date.Date("20110830")
        self.assertTrue(isinstance(vd2, date.Period))
        self.assertEqual(vd2.days, 1)
        vd2 = rv - "20110830"
        self.assertTrue(isinstance(vd2, date.Period))
        self.assertEqual(vd2.days, 1)
        # Reversed substraction
        rv = date.Date("20110831")
        vd2 = "20110830" - rv
        self.assertTrue(isinstance(vd2, date.Period))
        self.assertEqual(vd2.days, -1)
        vd2 = "2011083018" - rv
        self.assertTrue(isinstance(vd2, date.Period))
        self.assertEqual(vd2.days, -1)
        self.assertEqual(vd2.seconds, 18 * 3600)
        # Impossible ???
        with self.assertRaises(ValueError):
            vd2 = 'PT1D' - rv
        with self.assertRaises(ValueError):
            vd2 = date.Period('PT1D') - rv

    def test_date_replace(self):
        args = [
            {'month': 12},
            {'minute': 21},
            {'second': 59},
            {'year': 2015, 'second': 1}
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
        rv = date.at_minute()
        self.assertEqual(rv.microsecond, 0)
        self.assertEqual(rv.second, 0)
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

    def test_date_nivology(self):
        rv = date.Date("20110726121314")
        self.assertEqual(rv.nivologyseason_begin,
                         date.Date("201008010600"))
        self.assertEqual(rv.nivologyseason, "1011")
        rv = date.Date("20110926121314")
        self.assertEqual(rv.nivologyseason_begin,
                         date.Date("201108010600"))
        self.assertEqual(rv.nivologyseason, "1112")

    def test_date_range(self):
        rv = list(date.daterange('2017110821'))
        self.assertEqual(len(rv), 11)
        self.assertEqual(rv[0].compact(), '20171108210000')
        self.assertEqual(rv[-1].compact(), '20171118210000')
        rv = list(date.daterange('2017110803', '2017110821'))
        self.assertEqual(len(rv), 1)
        self.assertEqual(rv[0].compact(), '20171108030000')
        rv = list(date.daterange('2017110803', '2017110821', 'PT3H'))
        self.assertEqual(len(rv), 7)
        self.assertEqual(rv[0].compact(), '20171108030000')
        self.assertEqual(rv[-1].compact(), '20171108210000')
        self.assertEqual(
            [x for x in date.daterange('20150101', end='20150103')],
            [date.Date('20150101'), date.Date('20150102'), date.Date('20150103')])
        self.assertEqual(
            [x for x in date.daterange('2017020107', '2017020106', '-PT30M')],
            [date.Date('201702010600'), date.Date('201702010630'), date.Date('201702010700')])

    def test_date_rangex(self):
        rv = date.daterangex('2017110821')
        self.assertEqual(rv[-1], date.Date(2017, 11, 8, 21, 0))
        self.assertEqual(
            date.daterangex('2017110803', '2017110806'),
            [date.Date(2017, 11, 8, 3, 0), date.Date(2017, 11, 8, 4, 0),
             date.Date(2017, 11, 8, 5, 0), date.Date(2017, 11, 8, 6, 0)])
        self.assertEqual(
            date.daterangex('2017110803', '2017110806', 'PT3H'),
            [date.Date(2017, 11, 8, 3, 0), date.Date(2017, 11, 8, 6, 0)])
        self.assertEqual(
            date.daterangex('2017110803', '2017110806', 'PT3H', prefix='foo_', fmt='ymdh'),
            ['foo_2017110803', 'foo_2017110806'])
        self.assertEqual(
            date.daterangex('2017110803', end='2017110806', step='PT3H', shift='-P2D'),
            [date.Date(2017, 11, 6, 3, 0), date.Date(2017, 11, 6, 6, 0)])

    def test_date_getattr(self):
        rv = date.Date("2011072612")
        self.assertEqual(rv.addPT6H.compact(), "20110726180000")
        self.assertEqual(rv.addPT6H_ymdh, "2011072618")
        self.assertEqual(rv.subPT6H.compact(), "20110726060000")
        self.assertEqual(rv.subPT6H_ymdh, "2011072606")
        with self.assertRaises(AttributeError):
            rv.a_strange_attribute_that_does_not_exists
        with self.assertRaises(AttributeError):
            rv.subPT6H_
        with self.assertRaises(AttributeError):
            rv.subPT6H_aStrangeFormat
        self.assertEqual(rv.addterm_ymdh(dict(term=date.Period('PT6H')), dict()),
                         "2011072618")
        self.assertEqual(rv.addterm_ymdh(dict(), dict(term=date.Period('PT6H'))),
                         "2011072618")
        with self.assertRaises(AttributeError):
            rv.addadd_ymdh(dict(), dict(toto=date.Period('PT6H')))
        with self.assertRaises(AttributeError):
            rv.addnewadd_ymdh(dict(), dict(toto=date.Period('PT6H')))
        with self.assertRaises(KeyError):
            rv.addterm_ymdh(dict(), dict(toto=date.Period('PT6H')))
        # Now look for very complex stuff
        self.assertEqual(rv.addPT6H_subPT1H.compact(), "20110726170000")
        self.assertEqual(rv.addPT6H_subterm_subPT1H(dict(term='-PT2H'), dict()).compact(),
                         "20110726190000")
        self.assertEqual(rv.addPT6H_subterm_subPT1H_ymdh(dict(term='-PT2H'), dict()),
                         "2011072619")
        with self.assertRaises(KeyError):
            rv.addPT6H_subterm_subPT1H_addtoto(dict(term='-PT2H'), dict())
        self.assertEqual(rv.addPT6H_subterm_subPT1H_addtoto(dict(term='-PT2H',
                                                                 toto='PT1H'),
                                                            dict()).compact(),
                         "20110726200000")


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
        obj = date.Period(0, 1234567, 42)
        self.assertEqual(obj.days, 14)
        self.assertEqual(obj.seconds, 24967)
        self.assertEqual(obj.microseconds, 42)
        self.assertEqual(pickle.loads(pickle.dumps(obj)), obj)

    def test_period_utilities(self):
        obj_sec = 86410
        obj = date.Period(obj_sec)
        self.assertEqual(len(obj), obj_sec)
        self.assertEqual(obj.length, obj_sec)
        self.assertEqual(int(obj.time()), obj_sec // 60)  # 24h
        obj = date.Period(1, 314)
        self.assertEqual(obj.hms, '24:05:14')
        self.assertEqual(obj.hmscompact, '240514')

    def test_period_add(self):
        obj1 = date.Period('PT1S')
        obj2 = date.Period('PT10S')
        result = obj1 + obj2
        self.assertEqual(str(result), 'PT11S')
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
        self.assertEqual(pickle.loads(pickle.dumps(t)), t)

        for pred in (128, '128:00',
                     'T128', 'T128:00', 'T128:00Z', 'T128H00', 'T128H00Z',
                     'PT128H', 'PT128H00M', 'P5DT8H'):
            t = date.Time(pred)
            self.assertEqual(str(t), '128:00')

        for pred in (16.5, '16:30', 'T16:30', 'T16:30Z', 'T16H30', 'T16H30Z', 'PT16H30M'):
            t = date.Time(pred)
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

        t = date.Time('-7:45')
        self.assertEqual(str(t), '-07:45')

        t = date.Time('0007:45')
        self.assertEqual(str(t), '07:45')

        t = date.Time(18, 30)
        self.assertEqual(t.isoformat(), '18:30')
        self.assertEqual(t.iso8601(), 'T18:30Z')
        self.assertEqual(t.fmth, '0018')
        self.assertEqual(t.fmthm, '0018:30')
        self.assertEqual(t.fmthhmm, '1830')
        self.assertEqual(t.fmtdhm, '001830')
        self.assertEqual(t.fmtraw, '001830')
        self.assertEqual(t.fmtraw2, '0000001830')

        t = date.Time(-18, -30)
        self.assertEqual(t.isoformat(), '-18:30')
        self.assertEqual(t.iso8601(), 'T-18:30Z')
        self.assertEqual(t.fmth, '-0018')
        self.assertEqual(t.fmthm, '-0018:30')
        self.assertEqual(t.fmthhmm, '-1830')
        self.assertEqual(t.fmtdhm, '-001830')
        self.assertEqual(t.fmtraw, '-001830')
        self.assertEqual(t.fmtraw2, '-0000001830')

        t = date.Time(-66, -30)
        self.assertEqual(t.fmtdhm, '-021830')

        a = date.Time(48, 0)
        b = date.Time(0, 48 * 60)
        self.assertEqual(a, b)

    def test_time_compute(self):
        t = date.Time('07:45')
        t = t + date.Time(1, 22)
        self.assertEqual(str(t), '09:07')
        t = date.Time('07:45')
        t = '1:22' + t
        self.assertEqual(str(t), '09:07')
        t = t - date.Time(0, 10)
        self.assertEqual(str(t), '08:57')
        t = t - date.Time(8, 55)
        self.assertEqual(str(t), '00:02')
        t = '0:01' - t
        self.assertEqual(str(t), '-00:01')
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

    def test_time_getattr(self):
        rv = date.Time(12)
        self.assertEqual(str(rv.addPT6H), "18:00")
        self.assertEqual(str(rv.add6), "18:00")
        self.assertEqual(str(rv.add6H00), "18:00")
        self.assertEqual(rv.addPT6H_fmth, "0018")
        self.assertEqual(str(rv.subPT6H), "06:00")
        self.assertEqual(rv.subPT6H_fmthm, "0006:00")
        with self.assertRaises(AttributeError):
            rv.a_strange_attribute_that_does_not_exists
        with self.assertRaises(AttributeError):
            rv.subPT6H_
        with self.assertRaises(AttributeError):
            rv.subPT6H_aStrangeFormat
        self.assertEqual(rv.addmachin_fmth(dict(machin=6), dict()),
                         "0018")
        self.assertEqual(rv.addmachin_fmth(dict(machin=date.Period('PT6H')), dict()),
                         "0018")
        self.assertEqual(rv.addmachin_fmth(dict(), dict(machin=date.Period('PT6H'))),
                         "0018")
        with self.assertRaises(AttributeError):
            rv.addadd_fmth(dict(), dict(toto=date.Period('PT6H')))
        with self.assertRaises(KeyError):
            rv.addterm_fmth(dict(), dict(toto=date.Period('PT6H')))
        # Now look for very complex stuff
        self.assertEqual(str(rv.addPT6H_subPT1H), "17:00")
        self.assertEqual(str(rv.addPT6H_submachin_subPT1H(dict(machin='-PT2H'), dict())),
                         "19:00")
        self.assertEqual(rv.addPT6H_submachin_subPT1H_fmth(dict(machin='-PT2H'), dict()),
                         "0019")
        with self.assertRaises(KeyError):
            rv.addPT6H_subterm_subPT1H_addtoto(dict(term='-PT2H'), dict())
        self.assertEqual(str(rv.addPT6H_submachin_subPT1H_addtoto(dict(machin='-PT2H',
                                                                       toto='PT1H'),
                                                                  dict())),
                         "20:00")

    def assertTimeListEqual(self, val, exp):
        self.assertTrue(all([isinstance(v, date.Time) for v in val]))
        self.assertListEqual(val, [date.Time(e) for e in exp])

    def test_timetimerangex_basics(self):
        rv = date.timerangex(2)
        self.assertTimeListEqual(rv, [2])

        rv = date.timerangex(None)
        self.assertTimeListEqual(rv, [])

        rv = date.timerangex(2, 5)
        self.assertTimeListEqual(rv, [2, 3, 4, 5])

        rv = date.timerangex(7, 4, -1)
        self.assertTimeListEqual(rv, [4, 5, 6, 7])

        rv = date.timerangex(-9, -7, shift=2)
        self.assertTimeListEqual(rv, [-7, -6, -5])

        rv = date.timerangex(0, 12, 3, 1)
        self.assertTimeListEqual(rv, [1, 4, 7, 10, 13])

    def test_timetimerangex_basics_times(self):
        rv = date.timerangex('2:15')
        self.assertTimeListEqual(rv, ['2:15'])

        rv = date.timerangex('2:15,3:45')
        self.assertTimeListEqual(rv, ['2:15', '3:45'])

        rv = date.timerangex('10:00', '3:10', '-:15')
        self.assertTimeListEqual(rv, ['3:15', '3:30', '3:45', '4:00', '4:15', '4:30', '4:45', '5:00', '5:15', '5:30',
                                      '5:45', '6:00', '6:15', '6:30', '6:45', '7:00', '7:15', '7:30', '7:45', '8:00',
                                      '8:15', '8:30', '8:45', '9:00', '9:15', '9:30', '9:45', '10:00'])

        rv = date.timerangex('-9:00', '-7:00', shift=2)
        self.assertTimeListEqual(rv, [-7, -6, -5])

        rv = date.timerangex('-9:10', '-7:00', shift=2)
        self.assertTimeListEqual(rv, [date.Time(-7, -10), date.Time(-6, -10), date.Time(-5, -10)])

        rv = date.timerangex('-1:10', '2:10')
        self.assertTimeListEqual(rv, [date.Time(-1, -10), date.Time(0, -10), date.Time(0, 50), date.Time(1, 50)])

    def test_timetimerangex_minus(self):
        rv = date.timerangex('0-30-6,36-72-12')
        self.assertTimeListEqual(rv, [0, 6, 12, 18, 24, 30, 36, 48, 60, 72])

        rv = date.timerangex(['0-30-6', '36-72-12'])
        self.assertTimeListEqual(rv, [0, 6, 12, 18, 24, 30, 36, 48, 60, 72])

        rv = date.timerangex('0-30-6,36', 48, 12)
        self.assertTimeListEqual(rv, [0, 6, 12, 18, 24, 30, 36, 48])

        rv = date.timerangex(('0-30-6', 36), 48, 12)
        self.assertTimeListEqual(rv, [0, 6, 12, 18, 24, 30, 36, 48])

        rv = date.timerangex('-30--6-6,36')
        self.assertTimeListEqual(rv, [-30, -24, -18, -12, -6, 36])

        rv = date.timerangex('0-12', step=3, shift=1)
        self.assertTimeListEqual(rv, [1, 4, 7, 10, 13])

    def test_timetimerangex_minus_times(self):
        rv = date.timerangex('0-3-:15,3:30-6-:30')
        self.assertTimeListEqual(rv, ['0000:00', '0000:15', '0000:30', '0000:45', '0001:00', '0001:15', '0001:30',
                                      '0001:45', '0002:00', '0002:15', '0002:30', '0002:45', '0003:00', '0003:30',
                                      '0004:00', '0004:30', '0005:00', '0005:30', '0006:00'])

        rv = date.timerangex('0-3-:30,0:15', 6, '00:45')
        self.assertTimeListEqual(rv, ['0000:00', '0000:15', '0000:30', '0001:00', '0001:30', '0001:45', '0002:00',
                                      '0002:30', '0003:00', '0003:15', '0004:00', '0004:45', '0005:30'])

        rv = date.timerangex('0:30-12', step='1:00', shift=1)
        self.assertTimeListEqual(rv, ['0001:30', '0002:30', '0003:30', '0004:30', '0005:30', '0006:30', '0007:30',
                                      '0008:30', '0009:30', '0010:30', '0011:30', '0012:30'])

        rv = date.timerangex('00:30--1--:30')
        self.assertTimeListEqual(rv, [date.Time(-1, 0), date.Time(0, -30), date.Time(0, 0), date.Time(0, 30)])

    def test_timetimerangex_comma(self):
        rv = date.timerangex('0,4', 12, 3, 0)
        self.assertTimeListEqual(rv, [0, 3, 4, 6, 7, 9, 10, 12])

        rv = date.timerangex((0, 4), 12, 3, 0)
        self.assertTimeListEqual(rv, [0, 3, 4, 6, 7, 9, 10, 12])

    def test_timetimerangex_fmt(self):
        rv = date.timerangex('2-5', fmt='{0.hour:03d}')
        self.assertListEqual(rv, ['002', '003', '004', '005'])

    def test_timetimerangex_fmt_times(self):
        rv = date.timerangex('2-3-:30', fmt='{0!s:10s}')
        self.assertListEqual(rv, ['02:00     ', '02:30     ', '03:00     '])

    def test_timetimerangex_prefix(self):
        rv = date.timerangex(1, 7, 3, prefix='hello-')
        self.assertListEqual(rv, ['hello-01:00', 'hello-04:00', 'hello-07:00', ])

        rv = date.timerangex(1, 7, 3, prefix='hello-', shift=2, fmt='{0.hour:02d}')
        self.assertListEqual(rv, ['hello-03', 'hello-06', 'hello-09'])

        rv = date.timerangex(1, 7, 3, prefix='value no.', fmt='{1:d} is {0.hour:d}')
        self.assertListEqual(rv, ['value no.1 is 1', 'value no.2 is 4', 'value no.3 is 7'])

    def test_timetimerangex_prefix_times(self):
        rv = date.timerangex('10:00', '8:10', '-:15', prefix='toto-')
        self.assertListEqual(rv, ['toto-08:15', 'toto-08:30', 'toto-08:45', 'toto-09:00', 'toto-09:15', 'toto-09:30',
                                  'toto-09:45', 'toto-10:00'])

        rv = date.timerangex('10:00', '9:10', '-:15', prefix='toto-', shift='0:01')
        self.assertListEqual(rv, ['toto-09:16', 'toto-09:31', 'toto-09:46', 'toto-10:01'])

        rv = date.timerangex('10:00', '9:10', '-:15', prefix='value no.', fmt='{1:d} is {0!s}')
        self.assertListEqual(rv, ['value no.1 is 09:15', 'value no.2 is 09:30', 'value no.3 is 09:45',
                                  'value no.4 is 10:00'])


# A pure internal usage

class utTimeInt(TestCase):

    def test_time_basics(self):

        with self.assertRaises(ValueError):
            date.TimeInt("Toto")

        t = date.TimeInt(0)
        self.assertEqual(str(t), '0')
        self.assertEqual(t.str_time, '0000:00')
        self.assertEqual(pickle.loads(pickle.dumps(t)), t)

        t = date.TimeInt(128)
        self.assertEqual(str(t), '128')
        self.assertEqual(t.str_time, '0128:00')

        t = date.TimeInt('16:30')
        self.assertEqual(str(t), '0016:30')
        self.assertEqual(pickle.loads(pickle.dumps(t)), t)

        t = date.TimeInt('0007:45')
        self.assertEqual(str(t), '0007:45')

        a = date.TimeInt(48)
        b = date.TimeInt(':2880')
        self.assertEqual(a, b)

        self.assertEqual(a.realtype, 'int')
        self.assertEqual(b.realtype, 'int')

    def test_time_compute(self):
        for (lhs, rhs) in [(lambda x: date.TimeInt(x), lambda x: date.TimeInt(x)),
                           (lambda x: date.TimeInt(x), lambda x: x),
                           (lambda x: x, lambda x: date.TimeInt(x))]:
            t = lhs('07:45')
            t = t + rhs('1:22')
            self.assertEqual(str(t), '0009:07')
            t = lhs('09:07')
            t = t - rhs('9:05')
            self.assertEqual(str(t), '0000:02')
            t = lhs('00:02')
            t = t - rhs('0:04')
            self.assertEqual(str(t), '-0000:02')
            t = lhs('-00:02')
            t = t + rhs('0:04')
            self.assertEqual(str(t), '0000:02')
            t = lhs('00:02')
            t = t + rhs('1:04')
            self.assertEqual(str(t), '0001:06')
            t = lhs('07:45')
            t = t * rhs(2)
            self.assertEqual(str(t), '0015:30')
            t = lhs('07:45')
            t = t * rhs(-1)
            self.assertEqual(str(t), '-0007:45')
            t = lhs('01:30')
            t = t * rhs('0:20')
            self.assertEqual(str(t), '0000:30')

    def test_time_compare(self):
        t = date.TimeInt(6)
        self.assertFalse(t is None)
        self.assertFalse(t == 'Toto')
        self.assertTrue(t == 6)
        self.assertTrue(t >= 6)
        self.assertTrue(t <= 6)
        self.assertTrue(hash(t) == hash(date.TimeInt('6:00')))
        self.assertFalse(t > 6)
        self.assertFalse(t < 6)
        self.assertTrue(t == '06')
        self.assertTrue(t == '6:00')
        t = date.TimeInt('6:30')
        self.assertFalse(t == 6)
        self.assertFalse(hash(t) == hash(date.TimeInt('6:00')))
        self.assertTrue(t > 6)
        self.assertFalse(t < 6)
        self.assertFalse(t < '6:30')
        self.assertTrue(t < '6:31')
        self.assertTrue(t <= '6:31')
        self.assertTrue(t > '6:29')
        self.assertTrue(t >= '6:29')
        t = date.TimeInt('-6:30')
        self.assertFalse(t == -6)
        self.assertFalse(hash(t) == hash(date.TimeInt('6:00')))
        self.assertFalse(t > -6)
        self.assertTrue(t < -6)
        self.assertFalse(t < '-6:30')
        self.assertFalse(t < '-6:31')
        self.assertTrue(t < '-6:29')
        self.assertTrue(t < '6:30')

    def test_rangex_basics(self):
        rv = date.timeintrangex(2)
        self.assertListEqual(rv, [2])

        rv = date.timeintrangex(None)
        self.assertListEqual(rv, [])

        rv = date.timeintrangex(2, 5)
        self.assertListEqual(rv, [2, 3, 4, 5])

        rv = date.timeintrangex(7, 4, -1)
        self.assertListEqual(rv, [4, 5, 6, 7])

        rv = date.timeintrangex(-9, -7, shift=2)
        self.assertListEqual(rv, [-7, -6, -5])

        rv = date.timeintrangex(0, 12, 3, 1)
        self.assertListEqual(rv, [1, 4, 7, 10, 13])

    def test_rangex_basics_times(self):
        rv = date.timeintrangex('2:15')
        self.assertListEqual(rv, ['0002:15'])

        rv = date.timeintrangex('2:15,3:45')
        self.assertListEqual(rv, ['0002:15', '0003:45'])

        rv = date.timeintrangex('10:00', '3:10', '-:15')
        self.assertListEqual(rv,
                             ['0003:15', '0003:30', '0003:45', '0004:00', '0004:15', '0004:30', '0004:45', '0005:00',
                              '0005:15', '0005:30', '0005:45', '0006:00', '0006:15', '0006:30', '0006:45', '0007:00',
                              '0007:15', '0007:30', '0007:45', '0008:00', '0008:15', '0008:30', '0008:45', '0009:00',
                              '0009:15', '0009:30', '0009:45', '0010:00'])

        rv = date.timeintrangex('-9:00', '-7:00', shift=2)
        self.assertListEqual(rv, [-7, -6, -5])

        rv = date.timeintrangex('-9:10', '-7:00', shift=2)
        self.assertListEqual(rv, ['-0005:10', '-0006:10', '-0007:10'])

        rv = date.timeintrangex('-1:10', '2:10')
        self.assertListEqual(rv, ['-0000:10', '-0001:10', '0000:50', '0001:50'])

    def test_rangex_minus(self):
        rv = date.timeintrangex('0-30-6,36-72-12')
        self.assertListEqual(rv, [0, 6, 12, 18, 24, 30, 36, 48, 60, 72])

        rv = date.timeintrangex(['0-30-6', '36-72-12'])
        self.assertListEqual(rv, [0, 6, 12, 18, 24, 30, 36, 48, 60, 72])

        rv = date.timeintrangex('0-30-6,36', 48, 12)
        self.assertListEqual(rv, [0, 6, 12, 18, 24, 30, 36, 48])

        rv = date.timeintrangex(('0-30-6', 36), 48, 12)
        self.assertListEqual(rv, [0, 6, 12, 18, 24, 30, 36, 48])

        rv = date.timeintrangex('-30--6-6,36')
        self.assertListEqual(rv, [-30, -24, -18, -12, -6, 36])

        rv = date.timeintrangex('0-12', step=3, shift=1)
        self.assertListEqual(rv, [1, 4, 7, 10, 13])

    def test_rangex_minus_times(self):
        rv = date.timeintrangex('0-3-:15,3:30-6-:30')
        self.assertListEqual(rv,
                             ['0000:00', '0000:15', '0000:30', '0000:45', '0001:00', '0001:15', '0001:30', '0001:45',
                              '0002:00', '0002:15', '0002:30', '0002:45', '0003:00', '0003:30', '0004:00', '0004:30',
                              '0005:00', '0005:30', '0006:00'])

        rv = date.timeintrangex('0-3-:30,0:15', 6, '00:45')
        self.assertListEqual(rv,
                             ['0000:00', '0000:15', '0000:30', '0001:00', '0001:30', '0001:45', '0002:00', '0002:30',
                              '0003:00', '0003:15', '0004:00', '0004:45', '0005:30'])

        rv = date.timeintrangex('0:30-12', step='1:00', shift=1)
        self.assertListEqual(rv,
                             ['0001:30', '0002:30', '0003:30', '0004:30', '0005:30', '0006:30', '0007:30', '0008:30',
                              '0009:30', '0010:30', '0011:30', '0012:30'])

        rv = date.timeintrangex('00:30--1--:30')
        self.assertListEqual(rv, ['-0000:30', '-0001:00', '0000:00', '0000:30'])

    def test_rangex_comma(self):
        rv = date.timeintrangex('0,4', 12, 3, 0)
        self.assertListEqual(rv, [0, 3, 4, 6, 7, 9, 10, 12])

        rv = date.timeintrangex((0, 4), 12, 3, 0)
        self.assertListEqual(rv, [0, 3, 4, 6, 7, 9, 10, 12])

    def test_rangex_fmt(self):
        rv = date.timeintrangex('2-5', fmt='%03d')
        self.assertListEqual(rv, ['002', '003', '004', '005'])

        rv = date.timeintrangex('2-5', fmt='{0:03d}')
        self.assertListEqual(rv, ['002', '003', '004', '005'])

        rv = date.timeintrangex('2-5', fmt='{2:s}({0:02d})')
        self.assertListEqual(rv, ['int(02)', 'int(03)', 'int(04)', 'int(05)'])

    def test_rangex_fmt_times(self):
        rv = date.timeintrangex('2-3-:30', fmt='%10s')
        self.assertListEqual(rv, ['0002:00   ', '0002:30   ', '0003:00   '])

    def test_rangex_prefix(self):
        rv = date.timeintrangex('foo_0', 5, 2)
        self.assertListEqual(rv, ['foo_0', 'foo_2', 'foo_4', ])

        rv = date.timeintrangex('foo_0-5-2', fmt='%02d')
        self.assertListEqual(rv, ['foo_00', 'foo_02', 'foo_04', ])

        rv = date.timeintrangex(1, 7, 3, prefix='hello-')
        self.assertListEqual(rv, ['hello-1', 'hello-4', 'hello-7', ])

        rv = date.timeintrangex(1, 7, 3, prefix='hello-', shift=2, fmt='%02d')
        self.assertListEqual(rv, ['hello-03', 'hello-06', 'hello-09'])

        rv = date.timeintrangex(1, 7, 3, prefix='value no.', fmt='{1:d} is {0:d}')
        self.assertListEqual(rv, ['value no.1 is 1', 'value no.2 is 4', 'value no.3 is 7'])

    def test_rangex_prefix_times(self):
        rv = date.timeintrangex('foo_0:15', 2, ':15')
        self.assertListEqual(rv,
                             ['foo_0000:15', 'foo_0000:30', 'foo_0000:45', 'foo_0001:00', 'foo_0001:15', 'foo_0001:30',
                              'foo_0001:45', 'foo_0002:00'])

        rv = date.timeintrangex('foo_0', -2, ':15')
        self.assertListEqual(rv, [])

        rv = date.timeintrangex('foo_0', -1, '-:15')
        self.assertListEqual(rv, ['foo_-0000:15', 'foo_-0000:30', 'foo_-0000:45', 'foo_-0001:00', 'foo_0000:00'])

        rv = date.timeintrangex('10:00', '8:10', '-:15', prefix='toto-')
        self.assertListEqual(rv, ['toto-0008:15', 'toto-0008:30', 'toto-0008:45', 'toto-0009:00', 'toto-0009:15',
                                  'toto-0009:30', 'toto-0009:45', 'toto-0010:00'])

        rv = date.timeintrangex('10:00', '9:10', '-:15', prefix='toto-', shift='0:01')
        self.assertListEqual(rv, ['toto-0009:16', 'toto-0009:31', 'toto-0009:46', 'toto-0010:01'])

        rv = date.timeintrangex('10:00', '9:10', '-:15', prefix='value no.', fmt='{1:d} is {0:s}')
        self.assertListEqual(rv, ['value no.1 is 0009:15', 'value no.2 is 0009:30', 'value no.3 is 0009:45',
                                  'value no.4 is 0010:00'])


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
            self.assertEqual(rv.fmtraw, '{:04d}{:02d}'.format(thisyear, m))
            self.assertEqual(rv.fmtym, '{:04d}-{:02d}'.format(thisyear, m))

        rv = date.Month(2, 2014)
        self.assertEqual(rv.month, 2)
        self.assertEqual(rv.year, 2014)

        self.assertEqual(pickle.loads(pickle.dumps(rv)), rv)

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

        rv = date.Month('02')
        self.assertEqual(rv.month, 2)
        self.assertEqual(rv.year, thisyear)

        rv = date.Month('02', delta=12)
        self.assertEqual(rv.month, 2)
        self.assertEqual(rv.year, thisyear + 1)

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
