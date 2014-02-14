#!/bin/env python
# -*- coding:Utf-8 -*-

import footprints

try:
    from oper_test_config import *
except ImportError, e:
    print e
    raise

class UtElscf(TestCase):

    def setUp(self):
        self.caledonie = SpectralGeometry(id='Current op', area='caledonie', resolution=8.0)
        self.frangp = SpectralGeometry(id='Current op', area='frangp', resolution=2.50)
        self.mp1 = SpectralGeometry(id='Current op', area='testmp1')

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

        self.fp_prov3 = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'testmp1',
        )

        self.fp_elscf1 = dict(
            kind = 'elscf',
            cutoff = 'production',
            model = 'arome',
            source = 'arpege',
            term = 12,
            geometry = self.frangp,
            date = today() + Period('PT12H')
        )

        self.fp_elscf2 = dict(
            kind = 'elscf',
            cutoff = 'assim',
            model = 'aladin',
            source = 'ifs',
            term = 2,
            geometry = self.caledonie,
            date = today().ymd
        )

        self.fp_elscf3 = dict(
            kind = 'elscf',
            cutoff = 'production',
            model = 'aladin',
            source = 'arpege',
            term = 16,
            geometry = self.mp1,
            date = today().ymd
        )


        self.fp_cont1 = dict(
            local='ELSCFAROMALBC[term::fmth].rPM'
        )


    def test_ctlg1(self):
        ctlg = footprints.proxy.resources

        elscf = self.fp_elscf1
        res = ctlg.find_best(elscf)
        self.assertEqual(res.kind, 'boundary')

        elscf = self.fp_elscf2
        res = ctlg.find_best(elscf)
        self.assertEqual(res.kind, 'boundary')

        elscf = self.fp_elscf3
        res = ctlg.find_best(elscf)
        self.assertEqual(res.kind, 'boundary')
 
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
            datadir + '/arome/france/oper/data/fic_day/ELSCFAROMALBC012.rPM'
        )
        #uniquement sur Nec oper
        if t.env['HOSTNAME'] == 'kumo':
            self.assertTrue(os.stat(rl[0].locate()))

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
            datadir + '/aladin/caledonie/oper/data/fic_day/ELSCFALADALBC002.r00'
        )
        #uniquement sur Nec oper
        if t.env['HOSTNAME'] == 'kumo':
            self.assertTrue(os.stat(rl[0].locate()))

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
            datadir + '/aladin/testmp1/oper/data/fic_day/ELSCFALADALBC016.rAM'
        )
        #uniquement sur Nec oper
        if t.env['HOSTNAME'] == 'kumo':
            self.assertTrue(os.stat(rl[0].locate()))


if __name__ == '__main__':
    for test in [ UtElscf ]:
        x = TextTestRunner(verbosity=2).run(TestLoader().loadTestsFromTestCase(test))
        if x.errors or x.failures:
            print "Something went wrong !"
            break 

def get_test_class():
    return [ UtElscf ]

