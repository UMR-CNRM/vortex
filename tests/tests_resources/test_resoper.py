#!/bin/env python
# -*- coding: utf-8 -*-


import os
import logging
from unittest import TestCase, TestLoader, TextTestRunner

from vortex import toolbox, sessions
from vortex.data import resources
from vortex.data.geometries import SpectralGeometry, GridGeometry
from vortex.tools.date import today, Date
import common.data
import iga.data

t = sessions.ticket()
#t.debug()



class UtMatFilter(TestCase):

    def setUp(self):
        self.std = SpectralGeometry(id='oper', area='france', truncation=798)
        self.glob15 = GridGeometry(id='oper', area='GLOB15', resolution=15)
        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = self.std.area,
            glove = sessions.glove()
        )
        self.fp_cont = dict(
            local='matrix.fil.[scopedomain::area]'
        )
        self.fp_matfilter = dict(
            kind='matfilter',
            geometry = self.std,
            scopedomain = self.glob15
        )

    def tearDown(self):
        del self.std
        del self.glob15
        del self.fp_prov

    def test_ctlg(self):
        mat_filter = self.fp_matfilter
        ctlg = resources.catalog()
        res = ctlg.findbest(mat_filter)

        self.assertTrue(res.kind, 'matfilter')

    def test_rl(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_cont,
            self.fp_matfilter,
            model='arpege',
        )
        for rh in rl:
            self.assertTrue(rh.complete)

        self.assertEqual(rl[0].resource.kind, 'matfilter')
        self.assertEqual(rl[0].provider.realkind(), 'iga')
        self.assertEqual(rl[0].container.realkind(), 'file')
        self.assertEqual(
            rh.location(),
            'file://oper.inline.fr/arpege/france/oper/const/autres/matrix.fil.GLOB15'
        )
        self.assertEqual(
            rh.locate(),
            '/ch/mxpt/mxpt001/arpege/france/oper/const/autres/matrix.fil.GLOB15'
        )
        #self.assertTrue(os.stat(rh.locate()))


class UtRtCoef(TestCase):

    def setUp(self):
        self.std = SpectralGeometry(id='oper', area='france', truncation=798)
        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = self.std.area,
            glove = sessions.glove()
        )
        self.fp_cont = dict(
            local='rtcoef.tar'
        )
        self.fp_rtcoef = dict(
            kind='rtcoef',
            geometry = self.std,
            model='arpege'
        )

    def test_ctlg(self):
        rtcoef = self.fp_rtcoef
        ctlg = resources.catalog()
        res = ctlg.findbest(rtcoef)

        self.assertTrue(res.kind, 'rtcoef')

    def test_r1(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_rtcoef,
            self.fp_cont
        )
        for rh in rl:
            self.assertTrue(rh.complete)

        self.assertEqual(rl[0].resource.kind, 'rtcoef')
        self.assertEqual(rl[0].provider.realkind(), 'iga')
        self.assertEqual(rl[0].container.realkind(), 'file')
        self.assertEqual(
            rh.location(),
            'file://oper.inline.fr/arpege/france/oper/const/autres/rtcoef.tar'
        )
        self.assertEqual(
            rh.locate(),
            '/ch/mxpt/mxpt001/arpege/france/oper/const/autres/rtcoef.tar'
        )
        #self.assertTrue(os.stat(rh.locate()))


