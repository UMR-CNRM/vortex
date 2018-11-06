#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from unittest import main
import copy
import json
import os
import sys

sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))
from tests_contents.test_generic import _BaseDataContentTest

from common.data import eps

SAMPLE1_E = {
    "cutoff": "production",
    "date": "201610172100",
    "resource_kind": "mbsample",
    "vapp": "arome",
    "vconf": "pefrance",
    "experiment": "oper",
    "drawing": [
        {
            "cutoff": "production",
            "member": 10,
            "cluster_size": 10,
            "date": "201610171800",
            "vconf": "pearp",
            "vapp": "arpege",
            "experiment": "oper"
        },
        {
            "cutoff": "production",
            "member": 3,
            "cluster_size": 24,
            "date": "201610171800",
            "vconf": "pearp",
            "vapp": "arpege",
            "experiment": "oper"
        }
    ],
    "population": [
        {
            "date": "201610171800",
            "cutoff": "production",
            "member": m,
            "vconf": "pearp",
            "vapp": "arpege",
            "experiment": "oper",
        } for m in range(1, 34)]
}

SAMPLE1_T = json.dumps(SAMPLE1_E)

SAMPLE2_E = copy.deepcopy(SAMPLE1_E)
SAMPLE2_E['experiment'] = 'superdupont'

SAMPLE2_T = json.dumps(SAMPLE2_E)


class UtSampleContent(_BaseDataContentTest):

    _data = (SAMPLE1_T, SAMPLE2_T)
    _temporize = True

    def test_samplecontent_basic(self):
        ct = eps.SampleContent()
        ct.slurp(self.insample[0])
        ct2 = eps.SampleContent()
        ct2.slurp(self.insample[1])
        self.assertEqual(ct.data, SAMPLE1_E)
        self.assertEqual(ct2.data, SAMPLE2_E)
        self.assertNotEqual(ct.data, ct2.data)
        self.assertEqual(ct.is_diffable(), True)
        self.assertTrue(ct.diff(ct2))
        # Sample specials
        self.assertDictEqual(ct.drawing(dict(number=2), dict()),
                             ct.data['drawing'][1])
        self.assertEqual(ct.drawing(dict(number=0, virgin=0), dict()), 0)
        self.assertEqual(ct.member(dict(number=2), dict()), 3)
        self.assertEqual(ct.experiment(dict(number=2), dict()), 'oper')
        self.assertEqual(ct.members, [10, 3])
        self.assertEqual(ct.vapps, ['arpege', 'arpege'])
        self.assertEqual(ct.timedelta(dict(targetdate='201610172100', targetterm=24), dict()),
                         '27:00')


if __name__ == '__main__':
    main(verbosity=2)
