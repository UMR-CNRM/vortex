from __future__ import print_function, absolute_import, unicode_literals, division

import unittest

from vortex.util.names import VortexNameBuilder, VortexNameBuilderError


class FakeTime(object):

    @property
    def fmthm(self):
        return '0006:00'


class FakeNegTime(object):

    @property
    def fmthm(self):
        return '-0006:00'


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
        self.assertEqual(vb.pack(dict(src=['arpege', 'clim',
                                           {'cutoff': 'production'}])),
                         'dummy.arpege-clim-prod')
        self.assertEqual(vb.pack(dict(src=['arpege', 'clim',
                                           {'cutoff': 'assim'}])),
                         'dummy.arpege-clim-assim')
        self.assertEqual(vb.pack(dict(filtername='toto')),
                         'dummy.toto')
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
        # term option
        self.assertEqual(vb.pack(dict(term=6)),
                         'dummy+6')
        self.assertEqual(vb.pack(dict(term=-6)),
                         'dummy+6ago')
        self.assertEqual(vb.pack(dict(term=dict(time=6))),
                         'dummy+6')
        self.assertEqual(vb.pack(dict(term=dict(time=FakeTime()))),
                         'dummy+0006:00')
        self.assertEqual(vb.pack(dict(term=dict(time=FakeNegTime()))),
                         'dummy+0006:00ago')
        # period option
        self.assertEqual(vb.pack(dict(term=6, period=12)),
                         'dummy+6')
        self.assertEqual(vb.pack(dict(period=dict(begintime=FakeTime(),
                                                  endtime=FakeTime()))),
                         'dummy+0006:00-0006:00')
        self.assertEqual(vb.pack(dict(period=dict(begintime=FakeNegTime(),
                                                  endtime=FakeNegTime()))),
                         'dummy+0006:00ago-0006:00ago')
        # suffix option: already tested in testDefaults:
        # other options
        self.assertEqual(vb.pack(dict(fmt='fa')),
                         'dummy.fa')
        # number option
        self.assertEqual(vb.pack(dict(number=6)),
                         'dummy.6')


if __name__ == "__main__":
    unittest.main(verbosity=2)