class UtRawFields(TestCase):

    def setUp(self):
        self.fp_prov = dict(
            username = 'mxpt001',
            vapp = 'arpege',
            suite = 'oper',
            igakey = 'france',
        )
        self.fp_prov_2 = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'france',
            namespace='prod.inline.fr',
            vapp = 'arpege',
            tube = 'ftp',
        )
        self.fp_cont_nesdis = dict(
            local='sst.nesdis.bdap'
        )
        self.fp_cont_ostia = dict(
            local='sst.nesdis.bdap'
        )
        self.fp_cont_seaice = dict(
            local='ice_concent'
        )
        self.fp_nesdis = dict(
            kind='rawfields',
            origin = 'nesdis',
            fields = 'sst',
            date = today(),
            cutoff='assim',
        )

        self.fp_ostia = dict(
            kind='rawfields',
            origin = 'ostia',
            fields = 'sst',
            date = today(),
            cutoff='assim',
        )

        self.fp_seaice = dict(
            kind='rawfields',
            origin = 'bdm',
            fields = 'seaice',
            date = today(),
            cutoff='production',
        )


    def tearDown(self):
        del self.fp_prov
        del self.fp_prov_2
        del self.fp_cont_nesdis
        del self.fp_cont_ostia
        del self.fp_cont_seaice
        del self.fp_nesdis

    def test_ctlg(self):
        nesdis = self.fp_nesdis
        ctlg = resources.catalog()
        res = ctlg.findbest(nesdis)

        self.assertTrue(res.kind, 'rawfields')

        ostia = self.fp_ostia
        ctlg = resources.catalog()
        res = ctlg.findbest(ostia)

        self.assertTrue(res.kind, 'rawfields')

        seaice = self.fp_seaice
        ctlg = resources.catalog()
        res = ctlg.findbest(seaice)

        self.assertTrue(res.kind, 'rawfields')

    def test_r1(self):
        rl = toolbox.rload(
            self.fp_nesdis,
            self.fp_cont_nesdis,
            self.fp_prov
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arpege/france/oper/data/fic_day/sst.nesdis.bdap'
        )

        self.assertEqual(
            rh.locate(),
            '/ch/mxpt/mxpt001/arpege/france/oper/data/fic_day/sst.nesdis.bdap'
        )
        #uniquement sur kumo (sst.nesdis.bdap non phase)
        #self.assertTrue(os.stat(rh.locate()))

        rl = toolbox.rload(
            self.fp_ostia,
            self.fp_cont_ostia,
            self.fp_prov
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()

        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arpege/france/oper/data/fic_day/sst.ostia')

        self.assertEqual(
            rh.locate(),
            '/ch/mxpt/mxpt001/arpege/france/oper/data/fic_day/sst.ostia'
        )
        #uniquement sur kumo (sst.ostia non phase)
        #self.assertTrue(os.stat(rh.locate()))

        rl = toolbox.rload(
            self.fp_seaice,
            self.fp_prov_2,
            self.fp_cont_seaice
        )

        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()

        self.assertEqual(
            rl[0].location(),
            'ftp://prod.inline.fr/modele/oper/arpege/RW/SSMI.AM'
        )
        self.assertEqual(
            rh.locate(),
            '/SOPRANO/modele/oper/arpege/RW/SSMI.AM'
        )


class UtGeoFields(TestCase):

    def setUp(self):
        self.std = SpectralGeometry(id='Current op', area='france', truncation=798)
        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = '[geometry::area]',
            glove = sessions.glove()
        )
        self.fp_cont = dict(
            local='ICMSHANALSST'
        )
        self.fp_sst = dict(
            kind='geofields',
            fields = 'sst',
            date = today(),
            cutoff='assim',
            geometry = self.std,
            model='arpege'
        )

    def tearDown(self):
        """docstring for tearDown"""
        del self.fp_prov
        del self.fp_cont
        del self.fp_sst
        del self.std

    def test_ctlg(self):
        sstgeofields = self.fp_sst
        ctlg = resources.catalog()
        res = ctlg.findbest(sstgeofields)

        self.assertTrue(res.kind, 'geofields')

    def test_g1(self):
        rl = toolbox.rload(
            self.fp_sst,
            self.fp_prov,
            self.fp_cont
        )

        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()

        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arpege/france/oper/data/fic_day/ICMSHANALSST'
        )
        self.assertEqual(
            rl[0].locate(),
            '/ch/mxpt/mxpt001/arpege/france/oper/data/fic_day/ICMSHANALSST'
        )
        self.assertTrue(os.stat(rl[0].locate()))



class UtClimGlobal(TestCase):

    def setUp(self):
        self.std = SpectralGeometry(
            id='Current op',
            area='france',
            truncation=798,
            stretching=2.4
        )
        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'france',
            glove = sessions.glove()
        )
        self.fp_cont = dict(
            local='Const.Clim'
        )
        self.fp_climmodel = dict(
            kind='clim_model',
            month = today().month,
            geometry = self.std,
            model='arpege'
        )

    def test_ctlg(self):
        climmodel = self.fp_climmodel
        ctlg = resources.catalog()
        res = ctlg.findbest(climmodel)

        month = "{0:02d}".format(today().month)
        self.assertTrue(res.kind, 'clim_model')

    def test_v1(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_cont,
            self.fp_climmodel
        )

        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()

        month = "{0:02d}".format(today().month)
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arpege/france/oper/const/clim/mens/clim_t798_isba'+month
        )
        self.assertEqual(
            rl[0].locate(),
            '/ch/mxpt/mxpt001/arpege/france/oper/const/clim/mens/clim_t798_isba'+month
        )
        self.assertTrue(os.stat(rl[0].locate()))

class UtClimLAM(TestCase):

    def setUp(self):
        self.geocaledonie = SpectralGeometry(id='Current op', area='caledonie', resolution='08km00')
        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'caledonie',
            glove = sessions.glove()
        )
        self.fp_cont = dict(
            local='const.clim.[geometry::area]'
        )
        self.fp_climmodel = dict(
            kind='clim_model',
            month = today().month,
            geometry = self.geocaledonie,
            model='aladin'
        )

    def test_ctlg(self):
        climbdap = self.fp_climmodel
        ctlg = resources.catalog()
        res = ctlg.findbest(climbdap)

        month = "{0:02d}".format(today().month)
        self.assertTrue(res.kind, 'clim_bdap')

    def test_r1(self):
        rl = toolbox.rload(
            self.fp_climmodel,
            self.fp_cont,
            self.fp_prov
        )

        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()

        month = "{0:02d}".format(today().month)
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/aladin/caledonie/oper/const/clim/mens/clim_caledonie_isba'+month
        )

        self.assertEqual(
            rl[0].locate(),
            '/ch/mxpt/mxpt001/aladin/caledonie/oper/const/clim/mens/clim_caledonie_isba'+month
        )
        self.assertTrue(os.stat(rl[0].locate()))


