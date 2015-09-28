
import unittest

import footprints as fp
import common.data.fields  # @UnusedImport
from vortex.data import geometries
from vortex.tools.date import Date
from vortex.util.names import VortexNameBuilder


class TestFieldsRawFields(unittest.TestCase):

    def setUp(self):
        self.vb = VortexNameBuilder()

    def test_rawfields_names(self):
        fpcommon = dict(date=Date(1970, 1, 1, 1, 0, 0), cutoff='assim',
                        kind='rawfields')
        res = fp.proxy.resource(origin='ostia', fields='sst', ** fpcommon)
        self.assertEqual(res.olive_basename(), 'sstostia')
        self.assertEqual(res.archive_basename(), 'sst.ostia')
        self.assertEqual(self.vb.pack(res.basename_info()), 'sst.ostia')
        res = fp.proxy.resource(origin='nesdis', fields='sst', ** fpcommon)
        self.assertEqual(res.olive_basename(), 'sstnesdis')
        self.assertEqual(res.archive_basename(), 'sst.nesdis.bdap')
        self.assertEqual(self.vb.pack(res.basename_info()), 'sst.nesdis')
        res = fp.proxy.resource(origin='bdm', fields='seaice', ** fpcommon)
        self.assertEqual(res.olive_basename(), 'seaicebdm')
        self.assertEqual(res.archive_basename(), 'ice_concent')
        self.assertEqual(self.vb.pack(res.basename_info()), 'seaice.bdm')


class TestFieldsGeoFields(unittest.TestCase):

    def setUp(self):
        self.vb = VortexNameBuilder()
        self.geo = geometries.SpectralGeometry(tag='fgeo', kind='spectral',
                                               area='france', truncation=798,
                                               stretching=2.4, lam=False)
        self.geoL = geometries.SpectralGeometry(tag='fgeol', kind='spectral',
                                                area='france', resolution=2.5,
                                                runit='km', lam=True)

    def test_geofields_names(self):
        # Global
        fpcommon = dict(date=Date(1970, 1, 1, 1, 0, 0), cutoff='assim',
                        model='arpege', kind='geofields',
                        geometry=self.geo)
        res = fp.proxy.resource(fields='sst', ** fpcommon)
        self.assertEqual(res.olive_basename(), 'icmshanalsst')
        self.assertEqual(res.archive_basename(), 'icmshanalsst')
        self.assertEqual(self.vb.pack(res.basename_info()),
                         'sst.arpege.tl798-c24.fa')
        res = fp.proxy.resource(fields='seaice', ** fpcommon)
        self.assertEqual(res.olive_basename(), 'ICMSHANALSEAICE')
        self.assertEqual(res.archive_basename(), 'icmshanalseaice')
        self.assertEqual(self.vb.pack(res.basename_info()),
                         'seaice.arpege.tl798-c24.fa')
        # LAM case
        fpcommon['geometry'] = self.geoL
        res = fp.proxy.resource(fields='seaice', ** fpcommon)
        self.assertEqual(self.vb.pack(res.basename_info()),
                         'seaice.arpege.france-02km50.fa')


if __name__ == "__main__":
    unittest.main(verbosity=2)
