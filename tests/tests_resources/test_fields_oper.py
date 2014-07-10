#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import footprints

try:
    from oper_test_config import *
except ImportError, e:
    print e
    raise

#t.debug()

class UtRawFields(TestCase):

    def setUp(self):
        toolbox.defaults(namespace='prod.inline.fr')
        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'france',
            vapp = 'arpege',
        )
        self.fp_prov2 = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'france',
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
            model = 'arpege'
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
        del self.fp_prov2
        del self.fp_cont_nesdis
        del self.fp_cont_ostia
        del self.fp_cont_seaice
        del self.fp_nesdis

    def test_ctlg(self):
        ctlg = footprints.proxy.resources

        nesdis = self.fp_nesdis
        res = ctlg.find_best(nesdis)

        self.assertTrue(res.kind, 'rawfields')

        ostia = self.fp_ostia
        res = ctlg.find_best(ostia)

        self.assertEqual(res.kind, 'rawfields')

        seaice = self.fp_seaice
        res = ctlg.find_best(seaice)

        self.assertTrue(res.kind, 'rawfields')

    def test_r1(self):
        rl = toolbox.rload(
            self.fp_nesdis,
            self.fp_cont_nesdis,
            self.fp_prov
        )
        for rh in rl:
            self.assertTrue(rh.complete)
        self.assertEqual(
            rl[0].location(), 
            'file://oper.inline.fr/arpege/france/oper/data/fic_day/sst.nesdis.bdap'
        )

        self.assertEqual(
            rl[0].locate(),
            datadir + '/arpege/france/oper/data/fic_day/sst.nesdis.bdap'
        )
        #uniquement sur kumo (sst.nesdis.bdap non phase)
        if t.env['HOSTNAME'] == 'kumo':
            self.assertTrue(os.stat(rl[0].locate()))

        rl = toolbox.rload(
            self.fp_ostia,
            self.fp_cont_ostia,
            self.fp_prov
        )
        for rh in rl:
            self.assertTrue(rh.complete)

        self.assertEqual(
            rl[0].location(), 
            'file://oper.inline.fr/arpege/france/oper/data/fic_day/sst.ostia')

        self.assertEqual(
            rl[0].locate(),
            datadir + '/arpege/france/oper/data/fic_day/sst.ostia'
        )
        #uniquement sur kumo (sst.ostia non phase)
        if t.env['HOSTNAME'] == 'kumo':
            self.assertTrue(os.stat(rl[0].locate()))

        rl = toolbox.rload(
            self.fp_ostia,
            self.fp_cont_ostia,
            self.fp_prov2
        )
        for rh in rl:
            self.assertTrue(rh.complete)

        self.assertEqual(
            rl[0].location(), 
            'ftp://prod.inline.fr/modele/oper/arpege/RW/sst.ostia')

        #self.assertEqual(
        #    rh.locate(),
        #    '/SOPRANO/modele/oper/arpege/RW/sst.ostia'
        #)
        #uniquement sur kumo (sst.ostia non phase)
        if t.env['HOSTNAME'] == 'kumo':
            self.assertTrue(os.stat(rl[0].locate()))


        rl = toolbox.rload(
            self.fp_seaice,
            self.fp_prov2,
            self.fp_cont_seaice
        )

        for rh in rl:
            self.assertTrue(rh.complete)

        self.assertEqual(
            rl[0].location(),
            'ftp://prod.inline.fr/modele/oper/arpege/RW/SSMI.AM'
        )
        #ftp problem when trying to locate the resource
        #self.assertEqual(
        #    rh.locate(),
        #    '/SOPRANO/modele/oper/arpege/RW/SSMI.AM'
        #)


class UtGeoFields(TestCase):

    def setUp(self):
        self.std = SpectralGeometry(id='Current op', area='france', truncation=798)
        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = '[geometry::area]',
            vapp = 'arpege'
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
        )

        self.fp_contseaice = dict(
            local='ICMSHANALSEAICE'
        )
        self.fp_seaice = dict(
            kind='geofields',
            fields = 'seaice',
            date = today(),
            cutoff='assim',
            geometry = self.std,
        )


    def tearDown(self):
        """docstring for tearDown"""
        del self.fp_prov
        del self.fp_cont
        del self.fp_contseaice
        del self.fp_sst
        del self.fp_seaice
        del self.std

    def test_ctlg(self):
        ctlg = footprints.proxy.resources

        sstgeofields = self.fp_sst
        res = ctlg.find_best(sstgeofields)
        self.assertTrue(res.kind, 'geofields')

        icegeofields = self.fp_seaice
        res = ctlg.find_best(icegeofields)
        self.assertTrue(res.kind, 'geofields')

    def test_g1(self):
        rl = toolbox.rload(
            self.fp_sst,
            self.fp_prov,
            self.fp_cont
        )

        for rh in rl:
            self.assertTrue(rh.complete)

        self.assertEqual(
            rl[0].location(), 
            'file://oper.inline.fr/arpege/france/oper/data/fic_day/ICMSHANALSST'
        )
        self.assertEqual(
            rl[0].locate(), 
            datadir + '/arpege/france/oper/data/fic_day/ICMSHANALSST'
        )
        self.assertTrue(os.stat(rl[0].locate()))

    def test_g2(self):
        rl = toolbox.rload(
            self.fp_seaice,
            self.fp_prov,
            self.fp_contseaice
        )

        for rh in rl:
            self.assertTrue(rh.complete)

        self.assertEqual(
            rl[0].location(), 
            'file://oper.inline.fr/arpege/france/oper/data/fic_day/ICMSHANALSEAICE'
        )
        self.assertEqual(
            rl[0].locate(), 
            datadir + '/arpege/france/oper/data/fic_day/ICMSHANALSEAICE'
        )
        self.assertTrue(os.stat(rl[0].locate()))


if __name__ == '__main__':
    for test in [ UtRawFields, UtGeoFields ]:
        x = TextTestRunner(verbosity=2).run(TestLoader().loadTestsFromTestCase(test))
        if x.errors or x.failures:
            print "Something went wrong !"
            break 

def get_test_class():
        return [ UtRawFields, UtGeoFields ]