class UtClimBDAPLAM(TestCase):

    def setUp(self):
        self.geocaledonie = GridGeometry(id='Current op', area='caled', resolution='08km00')
        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'caledonie',
            glove = sessions.glove()
        )
        self.fp_cont = dict(
            local='const.clim.[geometry::area]'
        )
        self.fp_climmodel = dict(
            kind='clim_bdap',
            month = today().month,
            geometry = self.geocaledonie,
            model='aladin'
        )

    def test_ctlg(self):
        climbdap = self.fp_climmodel
        ctlg = resources.catalog()
        res = ctlg.findbest(climbdap)

        month = "{0:02d}".format(today().month)
        self.assertTrue(res.kind, 'clim_bdap')

    def test_r1(self):
        rl = toolbox.rload(
            self.fp_climmodel,
            self.fp_cont,
            self.fp_prov
        )

        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()

        month = "{0:02d}".format(today().month)
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/aladin/caledonie/oper/const/clim/domaine/clim_dap.caled01.m'+month
        )

        self.assertEqual(
            rl[0].locate(),
            '/ch/mxpt/mxpt001/aladin/caledonie/oper/const/clim/domaine/clim_dap.caled01.m'+month
        )
        self.assertTrue(os.stat(rl[0].locate()))


class UtClimBDAP(TestCase):

    def setUp(self):
        self.frangp0025 = GridGeometry(id='Current op', area='FRANGP0025', resolution='0025', nlat=601, nlon=801)
        self.glob15 = GridGeometry(id='Current op', area='GLOB15', resolution='15')
        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'france',
            glove = sessions.glove()
        )
        self.fp_cont = dict(
            local='const.clim.[geometry::area]'
        )
        self.fp_climbdap_1 = dict(
            kind='bdapclim',
            month = today().month,
            geometry = self.glob15,
            model = 'arpege'
        )
        self.fp_climbdap_2 = dict(
            kind='bdapclim',
            month = today().month,
            geometry = self.frangp0025,
            model = 'arome'
        )
    def test_ctlg(self):
        climbdap = self.fp_climbdap_1
        ctlg = resources.catalog()
        res = ctlg.findbest(climbdap)

        self.assertTrue(res.kind, 'clim_bdap')

        climbdap = self.fp_climbdap_2
        res = ctlg.findbest(climbdap)

        self.assertTrue(res.kind, 'clim_bdap')


    def test_v1(self):
        rl = toolbox.rload(
            self.fp_climbdap_1,
            self.fp_cont,
            self.fp_prov
        )

        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()

        month = "{0:02d}".format(today().month)
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arpege/france/oper/const/clim/domaine/const.clim.GLOB15_m' + month
        )
        self.assertEqual(
            rl[0].locate(),
            '/ch/mxpt/mxpt001/arpege/france/oper/const/clim/domaine/const.clim.GLOB15_m' + month
        )
        self.assertTrue(os.stat(rl[0].locate()))

    def test_v2(self):
        rl = toolbox.rload(
            self.fp_climbdap_2,
            self.fp_cont,
            self.fp_prov
        )

        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()

        month = "{0:02d}".format(today().month)
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arome/france/oper/const/clim/domaine/BDAP_frangp_isba' + month
        )
        self.assertEqual(
            rl[0].locate(),
            '/ch/mxpt/mxpt001/arome/france/oper/const/clim/domaine/BDAP_frangp_isba' + month
        )
        self.assertTrue(os.stat(rl[0].locate()))

