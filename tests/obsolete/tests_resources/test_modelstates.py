#!/usr/bin/env python
# -*- coding: utf-8 -*-

import logging
logging.basicConfig(level=logging.ERROR)

import sys

from unittest import TestCase, main

from vortex import toolbox
from vortex.data.geometries import SpectralGeometry, GridGeometry
import common.data
import olive.data
u_fill_fp_catalogs = olive.data, common.data


class UtGridPoint(TestCase):

    def setUp(self):
        self.attrset = dict(
            kind      = 'gridpoint',
            date      = '2014101606',
            cutoff    = 'production',
            namespace = '[suite].archive.fr'
        )
        self.franx01 = GridGeometry(
            id         = 'Current op',
            area       = 'FRANX01',
            resolution = 0.1,
            nlat       = 221,
            nlon       = 281
        )
        self.frangp0025 = GridGeometry(
            id         = 'Current op',
            area       = 'FRANGP0025',
            resolution = 0.025,
            nlat       = 601,
            nlon       = 801
        )
        self.glob15 = GridGeometry(
            id         = 'Current op',
            area       = 'GLOB15',
            resolution = 1.5
        )

    def test_v1(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='vortex.cache.fr',
            geometry=self.franx01,
            local='GRIDALADIN+[term:fmthour]',
            nativefmt='grib,fa',
            origin='historic',
            experiment='oper',
            block='forecast',
            cutoff='assim',
            term=6,
            model='aladin'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'vortex://vortex.cache.fr/play/sandbox/oper/20141016T0600A/forecast/grid.aladin-forecast.franx01+0006:00.grib'
        )
        self.assertEqual(
            rl[1].location(),
            'vortex://vortex.cache.fr/play/sandbox/oper/20141016T0600A/forecast/grid.aladin-forecast.franx01+0006:00.fa'
        )

    def test_g1(self):
        rl = toolbox.rload(
            self.attrset,
            geometry=self.franx01,
            local='GRIDALADIN+[term:fmthour]',
            nativefmt='grib',
            origin='historic',
            igakey='france',
            suite='oper',
            cutoff='assim,production',
            term=6,
            model='aladin'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'op://oper.archive.fr/france/oper/assim/2014/10/16/r6/GRIDFRANX01r6_0006'
        )
        self.assertEqual(
            rl[1].location(),
            'op://oper.archive.fr/france/oper/production/2014/10/16/r6/GRIDFRANX01r6_0006'
        )

    def test_g2(self):
        rl = toolbox.rload(
            self.attrset,
            geometry=self.frangp0025,
            local='GRIDAROME+[term:fmthour]',
            nativefmt='grib',
            origin='historic',
            igakey='arome',
            suite='oper',
            cutoff='production',
            term=6,
            model='arome'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'op://oper.archive.fr/arome/oper/production/2014/10/16/r6/GRIDFRANGP0025r6_0006'
        )

    def test_g3(self):
        rl = toolbox.rload(
            self.attrset,
            geometry=self.glob15,
            local='GRIDARPEGE+[term:fmthour]+[suite]',
            nativefmt='grib',
            origin='historic',
            igakey='arpege',
            suite='oper',
            cutoff='assim,production',
            term=6,
            model='arpege'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'op://oper.archive.fr/arpege/oper/assim/2014/10/16/r6/PE06006GLOB15'
        )
        self.assertEqual(
            rl[1].location(),
            'op://oper.archive.fr/arpege/oper/production/2014/10/16/r6/PESX006GLOB15'
        )

    def test_g4(self):
        rl = toolbox.rload(
            self.attrset,
            geometry=self.glob15,
            local='GRIDPEARP+[term:fmthour]',
            nativefmt='grib',
            origin='historic',
            igakey='pearp',
            suite='oper',
            cutoff='production',
            term=6,
            model='arpege',
            member='4'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'op://oper.archive.fr/pearp/oper/16/r6/fc_SX_4_GLOB15_0006')

    def test_g5(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='olive.archive.fr',
            geometry=self.glob15,
            local='GRIDOLIVE+[term:fmthour]',
            nativefmt='grib,fa',
            origin='historic',
            block='fc_00[member]',
            experiment='99A0',
            cutoff='production',
            term=6,
            model='arpege',
            member='4'
        )
 
        for rh in rl:
            self.assertTrue(rh.complete)

        self.assertEqual(rl[0].location(), 'olive://olive.archive.fr/99A0/20141016H06P/fc_004/GRIDHSTGLOB15+0006')
        self.assertEqual(rl[1].location(), 'olive://olive.archive.fr/99A0/20141016H06P/fc_004/PFFPOSHSTGLOB15+0006')

    def test_g6(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='olive.archive.fr',
            geometry=self.glob15,
            local='FA_MOCAGEHM_OLIVE+[term:fmthour]',
            nativefmt='fa',
            origin='historic',
            block='forecast',
            experiment='99A0',
            cutoff='production',
            term=6,
            model='mocage',
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'olive://olive.archive.fr/99A0/20141016H06P/forecast/HMGLOB15+0006')

    def test_g7(self):
        rl = toolbox.rload(
            self.attrset,
            igakey='mocage',
            geometry=self.glob15,
            local='FA_MOCAGEHM_CHAINE+[term:fmthour]',
            nativefmt='fa',
            origin='historic',
            suite='oper',
            cutoff='production',
            term=28,
            model='mocage',
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'op://oper.archive.fr/mocage/16/HMGLOB15+2014101710')

    def test_v7(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='vortex.cache.fr',
            geometry=self.glob15,
            local='FA_MOCAGEHM_CHAINE+[term:fmthour]',
            nativefmt='fa',
            origin='historic',
            experiment='oper',
            block='forecast',
            cutoff='production',
            term=6,
            model='mocage',
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'vortex://vortex.cache.fr/play/sandbox/oper/20141016T0600P/forecast/grid.mocage-forecast.glob15+0006:00.fa'
        )

    def test_g8(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='olive.archive.fr',
            geometry=self.glob15,
            local='FA_MOCAGESM_OLIVE+[term:fmthour]',
            nativefmt='fa',
            origin='sumo,interp',
            block='cplsurf',
            experiment='99A0',
            cutoff='production',
            term=28,
            model='mocage',
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'olive://olive.archive.fr/99A0/20141016H06P/cplsurf/SMGLOB15_void+20141017'
        )
        self.assertEqual(
            rl[1].location(),
            'olive://olive.archive.fr/99A0/20141016H06P/cplsurf/SMGLOB15_interp+20141017'
        )

    def test_g9(self):
        rl = toolbox.rload(
            self.attrset,
            igakey='mocage',
            geometry=self.glob15,
            local='FA_MOCAGESM_CHAINE+[term:fmthour]',
            nativefmt='fa',
            origin='interp',
            suite='oper',
            cutoff='production',
            term=28,
            model='mocage',
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(rl[0].location(), 'op://oper.archive.fr/mocage/16/SMGLOB15+20141017')

    def test_v9(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='vortex.cache.fr',
            geometry=self.glob15,
            local='FA_MOCAGESM_CHAINE+[term:fmthour]',
            nativefmt='fa',
            origin='sumo,interp',
            experiment='oper',
            block='coupling',
            cutoff='production',
            term=24,
            model='mocage',
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'vortex://vortex.cache.fr/play/sandbox/oper/20141016T0600P/coupling/grid.mocage-sumo.glob15+0024:00.fa'
        )
        self.assertEqual(
            rl[1].location(),
            'vortex://vortex.cache.fr/play/sandbox/oper/20141016T0600P/coupling/grid.mocage-sumo.glob15+0024:00.fa'
        )


class UtHistoric(TestCase):

    def setUp(self):
        self.attrset = dict(kind='historic', date='2014101600',
                            cutoff='production', namespace='[suite].archive.fr')
        self.std = SpectralGeometry(id='Current op', area='france',
                                    truncation=798, stretching=2.4, lam=False)
        self.caledonie = SpectralGeometry(id='Current op', area='caledonie', resolution=8.0)
        self.arome = SpectralGeometry(id='Current op', area='frangp')
        self.mnh = SpectralGeometry(id='Current op', area='france', resolution=1.5)

    def test_v1(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='vortex.cache.fr',
            geometry=self.std,
            local='ICMSHARPE+[term:fmthour]',
            experiment='oper',
            block='forecast',
            cutoff='assim',
            term=6,
            model='arpege'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'vortex://vortex.cache.fr/play/sandbox/oper/20141016T0000A/forecast/historic.arpege.tl798-c24+0006:00.fa'
        )

    def test_v2(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='vortex.cache.fr',
            geometry=self.caledonie,
            local='ICMSHARPE+[term:fmthour]',
            experiment='oper',
            block='forecast',
            cutoff='assim',
            term=6,
            model='aladin'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'vortex://vortex.cache.fr/play/sandbox/oper/20141016T0000A/forecast/historic.aladin.caledonie-08km00+0006:00.fa'
        )

    def test_v3(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='vortex.cache.fr',
            geometry=self.mnh,
            local='MESONH+[term:fmthour]',
            experiment='A000',
            block='forecast',
            cutoff='assim',
            term=6,
            model='mesonh',
            nativefmt='lfi'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'vortex://vortex.cache.fr/play/sandbox/A000/20141016T0000A/forecast/historic.mesonh.france-01km50+0006:00.lfi'
        )

    def test_h1(self):
        rl = toolbox.rload(
            self.attrset,
            geometry=self.std,
            local='ICMSHARPE+[term:fmthour]',
            igakey='arpege',
            suite='oper',
            cutoff='assim,production',
            term=(0,6),
            model='arpege'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'op://oper.archive.fr/arpege/oper/assim/2014/10/16/r0/icmsharpe+0000'
        )
        self.assertEqual(
            rl[1].location(),
            'op://oper.archive.fr/arpege/oper/assim/2014/10/16/r0/icmsharpe+0006'
        )
        self.assertEqual(
            rl[2].location(),
            'op://oper.archive.fr/arpege/oper/production/2014/10/16/r0/icmsharpe+0000'
        )
        self.assertEqual(
            rl[3].location(),
            'op://oper.archive.fr/arpege/oper/production/2014/10/16/r0/icmsharpe+0006'
        )

    def test_h2(self):
        rl = toolbox.rload(
           self.attrset,
           geometry=self.caledonie,
           local='ICMSHALAD+[term:fmthour]',
           igakey='caledonie',
           suite='oper',
           cutoff='assim',
           term=6,
           model='aladin'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'op://oper.archive.fr/caledonie/oper/assim/2014/10/16/r0/ICMSHALAD+0006'
        )

    def test_h3(self):
        rl = toolbox.rload(
            self.attrset,
            geometry=self.std,
            local='ICMSHAEARP[member]+[term:fmthour]',
            igakey='aearp',
            member='4',
            suite='oper',
            cutoff='assim',
            term=6,
            model='arpege'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'op://oper.archive.fr/aearp/oper/assim/2014/10/16/r0/RUN4/icmsharpe+0006'
        )

    def test_h4(self):
        rl = toolbox.rload(
            self.attrset,
            geometry=self.std,
            local='ICMSHPEARP[member]+[term:fmthour]',
            igakey='pearp',
            member='4',
            suite='oper',
            cutoff='production',
            term=6,
            model='arpege'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'op://oper.archive.fr/pearp/oper/production/2014/10/16/r0/RUN4/icmshprev+0006'
        )

    def test_h5(self):
        rl = toolbox.rload(
            self.attrset,
            geometry=self.arome,
            local='ICMSHAROM+[term:fmthour]',
            igakey='arome',
            suite='oper',
            term=6,
            model='arome'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'op://oper.archive.fr/arome/oper/production/2014/10/16/r0/ICMSHAROM+0006'
        )

    def test_h6(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='olive.archive.fr',
            geometry=self.std,
            local='ICMSHOLIVE+[term:fmthour]',
            block='forecast',
            term=6,
            model='arpege',
            experiment='99A0'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'olive://olive.archive.fr/99A0/20141016H00P/forecast/ICMSHARPE+0006'
        )

    def test_h7(self):
        #sessions.current().debug()
        rl = toolbox.rload(
            self.attrset,
            namespace='olive.archive.fr',
            geometry=self.std,
            local='MESONHOLIVE+[term:fmthour]',
            block='forecast',
            term=6,
            model='mesonh',
            experiment='99A0',
            nativefmt='lfi'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'olive://olive.archive.fr/99A0/20141016H00P/forecast/MESONH.FRAN+0006.lfi'
        )


class UtAnalysis(TestCase):

    def setUp(self):
        self.attrset = dict(kind='analysis', date = '20141016',
                            cutoff='production', namespace='[suite].archive.fr')
        self.std = SpectralGeometry(id='Current op', area='france',
                                    truncation=798, stretching=2.4, lam=False)
        self.caledonie = SpectralGeometry(id='Current op', area='caledonie', resolution=8.0)
        self.arome = SpectralGeometry(id='Current op', area='frangp', resolution=2.5)

    def test_v1(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='vortex.cache.fr',
            geometry=self.arome,
            local='ANALYSE_AROME_[filling]',
            experiment='oper',
            block='analysis',
            filling='full,surf',
            model='arome'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'vortex://vortex.cache.fr/play/sandbox/oper/20141016T0000P/analysis' +
            '/analysis.full-arome.frangp-02km50.fa'
        )
        self.assertEqual(
            rl[1].location(),
            'vortex://vortex.cache.fr/play/sandbox/oper/' +
            '20141016T0000P/analysis/analysis.surf-arome.frangp-02km50.fa'
        )

    def test_v2(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='vortex.cache.fr',
            geometry=self.std,
            local='ANALYSE_ARPEGE_[filling]',
            experiment='oper',
            block='analysis',
            filling='full,surf',
            model='arpege'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'vortex://vortex.cache.fr/play/sandbox/oper/20141016T0000P/' +
            'analysis/analysis.full-arpege.tl798-c24.fa'
        )
        self.assertEqual(
            rl[1].location(),
            'vortex://vortex.cache.fr/play/sandbox/oper/20141016T0000P/' +
            'analysis/analysis.surf-arpege.tl798-c24.fa'
        )

    def test_a1(self):
        rl = toolbox.rload(
            self.attrset,
            geometry=self.arome,
            local='ANALYSE_AROME_[filling]',
            igakey='arome',
            suite='oper',
            filling='full,surf',
            model='arome'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'op://oper.archive.fr/arome/oper/production/2014/10/16/r0/analyse'
        )
        self.assertEqual(
            rl[1].location(),
            'op://oper.archive.fr/arome/oper/production/2014/10/16/r0/analyse_surf'
        )

    def test_a2(self):
        rl = toolbox.rload(
            self.attrset,
            geometry=self.std,
            local='ANALYSE_ARPEGE_[filling]',
            igakey='arpege',
            suite='oper',
            filling='full,surf',
            model='arpege'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'op://oper.archive.fr/arpege/oper/production/2014/10/16/r0/analyse'
        )
        self.assertEqual(
            rl[1].location(),
            'op://oper.archive.fr/arpege/oper/production/2014/10/16/r0/analyse_surface1'
        )

    def test_a3(self):
        rh = toolbox.rload(
            self.attrset,
            geometry=self.caledonie,
            local='ANALYSE_CALEDONIE_full',
            model='aladin',
            igakey='[geometry::area]',
            suite='oper',
        ).pop()
        self.assertTrue(rh.complete)
        self.assertEqual(
            rh.location(),
            'op://oper.archive.fr/caledonie/oper/production/2014/10/16/r0/analyse'
        )

    def test_a4(self):
        rh = toolbox.rload(
            self.attrset,
            geometry=self.caledonie,
            local='ANALYSE_CALEDONIE__[filtering]',
            model='aladin',
            filtering='dfi',
            igakey='[geometry::area]',
            suite='oper',
        ).pop()
        self.assertTrue(rh.complete)
        self.assertEqual(
            rh.location(),
            'op://oper.archive.fr/caledonie/oper/production/2014/10/16/r0/ANALYSE_DFI'
        )

    def test_a5(self):
        rh = toolbox.rload(
            self.attrset,
            local='ANALYSE_full_OLIVE',
            namespace='olive.archive.fr',
            geometry=self.std,
            experiment = '99A0',
            block='canari',
            date='2011092200',
            model='arpege'
        ).pop()
        self.assertTrue(rh.complete)
        self.assertEqual(rh.location(), 'olive://olive.archive.fr/99A0/20110922H00P/canari/analyse')

    def test_a6(self):
        rh = toolbox.rload(
            self.attrset,
            local='ANALYSE_[filling]_OLIVE',
            namespace='olive.archive.fr',
            geometry=self.std,
            experiment = '99A0',
            filling='surf',
            block='canari',
            date='2011092200',
            model='aladin'
        ).pop()
        self.assertTrue(rh.complete)
        self.assertEqual(rh.location(), 'olive://olive.archive.fr/99A0/20110922H00P/canari/surfanalyse')


class UtHistsurf(TestCase):

    def setUp(self):
        self.attrset = dict(kind='historic', date='2014101600',
                            cutoff='production', namespace='[suite].archive.fr')
        self.arome = SpectralGeometry(id='Current op', area='frangp', resolution=2.5)

    def test_v1(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='vortex.cache.fr',
            geometry=self.arome,
            local='AROMOUT+[term:fmthour]',
            experiment='oper',
            block='forecast',
            term=6,
            model='surfex',
            nativefmt='lfi'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'vortex://vortex.cache.fr/play/sandbox/oper/20141016T0000P/' +
            'forecast/historic.surfex.frangp-02km50+0006:00.lfi'
        )

    def test_o1(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='olive.archive.fr',
            geometry=self.arome,
            local='AROMOUT+[term:fmthour]',
            experiment='A000',
            block='forecast',
            term=6,
            model='surfex',
            nativefmt='lfi'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'olive://olive.archive.fr/A000/20141016H00P/forecast/AROMOUT_SURF.fran.0006.lfi'
        )

    def test_h1(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='oper.archive.fr',
            geometry=self.arome,
            local='AROMOUT+[term:fmthour]',
            term=6,
            model='surfex',
            nativefmt='fa',
            suite='oper',
            inout='out',
            igakey='arome'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'op://oper.archive.fr/arome/oper/production/2014/10/16/r0/ICMSHSURF+0006'
        )

    def test_h2(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='oper.archive.fr',
            geometry=self.arome,
            local='AROMOUT+[term:fmthour]',
            term=0,
            model='surfex',
            nativefmt='fa',
            suite='oper',
            inout='out',
            igakey='arome'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(),
            'op://oper.archive.fr/arome/oper/production/2014/10/16/r0/ICMSHSURF+0000'
        )

if __name__ == '__main__':
    main(verbosity=2)
    vortex.exit()
