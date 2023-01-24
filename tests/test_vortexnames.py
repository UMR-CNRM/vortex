import unittest

from vortex.tools.names import VortexNameBuilder, VortexNameBuilderError
from vortex.tools.names import VortexDateNameBuilder, VortexPeriodNameBuilder, VortexFlatNameBuilder


class FakeTime:

    @property
    def fmthm(self):
        return '0006:00'


class FakeNegTime:

    @property
    def fmthm(self):
        return '-0006:00'


class FakeDate:

    @property
    def stdvortex(self):
        return '20180101T0000'


class FakeDate2:

    @property
    def stdvortex(self):
        return '20180101T1800'


class TestDateNameBuilder(unittest.TestCase):

    def testDateDefaults(self):
        vb = VortexDateNameBuilder(name='date@std')
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
        vb = VortexDateNameBuilder(name='date@std', suffix='test')
        self.assertEqual(vb.pack(dict()), 'vortexdata.test')
        self.assertEqual(vb.pack(dict(style='obs', nativefmt='toto')),
                         'toto-std.void.all.test')
        # Overriding the defaults...
        self.assertEqual(vb.pack(dict(suffix='over')), 'vortexdata.over')

    def testDateStyleObsBasename(self):
        vb = VortexDateNameBuilder(name='date@std')
        self.assertEqual(vb.pack(dict(style='obs', nativefmt='obsoul',
                                      stage='split', part='conv')),
                         'obsoul-std.split.conv')
        self.assertEqual(vb.pack(dict(style='obs', nativefmt='odb',
                                      layout='ecma', stage='split',
                                      part='conv')),
                         'odb-ecma.split.conv')

    def testDateStyleObsmapBasename(self):
        vb = VortexDateNameBuilder(name='date@std')
        self.assertEqual(vb.pack(dict(style='obsmap', radical='obsmap',
                                      stage='split', fmt='xml')),
                         'obsmap.split.xml')

    def testDateStyleStdBasename(self):
        vb = VortexDateNameBuilder(name='date@std', radical='dummy')
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
        self.assertEqual(vb.pack(dict(geo=[{'stretching': 2.2},
                                           {'truncation': (789, 'l', '')},
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

    def testDateStyleStdPathname(self):
        vb = VortexDateNameBuilder(name='date@std', radical='dummy')
        # No missing stuff !
        with self.assertRaises(VortexNameBuilderError):
            vb.pack_pathname(dict(src='arpege', fmt='.txt',
                                  vconf='4dvarfr',
                                  experiment='ABCD',
                                  flow=[{'date': '2018010100'}, ],
                                  block='forecast'))
        with self.assertRaises(VortexNameBuilderError):
            vb.pack_pathname(dict(src='arpege', fmt='.txt',
                                  vapp='arpege',
                                  experiment='ABCD',
                                  flow=[{'date': '2018010100'}, ],
                                  block='forecast'))
        with self.assertRaises(VortexNameBuilderError):
            vb.pack_pathname(dict(src='arpege', fmt='.txt',
                                  vapp='arpege', vconf='4dvarfr',
                                  flow=[{'date': '2018010100'}, ],
                                  block='forecast'))
        with self.assertRaises(VortexNameBuilderError):
            vb.pack_pathname(dict(src='arpege', fmt='.txt',
                                  vapp='arpege', vconf='4dvarfr',
                                  experiment='ABCD',
                                  block='forecast'))
        with self.assertRaises(VortexNameBuilderError):
            vb.pack_pathname(dict(src='arpege', fmt='.txt',
                                  vapp='arpege', vconf='4dvarfr',
                                  experiment='ABCD',
                                  flow=[{'date': '2018010100'}, ]))
        # Ok, let's role !
        vb = VortexDateNameBuilder(name='date@std', radical='dummy', src='arpege', fmt='txt')
        self.assertEqual(vb.pack_pathname(dict(vapp='arpege', vconf='4dvarfr',
                                               experiment='ABCD',
                                               flow=[{'date': '2018010100'}, ],
                                               block='forecast')),
                         'arpege/4dvarfr/ABCD/2018010100X/forecast')
        self.assertEqual(vb.pack_pathname(dict(vapp='arpege', vconf='4dvarfr',
                                               experiment='ABCD',
                                               flow=[{'date': '2018010100'}, {'shortcutoff': 'assim'}],
                                               block='forecast')),
                         'arpege/4dvarfr/ABCD/2018010100A/forecast')
        self.assertEqual(vb.pack_pathname(dict(vapp='arpege', vconf='4dvarfr',
                                               experiment='ABCD',
                                               flow=[{'date': FakeDate()}, {'shortcutoff': 'assim'}],
                                               block='forecast')),
                         'arpege/4dvarfr/ABCD/20180101T0000A/forecast')
        self.assertEqual(vb.pack_pathname(dict(vapp='arpege', vconf='4dvarfr',
                                               experiment='ABCD',
                                               flow=[{'date': FakeDate()}, {'shortcutoff': 'assim'}],
                                               block='forecast', member=1)),
                         'arpege/4dvarfr/ABCD/20180101T0000A/mb001/forecast')
        self.assertEqual(vb.pack_pathname(dict(vapp='arpege', vconf='4dvarfr',
                                               experiment='ABCD',
                                               flow=[{'date': FakeDate()}, {'shortcutoff': 'assim'}],
                                               block='forecast', member=99999)),
                         'arpege/4dvarfr/ABCD/20180101T0000A/mb99999/forecast')
        self.assertEqual(vb.pack_pathname(dict(vapp='arpege', vconf='4dvarfr',
                                               experiment='ABCD', scenario='RCP2.6',
                                               flow=[{'date': FakeDate()}, {'shortcutoff': 'assim'}],
                                               block='forecast', member=99999)),
                         'arpege/4dvarfr/ABCD/20180101T0000A/sRCP2.6/mb99999/forecast')
        self.assertEqual(vb.pack_pathname(dict(vapp='arpege', vconf='4dvarfr',
                                               experiment='ABCD', scenario='RCP2.6',
                                               flow=[{'date': FakeDate()}, {'shortcutoff': 'assim'}],
                                               block='forecast')),
                         'arpege/4dvarfr/ABCD/20180101T0000A/sRCP2.6/forecast')


class TestProxyNameBuilder(unittest.TestCase):

    def testDefaults(self):
        vb = VortexNameBuilder()
        # No defaults provided
        self.assertEqual(vb.pack(dict(vapp='arpege', vconf='4dvarfr', experiment='ABCD',
                                      flow=[{'date': FakeDate()}, {'shortcutoff': 'assim'}],
                                      block='forecast')),
                         'vortexdata')
        self.assertEqual(vb.pack(dict(vapp='arpege', vconf='4dvarfr', experiment='ABCD',
                                      block='forecast')),
                         'vortexdata')
        # Update the defaults
        vb.setdefault(radical='dummy', useless='why?')
        self.assertIn('useless', vb.defaults)
        self.assertEqual(vb.pack(dict(vapp='arpege', vconf='4dvarfr', experiment='ABCD',
                                      flow=[{'date': FakeDate()}, {'shortcutoff': 'assim'}],
                                      block='forecast')),
                         'dummy')
        self.assertEqual(vb.pack(dict(vapp='arpege', vconf='4dvarfr', experiment='ABCD',
                                      block='forecast')),
                         'dummy')
        # Defaults at object creation
        vb2 = VortexNameBuilder(suffix='test')
        self.assertEqual(vb2.pack(dict(vapp='arpege', vconf='4dvarfr', experiment='ABCD',
                                       block='forecast')),
                         'vortexdata.test')
        self.assertEqual(vb2.pack(dict(vapp='arpege', vconf='4dvarfr', experiment='ABCD',
                                       block='forecast', suffix='over')),
                         'vortexdata.over')
        # Overriding the defaults...
        self.assertEqual(vb2.pack(dict(vapp='arpege', vconf='4dvarfr', experiment='ABCD',
                                       block='forecast', suffix='over')),
                         'vortexdata.over')
        # vb, remains...
        self.assertEqual(vb.pack(dict(vapp='arpege', vconf='4dvarfr', experiment='ABCD',
                                      block='forecast')),
                         'dummy')

    def testPeriodStuff(self):
        vb = VortexPeriodNameBuilder(name='period@std')
        self.assertEqual(vb.pack_pathname(dict(vapp='arpege', vconf='4dvarfr', experiment='ABCD',
                                               flow=[{'begindate': FakeDate()}, {'enddate': FakeDate2()}, ],
                                               block='forecast')),
                         'arpege/4dvarfr/ABCD/20180101T0000-20180101T1800/forecast')
        with self.assertRaises(VortexNameBuilderError):
            vb.pack_pathname(dict(vapp='arpege', vconf='4dvarfr', experiment='ABCD',
                                  flow=[{'begindate': FakeDate()}, ],
                                  block='forecast')),
        self.assertEqual(vb.pack_pathname(dict(vapp='arpege', vconf='4dvarfr', experiment='ABCD',
                                               flow=[{'begindate': FakeDate()}, {'enddate': FakeDate2()},
                                                     {'shortcutoff': 'assim'}],
                                               block='forecast')),
                         'arpege/4dvarfr/ABCD/20180101T0000A-20180101T1800/forecast')
        # Basename stuff w/o proxy
        self.assertEqual(vb.pack_basename(dict(src='arpege',
                                               vapp='arpege', vconf='4dvarfr', experiment='ABCD',
                                               flow=[{'begindate': FakeDate()}, {'enddate': FakeDate2()},
                                                     {'shortcutoff': 'assim'}, {'date': FakeDate()}],
                                               period=[{'begintime': FakeTime()}, {'endtime': 100}, ],
                                               block='forecast')),
                         'vortexdata.arpege.20180101T0000A+0006:00-100')
        # Basename stuff with proxy
        vb2 = VortexNameBuilder(vapp='arpege', vconf='4dvarfr', experiment='ABCD',
                                flow=[{'begindate': FakeDate()}, {'enddate': FakeDate2()}, ],
                                block='forecast')
        self.assertEqual(vb2.pack_basename(dict(src='arpege')), 'vortexdata.arpege')
        self.assertEqual(vb2.pack_basename(dict(src='arpege', term='01')),
                         'vortexdata.arpege+01')
        self.assertEqual(vb2.pack_basename(dict(src='arpege', term='01',
                                                period=[{'begintime': FakeTime()}, {'endtime': 100}, ],)),
                         'vortexdata.arpege+01')
        self.assertEqual(vb2.pack_basename(dict(src='arpege',
                                                period=[{'begintime': FakeTime()}, {'endtime': 100}, ],)),
                         'vortexdata.arpege+0006:00-100')

    def testFlatStuff(self):
        vb = VortexFlatNameBuilder(name='flat@std')
        self.assertEqual(vb.pack_pathname(dict(vapp='arpege', vconf='4dvarfr', experiment='ABCD',
                                               block='forecast')),
                         'arpege/4dvarfr/ABCD/forecast')
        self.assertEqual(vb.pack_pathname(dict(vapp='arpege', vconf='4dvarfr', experiment='ABCD',
                                               flow=[{'begindate': FakeDate()}, ],
                                               block='forecast')),
                         'arpege/4dvarfr/ABCD/forecast')
        # Basename stuff w/o proxy
        self.assertEqual(vb.pack_basename(dict(src='arpege',
                                               vapp='arpege', vconf='4dvarfr', experiment='ABCD',
                                               flow=[{'begindate': FakeDate()}, {'enddate': FakeDate2()},
                                                     {'shortcutoff': 'assim'}, {'date': FakeDate()}],
                                               period=[{'begintime': FakeTime()}, {'endtime': 100}, ],
                                               block='forecast')),
                         'vortexdata.arpege.20180101T0000A.20180101T0000A-20180101T1800+0006:00-100')
        # Basename stuff with proxy
        vb2 = VortexNameBuilder(vapp='arpege', vconf='4dvarfr', experiment='ABCD',
                                block='forecast')
        self.assertEqual(vb2.pack_basename(dict(src='arpege')), 'vortexdata.arpege')
        self.assertEqual(vb2.pack_basename(dict(src='arpege', term='01')),
                         'vortexdata.arpege+01')
        self.assertEqual(vb2.pack_basename(dict(src='arpege', term='01',
                                                period=[{'begintime': FakeTime()}, {'endtime': 100}, ],)),
                         'vortexdata.arpege+01')
        self.assertEqual(vb2.pack_basename(dict(src='arpege',
                                                period=[{'begintime': FakeTime()}, {'endtime': 100}, ],)),
                         'vortexdata.arpege+0006:00-100')

    def testDateProxyStuff(self):
        # Basename stuff with proxy
        vb2 = VortexNameBuilder(vapp='arpege', vconf='4dvarfr', experiment='ABCD',
                                flow=[{'shortcutoff': 'assim'}, {'date': FakeDate()}],
                                block='forecast')
        self.assertEqual(vb2.pack_basename(dict(src='arpege')), 'vortexdata.arpege')
        self.assertEqual(vb2.pack_basename(dict(src='arpege', term='01')),
                         'vortexdata.arpege+01')
        self.assertEqual(vb2.pack_basename(dict(src='arpege', term='01',
                                                period=[{'begintime': FakeTime()}, {'endtime': 100}, ],)),
                         'vortexdata.arpege+01')
        self.assertEqual(vb2.pack_basename(dict(src='arpege',
                                                period=[{'begintime': FakeTime()}, {'endtime': 100}, ],)),
                         'vortexdata.arpege+0006:00-100')
        self.assertEqual(vb2.pack_basename(dict(src='arpege',
                                                flow=[{'shortcutoff': 'assim'}, {'date': FakeDate()},
                                                      {'begindate': FakeDate()}, {'enddate': FakeDate2()}],
                                                period=[{'begintime': FakeTime()}, {'endtime': 100}, ],)),
                         'vortexdata.arpege.20180101T0000A-20180101T1800+0006:00-100')


if __name__ == "__main__":
    unittest.main(verbosity=2)
