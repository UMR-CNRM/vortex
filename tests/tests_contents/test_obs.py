#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from unittest import main, skipUnless
import os
import sys

if __name__ == '__main__':
    sys.path.insert(0, os.path.realpath(os.path.join(os.path.dirname(__file__), '..')))

from .test_generic import _BaseDataContentTest

from bronx.fancies import loggers
from bronx.stdtypes.date import Date
from bronx.syntax.externalcode import ExternalCodeImportChecker
from vortex.data.containers import DataSizeTooBig, InCore
from common.data import obs

# Numpy is not mandatory
npchecker = ExternalCodeImportChecker('numpy')
with npchecker as npregister:
    import numpy as np  # @UnusedImport


class _FakeResource(object):

    def __init__(self, *args, **kwargs):
        super(_FakeResource, self).__init__(*args, **kwargs)
        self.date = Date(2000, 1, 1, 6, 0, 0)
        self.other = 1


VBC_T = """VARBC_cycle.version005
MINI  20000101         0
         1     10980
ix=1
class=rad
key=4 3 4
label=Tb    METOP    2     4 SENSOR=AMSUA    channel=4
ndata=0
npred=8
predcs=0 8 9 10 15 16 17 18
param0= 0.000E+00  0.000E+00  0.000E+00  0.000E+00  0.000E+00  0.000E+00  0.000E+00  0.000E+00
params= 0.000E+00  0.000E+00  0.000E+00  0.000E+00  0.000E+00  0.000E+00  0.000E+00  0.000E+00
hstgrm=6 0 1 2 2 3 13 4 8 0 1 0 3 12 5 11 13 10 4 9 24 14 16 12 22 14 21 15 17 23 40 30 39 46 42 50 79 59 70 102 107 146 234 301 502 819 1322 2711 5841 9794 12656 13018 11735 10097 7960 6230 4653 3601 2727 1822 1306 970 755 687 598 519 465 459 362 282 221 124 115 100 99 60 64 34 33 30 44 39 35 24 22 30 11 19 24 12 8 16 14 8 9 9 4 6 7 5 """


class UtVarBCContentLimited(_BaseDataContentTest):

    _data = (VBC_T, )
    _container_limit = 50  # This limit is intentionally very small

    @skipUnless(npchecker.is_available(), "The Numpy package is unavailable")
    def test_indexedtable_basic(self):
        resource = _FakeResource()
        ct = obs.VarBCContent()
        ct.slurp(self.insample[0])
        self.assertEqual(ct.is_diffable(), False)
        self.assertEqual(ct.metadata['version'], 5)
        self.assertTrue(ct.metadata_check(resource, delta=dict(date='-PT6H')))
        # The VarBC file size is too big wrt _container_limit : it fails...
        with self.assertRaises(DataSizeTooBig):
            len(ct.data)


class UtVarBCContent(_BaseDataContentTest):

    _data = (VBC_T, )

    @skipUnless(npchecker.is_available(), "The Numpy package is unavailable")
    def test_indexedtable_basic2(self):
        ct = obs.VarBCContent()
        ct.slurp(self.insample[0])
        self.assertEqual(ct.size, 1)    # This time _container_limit is big enough
        self.assertTrue(len(ct.data[1].params), 8)


REFDATA_T = """conv     OBSOUL   conv             20170410  0    14176    179636 5    0 20170409210000 20170410025900  SYNOP                   TEMP  PILOT
acar BUFR acar 20170410 00
tovhirs BUFR hirs 20170410 00"""

REFDATA_R = """conv     OBSOUL   conv             20170410 0
acar     BUFR     acar             20170410 00
tovhirs  BUFR     hirs             20170410 00
"""

REFDATA_E = [obs.ObsRefItem('conv', 'OBSOUL', 'conv', '20170410', '0'),
             obs.ObsRefItem('acar', 'BUFR', 'acar', '20170410', '00'),
             obs.ObsRefItem('tovhirs', 'BUFR', 'hirs', '20170410', '00'), ]