class UtBcor(TestCase):

    def setUp(self):
        self.attrset = dict(kind='bcor', date = '2012021406', cutoff='production', namespace='[suite].archive.fr')

    def test_b1(self):
        rl = toolbox.rload(
            self.attrset,
            local='bcor_[collected].dat',
            collected='noaa,ssmi,mtop',
            igakey='arpege',
            suite='oper',
            model='arpege',
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/arpege/oper/production/2012/02/14/r6/entree.tar?extract=bcor_noaa.dat')
        self.assertEqual(rl[1].location(), 'ftp://oper.archive.fr/arpege/oper/production/2012/02/14/r6/entree.tar?extract=bcor_ssmi.dat')
        self.assertEqual(rl[2].location(), 'ftp://oper.archive.fr/arpege/oper/production/2012/02/14/r6/entree.tar?extract=bcor_mtop.dat')

class UtObsmap(TestCase):

    def setUp(self):
        self.attrset = dict(kind='obsmap', date = '2012021406', cutoff='production', namespace='[suite].archive.fr')

    def test_o1(self):
        rl = toolbox.rload(
            self.attrset,
            local='obsmap',
            igakey='arpege',
            suite='oper',
            model='arpege',
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/arpege/oper/production/2012/02/14/r6/entree.tar?extract=BATOR_MAP')

    def test_o2(self):
        rl = toolbox.rload(
            self.attrset,
            namespace='open.archive.fr',
            date='2011092200',
            local='obsmap_olive_split',
            model='arpege',
            experiment='99A0',
            stage='split',
            block='observations',
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(rl[0].location(), 'olive://open.archive.fr/9/9/A/0/20110922H00P/observations/OBSMAP_split')

class UtBlackListLoc(TestCase):

    def setUp(self):
        self.attrset = dict(kind='blacklistloc', date = '2012021406', cutoff='production', namespace='[suite].archive.fr')

    def test_o1(self):
        rl = toolbox.rload(
            self.attrset,
            local='blacklist_loc',
            igakey='arpege',
            suite='oper',
            model='arpege',
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/arpege/oper/production/2012/02/14/r6/entree.tar?extract=LISTE_LOC')

class UtBlackListDiap(TestCase):

    def setUp(self):
        self.attrset = dict(kind='blacklistdiap', date = '2012021406', cutoff='production', namespace='[suite].archive.fr')

    def test_o1(self):
        rl = toolbox.rload(
            self.attrset,
            local='blacklist_diap',
            igakey='arpege',
            suite='oper',
            model='arpege',
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/arpege/oper/production/2012/02/14/r6/entree.tar?extract=LISTE_NOIRE_DIAP')


class UtObservations(TestCase):

    def setUp(self):
        self.std = SpectralGeometry(id='Current op', area='france', truncation=798)
        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'france',
            glove = sessions.glove()
        )
        self.fp_cont = dict(
            local='obsoul.conv'
        )
        self.fp_obs1 = dict(
            kind='observations',
            stage = 'void',
            geometry = self.std,
            cutoff = 'production',
            date = Date(today().get_fmt_date("yyyymmdd")).add_delta("P6H",
                                                                    "yyyymmddhh"),
            model = 'arpege',
            part = 'conv',
            nativefmt = 'obsoul'
        )
        self.fp_obs2 = dict(
            kind='observations',
            stage = 'void',
            geometry = self.std,
            cutoff = 'production',
            date = Date(today().get_fmt_date("yyyymmdd")).add_delta("P6H",
                                                                    "yyyymmddhh"),
            model = 'arpege',
            part = 'surf',
            nativefmt = 'obsoul'
        )
        self.fp_obs3 = dict(
            kind='observations',
            stage = 'void',
            geometry = self.std,
            cutoff = 'production',
            date = Date(today().get_fmt_date("yyyymmdd")).add_delta("P6H",
                                                                    "yyyymmddhh"),
            model = 'arpege',
            part = 'prof',
            nativefmt = 'obsoul'
        )
        self.liste_fp_ecma = []
        for i in ('airs', 'tovssh', 'tovsb', 'ssmis', 'iasi', 'tovsa', 'sev',
                  'gps', 'scat', 'geow'):
            for ct in ('production', 'assimilation'):
                for delta in ('P0H', 'P6H', 'P12H', 'P18H'):
                    logging.debug('delta %s', delta)
                    fp_obs = dict(
                        kind='observations',
                        stage = 'void',
                        geometry = self.std,
                        cutoff = ct,
                        date = Date(
                            today().get_fmt_date("yyyymmdd")).add_delta(delta,
                                                              "yyyymmddhh"),
                        model = 'arpege',
                        part = i,
                        nativefmt = 'ecma'
                    )
                    self.liste_fp_ecma.append(fp_obs)

        self.fp_obs4 = dict(
            kind='observations',
            stage = 'std',
            geometry = self.std,
            cutoff = 'production',
            date = Date(today().get_fmt_date("yyyymmdd")).add_delta("P6H",
                                                                    "yyyymmddhh"),
            model = 'arpege',
            part = 'surf',
            nativefmt = 'ecma'
        )


    def test_ctlg1(self):
        cpt = 0
        #day = "{0:02d}".format(today().day)
        for fp in (self.fp_obs1, self.fp_obs2, self.fp_obs3, self.fp_obs4,
                  self.fp_obs5
                  ):
            obsoulconv = fp
            ctlg = resources.catalog()
            res = ctlg.findbest(obsoulconv)
            self.assertTrue(res.kind, 'observations')
            cpt += 1

    def test_v1(self):
        cpt = 0
        ref = ['obsoul.conv.rSX', 'obsoul.surf.rSX', 'obsoul.prof.rSX']
        for fp in (self.fp_obs1, self.fp_obs2, self.fp_obs3):
            rl = toolbox.rload(
                fp,
                self.fp_cont,
                self.fp_prov
            )
            for rh in rl:
                self.assertTrue(rh.complete)
                print ' > ', rh.location()

            self.assertEqual(
                rl[0].location(),
                'file://oper.inline.fr/arpege/france/oper/data/workdir/obs/' +\
ref[cpt]
            )
            self.assertEqual(
                rl[0].locate(),
                '/ch/mxpt/mxpt001/arpege/france/oper/data/workdir/obs/' +\
ref[cpt]
            )
            #uniquement sur kumo (sst.ostia non phase)
            #self.assertTrue(os.stat(rl[0].locate()))
            cpt += 1


#    def test_o1(self):
#        rl = toolbox.rload(
#            self.attrset,
#            local='obsoul.conv',
#            igakey='arpege',
#            suite='oper',
#            model='arpege',
#            geometry=self.std,
#            part='conv',
#            nativefmt='obsoul',
#            stage='void'
#        )
#        for rh in rl:
#            self.assertTrue(rh.complete)
#            print ' > ', rh.location()
#        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/arpege/oper/production/2012/02/14/r6/obsoul.conv')
#
#    def test_o2(self):
#        rl = toolbox.rload(
#            self.attrset,
#            local='bufr.iasi',
#            igakey='arpege',
#            suite='oper',
#            model='arpege',
#            geometry=self.std,
#            part='iasi',
#            nativefmt='bufr',
#            stage='void'
#        )
#        for rh in rl:
#            self.assertTrue(rh.complete)
#            print ' > ', rh.location()
#        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/arpege/oper/production/2012/02/14/r6/bufr.iasi')
#
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
            glove = sessions.glove()
        )
        self.fp_cont = dict(
            local='refdata'
        )
        self.fp_refdata = dict(
            kind='refdata',
            geometry = self.std,
            cutoff = 'production',
            date = Date(today().get_fmt_date("yyyymmdd")).add_delta("P6H",
                                                                    "yyyymmddhh"),
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
        #self.assertTrue(os.stat(rl[0].locate()))


class UtGridpoint(TestCase):

    def setUp(self):
        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'france',
            glove = sessions.glove()
        )
        self.fp_cont = dict(
            local='PFARPE[geometry::area]+[term].rSX'
        )
        self.franx01 = GridGeometry(id='Current op', area='FRANX01', resolution=01, nlat=221, nlon=281)
        self.frangp0025 = GridGeometry(id='Current op', area='FRANGP0025', resolution=0025, nlat=601, nlon=801)
        self.glob15 = GridGeometry(id='Current op', area='GLOB15', resolution=15)
        self.fp_gridpoint1 = dict(
            kind = 'gridpoint',
            geometry = self.glob15,
            nativefmt='fa',
            origin = 'historic',
            model = 'arpege',
            cutoff = 'production',
            date = Date(today().get_fmt_date("yyyymmdd")).add_delta("P6H",
                                                                    "yyyymmddhh"),
            term = 0
        )
        self.fp_gridpoint2 = dict(
            kind = 'gridpoint',
            geometry = self.glob15,
            nativefmt='fa',
            origin = 'historic',
            model = 'arpege',
            cutoff = 'production',
            date = Date(today().get_fmt_date("yyyymmdd")).add_delta("P6H",
                                                                    "yyyymmddhh"),
            term = 3
        )

        self.fp_gridpoint3 = dict(
            kind = 'gridpoint',
            geometry = self.franx01,
            nativefmt='fa',
            origin = 'historic',
            model = 'aladin',
            cutoff = 'production',
            date = Date(today().get_fmt_date("yyyymmdd")).add_delta("P6H",
                                                                    "yyyymmddhh"),
            term = 6
        )

        self.fp_gridpoint4 = dict(
            kind = 'gridpoint',
            geometry = self.frangp0025,
            nativefmt='fa',
            origin = 'historic',
            model = 'arome',
            cutoff = 'production',
            date = Date(today().get_fmt_date("yyyymmdd")).add_delta("P6H",
                                                                    "yyyymmddhh"),
            term = 6
        )

        self.fp_gridpoint5 = dict(
            kind = 'gridpoint',
            geometry = self.glob15,
            nativefmt='grib',
            origin = 'historic',
            model = 'arpege',
            cutoff = 'assim',
            date = Date(today().get_fmt_date("yyyymmdd")).add_delta("P6H",
                                                                    "yyyymmddhh"),
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
            date = Date(today().get_fmt_date("yyyymmdd")).add_delta("P6H",
                                                                    "yyyymmddhh"),
            term = 6,
            member = 4
        )

    def test_ctlg1(self):
        gridpoint = self.fp_gridpoint1
        ctlg = resources.catalog()
        res = ctlg.findbest(gridpoint)
        self.assertTrue(res.kind, 'gridpoint')

        gridpoint = self.fp_gridpoint2
        res = ctlg.findbest(gridpoint)
        self.assertTrue(res.kind, 'gridpoint')

        gridpoint = self.fp_gridpoint3
        res = ctlg.findbest(gridpoint)
        self.assertTrue(res.kind, 'gridpoint')

        gridpoint = self.fp_gridpoint4
        res = ctlg.findbest(gridpoint)
        self.assertTrue(res.kind, 'gridpoint')

        gridpoint = self.fp_gridpoint5
        res = ctlg.findbest(gridpoint)
        self.assertTrue(res.kind, 'gridpoint')

        gridpoint = self.fp_gridpoint6
        res = ctlg.findbest(gridpoint)
        self.assertTrue(res.kind, 'gridpoint')

    def test_v1(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_cont,
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
            '/ch/mxpt/mxpt001/arpege/france/oper/data/fic_day/PFARPEGLOB15+0000.rSX'
        )
        #uniquement sur machine oper (pas de phasage)
        #self.assertTrue(os.stat(rl[0].locate()))

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
            '/ch/mxpt/mxpt001/arpege/france/oper/data/fic_day/PFARPEGLOB15+0003.rSX'
        )
        #uniquement sur machine oper (pas de phasage)
        #self.assertTrue(os.stat(rl[0].locate()))

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
            '/ch/mxpt/mxpt001/aladin/france/oper/data/fic_day/PFALADFRANX01+0006.rSX'
        )
        #uniquement sur machine oper (pas de phasage)
        #self.assertTrue(os.stat(rl[0].locate()))

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
            '/ch/mxpt/mxpt001/arome/france/oper/data/fic_day/PFAROMFRANGP0025+0006.rSX'
        )
        #uniquement sur machine oper (pas de phasage)
        #self.assertTrue(os.stat(rl[0].locate()))

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
            '/ch/mxpt/mxpt001/arpege/france/oper/data/bdap/PE06000GLOB15'
        )
        #uniquement sur machine oper (pas de phasage)
        #self.assertTrue(os.stat(rl[0].locate()))

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
            '/ch/mxpt/mxpt001/arpege/pearp/oper/data/bdap/RUN4/fc_SX_4_GLOB15_0006'
        )
        #uniquement sur machine oper (pas de phasage)
        #self.assertTrue(os.stat(rl[0].locate()))

