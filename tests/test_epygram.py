#!/usr/bin/env python
# -*- coding: utf-8 -*-

numpy_looks_fine = True
try:
    import numpy as np
except ImportError:
    numpy_looks_fine = False

import tempfile
import unittest

import footprints

import vortex
from vortex.tools.date import Date, Time
from common.tools.grib import GRIBFilter
import common.util.usepygram as uepy

clog = footprints.loggers.getLogger('common')
clog.setLevel('ERROR')

u10_filter = '''
{
  "fields_exclude": [
    {
      "shortName": [
        "10v",
        "t"
      ]
    }
  ],
  "fid_format": "GRIB1",
  "filter_name": "blow"
}'''

t_filter = '''
{
  "fields_include": [
    {
      "comment0": "Temperature",
      "indicatorOfTypeOfLevel": 100,
      "shortName": "t",
      "level": [
        850,
        500
      ]
    },
    {
      "comment": "wind",
      "shortName": "10u"
    }
  ],
  "fid_format": "GRIB1",
  "filter_name": "hot"
}'''


class _FakeRH(object):

    def __init__(self, infile, actualfmt):
        self.container = vortex.data.containers.SingleFile(filename=infile,
                                                           actualfmt=actualfmt)
        self.contents = vortex.data.contents.FormatAdapter(datafmt=actualfmt)
        self.contents.slurp(self.container)

    def exists(self):
        return True


class _EpyTestBase(unittest.TestCase):

    def setUp(self):
        if not (numpy_looks_fine and uepy.is_epygram_available('1.0.0')):
            raise self.skipTest('Epygram >= v1.0.0 is not available')

        uepy.epygram.epylog.setLevel('ERROR')

        self.t = vortex.sessions.current()
        self.sh = self.t.system()

        self.datapath = self.sh.path.join(self.t.glove.siteroot, 'tests', 'data')

    def demofile(self, demofile):
        return self.sh.path.join(self.datapath, demofile)


class TestEpygramContents(_EpyTestBase):

    def test_contents(self):
        # FA
        fa_c = vortex.data.containers.SingleFile(filename=self.demofile('historic.light.fa'),
                                                 actualfmt='fa')
        ct = vortex.data.contents.FormatAdapter(datafmt='fa')
        ct.slurp(fa_c)
        self.assertEqual(ct.data.format, 'FA')
        self.assertListEqual(['S090TEMPERATURE', 'SURFTEMPERATURE', ],
                             ct.data.listfields())
        self.assertItemsEqual({'date': Date(2016, 5, 30, 18, 0), 'term': Time(0, 0)},
                              ct.metadata)
        # GRIB
        grib_c = vortex.data.containers.SingleFile(filename=self.demofile('fullpos.light.grib'),
                                                   actualfmt='grib')
        ct = vortex.data.contents.FormatAdapter(datafmt='grib')
        ct.slurp(grib_c)
        self.assertEqual(ct.data.format, 'GRIB')
        self.assertEqual(12, len(ct.data.listfields()))
        self.assertItemsEqual({'date': Date(2016, 5, 30, 18, 0), 'term': Time(0, 0)},
                              ct.metadata)


class TestEpygramAdvanced(_EpyTestBase):

    def setUp(self):
        super(TestEpygramAdvanced, self).setUp()

        # Work in a dedicated directory
        self.tmpdir = tempfile.mkdtemp(suffix='test_epygram')
        self.oldpwd = self.sh.pwd()
        self.sh.cd(self.tmpdir)
        self.sh.signal_intercept_on()

    def tearDown(self):
        self.sh.cd(self.oldpwd)
        self.sh.remove(self.tmpdir)
        self.sh.signal_intercept_off()

    def test_epygram_hooks(self):
        self.sh.cp(self.demofile('historic.verylight.fa'),
                   'historic.verylight.fa')
        rh1 = _FakeRH(self.demofile('historic.light.fa'), 'fa')
        rh2 = _FakeRH('historic.verylight.fa', 'fa')
        f1_ref = rh1.contents.data.readfield('SURFTEMPERATURE').getdata()
        uepy.copyfield(self.t, rh2, rh1, 'SURFTEMPERATURE', 'SURFTEMPERATURE')
        # Check that the copy went fine
        self.assertTrue(np.ma.allequal(rh2.contents.data.readfield('SURFTEMPERATURE').getdata(),
                                       f1_ref))
        # Overwrite but change compression
        uepy.overwritefield(self.t, rh2, rh1, 'SURFTEMPERATURE', None, dict(KNBPDG=12))
        # ...bits the result remain the same since we are increasing the number of bits
        self.assertTrue(np.ma.allequal(rh2.contents.data.readfield('SURFTEMPERATURE').getdata(),
                                       f1_ref))
        # Addfield (add 2 fields at once)
        uepy.addfield(self.t, rh2,
                      ['SURFTEMPERATURE', ], ['SURFTOTO', 'SURFTITI', ],
                      0, dict(KNBPDG=2))
        self.assertEqual(rh2.contents.data.readfield('SURFTOTO').quadmean(),
                         0)
        self.assertEqual(rh2.contents.data.readfield('SURFTOTO').quadmean(),
                         0)

    @staticmethod
    def _simplified_grib_fid(fid):
        return '{:s}_{:s}_level_{:d}'.format(fid['shortName'], fid['typeOfLevel'],
                                             fid['level'])

    def test_gribfilter(self):
        self.sh.cp(self.demofile('fullpos.light.grib'), 'fullpos.light.grib')
        gfilter = GRIBFilter(concatenate=True)
        gfilter.add_filters(u10_filter, t_filter)
        gfilter('fullpos.light.grib', 'fullpos.light_{filtername:s}.grib')
        n_cat = _FakeRH('fullpos.light_concatenate.grib', 'grib')
        self.assertEqual(len(n_cat.contents.data.listfields()), 12)
        n_blow = _FakeRH('fullpos.light_blow.grib', 'grib')
        self.assertListEqual([self._simplified_grib_fid(fid)
                              for fid in n_blow.contents.data.listfields()],
                             ['10u_heightAboveGround_level_10'])
        n_hot = _FakeRH('fullpos.light_hot.grib', 'grib')
        self.assertListEqual([self._simplified_grib_fid(fid)
                              for fid in n_hot.contents.data.listfields()],
                             ['10u_heightAboveGround_level_10',
                              't_isobaricInhPa_level_850',
                              't_isobaricInhPa_level_500'])

if __name__ == '__main__':
    unittest.main()