class UtRefdataContent(_BaseDataContentTest):

    _data = (REFDATA_T, )

    def test_refadata_basic(self):
        ct = obs.ObsRefContent()
        ct.slurp(self.insample[0])
        self.assertEqual(ct.data, REFDATA_E)
        self.assertEqual(len(ct), 3)
        outincore = InCore()
        ct.rewrite(outincore)
        outincore.seek(0)
        self.assertEqual(outincore.read(), REFDATA_R)


OBSMAP_T = """conv conv OBSOUL conv
# Blop
conv acar BUFR acar
conv airep BUFR airep
tovsa tovamsua BUFR amsua"""

OBSMAP_R = """conv         conv         OBSOUL       conv
conv         acar         BUFR         acar
conv         airep        BUFR         airep
tovsa        tovamsua     BUFR         amsua
"""

OBSMAP_E = [obs.ObsMapItem('conv', 'conv', 'OBSOUL', 'conv'),
            obs.ObsMapItem('conv', 'acar', 'BUFR', 'acar'),
            obs.ObsMapItem('conv', 'airep', 'BUFR', 'airep'),
            obs.ObsMapItem('tovsa', 'tovamsua', 'BUFR', 'amsua'), ]


class UtObsMapContent(_BaseDataContentTest):

    _data = (OBSMAP_T, )

    def test_obsmap_basic(self):
        ct = obs.ObsMapContent(discarded=set())
        ct.slurp(self.insample[0])
        self.assertEqual(ct.data, OBSMAP_E)
        self.assertEqual(len(ct), 4)
        outincore = InCore()
        ct.rewrite(outincore)
        outincore.seek(0)
        self.assertEqual(outincore.read(), OBSMAP_R)
        # ObsMap specifics
        self.assertEqual(ct.odbset(), set(['conv', 'tovsa']))
        self.assertEqual(ct.dataset(), set(['conv', 'airep', 'acar', 'tovamsua']))
        self.assertEqual(ct.fmtset(), set(['OBSOUL', 'BUFR']))
        self.assertEqual(ct.instrset(), set(['conv', 'airep', 'acar', 'amsua']))
        self.assertEqual(ct.getfmt(dict(part='airep'), dict()), 'BUFR')
        with loggers.contextboundGlobalLevel('critical'):
            self.assertEqual(ct.getfmt(dict(part='toto'), dict()), None)
        # Discard
        ct = obs.ObsMapContent(discarded=set(['conv', ]))
        ct.slurp(self.insample[0])
        self.assertEqual(ct.data, [OBSMAP_E[3], ])
        ct = obs.ObsMapContent(discarded=set(['conv:conv', 'conv:airep', ]))
        ct.slurp(self.insample[0])
        self.assertEqual(ct.data, [OBSMAP_E[1], OBSMAP_E[3], ])
        ct = obs.ObsMapContent(discarded=set(['conv:a', ]))
        ct.slurp(self.insample[0])
        self.assertEqual(ct.data, [OBSMAP_E[0], OBSMAP_E[3], ])
        ct = obs.ObsMapContent(discarded=set(['conv:a[a-i]', ]))
        ct.slurp(self.insample[0])
        self.assertEqual(ct.data, [OBSMAP_E[0], OBSMAP_E[3], ])
        # Only
        ct = obs.ObsMapContent(only=set(['conv', ]))
        ct.slurp(self.insample[0])
        self.assertEqual(ct.data, [OBSMAP_E[0], OBSMAP_E[1], OBSMAP_E[2], ])
        ct = obs.ObsMapContent(only=set(['conv:a[a-i]', ]))
        ct.slurp(self.insample[0])
        self.assertEqual(ct.data, [OBSMAP_E[1], OBSMAP_E[2], ])
        ct = obs.ObsMapContent(only=set(['conv', ]), discarded=set(['conv:a[a-i]', ]))
        ct.slurp(self.insample[0])
        self.assertEqual(ct.data, [OBSMAP_E[0], ])


if __name__ == '__main__':
    main(verbosity=2)