class UtHistoric(TestCase):

    def setUp(self):
        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'france',
            glove = sessions.glove()
        )
        self.fp_prov2 = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'caledonie',
            glove = sessions.glove()
        )

        self.fp_cont = dict(
            local='ICMSH[geometry::area]+[term].rDH'
        )

        self.std = SpectralGeometry(id='Current op', area='france', truncation=798)
        self.caledonie = SpectralGeometry(id='Current op', area='caledonie', resolution='08km00')
        self.frangp = SpectralGeometry(area='frangp')

        self.fp_historic1 = dict(
            kind = 'historic',
            geometry = self.frangp,
            origin = 'historic',
            model = 'arome',
            cutoff = 'production',
            date = Date(today().get_fmt_date("yyyymmdd")).add_delta("P18H",
                                                                    "yyyymmddhh"),
            term = 0
        )

        self.fp_historic2 = dict(
            kind = 'historic',
            geometry = self.caledonie,
            origin = 'historic',
            model = 'aladin',
            cutoff = 'production',
            date = Date(today().get_fmt_date("yyyymmdd")).add_delta("P12H",
                                                                    "yyyymmddhh"),
            term = 0
        )
        self.fp_historic3 = dict(
            kind = 'historic',
            geometry = self.frangp,
            origin = 'historic',
            model = 'arpege',
            cutoff = 'production',
            date = Date(today().get_fmt_date("yyyymmdd")).add_delta("P18H",
                                                                    "yyyymmddhh"),
            term = 0
        )

    def test_ctlg1(self):
        historic = self.fp_historic1
        ctlg = resources.catalog()
        res = ctlg.findbest(historic)
        self.assertTrue(res.kind, 'historic')

        historic = self.fp_historic2
        res = ctlg.findbest(historic)
        self.assertTrue(res.kind, 'historic')

        historic = self.fp_historic3
        res = ctlg.findbest(historic)
        self.assertTrue(res.kind, 'historic')

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
            '/ch/mxpt/mxpt001/arome/france/oper/data/fic_day/ICMSHAROM+0000.rDH'
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
            '/ch/mxpt/mxpt001/aladin/caledonie/oper/data/fic_day/ICMSHALAD+0000.rPM'
        )
        #uniquement sur machine oper (pas de phasage)
        #self.assertTrue(os.stat(rl[0].locate()))

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
            '/ch/mxpt/mxpt001/arpege/france/oper/data/fic_day/ICMSHARPE+0000.rDH'
        )
        self.assertTrue(os.stat(rl[0].locate()))

