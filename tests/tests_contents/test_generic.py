#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import json
from unittest import TestCase, main

from vortex.data import contents
from vortex.data.containers import CONTAINER_INCORELIMIT, InCore


class _BaseDataContentTest(TestCase):

    _data = b'Very short fake data'
    _temporize = False
    _container_limit = CONTAINER_INCORELIMIT

    @property
    def data(self):
        return self._data

    def setUp(self):
        super(_BaseDataContentTest, self).setUp()
        if not isinstance(self._data, (tuple, list)):
            self._data = (self._data, )
        self.insample = list()
        for d in self.data:
            self.insample.append(InCore(actualfmt='foo',
                                        maxreadsize=self._container_limit))
            incorefh = self.insample[-1].iodesc()
            incorefh.write(d)
            if self._temporize:
                self.insample[-1].temporize()


class UtDataContent(_BaseDataContentTest):

    def test_datacontent_basic(self):
        ct = contents.DataContent(data=self.data[0])
        ct.slurp(self.insample[0])
        self.assertEqual(ct.data, self.data[0])
        self.assertEqual(ct.datafmt, None)
        self.assertEqual(ct.upper(), self.data[0].upper())
        self.assertEqual(len(ct.metadata), 0)
        self.assertTrue(ct.metadata_check(object()))
        self.assertEqual(ct.size, len(self.data[0]))
        self.assertEqual(ct.export_dict(), ('vortex.data.contents', 'DataContent') )
        self.assertEqual(ct.is_diffable(), False)


INDEXED_E = {'machin': ['bidule'], 'toto': ['1', '2', '3']}

INDEXED_T = """# A comment to start with
toto 1 2 3
machin bidule
# A final comment"""

INDEXED_T2 = """# A comment to start with
toto 1 2   3
machin bidule"""


class UtIndexedTable(_BaseDataContentTest):

    _data = (INDEXED_T, INDEXED_T2)

    def test_indexedtable_basic(self):
        ct = contents.IndexedTable()
        ct.slurp(self.insample[0])
        self.assertEqual(ct.data, INDEXED_E)
        self.assertEqual(ct.size, len(self.data[0]))
        self.assertEqual(ct.is_diffable(), True)
        ct2 = contents.IndexedTable()
        ct2.slurp(self.insample[1])
        self.assertTrue(ct.diff(ct2))
        # Dict like features
        self.assertIn('machin', ct)
        self.assertEqual(len(ct), len(INDEXED_E))
        ct['other'] = 1
        self.assertEqual(ct['machin'], ['bidule', ])
        self.assertEqual(ct['other'], 1)
        del ct['other']
        self.assertNotIn('other', ct)


JSON_E = dict(a=1, b=1.5, c='toto', d=[1, 2, 3])
JSON_T = json.dumps(JSON_E)


class UtJsonContent(_BaseDataContentTest):

    _data = (JSON_T, )
    _temporize = True

    def test_jsoncontent_basic(self):
        ct = contents.JsonDictContent()
        ct.slurp(self.insample[0])
        self.assertEqual(ct.data, JSON_E)
        self.assertEqual(ct.size, len(self.data[0]))
        self.assertEqual(ct.is_diffable(), True)


ALMOST_LIST_E = ['1\n', '#Truc\n', 'toto\n']
ALMOST_LIST_T = ''.join(ALMOST_LIST_E)


class UtAlmostListContent(_BaseDataContentTest):

    _data = (ALMOST_LIST_T, )

    def test_almostlistcontent_basic(self):
        ct = contents.AlmostListContent()
        ct.slurp(self.insample[0])
        self.assertEqual(ct.data, ALMOST_LIST_E)
        self.assertEqual(ct(), ALMOST_LIST_E)
        self.assertEqual(ct.size, len(self.data[0]))
        self.assertEqual(len(ct), len(ALMOST_LIST_E))
        self.assertEqual(ct.is_diffable(), True)
        # Maxprint is no less than 10
        ct.maxprint = 5
        self.assertEqual(ct.maxprint, 10)
        ct.maxprint = -20.1
        self.assertEqual(ct.maxprint, 20)
        # List like features
        self.assertEqual(ct[-1], 'toto\n')
        ct[2] = 2
        self.assertEqual(ct[-1], 2)
        self.assertEqual(ct[1:3], ['#Truc\n', 2])
        ct[1:3] = [2, 2]
        self.assertEqual(ct[1:3], [2, 2])
        del ct[0]
        self.assertEqual(ct.data, [2, 2])
        del ct[0:2]
        self.assertEqual(len(ct), 0)
        # Merge
        ct = contents.AlmostListContent()
        ct.slurp(self.insample[0])
        ct2 = contents.AlmostListContent()
        ct2.slurp(self.insample[0])
        ct.merge(ct2)
        self.assertEqual(ct.size, len(self.data[0] * 2))
        self.assertEqual(ct.data, ALMOST_LIST_E + ALMOST_LIST_E)


TEXT_E = [['1', 'blop', '3.5'], ['5', 'toto', '10.5']]
TEXT_T = """1   blop  3.5
#Un truc a ignorer
5 toto   10.5"""


class UtTextContent(_BaseDataContentTest):

    _data = (TEXT_T, )

    def test_textcontent_basic(self):
        ct = contents.TextContent(fmt='i={0:s} name={1:s} real={2:s}')
        ct.slurp(self.insample[0])
        self.assertEqual(ct.data, TEXT_E)
        self.assertEqual(ct.size, len(self.data[0]))
        self.assertEqual(ct.is_diffable(), True)
        self.assertEqual(ct.formatted_data(ct[0]),
                         'i=1 name=blop real=3.5')
        self.assertEqual(str(ct), '\n'.join([str(t) for t in TEXT_E]))


class UtDataRawContent(_BaseDataContentTest):

    _data = (ALMOST_LIST_T, )

    def test_almostlistcontent_basic(self):
        ct = contents.DataRaw(window=2)
        ct.slurp(self.insample[0])
        self.assertEqual(list(ct.data), ALMOST_LIST_E[:2])
        self.assertEqual(ct.size, 0)
        self.assertEqual(len(ct), 2)
        self.assertEqual(ct.is_diffable(), True)


if __name__ == '__main__':
    main(verbosity=2)