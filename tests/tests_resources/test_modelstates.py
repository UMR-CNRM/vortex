
import unittest

from bronx.stdtypes.date import Date
import footprints as fp

from vortex.data import geometries
import common.data.modelstates  # @UnusedImport

from vortex.util.names import VortexNameBuilder

rcollect = fp.collectors.get(tag='resource')
rcollect.fasttrack = ('kind', )


class TestAnalysis(unittest.TestCase):

    def setUp(self):
        self.vb = VortexNameBuilder()
        self.geo = geometries.GaussGeometry(tag='fgeo', area='france',
                                            truncation=798, stretching=2.4,
                                            new=True)

    def test_names(self):
        fpcommon = dict(date=Date(1970, 1, 1, 1, 0, 0), cutoff='assim',
                        model='arpege', kind='analysis', geometry=self.geo)
        answer = 'analysis.surf-arpege.tl798-c24.fa'
        res = fp.proxy.resource(filling='surf', ** fpcommon)
        self.assertEqual(self.vb.pack(res.basename_info()), answer)


class TestInitialCondition(unittest.TestCase):

    def setUp(self):
        self.vb = VortexNameBuilder()
        self.geo = geometries.GaussGeometry(tag='fgeo', area='france',
                                            truncation=798, stretching=2.4,
                                            new=True)

    def test_names(self):
        fpcommon = dict(date=Date(1970, 1, 1, 1, 0, 0), cutoff='assim',
                        model='arpege', kind='ic', geometry=self.geo)
        answer = 'ic.surf-arpege.tl798-c24.fa'
        res = fp.proxy.resource(filling='surf', ** fpcommon)
        self.assertEqual(res.olive_basename(), 'ICMSHARPE+0000')
        with self.assertRaises(NotImplementedError):
            res.archive_basename()
        self.assertEqual(self.vb.pack(res.basename_info()), answer)


if __name__ == "__main__":
    unittest.main(verbosity=2)
