#!/bin/env python
# -*- coding:Utf-8 -*-

import footprints

try:
    from oper_test_config import *
except ImportError, e:
    print e
    raise

#t.debug()

class UtGridpoint(TestCase):

    def setUp(self):
        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'france',
        )
        self.fp_store = dict(
            netloc = 'oper.inline.fr',
        )
        self.fp_cont = dict(
            local='PFARPE[geometry::area]+[term::fmth].rSX'
        )
        self.franx01 = GridGeometry(id='Current op', area='FRANX01', resolution=0.1, nlat=221, nlon=281)
        self.frangp0025 = GridGeometry(id='Current op', area='FRANGP0025', resolution=0.025, nlat=601, nlon=801)
        self.glob15 = GridGeometry(id='Current op', area='GLOB15', resolution=1.5)

        self.fp_gridpoint1 = dict(
            kind = 'gridpoint',
            geometry = self.glob15,
            nativefmt='fa',
            origin = 'historic',
            model = 'arpege',
            cutoff = 'production',
            date = today() + 'PT6H',
            term = 0
        )
        self.fp_gridpoint2 = dict(
            kind = 'gridpoint',
            geometry = self.glob15,
            nativefmt='fa',
            origin = 'historic',
            model = 'arpege',
            cutoff = 'production',
            date = today() + 'PT6H',
            term = 3
        )

        self.fp_gridpoint3 = dict(
            kind = 'gridpoint',
            geometry = self.franx01,
            nativefmt='fa',
            origin = 'historic',
            model = 'aladin',
            cutoff = 'production',
            date = today() + 'PT6H',
            term = 6
        )

        self.fp_gridpoint4 = dict(
            kind = 'gridpoint',
            geometry = self.frangp0025,
            nativefmt='fa',
            origin = 'historic',
            model = 'arome',
            cutoff = 'production',
            date = today() + 'PT6H',
            term = 6
        )
        
        self.fp_gridpoint5 = dict(
            kind = 'gridpoint',
            geometry = self.glob15,
            nativefmt='grib',
            origin = 'historic',
            model = 'arpege',
            cutoff = 'assim',
            date = today() + 'PT6H',
            term = 0
        )

        self.fp_gridpoint6 = dict(
            kind = 'gridpoint',
            geometry = self.glob15,
            nativefmt='grib',
            origin = 'historic',
            model = 'arpege',
            igakey = 'pearp',
            cutoff = 'assim',
            date = today() + 'PT6H',
            term = 6,
            member = 4
        )

    def test_ctlg1(self):
        gridpoint = self.fp_gridpoint1
        ctlg = footprints.proxy.resources
        res = ctlg.find_best(gridpoint)
        self.assertEqual(res.kind, 'gridpoint')

        gridpoint = self.fp_gridpoint2
        res = ctlg.find_best(gridpoint)
        self.assertEqual(res.kind, 'gridpoint')

        gridpoint = self.fp_gridpoint3
        res = ctlg.find_best(gridpoint)
        self.assertEqual(res.kind, 'gridpoint')
 
        gridpoint = self.fp_gridpoint4
        res = ctlg.find_best(gridpoint)
        self.assertEqual(res.kind, 'gridpoint')

        gridpoint = self.fp_gridpoint5
        res = ctlg.find_best(gridpoint)
        self.assertEqual(res.kind, 'gridpoint')

        gridpoint = self.fp_gridpoint6
        res = ctlg.find_best(gridpoint)
        self.assertEqual(res.kind, 'gridpoint')

    def test_v1(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_cont,
            self.fp_store,
            self.fp_gridpoint1
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(), 
            'file://oper.inline.fr/arpege/france/oper/data/fic_day/PFARPEGLOB15+0000.rSX'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/arpege/france/oper/data/fic_day/PFARPEGLOB15+0000.rSX'
        )
        #uniquement sur machine oper (pas de phasage)
        if t.env['HOSTNAME'] == 'kumo':
            self.assertTrue(os.stat(rl[0].locate()))

    def test_v2(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_cont,
            self.fp_gridpoint2
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(), 
            'file://oper.inline.fr/arpege/france/oper/data/fic_day/PFARPEGLOB15+0003.rSX'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/arpege/france/oper/data/fic_day/PFARPEGLOB15+0003.rSX'
        )
        #uniquement sur machine oper (pas de phasage)
        if t.env['HOSTNAME'] == 'kumo':
            self.assertTrue(os.stat(rl[0].locate()))

    def test_v3(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_cont,
            self.fp_gridpoint3
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(), 
            'file://oper.inline.fr/aladin/france/oper/data/fic_day/PFALADFRANX01+0006.rSX'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/aladin/france/oper/data/fic_day/PFALADFRANX01+0006.rSX'
        )
        #uniquement sur machine oper (pas de phasage)
        if t.env['HOSTNAME'] == 'kumo':
            self.assertTrue(os.stat(rl[0].locate()))

    def test_v4(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_cont,
            self.fp_gridpoint4
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(), 
            'file://oper.inline.fr/arome/france/oper/data/fic_day/PFAROMFRANGP0025+0006.rSX'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/arome/france/oper/data/fic_day/PFAROMFRANGP0025+0006.rSX'
        )
        #uniquement sur machine oper (pas de phasage)
        if t.env['HOSTNAME'] == 'kumo':
            self.assertTrue(os.stat(rl[0].locate()))

    def test_v5(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_cont,
            self.fp_gridpoint5
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(), 
            'file://oper.inline.fr/arpege/france/oper/data/bdap/PE06000GLOB15'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/arpege/france/oper/data/bdap/PE06000GLOB15'
        )
        #uniquement sur machine oper (pas de phasage)
        if t.env['HOSTNAME'] == 'kumo':
            self.assertTrue(os.stat(rl[0].locate()))

    def test_v6(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_cont,
            self.fp_gridpoint6
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(), 
            'file://oper.inline.fr/arpege/pearp/oper/data/bdap/RUN4/fc_SX_4_GLOB15_0006'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/arpege/pearp/oper/data/bdap/RUN4/fc_SX_4_GLOB15_0006'
        )
        #uniquement sur machine oper (pas de phasage)
        if t.env['HOSTNAME'] == 'kumo':
            self.assertTrue(os.stat(rl[0].locate()))

