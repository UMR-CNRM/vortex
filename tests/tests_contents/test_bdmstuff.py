# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from collections import deque
import io
from unittest import main, TestCase
import os

from bronx.fancies import loggers
from bronx.stdtypes.date import Date, Period
from footprints import proxy as fpx

from vortex.data.contents import FormatAdapter
from vortex.tools.listings import ListBasedCutoffDispenser
from common.data.query import BDMQueryContent
from common.util.hooks import _new_static_cutoff_dispencer

tloglevel = 'critical'

DATADIR = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'data'))


@loggers.unittestGlobalLevel(tloglevel)
class UtBdmStuff(TestCase):

    @property
    def ouloutput_ct(self):
        container = fpx.container(filename=os.path.join(DATADIR, 'ouloutput'),
                                  actualfmt='bdmbufr_listing')
        ct = FormatAdapter(datafmt=container.actualfmt)
        ct.slurp(container)
        return ct

    @property
    def bdmquery_ct(self):
        container = fpx.container(filename=os.path.join(DATADIR, 'dir_script_alim_bufr_sample'),
                                  actualfmt='ascii')
        ct = BDMQueryContent()
        ct.slurp(container)
        return ct

    def test_ouloutput_basic(self):
        ct = self.ouloutput_ct
        self.assertEqual(
            ct.data.cutoffs,
            {
                'aeoluswind': deque([Date(2021, 4, 14, 2, 10, 6)]),
                'airsbt': deque([None]),
                'amsr': deque([Date(2021, 4, 14, 2, 10, 12)]),
                'ascat': deque([Date(2021, 4, 14, 2, 10, 11)]),
                'atms': deque([Date(2021, 4, 14, 2, 10, 7)]),
                'geowind': deque([Date(2021, 4, 14, 2, 10, 7)]),
                'gmi': deque([Date(2021, 4, 14, 2, 10, 12)]),
                'kuscat': deque([None]),
                'mwri': deque([None]),
                'saphir': deque([Date(2021, 4, 14, 2, 10, 8)]),
                'satwind': deque([Date(2021, 4, 14, 2, 10, 9)]),
                'ssmis': deque([Date(2021, 4, 14, 2, 10, 10)]),
                'tovsamsua': deque([None,
                                    Date(2021, 4, 14, 2, 10, 8),
                                    None,
                                    Date(2021, 4, 14, 2, 10, 9),
                                    Date(2021, 4, 14, 2, 10, 9)]),
                'tovsamsub': deque([None,
                                    Date(2021, 4, 14, 2, 10, 6),
                                    Date(2021, 4, 14, 2, 10, 7),
                                    Date(2021, 4, 14, 2, 10, 8)])
            })

        c_disp = ct.data.cutoffs_dispenser()
        self.assertEqual(c_disp.max_cutoff, Date(2021, 4, 14, 2, 10, 12))
        self.assertEqual(
            c_disp.default_cutoffs,
            {
                'aeoluswind': Date(2021, 4, 14, 2, 10, 6),
                'amsr': Date(2021, 4, 14, 2, 10, 12),
                'ascat': Date(2021, 4, 14, 2, 10, 11),
                'atms': Date(2021, 4, 14, 2, 10, 7),
                'geowind': Date(2021, 4, 14, 2, 10, 7),
                'gmi': Date(2021, 4, 14, 2, 10, 12),
                'saphir': Date(2021, 4, 14, 2, 10, 8),
                'satwind': Date(2021, 4, 14, 2, 10, 9),
                'ssmis': Date(2021, 4, 14, 2, 10, 10),
                'tovsamsua': Date(2021, 4, 14, 2, 10, 9),
                'tovsamsub': Date(2021, 4, 14, 2, 10, 8)
            })
        self.assertEqual(c_disp.default_cutoffs['newone'],
                         Date(2021, 4, 14, 2, 10, 12))
        self.assertEqual(c_disp('tovsamsua'), Date(2021, 4, 14, 2, 10, 9))
        self.assertEqual(c_disp('tovsamsua'), Date(2021, 4, 14, 2, 10, 8))
        self.assertEqual(c_disp('tovsamsua'), Date(2021, 4, 14, 2, 10, 9))
        self.assertEqual(c_disp('tovsamsua'), Date(2021, 4, 14, 2, 10, 9))
        self.assertEqual(c_disp('tovsamsua'), Date(2021, 4, 14, 2, 10, 9))
        self.assertEqual(c_disp('tovsamsua'), Date(2021, 4, 14, 2, 10, 9))
        self.assertEqual(c_disp('other_one'), Date(2021, 4, 14, 2, 10, 12))
        self.assertEqual(c_disp('ssmis'), Date(2021, 4, 14, 2, 10, 10))
        self.assertEqual(c_disp('ssmis'), Date(2021, 4, 14, 2, 10, 10))

        c_disp = ct.data.cutoffs_dispenser(fuse_per_obstype=True)
        self.assertEqual(c_disp('tovsamsub'), Date(2021, 4, 14, 2, 10, 8))
        self.assertEqual(c_disp('tovsamsub'), Date(2021, 4, 14, 2, 10, 8))
        self.assertEqual(c_disp('tovsamsub'), Date(2021, 4, 14, 2, 10, 8))
        self.assertEqual(c_disp('tovsamsub'), Date(2021, 4, 14, 2, 10, 8))
        self.assertEqual(c_disp('other_one'), Date(2021, 4, 14, 2, 10, 12))
        self.assertEqual(c_disp('ssmis'), Date(2021, 4, 14, 2, 10, 10))

    def test_bdm_query_basics(self):
        # Nominal case
        ct = self.bdmquery_ct
        c_disp = self.ouloutput_ct.data.cutoffs_dispenser()
        ct.add_cutoff_info(c_disp)
        with io.open(os.path.join(DATADIR, 'dir_script_alim_bufr_sample_w_cut'), 'r') as fh_b:
            self.assertListEqual(ct.data, list(fh_b.readlines()))
        # Static case
        ct = self.bdmquery_ct
        c_disp = _new_static_cutoff_dispencer('2021041400', 'PT2H10M')
        ct.add_cutoff_info(c_disp)
        with io.open(os.path.join(DATADIR, 'dir_script_alim_bufr_sample_w_cut_s0'), 'r') as fh_b:
            self.assertListEqual(ct.data, list(fh_b.readlines()))
        ct = self.bdmquery_ct
        c_disp = _new_static_cutoff_dispencer(Date('2021041400'), Period('PT2H10M'))
        ct.add_cutoff_info(c_disp)
        with io.open(os.path.join(DATADIR, 'dir_script_alim_bufr_sample_w_cut_s0'), 'r') as fh_b:
            self.assertListEqual(ct.data, list(fh_b.readlines()))
        ct = self.bdmquery_ct
        c_disp = _new_static_cutoff_dispencer(Date('2021041400'),
                                              {Period('PT2H10M'): [],
                                               '02:05:00': ['TOVSAMSUA', 'saphir']})
        ct.add_cutoff_info(c_disp)
        with io.open(os.path.join(DATADIR, 'dir_script_alim_bufr_sample_w_cut_s1'), 'r') as fh_b:
            self.assertListEqual(ct.data, list(fh_b.readlines()))
        # No cutoff can be found
        ct = self.bdmquery_ct
        ct.add_cutoff_info(ListBasedCutoffDispenser({}))
        with io.open(os.path.join(DATADIR, 'dir_script_alim_bufr_sample'), 'r') as fh_b:
            self.assertListEqual(ct.data, list(fh_b.readlines()))
        ct = self.bdmquery_ct
        ct.add_cutoff_info(ListBasedCutoffDispenser({'toto': deque([None, ])}))
        with io.open(os.path.join(DATADIR, 'dir_script_alim_bufr_sample'), 'r') as fh_b:
            self.assertListEqual(ct.data, list(fh_b.readlines()))


if __name__ == '__main__':
    main()