class UtVarbc(TestCase):

    def setUp(self):
        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'reunion',
            glove = sessions.glove()
        )

        self.fp_prov2 = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'france',
            glove = sessions.glove()
        )


        self.fp_cont = dict(
            local='VARBC.cycle_alad.rDH'
        )

        self.fp_varbc1 = dict(
            kind = 'varbc',
            cutoff = 'production',
            model = 'aladin',
            date = Date(today().get_fmt_date("yyyymmdd")).add_delta("P12H",
                                                                    "yyyymmddhh")
        )

        self.fp_varbc2 = dict(
            kind = 'varbc',
            cutoff = 'production',
            model = 'arpege',
            date = Date(today().get_fmt_date("yyyymmdd")).add_delta("P12H",
                                                                    "yyyymmddhh")
        )

        self.fp_varbc3 = dict(
            kind = 'varbc',
            cutoff = 'production',
            model = 'arome',
            date = Date(today().get_fmt_date("yyyymmdd")).add_delta("P12H",
                                                                    "yyyymmddhh")
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

class UtErrgribvor(TestCase):

    def setUp(self):
        self.attrset = dict(kind='errgribvor', date = '2012021400', cutoff='production', namespace='[suite].archive.fr')
        self.std = SpectralGeometry(id='Current op', area='france', truncation=798)
        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'france',
            glove = sessions.glove()
        )

        self.fp_cont = dict(
            local='VARBC.cycle_alad.rDH'
        )

        self.fp_varbc1 = dict(
            kind = 'varbc',
            cutoff = 'production',
            model = 'aladin',
            date = Date(today().get_fmt_date("yyyymmdd")).add_delta("P12H",
                                                                    "yyyymmddhh")
        )



    def test_e1(self):
        rl = toolbox.rload(
            self.attrset,
            local='errgribvor+arpege+[term]',
            suite='oper',
            term='3',
            model='arpege',
            igakey='arpege'
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/arpege/oper/production/2012/02/14/r0/errgribvor')

    def test_e2(self):
        rl = toolbox.rload(
            self.attrset,
            local='errgribvor+aearp+[term].in',
            suite='oper',
            term='3',
            inout='in',
            model='aearp',
            cutoff='assim',
            igakey='aearp'
        )

        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/aearp/oper/assim/2012/02/14/r0/errgribvor.in')

    def test_e3(self):
        rl = toolbox.rload(
            self.attrset,
            local='errgribvor+aearp+[term].out',
            suite='oper',
            term='9',
            inout='out',
            model='aearp',
            cutoff='assim',
            igakey='aearp'
        )

        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/aearp/oper/assim/2012/02/14/r0/errgribvor_production.out')

    def test_e4(self):
        rl = toolbox.rload(
            self.attrset,
            local='errgribvor+aearp+[term].dsbscr.out',
            suite='oper',
            term='12',
            inout='out',
            model='aearp',
            cutoff='assim',
            igakey='aearp'
        )

        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(rl[0].location(), 'ftp://oper.archive.fr/aearp/oper/assim/2012/02/14/r0/errgribvor_production_dsbscr.out')

class UtElscf(TestCase):

    def setUp(self):
        self.caledonie = SpectralGeometry(id='Current op', area='caledonie', resolution='08km00')
        self.frangp = SpectralGeometry(id='Current op', area='frangp', resolution='02km50')
        self.mp1 = SpectralGeometry(id='Current op', area='testmp1')

        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'france',
            glove = sessions.glove()
        )

        self.fp_prov2 = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'caledonie',
            glove = sessions.glove()
        )

        self.fp_prov3 = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'testmp1',
            glove = sessions.glove()
        )

        self.fp_elscf1 = dict(
            kind = 'elscf',
            cutoff = 'production',
            model = 'arome',
            source = 'arpege',
            term = 12,
            geometry = self.frangp,
            date = Date(today().get_fmt_date("yyyymmdd")).add_delta("P12H", "yyyymmddhh")
        )

        self.fp_elscf2 = dict(
            kind = 'elscf',
            cutoff = 'assim',
            model = 'aladin',
            source = 'ifs',
            term = 2,
            geometry = self.caledonie,
            date = Date(today().get_fmt_date("yyyymmdd"))
        )

        self.fp_elscf3 = dict(
            kind = 'elscf',
            cutoff = 'production',
            model = 'aladin',
            source = 'arpege',
            term = 16,
            geometry = self.mp1,
            date = Date(today().get_fmt_date("yyyymmdd"))
        )


        self.fp_cont1 = dict(
            local='ELSCFAROMALBC[term].rPM'
        )


    def test_ctlg1(self):
        elscf = self.fp_elscf1
        ctlg = resources.catalog()
        res = ctlg.findbest(elscf)
        self.assertTrue(res.kind, 'elscf')

        elscf = self.fp_elscf2
        ctlg = resources.catalog()
        res = ctlg.findbest(elscf)
        self.assertTrue(res.kind, 'elscf')

        elscf = self.fp_elscf3
        ctlg = resources.catalog()
        res = ctlg.findbest(elscf)
        self.assertTrue(res.kind, 'elscf')

    def test_v1(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_cont1,
            self.fp_elscf1
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arome/france/oper/data/fic_day/ELSCFAROMALBC012.rPM'
        )
        self.assertEqual(
            rl[0].locate(),
            '/ch/mxpt/mxpt001/arome/france/oper/data/fic_day/ELSCFAROMALBC012.rPM'
        )
        #uniquement sur Nec oper
        #self.assertTrue(os.stat(rl[0].locate()))

    def test_v2(self):
        rl = toolbox.rload(
            self.fp_prov2,
            self.fp_cont1,
            self.fp_elscf2
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/aladin/caledonie/oper/data/fic_day/ELSCFALADALBC002.r00'
        )
        self.assertEqual(
            rl[0].locate(),
            '/ch/mxpt/mxpt001/aladin/caledonie/oper/data/fic_day/ELSCFALADALBC002.r00'
        )
        #uniquement sur Nec oper
        #self.assertTrue(os.stat(rl[0].locate()))

    def test_v3(self):
        rl = toolbox.rload(
            self.fp_prov3,
            self.fp_cont1,
            self.fp_elscf3
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/aladin/testmp1/oper/data/fic_day/ELSCFALADALBC016.rAM'
        )
        self.assertEqual(
            rl[0].locate(),
            '/ch/mxpt/mxpt001/aladin/testmp1/oper/data/fic_day/ELSCFALADALBC016.rAM'
        )
        #uniquement sur Nec oper
        #self.assertTrue(os.stat(rl[0].locate()))




