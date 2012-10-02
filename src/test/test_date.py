#!/bin/env python
# -*- coding:Utf-8 -*-

from datetime import datetime, timedelta
from vortex.tools import date
from unittest import TestCase, main


class utdate(TestCase):

    def test__init__(self):
        vdate = date.Date("20110726121314")
        self.assertEquals(vdate.get_date(), "20110726121314")
        dt = datetime(2011, 7, 26, 12, 13, 14)
        vdate = date.Date(dt)
        self.assertEquals(vdate.get_date(), "20110726121314")
        vdate = date.Date(2011, 7, 26)
        self.assertEquals(vdate.get_date(), "20110726000000")
        vdate = date.Date(2011, 7, 26, 12)
        self.assertEquals(vdate.get_date(), "20110726120000")
        vdate = date.Date(2011, 7, 26, 12, 13)
        self.assertEquals(vdate.get_date(), "20110726121300")
        vdate = date.Date(2011, 7, 26, 12, 13, 14)
        self.assertEquals(vdate.get_date(), "20110726121314")
        print "test __init__ Ok"

    def test_get_nbdays_month(self):
        vdate = date.Date("20110726121314")
        self.assertEquals(vdate.get_nbdays_month(), 31)
        print "test get_nbdays_month Ok"

    def test_get_julian_day(self):
        vdate = date.Date("20110726121314")
        self.assertEquals(vdate.get_julian_day(), '207')
        print "test get_julian_day Ok"

    def test_fmt_date(self):
        vdate = date.Date("20110726121314")
        td = timedelta(days=1)
        vd2 = vdate + td

    def test_get_fmt_date(self):
        vdate = date.Date("20110726121314")
        args = [
            "yyyy",
            "yyyymm",
            "yyyymmdd",
            "yyyymmddhh",
            "yyyymmddhhmn",
            "yyyymmddhhmnss",
            "mn"
        ]
        res = [
            "2011",
            "201107",
            "20110726",
            "2011072612",
            "201107261213",
            "20110726121314",
            "13"
        ]
        for i, fmt in enumerate(args):
            self.assertEquals(vdate.get_fmt_date(fmt), res[i])
        print "test get_fmt_date Ok"

    def test_get_mn_from_date(self):
        vdate = date.Date("20110726121314")
        self.assertEquals(vdate.get_mn_from_date(), '13')
        print "test get_mn_from_date Ok"

    def test_add_delta(self):
        args = [
            ("P1M", "yyyy"),
            ("P1M", "yyyymm"),
            ("P1M", "yyyymmdd"),
            ("P1M", "yyyymmddhh"),
            ("P1D", "yyyymmdd"),
            ("P365D", "yyyymmdd"),
            ("P3650D", "yyyymmdd")
        ]
        res = [
            '2011',
            '201108',
            '20110826',
            '2011082612',
            '20110727',
            '20120725',
            '20210723'
        ]
        vdate = date.Date("20110726121314")
        for i, delta in enumerate(args):
            self.assertEquals(vdate.add_delta(*delta), res[i])
        print "test add_delta Ok"

    def test_sub_delta(self):
        args = [
            ("M1M", "yyyy"),
            ("M1M", "yyyymm"),
            ("M1M", "yyyymmdd"),
            ("M1M", "yyyymmddhh"),
            ("M13H", "yyyymmddhhmnss")
        ]
        res = [
            '2011',
            '201106',
            '20110626',
            '2011062612',
            '20110725231314',
        ]
        vdate = date.Date("20110726121314")
        for i, delta in enumerate(args):
            self.assertEquals(vdate.sub_delta(*delta), res[i])
        print "test sub_delta Ok"

    def test_diff_dates(self):
        vdate = date.Date("20110831")
        self.assertEquals(vdate.diff_dates("20110601"), '2184h00mn')
        print "test diff_dates Ok"

    def test_add(self):
        vdate = date.Date("20110831")
        td = timedelta(days=1)
        vd2 = vdate + td
        self.assertTrue(isinstance(vd2, date.Date))
        self.assertEquals(vd2.get_date(), "20110901000000")
        vd2 = vdate + "P1D"
        self.assertTrue(isinstance(vd2, date.Date))
        self.assertEquals(vd2.get_date(), "20110901000000")
        print "test __add__ Ok"

    def test_sub(self):
        vdate = date.Date("20110831")
        td = timedelta(days=1)
        vd2 = vdate - td
        self.assertTrue(isinstance(vd2, date.Date))
        self.assertEquals(vd2.get_date(), "20110830000000")
        vd2 = vdate + "M1D"
        self.assertTrue(isinstance(vd2, date.Date))
        self.assertEquals(vd2.get_date(), "20110830000000")
        print "test __add__ Ok"

    def test_replace(self):
        args = [
            { 'month': 12 },
            { 'minute': 21 },
            { 'second': 59 },
            { 'year': 2015, 'second': 01 }
        ]
        res = [
            date.Date("20111231").get_date(),
            date.Date("201108310021").get_date(),
            date.Date("20110831000059").get_date(),
            date.Date("20150831000001").get_date()
        ]
        vdate = date.Date("20110831")
        for ind, value in enumerate(args):
            self.assertEquals(vdate.replace(**value).get_date(), res[ind])
        print "test replace Ok"

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
        print "test to_cnesjulian Ok"

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
            self.assertEquals(do.from_cnesjulian(j), d)
        print "test from_cnesjulian Ok"


