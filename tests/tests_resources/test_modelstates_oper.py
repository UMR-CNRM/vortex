#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import footprints

from oper_test_config import *  # @UnusedWildImport

#t.debug()

class UtGridPoint(TestCase):

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
            local='PFARPE[geometry::area]+[term::fmth].rDH'
        )
        self.franx01 = GridGeometry(id='Current op', area='FRANX01',
                                    resolution=0.1, nlat=221, nlon=281)
        self.frangp0025 = GridGeometry(id='Current op', area='FRANGP0025',
                                       resolution=0.025, nlat=601, nlon=801)
        self.glob15 = GridGeometry(id='Current op', area='GLOB15', resolution=1.5)

        self.fp_gridpoint1 = dict(
            kind = 'gridpoint',
            geometry = self.glob15,
            nativefmt='fa',
            origin = 'historic',
            model = 'arpege',
            cutoff = 'production',
            date = rundate,
            term = 0
        )
        self.fp_gridpoint2 = dict(
            kind = 'gridpoint',
            geometry = self.glob15,
            nativefmt='fa',
            origin = 'historic',
            model = 'arpege',
            cutoff = 'production',
            date = rundate,
            term = 3
        )

        self.fp_gridpoint3 = dict(
            kind = 'gridpoint',
            geometry = self.franx01,
            nativefmt='fa',
            origin = 'historic',
            model = 'aladin',
            cutoff = 'production',
            date = rundate,
            term = 6
        )

        self.fp_gridpoint4 = dict(
            kind = 'gridpoint',
            geometry = self.frangp0025,
            nativefmt='fa',
            origin = 'historic',
            model = 'arome',
            cutoff = 'production',
            date = rundate,
            term = 6
        )

        self.fp_gridpoint5 = dict(
            kind = 'gridpoint',
            geometry = self.glob15,
            nativefmt='grib',
            origin = 'historic',
            model = 'arpege',
            cutoff = 'assim',
            date = rundate,
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
            date = rundate,
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
            #print ' > ', rh.location()            
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arpege/france/oper/data/fic_day/PFARPEGLOB15+0000.rDH'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/arpege/france/oper/data/fic_day/PFARPEGLOB15+0000.rDH'
        )
        self.assertTrue(rl[0].get())

    def test_v2(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_cont,
            self.fp_gridpoint2
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            # print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arpege/france/oper/data/fic_day/PFARPEGLOB15+0003.rDH'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/arpege/france/oper/data/fic_day/PFARPEGLOB15+0003.rDH'
        )
        self.assertTrue(rl[0].get())

    def test_v3(self):
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
            'file://oper.inline.fr/arome/france/oper/data/fic_day/PFAROMFRANGP0025+0006.rDH'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/arome/france/oper/data/fic_day/PFAROMFRANGP0025+0006.rDH'
        )
        self.assertTrue(rl[0].get())

    def test_v4(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_cont,
            self.fp_gridpoint4
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            # print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arome/france/oper/data/fic_day/PFAROMFRANGP0025+0006.rDH'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/arome/france/oper/data/fic_day/PFAROMFRANGP0025+0006.rDH'
        )
	self.assertTrue(rl[0].get())

    def test_v5(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_cont,
            self.fp_gridpoint5
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            # print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arpege/france/oper/data/bdap/PE18000GLOB15'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/arpege/france/oper/data/bdap/PE18000GLOB15'
        )
        self.assertTrue(rl[0].get())



    def test_v6(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_cont,
            self.fp_gridpoint6
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            # print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arpege/pearp/oper/data/bdap/RUN4/fc_DH_4_GLOB15_0006'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/arpege/pearp/oper/data/bdap/RUN4/fc_DH_4_GLOB15_0006'
        )
        self.assertTrue(rl[0].get())


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
            date = rundate,
            term = 0
        )

        self.fp_historic2 = dict(
            kind = 'historic',
            geometry = self.caledonie,
            origin = 'historic',
            model = 'aladin',
            cutoff = 'production',
            date = rundate_bis,
            term = 0
        )
        
        self.fp_historic2_bis = dict(
            kind = 'historic',
            geometry = self.caledonie,
            origin = 'historic',
            model = 'aladin',
            cutoff = 'assimilation',
            date = rundate,
            term = 0
        )
        self.fp_historic3 = dict(
            kind = 'historic',
            geometry = self.frangp,
            origin = 'historic',
            model = 'arpege',
            cutoff = 'production',
            date = rundate,
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
            # print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arome/france/oper/data/fic_day/ICMSHAROM+0000.rDH'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/arome/france/oper/data/fic_day/ICMSHAROM+0000.rDH'
        )
        self.assertTrue(sh.stat(rl[0].locate()))
        self.assertTrue(rl[0].get())

    def test_v2(self):
        rl = toolbox.rload(
            self.fp_prov2,
            self.fp_cont,
            self.fp_historic2
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            # print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/aladin/caledonie/oper/data/fic_day/ICMSHALAD+0000.rAM'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/aladin/caledonie/oper/data/fic_day/ICMSHALAD+0000.rAM'
        )
        self.assertTrue(rl[0].get())
        
    def test_v2_bis(self):
        rl = toolbox.rload(
            self.fp_prov2,
            self.fp_cont,
            self.fp_historic2_bis
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            # print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/aladin/caledonie/oper/data/fic_day/ICMSHALAD+0000.r18'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/aladin/caledonie/oper/data/fic_day/ICMSHALAD+0000.r18'
        )
        self.assertTrue(rl[0].get())


    def test_v3(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_cont,
            self.fp_historic3
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            # print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arpege/france/oper/data/fic_day/ICMSHARPE+0000.rDH'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/arpege/france/oper/data/fic_day/ICMSHARPE+0000.rDH'
        )
        self.assertTrue(sh.stat(rl[0].locate()))
        self.assertTrue(rl[0].get())


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
            date = rundate,
        )

        self.fp_analys1_b = dict(
            kind = 'analysis',
            cutoff = 'production',
            model = 'arome',
            geometry = self.frangp,
            nativefmt = 'fa',
            filling = 'surf',
            date = rundate,
        )

        self.fp_analys2 = dict(
            kind = 'analysis',
            cutoff = 'assimilation',
            model = 'aladin',
            geometry = self.frangp,
            date = rundate,
        )
        
        self.fp_analys2_bis = dict(
            kind = 'analysis',
            cutoff = 'production',
            model = 'aladin',
            geometry = self.frangp,
            date = rundate_bis,
        )

        self.fp_analys3 = dict(
            kind = 'analysis',
            cutoff = 'assim',
            model = 'arpege',
            geometry = self.std,
            filling = 'surf',
            date = rundate,
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
            # print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arome/france/oper/data/workdir/analyse/ICMSHAROMINIT.rDH'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/arome/france/oper/data/workdir/analyse/ICMSHAROMINIT.rDH'
        )
        self.assertTrue(rl[0].get())

    def test_v1_b(self):
        rl = toolbox.rload(
            self.fp_prov1,
            self.fp_cont1,
            self.fp_analys1_b
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            # print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arome/france/oper/data/fic_day/INIT_SURF.fa.rDH'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/arome/france/oper/data/fic_day/INIT_SURF.fa.rDH'
        )
        self.assertTrue(rl[0].get())
        

    def test_v2(self):
        rl = toolbox.rload(
            self.fp_prov2,
            self.fp_cont1,
            self.fp_analys2
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            # print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/aladin/caledonie/oper/data/workdir/analyse/ICMSHALADINIT.r18'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/aladin/caledonie/oper/data/workdir/analyse/ICMSHALADINIT.r18'
        )
        self.assertTrue(rl[0].get())
    
    def test_v2_bis(self):
        rl = toolbox.rload(
            self.fp_prov2,
            self.fp_cont1,
            self.fp_analys2_bis
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            # print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/aladin/caledonie/oper/data/workdir/analyse/ICMSHALADINIT.rAM'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/aladin/caledonie/oper/data/workdir/analyse/ICMSHALADINIT.rAM'
        )
        self.assertTrue(rl[0].get())


    def test_v3(self):
        rl = toolbox.rload(
            self.fp_prov1,
            self.fp_cont1,
            self.fp_analys3
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            # print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arpege/france/oper/data/workdir/analyse/ICMSHANALINIT_SURF.r18'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/arpege/france/oper/data/workdir/analyse/ICMSHANALINIT_SURF.r18'
        )
        self.assertTrue(rl[0].get())