class UtAnalysis(TestCase):

    def setUp(self):
        self.std = SpectralGeometry(id='Current op', area='france', truncation=798)
        self.caledonie = SpectralGeometry(id='Current op', area='caledonie', resolution='08km00')
        self.frangp = SpectralGeometry(id='Current op', area='frangp', resolution='02km50')

        self.fp_prov1 = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'france',
            glove = sessions.glove()
        )

        self.fp_prov2 = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'caledonie',
            glove = sessions.glove()
        )

        self.fp_analys1 = dict(
            kind = 'analysis',
            cutoff = 'production',
            model = 'arome',
            geometry = self.frangp,
            date = Date(today().get_fmt_date("yyyymmdd")).add_delta("P12H",
                                                                    "yyyymmddhh")
        )

        self.fp_analys2 = dict(
            kind = 'analysis',
            cutoff = 'assim',
            model = 'aladin',
            geometry = self.frangp,
            date = Date(today().get_fmt_date("yyyymmdd")).add_delta("P18H",
                                                                    "yyyymmddhh")
        )

        self.fp_analys3 = dict(
            kind = 'analysis',
            cutoff = 'assim',
            model = 'arpege',
            geometry = self.std,
            filling = 'surf',
            date = Date(today().get_fmt_date("yyyymmdd")).add_delta("P6H",
                                                                    "yyyymmddhh")
        )

        self.fp_cont1 = dict(
            local='ICMSHFCSTINIT'
        )

    def test_ctlg1(self):
        analys = self.fp_analys1
        ctlg = resources.catalog()
        res = ctlg.findbest(analys)
        self.assertTrue(res.kind, 'analysis')

        analys = self.fp_analys2
        ctlg = resources.catalog()
        res = ctlg.findbest(analys)
        self.assertTrue(res.kind, 'analysis')

        analys = self.fp_analys3
        ctlg = resources.catalog()
        res = ctlg.findbest(analys)
        self.assertTrue(res.kind, 'analysis')

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
            '/ch/mxpt/mxpt001/arome/france/oper/data/workdir/analyse/ICMSHAROMINIT.rPM'
        )
        #uniquement sur Nec oper
        #self.assertTrue(os.stat(rl[0].locate()))

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
            '/ch/mxpt/mxpt001/aladin/caledonie/oper/data/workdir/analyse/ICMSHALADINIT.r18'
        )
        #uniquement sur Nec oper
        #self.assertTrue(os.stat(rl[0].locate()))

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
            '/ch/mxpt/mxpt001/arpege/france/oper/data/workdir/analyse/ICMSHANALINIT_SURF.r06'
        )
        #uniquement sur Nec oper
        #self.assertTrue(os.stat(rl[0].locate()))

