
from __future__ import print_function, absolute_import, unicode_literals, division

import unittest

from bronx.stdtypes.date import Date
import footprints as fp

from vortex.data import geometries
from vortex.tools import env
from vortex.util.names import VortexNameBuilder
import common.data.boundaries  # @UnusedImport

rcollect = fp.collectors.get(tag='resource')
rcollect.fasttrack = ('kind', )


class TestLAMBoundary(unittest.TestCase):

    def setUp(self):
        self.vb = VortexNameBuilder()
        self.geo = geometries.ProjectedGeometry(tag='fgeol', area='FRANGP',
                                                resolution=16, runit='km',
                                                lam=True, new=True)
        self.fpcommon = dict(date=Date(1970, 1, 1, 3, 0, 0), cutoff='assim',
                             kind='boundary', geometry=self.geo, term=1,
                             model='arome')

    def test_lam_boundary(self):
        res = fp.proxy.resource(source='arpege', ** self.fpcommon)
        self.assertEqual(res.olive_basename(), 'ELSCFALAD_FRANGP+0004')
        self.assertEqual(res.archive_basename(), 'COUPL0001.r03')
        self.assertEqual(self.vb.pack(res.basename_info()),
                         'cpl.arpege.frangp-16km00+0001:00.fa')

        e = env.current()
        locenv = e.clone()
        locenv.active(True)
        locenv.HHDELTA_CPL = '2'
        self.assertEqual(res.olive_basename(), 'ELSCFALAD_FRANGP+0003')
        locenv.active(False)

        res = fp.proxy.resource(source='ifs', ** self.fpcommon)
        self.assertEqual(res.archive_basename(), 'COUPLIFS0001.r03')

    def test_enhanced_lam_boundary(self):
        res = fp.proxy.resource(source_app='arpege', source_conf='courtfr',
                                ** self.fpcommon)
        self.assertEqual(res.olive_basename(), 'ELSCFALAD_FRANGP+0004')
        self.assertEqual(res.archive_basename(), 'COUPL0001.r03')
        self.assertEqual(self.vb.pack(res.basename_info()),
                         'cpl.arpege-courtfr-prod.frangp-16km00+0001:00.fa')

        res = fp.proxy.resource(source_app='ifs', source_conf='eps',
                                source_cutoff='assim', ** self.fpcommon)
        self.assertEqual(res.archive_basename(), 'COUPLIFS0001.r03')
        self.assertEqual(self.vb.pack(res.basename_info()),
                         'cpl.ifs-eps-assim.frangp-16km00+0001:00.fa')


if __name__ == "__main__":
    unittest.main(verbosity=2)
