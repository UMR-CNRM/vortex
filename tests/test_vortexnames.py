
import unittest

from vortex.util.names import VortexNameBuilder, VortexNameBuilderError


class TestNameBuilder(unittest.TestCase):

    def testDefaults(self):
        vb = VortexNameBuilder()
        # No defaults provided
        self.assertEqual(vb.pack(dict()), 'vortexdata')
        with self.assertRaises(VortexNameBuilderError):
            vb.pack(dict(style='obs'))
        self.assertEqual(vb.pack(dict(style='obs', nativefmt='toto')),
                         'toto-std.void.all')
        self.assertEqual(vb.pack(dict(style='obsmap')), 'vortexdata.none.txt')
        # Update the defaults
        vb.setdefault(radical='dummy', useless='why?')
        self.assertIn('useless', vb.defaults)
        self.assertEqual(vb.pack(dict()), 'dummy')
        self.assertEqual(vb.pack(dict(style='obsmap')), 'dummy.none.txt')
        # Defaults at object creation
        vb = VortexNameBuilder(suffix='test')
        self.assertEqual(vb.pack(dict()), 'vortexdata.test')
        self.assertEqual(vb.pack(dict(style='obs', nativefmt='toto')),
                         'toto-std.void.all.test')
        # Overriding the defaults...
        self.assertEqual(vb.pack(dict(suffix='over')), 'vortexdata.over')

    def testStyleObs(self):
        vb = VortexNameBuilder()
        self.assertEqual(vb.pack(dict(style='obs', nativefmt='obsoul',
                                      stage='split', part='conv')),
                         'obsoul-std.split.conv')
        self.assertEqual(vb.pack(dict(style='obs', nativefmt='odb',
                                      layout='ecma', stage='split',
                                      part='conv')),
                         'odb-ecma.split.conv')

    def testStyleObsmap(self):
        vb = VortexNameBuilder()
        self.assertEqual(vb.pack(dict(style='obsmap', radical='obsmap',
                                      stage='split', fmt='xml')),
                         'obsmap.split.xml')

    def testStyleStd(self):
        vb = VortexNameBuilder(radical='dummy')
        # src option:
        self.assertEqual(vb.pack(dict(src='arpege')),
                         'dummy.arpege')
        self.assertEqual(vb.pack(dict(src=['arpege', 'minim1'])),
                         'dummy.arpege-minim1')
        self.assertEqual(vb.pack(dict(src=['arpege', 'clim', {'month': 2}])),
                         'dummy.arpege-clim-m2')
        # geo option:
        self.assertEqual(vb.pack(dict(geo=[{'stretching': 2.2},
                                           {'truncation': 789},
                                           {'filtering': 'GLOB15'}])),
                         'dummy.c22-tl789-fglob15')
        # compute: option
        self.assertEqual(vb.pack(dict(compute=[{'seta': 1},
                                               {'setb': 1}])),
                         'dummy.a0001-b0001')
        self.assertEqual(vb.pack(dict(compute=[{'mpi': 12},
                                               {'openmp': 2}])),
                         'dummy.n0012-omp02')
        # suffix option: already tested in testDefaults:
        # other options
        self.assertEqual(vb.pack(dict(term=6)),
                         'dummy+6')
        self.assertEqual(vb.pack(dict(fmt='fa')),
                         'dummy.fa')



if __name__ == "__main__":
    unittest.main(verbosity=2)