#class UtNamel(TestCase):
#
#    def setUp(self):
#
#        self.fp_prov1 = dict(
#            username = 'mxpt001',
#            suite = 'oper',
#            igakey = 'france',
#            glove = sessions.glove()
#        )
#
#        self.fp_prov2 = dict(
#            username = 'mxpt001',
#            suite = 'oper',
#            igakey = 'caledonie',
#            glove = sessions.glove()
#        )
#
#        self.fp_namel1 = dict(
#            kind = 'namelist',
#            model = 'arpege',
#        )
#
#        self.fp_namel2 = dict(
#            kind = 'namelist',
#            model = 'aladin',
#        )
#
#        self.fp_namel3 = dict(
#            kind = 'namelist',
#            model = 'aladin',
#        )
#
#       self.fp_cont1 = dict(
#            local='ICMSHFCSTINIT'
#        )
#
#    def test_ctlg1(self):
#        analys = self.fp_analys1
#        ctlg = resources.catalog()
#        res = ctlg.findbest(analys)
#        self.assertTrue(res.kind, 'analysis')
#
#        analys = self.fp_analys2
#        ctlg = resources.catalog()
#        res = ctlg.findbest(analys)
#        self.assertTrue(res.kind, 'analysis')
#
#        analys = self.fp_analys3
#        ctlg = resources.catalog()
#        res = ctlg.findbest(analys)
#        self.assertTrue(res.kind, 'analysis')
#
#    def test_v1(self):
#        rl = toolbox.rload(
#            self.fp_prov1,
#            self.fp_cont1,
#            self.fp_analys1
#        )
#        for rh in rl:
#            self.assertTrue(rh.complete)
#            print ' > ', rh.location()
#        self.assertEqual(
#            rl[0].location(),
#            'file://oper.inline.fr/arome/france/oper/data/workdir/analyse/ICMSHAROMINIT.rPM'
#        )
#        self.assertEqual(
#            rl[0].locate(),
#            '/ch/mxpt/mxpt001/arome/france/oper/data/workdir/analyse/ICMSHAROMINIT.rPM'
#        )
#        #uniquement sur Nec oper
#        #self.assertTrue(os.stat(rl[0].locate()))
#
#    def test_v2(self):
#        rl = toolbox.rload(
#            self.fp_prov2,
#            self.fp_cont1,
#            self.fp_analys2
#        )
#        for rh in rl:
#            self.assertTrue(rh.complete)
#            print ' > ', rh.location()
#        self.assertEqual(
#            rl[0].location(),
#            'file://oper.inline.fr/aladin/caledonie/oper/data/workdir/analyse/ICMSHALADINIT.r18'
#        )
#        self.assertEqual(
#            rl[0].locate(),
#            '/ch/mxpt/mxpt001/aladin/caledonie/oper/data/workdir/analyse/ICMSHALADINIT.r18'
#        )
#        #uniquement sur Nec oper
#        #self.assertTrue(os.stat(rl[0].locate()))
#
#    def test_v3(self):
#        rl = toolbox.rload(
#            self.fp_prov1,
#            self.fp_cont1,
#            self.fp_analys3
#        )
#        for rh in rl:
#            self.assertTrue(rh.complete)
#            print ' > ', rh.location()
#        self.assertEqual(
#            rl[0].location(),
#            'file://oper.inline.fr/arpege/france/oper/data/workdir/analyse/ICMSHANALINIT_SURF.r06'
#        )
#        self.assertEqual(
#            rl[0].locate(),
#            '/ch/mxpt/mxpt001/arpege/france/oper/data/workdir/analyse/ICMSHANALINIT_SURF.r06'
#        )
        #uniquement sur Nec oper
        #self.assertTrue(os.stat(rl[0].locate()))


if __name__ == '__main__':
#    for test in [ UtErrgribvor, UtObservations, UtBlackListDiap, UtBlackListLoc, UtObsmap, UtBcor ]:
    for test in [ UtMatFilter, UtRtCoef, UtRawFields, UtGeoFields, UtClimGlobal,
                UtClimLAM, UtClimBDAPLAM, UtClimBDAP, UtGridpoint, UtHistoric,
                 UtVarbc, UtElscf, UtAnalysis, UtRefdata ]:
    #for test in [ UtGridpoint ]:
        x = TextTestRunner(verbosity=2).run(TestLoader().loadTestsFromTestCase(test))
        if x.errors or x.failures:
            print "Something went wrong !"
            break