class UtHistoric(TestCase):

    def setUp(self):
        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'france',
        )
        self.fp_prov2 = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'caledonie',
        )
        
        self.fp_cont = dict(
            local='ICMSH[geometry::area]+[term::fmth].rDH'
        )

        self.std = SpectralGeometry(id='Current op', area='france', truncation=798)
        self.caledonie = SpectralGeometry(id='Current op', area='caledonie', resolution=8.0)
        self.frangp = SpectralGeometry(area='frangp')

        self.fp_historic1 = dict(
            kind = 'historic',
            geometry = self.frangp,
            origin = 'historic',
            model = 'arome',
            cutoff = 'production',
            date = today() + 'PT18H',
            term = 0
        )

        self.fp_historic2 = dict(
            kind = 'historic',
            geometry = self.caledonie,
            origin = 'historic',
            model = 'aladin',
            cutoff = 'production',
            date = today() + 'PT12H',
            term = 0
        )
        self.fp_historic3 = dict(
            kind = 'historic',
            geometry = self.frangp,
            origin = 'historic',
            model = 'arpege',
            cutoff = 'production',
            date = today() + 'PT18H',
            term = 0
        )

    def test_ctlg1(self):
        historic = self.fp_historic1
        ctlg = footprints.proxy.resources
        res = ctlg.find_best(historic)
        self.assertEqual(res.kind, 'historic')

        historic = self.fp_historic2
        res = ctlg.find_best(historic)
        self.assertEqual(res.kind, 'historic')

        historic = self.fp_historic3
        res = ctlg.find_best(historic)
        self.assertEqual(res.kind, 'historic')

    def test_v1(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_cont,
            self.fp_historic1
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(), 
            'file://oper.inline.fr/arome/france/oper/data/fic_day/ICMSHAROM+0000.rDH'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/arome/france/oper/data/fic_day/ICMSHAROM+0000.rDH'
        )
        self.assertTrue(os.stat(rl[0].locate()))

    def test_v2(self):
        rl = toolbox.rload(
            self.fp_prov2,
            self.fp_cont,
            self.fp_historic2
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(), 
            'file://oper.inline.fr/aladin/caledonie/oper/data/fic_day/ICMSHALAD+0000.rPM'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/aladin/caledonie/oper/data/fic_day/ICMSHALAD+0000.rPM'
        )
        #uniquement sur machine oper (pas de phasage)
        if t.env['HOSTNAME'] == 'kumo':
            self.assertTrue(os.stat(rl[0].locate()))

    def test_v3(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_cont,
            self.fp_historic3
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(), 
            'file://oper.inline.fr/arpege/france/oper/data/fic_day/ICMSHARPE+0000.rDH'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/arpege/france/oper/data/fic_day/ICMSHARPE+0000.rDH'
        )
        self.assertTrue(os.stat(rl[0].locate()))

              
