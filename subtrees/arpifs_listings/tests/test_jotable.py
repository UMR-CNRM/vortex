import io
import os
import unittest

from arpifs_listings import jo_tables

DATADIR = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))


def _find_testfile(fname):
    return os.path.join(DATADIR, fname)


class TestListingJoTable(unittest.TestCase):

    NODIFFS_STR = """=====================
Jo-table: SCREENING JOB    T1198 NCONF=     1 NSIM4D=     0 NUPTRA=     0
(Worst differences)
Obscount:          0 ( 0.00%)
Jo:             0.00 ( 0.00%)
Jo/n:           0.00 ( 0.00%)

"""
    BIGDIFFS_STR = """=====================
Jo-table: SCREENING JOB    T1198 NCONF=     1 NSIM4D=     0 NUPTRA=     0
(Worst differences)
Obscount:    2491340 (100.00%)
Jo:       3395197.93 (100.00%)
Jo/n:           1.36 (100.00%)

"""

    @staticmethod
    def _ingest(fname):
        filename = _find_testfile(fname)
        with open(filename) as fh:
            return (filename, [line.rstrip("\n") for line in fh])

    def test_single(self):
        l1_j = jo_tables.JoTables(* self._ingest('listing_screen_li1'))
        self.assertEqual(len(l1_j), 1)
        l1_t = l1_j["SCREENING JOB    T1198 NCONF=     1 NSIM4D=     0 NUPTRA=     0"]
        self.assertEqual(l1_t.jon, 50.52486883414493)
        otlist = list(l1_t.keys())
        self.assertEqual(otlist[0].rstrip(), 'SYNOP, LAND STATIONS AND SHIPS')
        self.assertEqual(otlist[1].rstrip(), 'AIREP, AIRCRAFT DATA')
        self.assertEqual(otlist[6].rstrip(), 'SATEM, SATELLITE SOUNDING DATA')
        l1_conv = l1_t[otlist[0]]
        self.assertEqual(len(l1_conv), 7)
        slist = list(l1_conv.keys())
        l1_ships = l1_conv[slist[2]]
        self.assertListEqual(list(l1_ships.keys()), ['U', 'H2', 'Z', 'T2', 'TS'])
        # Empty equals
        self.assertEqual(jo_tables.JoTables("dummy1", []),
                         jo_tables.JoTables("dummy2", []))

    def test_diff_easy(self):
        # Norm comparison
        l1_j = jo_tables.JoTables(_find_testfile('listing_screen_li1'))
        l2_j = jo_tables.JoTables(_find_testfile('listing_screen_li1'))
        self.assertEqual(l1_j, l2_j)
        fulldiff = l2_j.compute_diff(l1_j)
        nulldiff = {'jo': dict(diff=0., reldiff=0.),
                    'jo/n': dict(diff=0., reldiff=0.),
                    'n': dict(diff=0, reldiff=0.), }
        for table in fulldiff.values():
            for otype in table.values():
                for osensor in otype.values():
                    for ovar in osensor.values():
                        tmpdiff = {'jo': ovar['jo'],
                                   'jo/n': ovar['jo/n'],
                                   'n': ovar['n'], }
                        self.assertDictEqual(tmpdiff, nulldiff)
        str_out = io.StringIO()
        l2_j.print_diff(l1_j, out=str_out, onlymaxdiff=True)
        str_out.seek(0)
        self.assertEqual(str_out.read(), self.NODIFFS_STR)

    def test_diff_blurp(self):
        # Norm comparison
        l1_j = jo_tables.JoTables(_find_testfile('listing_screen_li1'))
        l2_j = jo_tables.JoTables(_find_testfile('listing_screen_li2'))
        self.assertNotEqual(l1_j, l2_j)
        bigdiff = {'n': dict(diff=2491340, reldiff=1.),
                   'jo': dict(diff=3395197.925141, reldiff=1.),
                   'jo/n': dict(diff=1.3627999089409717, reldiff=1.)}
        self.assertDictEqual(l2_j.maxdiff(l1_j), bigdiff)
        str_out = io.StringIO()
        l2_j.print_diff(l1_j, out=str_out, onlymaxdiff=True)
        str_out.seek(0)
        self.assertEqual(str_out.read(), self.BIGDIFFS_STR)

    def test_as_dict(self):
        l1_j = jo_tables.JoTables(_find_testfile('listing_screen_li1'))
        l1_jbis = jo_tables.JoTables(_find_testfile('listing_screen_li1'))
        self.assertEqual(l1_j.as_dict(), l1_jbis.as_dict())
        d1 = l1_j.as_dict()
        d1_s = d1['SCREENING JOB    T1198 NCONF=     1 NSIM4D=     0 NUPTRA=     0']
        self.assertEqual(d1_s['SYNOP, LAND STATIONS AND SHIPS  ']['SYNOP LAND MANUAL REPORT        ']['U10']['n'],
                         18464)
        self.assertEqual(d1_s['SATOB, ATMOSPHERIC MOTION WINDS ']['METEOSAT    57 METHOD=VIS2      ']['U']['n'],
                         200)


if __name__ == '__main__':
    unittest.main()
