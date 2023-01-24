import unittest

from bronx.stdtypes.date import Date
import footprints as fp

from vortex.data import geometries
from vortex.tools.names import VortexNameBuilder
import common.data.eps  # @UnusedImport

rcollect = fp.collectors.get(tag='resource')
rcollect.fasttrack = ('kind', )


class TestPerturbedState(unittest.TestCase):

    def setUp(self):
        self.vb = VortexNameBuilder()
        self.geo = geometries.GaussGeometry(tag='fgeo', area='france',
                                            truncation=798, stretching=2.4,
                                            new=True)

    def test_names(self):
        fpcommon = dict(date=Date(1970, 1, 1, 1, 0, 0), cutoff='assim',
                        model='arpege', kind='perturbation', geometry=self.geo,
                        number=15, term='6:15')
        answer = 'pert.arpege.tl798-c24+0006:15.015.fa'
        res = fp.proxy.resource(** fpcommon)
        with self.assertRaises(NotImplementedError):
            res.olive_basename()
        with self.assertRaises(NotImplementedError):
            res.archive_basename()
        self.assertEqual(self.vb.pack_basename(res.namebuilding_info()), answer)
        res = fp.proxy.resource(processing='unit', ** fpcommon)
        self.assertEqual(self.vb.pack_basename(res.namebuilding_info()), 'u' + answer)
        res = fp.proxy.resource(processing='normed', ** fpcommon)
        self.assertEqual(self.vb.pack_basename(res.namebuilding_info()), 'n' + answer)


class TestSingularVector(unittest.TestCase):

    def setUp(self):
        self.vb = VortexNameBuilder()
        self.geo = geometries.GaussGeometry(tag='fgeo', area='france',
                                            truncation=798, stretching=2.4,
                                            new=True)

    def test_names(self):
        fpcommon = dict(date=Date(1970, 1, 1, 1, 0, 0), cutoff='assim',
                        model='arpege', kind='svector', geometry=self.geo,
                        number=15, term='6:15', zone='trop1')
        answer = 'svector-trop1.arpege.tl798-c24+0006:15.015.fa'
        res = fp.proxy.resource(** fpcommon)
        self.assertEqual(res.olive_basename(), 'SVARPE015+0000')
        self.assertEqual(res.archive_basename(), 'SVARPE015+0000')
        self.assertEqual(self.vb.pack_basename(res.namebuilding_info()), answer)


class TestNormCoeff(unittest.TestCase):

    def setUp(self):
        self.vb = VortexNameBuilder()

    def test_names(self):
        fpcommon = dict(date=Date(1970, 1, 1, 1, 0, 0), cutoff='assim',
                        model='arpege', kind='coeffnorm')
        answer = 'coeff{}.arpege.json'
        res = fp.proxy.resource(** fpcommon)
        self.assertEqual(self.vb.pack(res.namebuilding_info()), answer.format('sv'))
        for pkind in ('sv', 'bd'):
            res = fp.proxy.resource(pertkind=pkind, ** fpcommon)
            self.assertEqual(self.vb.pack_basename(res.namebuilding_info()), answer.format(pkind))


class TestSample(unittest.TestCase):

    def setUp(self):
        self.vb = VortexNameBuilder()

    def test_names(self):
        fpcommon = dict(date=Date(1970, 1, 1, 1, 0, 0), cutoff='assim',
                        model='arpege', nbsample=5)
        answer = '{}of5.json'
        for skind in ('mbsample', 'physample'):
            res = fp.proxy.resource(kind=skind, ** fpcommon)
            self.assertEqual(self.vb.pack_basename(res.namebuilding_info()), answer.format(skind))


class TestGeneralCluster(unittest.TestCase):

    def setUp(self):
        self.vb = VortexNameBuilder()

    def test_names(self):
        fpcommon = dict(date=Date(1970, 1, 1, 1, 0, 0), cutoff='assim',
                        model='arpege', kind='clustering')
        answer = 'clustering_{}.txt'
        for sfill in ('population', 'pop', 'members'):
            res = fp.proxy.resource(filling=sfill, ** fpcommon)
            self.assertEqual(self.vb.pack_basename(res.namebuilding_info()),
                             answer.format({'population': 'pop'}.get(sfill, sfill)))


if __name__ == "__main__":
    unittest.main(verbosity=2)
