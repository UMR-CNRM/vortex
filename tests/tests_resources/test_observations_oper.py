#!/bin/env python
# -*- coding: utf-8 -*-


try:
    from oper_test_config import *
except ImportError, e:
    print e
    raise

#t.debug()

class UtObsmap(TestCase):

    def setUp(self):
        self.fp_obsmap = dict(
            kind='obsmap',
            date = today(),
            cutoff='production',
            model = 'arpege'
        )
        self.fp_obsmap2 = dict(
            kind='obsmap',
            date = today(),
            cutoff='production',
            model = 'arome'
        )
        self.fp_obsmap3 = dict(
            kind='obsmap',
            date = today(),
            cutoff='assim',
            model = 'aladin'
        )
        self.fp_prov = dict(
            namespace='[suite].inline.fr',
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'france',
        )
        self.fp_prov3 = dict(
            namespace='[suite].inline.fr',
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'reunion',
        )
        self.fp_cont_obsmap = dict(
            local='BATOR_MAP_[cutoff]'
        )
        self.fp_store = dict(
            rootdir = 'sopranohome'
        )

    def tearDown(self):
        del self.fp_prov
        del self.fp_prov3
        del self.fp_cont_obsmap
        del self.fp_obsmap
        del self.fp_obsmap2
        del self.fp_obsmap3
        del self.fp_store

    def test_ctlg(self):
        obsmap = self.fp_obsmap
        ctlg = resources.catalog()
        res = ctlg.findbest(obsmap)
        self.assertTrue(res.kind, 'obsmap')

        obsmap = self.fp_obsmap2
        ctlg = resources.catalog()
        res = ctlg.findbest(obsmap)
        self.assertTrue(res.kind, 'obsmap')

        obsmap = self.fp_obsmap3
        ctlg = resources.catalog()
        res = ctlg.findbest(obsmap)
        self.assertTrue(res.kind, 'obsmap')

    def test_r1(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_cont_obsmap,
            self.fp_obsmap,
            self.fp_store
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arpege/france/oper/const/autres/BATOR_MAP_production'
        )
        self.assertEqual(
            rh.locate(),
            '/ch/mxpt/mxpt001/arpege/france/oper/const/autres/BATOR_MAP_production'
        )

        rl = toolbox.rload(
            self.fp_prov,
            self.fp_cont_obsmap,
            self.fp_obsmap2
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arome/france/oper/const/autres/BATOR_MAP_production'
        )
        self.assertEqual(
            rh.locate(),
            '/ch/mxpt/mxpt001/arome/france/oper/const/autres/BATOR_MAP_production'
        )

        rl = toolbox.rload(
            self.fp_prov3,
            self.fp_cont_obsmap,
            self.fp_obsmap3
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/aladin/reunion/oper/const/autres/BATOR_MAP_assim'
        )
        self.assertEqual(
            rh.locate(),
            '/ch/mxpt/mxpt001/aladin/reunion/oper/const/autres/BATOR_MAP_assim'
        )


class UtBlackListLoc(TestCase):

    def setUp(self):
        self.fp_bckll = dict(
            kind='blacklist',
            scope='local',
            date = today(),
            cutoff='production',
            model = 'arpege'
        )
        self.fp_bckll2 = dict(
            kind='blacklist',
            scope='local',
            date = today(),
            cutoff='production',
            model = 'arome'
        )
        self.fp_prov = dict(
            namespace='[suite].inline.fr',
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'france',
        )

        self.fp_cont_bckll = dict(
            local='LISTE_LOC'
        )

    def tearDown(self):
        del self.fp_prov
        del self.fp_cont_bckll
        del self.fp_bckll
        del self.fp_bckll2

    def test_ctlg(self):
        bckll = self.fp_bckll
        ctlg = resources.catalog()
        res = ctlg.findbest(bckll)
        self.assertTrue(res.kind, 'blacklist')

        bckll = self.fp_bckll2
        ctlg = resources.catalog()
        res = ctlg.findbest(bckll)
        self.assertTrue(res.kind, 'blacklist')


    def test_r1(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_cont_bckll,
            self.fp_bckll
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arpege/france/oper/const/autres/LISTE_LOC'
        )
        self.assertEqual(
            rh.locate(),
            '/ch/mxpt/mxpt001/arpege/france/oper/const/autres/LISTE_LOC'
        )

        rl = toolbox.rload(
            self.fp_prov,
            self.fp_cont_bckll,
            self.fp_bckll2
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arome/france/oper/const/autres/LISTE_LOC'
        )
        self.assertEqual(
            rh.locate(),
            '/ch/mxpt/mxpt001/arome/france/oper/const/autres/LISTE_LOC'
        )