class UtAnalysis(TestCase):

    def setUp(self):
        self.std = SpectralGeometry(id='Current op', area='france', truncation=798)
        self.caledonie = SpectralGeometry(id='Current op', area='caledonie', resolution=8.0)
        self.frangp = SpectralGeometry(id='Current op', area='frangp', resolution=2.5)

        self.fp_prov1 = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'france',
        )

        self.fp_prov2 = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'caledonie',
        )

        self.fp_analys1 = dict(
            kind = 'analysis',
            cutoff = 'production',
            model = 'arome',
            geometry = self.frangp,
            date = today() + 'PT12H',
        )

        self.fp_analys1_b = dict(
            kind = 'analysis',
            cutoff = 'production',
            model = 'arome',
            geometry = self.frangp,
            nativefmt = 'lfi',
            filling = 'surf',
            date = today() + 'PT12H',
        )

        self.fp_analys2 = dict(
            kind = 'analysis',
            cutoff = 'assim',
            model = 'aladin',
            geometry = self.frangp,
            date = today() + 'PT18H',
        )

        self.fp_analys3 = dict(
            kind = 'analysis',
            cutoff = 'assim',
            model = 'arpege',
            geometry = self.std,
            filling = 'surf',
            date = today() + 'PT6H',
        )

        self.fp_cont1 = dict(
            local='ICMSHFCSTINIT'
        )

    def test_ctlg1(self):
        ctlg = footprints.proxy.resources

        analys = self.fp_analys1
        res = ctlg.find_best(analys)
        self.assertEqual(res.kind, 'analysis')

        analys = self.fp_analys1_b
        res = ctlg.find_best(analys)
        self.assertEqual(res.kind, 'analysis')

        analys = self.fp_analys2
        res = ctlg.find_best(analys)
        self.assertEqual(res.kind, 'analysis')

        analys = self.fp_analys3
        res = ctlg.find_best(analys)
        self.assertEqual(res.kind, 'analysis')

    def test_v1(self):
        rl = toolbox.rload(
            self.fp_prov1,
            self.fp_cont1,
            self.fp_analys1
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(), 
            'file://oper.inline.fr/arome/france/oper/data/workdir/analyse/ICMSHAROMINIT.rPM'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/arome/france/oper/data/workdir/analyse/ICMSHAROMINIT.rPM'
        )
        #uniquement sur Nec oper
        if t.env['HOSTNAME'] == 'kumo':
            self.assertTrue(os.stat(rl[0].locate()))

    def test_v1_b(self):
        rl = toolbox.rload(
            self.fp_prov1,
            self.fp_cont1,
            self.fp_analys1_b
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(), 
            'file://oper.inline.fr/arome/france/oper/data/fic_day/INIT_SURF.lfi.rPM'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/arome/france/oper/data/fic_day/INIT_SURF.lfi.rPM'
        )
        #uniquement sur Nec oper
        if t.env['HOSTNAME'] == 'kumo':
            self.assertTrue(os.stat(rl[0].locate()))


    def test_v2(self):
        rl = toolbox.rload(
            self.fp_prov2,
            self.fp_cont1,
            self.fp_analys2
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(), 
            'file://oper.inline.fr/aladin/caledonie/oper/data/workdir/analyse/ICMSHALADINIT.r18'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/aladin/caledonie/oper/data/workdir/analyse/ICMSHALADINIT.r18'
        )
        #uniquement sur Nec oper
        if t.env['HOSTNAME'] == 'kumo':
            self.assertTrue(os.stat(rl[0].locate()))

    def test_v3(self):
        rl = toolbox.rload(
            self.fp_prov1,
            self.fp_cont1,
            self.fp_analys3
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(), 
            'file://oper.inline.fr/arpege/france/oper/data/workdir/analyse/ICMSHANALINIT_SURF.r06'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/arpege/france/oper/data/workdir/analyse/ICMSHANALINIT_SURF.r06'
        )
        #uniquement sur Nec oper
        if t.env['HOSTNAME'] == 'kumo':
            self.assertTrue(os.stat(rl[0].locate()))

class UtHistsurf(TestCase):

    def setUp(self):
        self.geom = SpectralGeometry(id='Current op', area='frangp', resolution=2.5)
        self.fp_histsurf = dict(
            kind = 'histsurf',
            date = today() + 'PT15H',
            cutoff = 'production',
            geometry = self.geom,
            nativefmt = 'lfi',
            model = 'arome',
            term = '6'
        )

        self.fp_cont = dict(
            file = 'PREP.lfi'
        )

        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'france',
        )

    def test_ctlg1(self):
        histsurf = self.fp_histsurf
        ctlg = footprints.proxy.resources
        res = ctlg.find_best(histsurf)
        self.assertEqual(res.kind, 'histsurf')


    def test_h1(self):
        rl = toolbox.rload(
            self.fp_histsurf,
            self.fp_cont,
            self.fp_prov
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()

        self.assertEqual(
            rl[0].location(), 
            'file://oper.inline.fr/arome/france/oper/data/fic_day/PREP.lfi.rQZ'
        )
        self.assertEqual(
            rl[0].locate(), 
            datadir + '/arome/france/oper/data/fic_day/PREP.lfi.rQZ'
        )

if __name__ == '__main__':
    for test in [ UtGridpoint, UtHistoric, UtAnalysis, UtHistsurf ]:
        x = TextTestRunner(verbosity=2).run(TestLoader().loadTestsFromTestCase(test))
        if x.errors or x.failures:
            print "Something went wrong !"
            break 

def get_test_class():
    return [ UtGridpoint, UtHistoric, UtAnalysis, UtHistsurf ]