class utstrdate(TestCase):

    def test_get_tuple_ym_other(self):
        svdate = date.StrDate("20110726121314")
        self.assertEquals(svdate._get_tuple_ym_other("20110726121314"),
                            ('2011', '07', '26121314'))
        print "test _get_tuple_ym_other ok"

    def test_verify_date(self):
        svdate = date.StrDate("20110726121314")
        args = [
            ('2011', '02', '31'),
            ('2011', '04', '31'),
            ('2011', '04', '31121506')
        ]
        res = [
            ('2011', '02', '28'),
            ('2011', '04', '30'),
            ('2011', '04', '30121506')
        ]
        for i, val in enumerate(args):
            self.assertEquals(svdate._verify_date(val), res[i])
        print "test _verify_date ok"

    def test__init__(self):
        svdate = date.StrDate("20110726121314")
        self.assertEquals(svdate._vxdate, "20110726121314")
        svdate = date.StrDate("20110231121314")
        self.assertEquals(svdate._vxdate, "20110228121314")
        print "test __init__ Ok"

    def test_date_type_1(self):
        svdate = date.StrDate("20110726")
        self.assertEquals(svdate._date_type_1([ 0, 4, 6, 8 ]), 
                                        ('2011', '07', '26', '0', '0', '0'))
        print "test _date_type_1 ok"

    def test_date_type_2(self):
        svdate = date.StrDate("2011072612")
        self.assertEquals(svdate._date_type_2([ 0, 4, 6, 8, 10 ]), 
                                        ('2011', '07', '26', '12', '0', '0'))
        print "test _date_type_2 ok"

    def test_date_type_3(self):
        svdate = date.StrDate("201107261213")
        self.assertEquals(svdate._date_type_3([ 0, 4, 6, 8, 10, 12 ]), 
                                        ('2011', '07', '26', '12', '13', '0'))
        print "test _date_type_3 ok"

    def test_date_type_4(self):
        svdate = date.StrDate("20110726121314")
        self.assertEquals(svdate._date_type_4([ 0, 4, 6, 8, 10, 12, 14 ]),
                                        ('2011', '07', '26', '12', '13', '14'))
        svdate = date.StrDate("20110726")
        self.assertEquals(svdate._date_type_4([ 0, 4, 6, 8, 10, 12, 14 ]),
                                        ('2011', '07', '26', '', '', ''))
        print "test _date_type_4 ok"

    def test_gen_date_str(self):
        args = [
            "20110726",
            "2011072613",
            "201107261301",
            "20110726130159"
        ]
        res = [
            ('2011', '07', '26', '0', '0', '0'),
            ('2011', '07', '26', '13', '0', '0'),
            ('2011', '07', '26', '13', '01', '0'),
            ('2011', '07', '26', '13', '01', '59')
        ]
        for i, val in enumerate(args):
            svdate = date.StrDate(val)
            self.assertEquals(svdate.gen_date_str(), res[i])
        print "test _gen_date_str ok"

    def test_bissextile(self):
        args = [
            '16000228',
            '20001211',
            '19000701000001'
            '19920523090805'
        ]
        res = [
            True,
            True,
            False,
            True]

        for i, val in enumerate(args):
            svdate = date.StrDate(val)
            self.assertEquals(svdate.leap_year(), res[i])
        print "test _bissextile ok"

    def test_gen_date_fmt(self):
        args = [
            ("20110726", 'yyyy'),
            ("20110726", 'yyyymm'),
            ("20110726", 'yyyymmdd'),
            ("2011072613", 'yyyymmddhh'),
            ("201107261213", 'mn'),
            ("20110726", 'mn')
        ]
        res = [
            '2011',
            '201107',
            '20110726',
            '2011072613',
            '13',
            '0'
        ]
        for i, val in enumerate(args):
            svdate = date.StrDate(val[0])
            self.assertEquals(svdate._gen_date_fmt(val[1]), res[i])
        print "test _bissextile ok"

if __name__ == '__main__':
    main()