class UtBlackListDiap(TestCase):

    def setUp(self):
        self.fp_bckld = dict(
            kind='blacklist',
            scope='site',
            date = today(),
            cutoff='production',
            model = 'arpege'
        )
        self.fp_prov = dict(
            namespace='[suite].inline.fr',
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'france',
        )

        self.fp_cont_bckld = dict(
            local='LISTE_NOIRE_LOC'
        )

    def tearDown(self):
        del self.fp_prov
        del self.fp_cont_bckld
        del self.fp_bckld

    def test_ctlg(self):
        bckld = self.fp_bckld
        ctlg = resources.catalog()
        res = ctlg.findbest(bckld)
        self.assertTrue(res.kind, 'blacklist')

    def test_r1(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_cont_bckld,
            self.fp_bckld
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arpege/france/oper/const/autres/LISTE_NOIRE_LOC'
        )
        self.assertEqual(
            rh.locate(),
            '/ch/mxpt/mxpt001/arpege/france/oper/const/autres/LISTE_NOIRE_LOC'
        )

class UtRefData(TestCase):

    def setUp(self):
        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'france',
            namespace = 'prod.inline.fr',
            vapp = 'arpege',
            tube = 'ftp'
        )
        self.fp_cont1 = dict(
            local='RD_1'
        )
        self.fp_cont2 = dict(
            local='RD_2'
        )
        self.fp_cont_bufr = dict(
            local='bufr'
        )
        self.fp_rdconv = dict(
            kind='refdata',
            cutoff = 'production',
            date = today() + Period('PT6H'),
            model = 'arpege',
            part = 'conv',
            nativefmt = 'obsoul'
        )
        self.fp_rdprof = dict(
            kind='refdata',
            cutoff = 'production',
            date = today() + Period('PT6H'),
            model = 'arpege',
            part = 'prof',
            nativefmt = 'obsoul'
        )
        self.fp_rdsurf = dict(
            kind='refdata',
            cutoff = 'production',
            date = today() + Period('PT6H'),
            model = 'arpege',
            part = 'surf',
            nativefmt = 'obsoul'
        )
        self.liste_fp_bufr = []
        for i in ('airs', 'tovssh', 'tovsb', 'ssmis', 'iasi', 'tovsa', 'sev',
                  'gps', 'scat', 'geow'):
            for ct in ('assimilation', 'production'):
                for delta in ('PT0H', 'PT6H', 'PT12H', 'PT18H'):
                    logging.debug('delta %s', delta)
                    fp_obs = dict(
                        kind='refdata',
                        stage = 'void',
                        cutoff = ct,
                        date = today() + Period(delta),
                        model = 'arpege',
                        part = i,
                        nativefmt = 'bufr'
                    )
                    self.liste_fp_bufr.append(fp_obs)

    def test_ctlg1(self):
         obs = self.fp_rdconv
         ctlg = resources.catalog()
         res = ctlg.findbest(obs)
         self.assertTrue(res.kind, 'refdata')

         obs = self.fp_rdprof
         res = ctlg.findbest(obs)
         self.assertTrue(res.kind, 'refdata')

         obs = self.fp_rdsurf
         res = ctlg.findbest(obs)
         self.assertTrue(res.kind, 'refdata')

    def test_ctlg_bufr(self):
         ctlg = resources.catalog()
         for obs in self.liste_fp_bufr:
            res = ctlg.findbest(obs)
            self.assertTrue(res.kind, 'refdata')

    def test_v1(self):
        rl = toolbox.rload(
            self.fp_rdconv,
            self.fp_cont1,
            self.fp_prov
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()

        self.assertEqual(
            rl[0].location(),
            'ftp://prod.inline.fr/modele/oper/arpege/RW/RD_1.SX'
        )

        rl = toolbox.rload(
            self.fp_rdprof,
            self.fp_cont2,
            self.fp_prov
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()

        self.assertEqual(
            rl[0].location(),
            'ftp://prod.inline.fr/modele/oper/arpege/RW/RD_2.SX'
        )

        rl = toolbox.rload(
            self.fp_rdsurf,
            self.fp_cont2,
            self.fp_prov
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()

        self.assertEqual(
            rl[0].location(),
            'ftp://prod.inline.fr/modele/oper/arpege/RW/RD_SURFAN.SX'
        )


    def test_v_bufr(self):
        #TODO: traiter CM
        reseau = ('00','06','12','18', 'AM', 'SX', 'PM', 'DH')
        reseau = ['.' + elmt for elmt in reseau]
        core = ('airs', 'tovssh', 'tovsb', 'ssmis', 'iasi', 'tovsa', 'sev',
                'gps', 'scat', 'geow')
        res_name = [
            'rd_' + elmt2 for elmt2 in [
                elmt + suffixe for elmt in core for suffixe in reseau]
        ]
        cpt = 0
        for fp_obs in self.liste_fp_bufr:
            rl = toolbox.rload(
                fp_obs,
                self.fp_cont_bufr,
                self.fp_prov
            )
            for rh in rl:
                self.assertTrue(rh.complete)
                print ' > ', rh.location()

            self.assertEqual(
                rl[0].location(),
                'ftp://prod.inline.fr/modele/oper/arpege/RW/' + res_name[cpt]
            )
            cpt += 1



class UtObservations(TestCase):

    def setUp(self):
        self.std = SpectralGeometry(id='Current op', area='france', truncation=798)
        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'france',
            namespace = 'prod.inline.fr',
            vapp = 'arpege',
            tube = 'ftp'
        )
        self.fp_cont1 = dict(
            local='OBSOUL1_F'
        )
        self.fp_cont2 = dict(
            local='OBSOUL2_F'
        )
        self.fp_cont_bufr = dict(
            local='BUFR'
        )
        self.fp_obsconv = dict(
            kind='observations',
            geometry = self.std,
            cutoff = 'production',
            date = today() + Period('PT6H'),
            model = 'arpege',
            part = 'conv',
            nativefmt = 'obsoul'
        )
        self.fp_obsprof = dict(
            kind='observations',
            geometry = self.std,
            cutoff = 'production',
            date = today() + Period('PT6H'),
            model = 'arpege',
            part = 'prof',
            nativefmt = 'obsoul'
        )
        self.fp_obssurf = dict(
            kind='observations',
            geometry = self.std,
            cutoff = 'production',
            date = today() + Period('PT6H'),
            model = 'arpege',
            part = 'surf',
            nativefmt = 'obsoul'
        )
        self.liste_fp_bufr = []
        for i in ('airs', 'tovssh', 'tovsb', 'ssmis', 'iasi', 'tovsa', 'sev',
                  'gps', 'scat', 'geow'):
            for ct in ('assimilation', 'production'):
                for delta in ('PT0H', 'PT6H', 'PT12H', 'PT18H'):
                    logging.debug('delta %s', delta)
                    fp_obs = dict(
                        kind='observations',
                        stage = 'void',
                        geometry = self.std,
                        cutoff = ct,
                        date = today() + Period(delta),
                        model = 'arpege',
                        part = i,
                        nativefmt = 'bufr'
                    )
                    self.liste_fp_bufr.append(fp_obs)

    def test_ctlg1(self):
         obs = self.fp_obsconv
         ctlg = resources.catalog()
         res = ctlg.findbest(obs)
         self.assertTrue(res.kind, 'observations')

         obs = self.fp_obsprof
         res = ctlg.findbest(obs)
         self.assertTrue(res.kind, 'observations')

         obs = self.fp_obssurf
         res = ctlg.findbest(obs)
         self.assertTrue(res.kind, 'observations')

    def test_ctlg_bufr(self):
         ctlg = resources.catalog()
         for obs in self.liste_fp_bufr:
            res = ctlg.findbest(obs)
            self.assertTrue(res.kind, 'observations')

    def test_v1(self):
        rl = toolbox.rload(
            self.fp_obsconv,
            self.fp_cont1,
            self.fp_prov
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()

        self.assertEqual(
            rl[0].location(),
            'ftp://prod.inline.fr/modele/oper/arpege/RW/OBSOUL1F.SX'
        )

        rl = toolbox.rload(
            self.fp_obsprof,
            self.fp_cont2,
            self.fp_prov
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()

        self.assertEqual(
            rl[0].location(),
            'ftp://prod.inline.fr/modele/oper/arpege/RW/OBSOUL2F.SX'
        )
        rl = toolbox.rload(
            self.fp_obssurf,
            self.fp_cont2,
            self.fp_prov
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()

        self.assertEqual(
            rl[0].location(),
            'ftp://prod.inline.fr/modele/oper/arpege/RW/OBSOUL_SURFAN.SX'
        )


    def test_v_bufr(self):
        #TODO: traiter CM
        reseau = ('00','06','12','18', 'AM', 'SX', 'PM', 'DH')
        reseau = ['.' + elmt for elmt in reseau]
        core = ('airs', 'tovssh', 'tovsb', 'ssmis', 'iasi', 'tovsa', 'sev',
                'gps', 'scat', 'geow')
        res_name = [
            'BUFR.' + elmt2 for elmt2 in [
                elmt + suffixe for elmt in core for suffixe in reseau]
        ]
        cpt = 0
        for fp_obs in self.liste_fp_bufr:
            rl = toolbox.rload(
                fp_obs,
                self.fp_cont_bufr,
                self.fp_prov
            )
            for rh in rl:
                self.assertTrue(rh.complete)
                print ' > ', rh.location()

            self.assertEqual(
                rl[0].location(),
                'ftp://prod.inline.fr/modele/oper/arpege/RW/' + res_name[cpt]
            )
            cpt += 1


#    def test_o3(self):
#        rl = toolbox.rload(
#            self.attrset,
#            local='odb_screen.tar',
#            igakey='arpege',
#            suite='oper',
#            model='arpege',
#            geometry=self.std,
#            part='full',
#            nativefmt='odb',
#            stage='screen'
#        )
#        for rh in rl:
#            self.assertTrue(rh.complete)
#            print ' > ', rh.location()
#        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/arpege/oper/production/2012/02/14/r6/odb_screen.tar?extract=all')
#
#    def test_o4(self):
#        rl = toolbox.rload(
#            self.attrset,
#            local='odb_cpl.tar',
#            igakey='arpege',
#            suite='oper',
#            model='arpege',
#            geometry=self.std,
#            part='full',
#            nativefmt='odb',
#            stage='complete'
#        )
#        for rh in rl:
#            self.assertTrue(rh.complete)
#            print ' > ', rh.location()
#        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/arpege/oper/production/2012/02/14/r6/odb_cpl.tar?extract=all')

class UtRefdata(TestCase):

    def setUp(self):
        self.std = SpectralGeometry(id='Current op', area='france', truncation=798)
        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'france',
        )
        self.fp_cont = dict(
            local='refdata'
        )
        self.fp_refdata = dict(
            kind='refdata',
            geometry = self.std,
            cutoff = 'production',
            date = today() + Period('PT6H'),
            model = 'arpege'
        )

    def test_ctlg1(self):
        refdata = self.fp_refdata
        ctlg = resources.catalog()
        res = ctlg.findbest(refdata)
        self.assertTrue(res.kind, 'refdata')

    def test_v1(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_cont,
            self.fp_refdata
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arpege/france/oper/data/workdir/obs/refdata.rSX'
        )
        self.assertEqual(
            rl[0].locate(),
            '/ch/mxpt/mxpt001/arpege/france/oper/data/workdir/obs/refdata.rSX'
        )
        #uniquement sur machine oper (pas de phasage)
        if t.env['HOSTNAME'] == 'kumo':
            self.assertTrue(os.stat(rl[0].locate()))


class UtVarbc(TestCase):

    def setUp(self):
        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'reunion',
        )

        self.fp_prov2 = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'france',
        )


        self.fp_cont = dict(
            local='VARBC.cycle_alad.rDH'
        )

        self.fp_varbc1 = dict(
            kind = 'varbc',
            cutoff = 'production',
            model = 'aladin',
            date = today() + Period('PT12H'),
        )

        self.fp_varbc2 = dict(
            kind = 'varbc',
            cutoff = 'production',
            model = 'arpege',
            date = today() + Period('PT12H'),
        )

        self.fp_varbc3 = dict(
            kind = 'varbc',
            cutoff = 'production',
            model = 'arome',
            date = today() + Period('PT12H'),
        )


    def test_ctlg1(self):
        varbc = self.fp_varbc1
        ctlg = resources.catalog()
        res = ctlg.findbest(varbc)
        self.assertTrue(res.kind, 'varbc')

        varbc2 = self.fp_varbc2
        res = ctlg.findbest(varbc2)
        self.assertTrue(res.kind, 'varbc2')

        varbc3 = self.fp_varbc3
        res = ctlg.findbest(varbc3)
        self.assertTrue(res.kind, 'varbc3')

    def test_v1(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_cont,
            self.fp_varbc1
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/aladin/reunion/oper/data/fic_day/VARBC.cycle_alad.r12'
        )
        self.assertEqual(
            rl[0].locate(),
            '/ch/mxpt/mxpt001/aladin/reunion/oper/data/fic_day/VARBC.cycle_alad.r12'
        )
        self.assertTrue(os.stat(rl[0].locate()))

    def test_v2(self):
        rl = toolbox.rload(
            self.fp_prov2,
            self.fp_cont,
            self.fp_varbc2
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arpege/france/oper/data/fic_day/VARBC.cycle.r12'
        )
        self.assertEqual(
            rl[0].locate(),
            '/ch/mxpt/mxpt001/arpege/france/oper/data/fic_day/VARBC.cycle.r12'
        )
        self.assertTrue(os.stat(rl[0].locate()))

    def test_v3(self):
        rl = toolbox.rload(
            self.fp_prov2,
            self.fp_cont,
            self.fp_varbc3
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arome/france/oper/data/fic_day/VARBC.cycle_aro.r12'
        )
        self.assertEqual(
            rl[0].locate(),
            '/ch/mxpt/mxpt001/arome/france/oper/data/fic_day/VARBC.cycle_aro.r12'
        )
        self.assertTrue(os.stat(rl[0].locate()))


if __name__ == '__main__':
    for test in [ UtBlackListDiap, UtBlackListLoc, UtVarbc, UtObsmap,
                  UtObservations, UtRefData]:
        x = TextTestRunner(verbosity=2).run(TestLoader().loadTestsFromTestCase(test))
        if x.errors or x.failures:
            print "Something went wrong !"
            break
def get_test_class():
    """ return the list of the TestCase classes names"""
    return [ UtBlackListDiap, UtBlackListLoc, UtVarbc, UtObsmap, UtObservations,
           UtRefData]
