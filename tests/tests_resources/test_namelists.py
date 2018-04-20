
from __future__ import print_function, absolute_import, unicode_literals, division

import unittest

import footprints as fp
import common.data.namelists  # @UnusedImport

rcollect = fp.collectors.get(tag='resource')
rcollect.fasttrack = ('kind', )


class TestNamelist(unittest.TestCase):

    def test_ggetoption(self):
        # Test the namelist selection based on dates
        fpcommon = dict(kind='namelist', model='arpege')
        answer = 'extract={}'

        res = fp.proxy.resource(** fpcommon)
        self.assertEqual(res.gget_urlquery(), answer.format('namel_arpege'))

        prev_loglev = common.data.namelists.logger.level
        common.data.namelists.logger.setLevel('CRITICAL')

        # Test the simple case (ordered, unordered and duplicated elements)
        for lsrc in (('n_zzzz:YYYY0110|n_snow:YYYY0130|n_eggs:YYYY0402|' +
                      'n_beach:YYYY0701|n_indian_summer:YYYY0915|' +
                      'n_glagla:YYYY1101|n_hips:YYYY1220'),
                     ('n_glagla:YYYY1101|n_hips:YYYY1220|' +
                      'n_beach:YYYY0701|n_indian_summer:YYYY0915|' +
                      'n_zzzz:YYYY0110|n_snow:YYYY0130|n_eggs:YYYY0402'),
                     ('n_glagla:YYYY1101|n_snow:YYYY0130|n_hips:YYYY1220|' +
                      'n_beach:YYYY0701|n_indian_summer:YYYY0915|' +
                      'n_zzzz:YYYY0110|n_oups:YYYY0130|n_eggs:YYYY0402')
                     ):
            res = fp.proxy.resource(source=lsrc, ** fpcommon)
            with self.assertRaises(AttributeError):
                res.gget_urlquery()
            res = fp.proxy.resource(date='2015010106', source=lsrc, ** fpcommon)
            self.assertEqual(res.gget_urlquery(), answer.format('n_hips'))
            res = fp.proxy.resource(date='2015012923', source=lsrc, ** fpcommon)
            self.assertEqual(res.gget_urlquery(), answer.format('n_zzzz'))
            res = fp.proxy.resource(date='2015013000', source=lsrc, ** fpcommon)
            self.assertEqual(res.gget_urlquery(), answer.format('n_snow'))
            res = fp.proxy.resource(date='2016022912', source=lsrc, ** fpcommon)
            self.assertEqual(res.gget_urlquery(), answer.format('n_snow'))
            res = fp.proxy.resource(date='20161103', source=lsrc, ** fpcommon)
            self.assertEqual(res.gget_urlquery(), answer.format('n_glagla'))
            res = fp.proxy.resource(date='20161225', source=lsrc, ** fpcommon)
            self.assertEqual(res.gget_urlquery(), answer.format('n_hips'))

        # Implicit first element
        lsrc = ('n_newyear|n_zzzz:YYYY0110|n_snow:YYYY0130|n_eggs:YYYY0402|' +
                'n_beach:YYYY0701|n_indian_summer:YYYY0915|' +
                'n_glagla:YYYY1101|n_hips:YYYY1220')
        res = fp.proxy.resource(date='20160102', source=lsrc, ** fpcommon)
        self.assertEqual(res.gget_urlquery(), answer.format('n_newyear'))
        res = fp.proxy.resource(date='2015012923', source=lsrc, ** fpcommon)
        self.assertEqual(res.gget_urlquery(), answer.format('n_zzzz'))

        common.data.namelists.logger.setLevel(prev_loglev)


if __name__ == "__main__":
    unittest.main(verbosity=2)