class UtHistsurf(TestCase):

    def setUp(self):
        self.geom = SpectralGeometry(id='Current op', area='frangp', resolution=2.5)
        self.fp_histsurf = dict(
            kind = 'historic',
            date = rundate,
            cutoff = 'production',
            geometry = self.geom,
            nativefmt = 'fa',
            model = 'surfex',
            term = 6
        )

        self.fp_cont = dict(
            file = 'PREP.fa'
        )

        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            vapp = 'arome',
            igakey = 'france',
        )

    def test_ctlg1(self):
        histsurf = self.fp_histsurf
        ctlg = footprints.proxy.resources
        res = ctlg.find_best(histsurf)
        self.assertEqual(res.kind, 'historic')


    def test_h1(self):
        rl = toolbox.rload(
            self.fp_histsurf,
            self.fp_cont,
            self.fp_prov
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            # print ' > ', rh.location()

        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arome/france/oper/data/fic_day/PREP.fa.rDH'
        )
        self.assertEqual(
            rl[0].locate(),
            datadir + '/arome/france/oper/data/fic_day/PREP.fa.rDH'
        )
        self.assertTrue(rl[0].get())
        

if __name__ == '__main__':
    for test in [ UtGridPoint, UtHistoric, UtAnalysis, UtHistsurf ]:
        x = TextTestRunner(verbosity=2).run(TestLoader().loadTestsFromTestCase(test))
        if x.errors or x.failures:
            print "Something went wrong !"
            break

def get_test_class():
    return [ UtGridPoint, UtHistoric, UtAnalysis, UtHistsurf ]
