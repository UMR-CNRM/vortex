#!/bin/env python
# -*- coding:Utf-8 -*-

try:
    from oper_test_config import *
except ImportError, e:
    print e
    raise

cr = vortex.data.resources.catalog()
cr.track = True
t.warning()

class UtBackgroundErrStd(TestCase):
    
    def setUp(self):
        self.std = SpectralGeometry(id='Current op', truncation=224)
        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'aearp',
        )

        self.fp_prov2 = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'france'
        )

        self.fp_bckgerr1 = dict(
            kind = 'bgerrstd',
            cutoff = 'production',
            model = 'arpege',
            term = 9,
            native_fmt = 'grib',
            geometry = self.std,
            date = today() - Period('PT12H')
        )

        self.fp_bckgerr2 = dict(
            kind = 'bgerrstd',
            cutoff = 'assimilation',
            model = 'arpege',
            term = 3,
            native_fmt = 'grib',
            geometry = self.std,
            date = today() - Period('PT6H')
        )

        self.fp_bckgerr3 = dict(
            kind = 'bgerrstd',
            cutoff = 'assimilation',
            model = 'arpege',
            term = 12,
            native_fmt = 'grib',
            geometry = self.std,
            date = today() - Period('PT12H')
        )

        self.fp_bckgerr4 = dict(
            kind = 'bgerrstd',
            cutoff = 'assim',
            model = 'arpege',
            term = 6,
            native_fmt = 'grib',
            geometry = self.std,
            date = today() - Period('PT6H')
        )

        self.fp_cont = dict(local='errgribvor')
        self.fp_cont2 = dict(local='errgribscr')

    def test_ctlg(self):
        bckgerr = self.fp_bckgerr1
        ctlg = resources.catalog()
        res = ctlg.findbest(bckgerr)
        self.assertEqual(res.kind, 'bgerrstd')
        bckgerr = self.fp_bckgerr2
        res = ctlg.findbest(bckgerr)
        self.assertEqual(res.kind, 'bgerrstd')
        bckgerr = self.fp_bckgerr3
        res = ctlg.findbest(bckgerr)
        self.assertEqual(res.kind, 'bgerrstd')
        bckgerr = self.fp_bckgerr4
        res = ctlg.findbest(bckgerr)
        self.assertEqual(res.kind, 'bgerrstd')

    def test_r1(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_bckgerr1,
            self.fp_cont
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        name_ref = 'file://oper.inline.fr/arpege/aearp/oper/data/fic_day/errgribvor_production.'
        suffix_ref = today().compact()
        self.assertEqual(
            rl[0].location(), 
            name_ref + suffix_ref
        )

        name_ref = '/ch/mxpt/mxpt001/arpege/aearp/oper/data/fic_day/errgribvor_production.'
        self.assertEqual(
            rl[0].locate(),
            name_ref + suffix_ref
        )

    def test_r2(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_bckgerr2,
            self.fp_cont
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        name_ref = 'file://oper.inline.fr/arpege/aearp/oper/data/fic_day/errgribvor_assim.'
        suffix_ref = today().compact()
        self.assertEqual(
            rl[0].location(), 
            name_ref + suffix_ref
        )

        name_ref = '/ch/mxpt/mxpt001/arpege/aearp/oper/data/fic_day/errgribvor_assim.'
        self.assertEqual(
            rl[0].locate(),
            name_ref + suffix_ref
        )

    def test_r3(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_bckgerr3,
            self.fp_cont
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        name_ref ='file://oper.inline.fr/arpege/aearp/oper/data/fic_day/errgribvor_production_dsbscr.'
        suffix_ref = today().compact()
        self.assertEqual(
            rl[0].location(), 
            name_ref + suffix_ref
        )

        name_ref =\
'/ch/mxpt/mxpt001/arpege/aearp/oper/data/fic_day/errgribvor_production_dsbscr.'
        self.assertEqual(
            rl[0].locate(),
            name_ref + suffix_ref
        )

    def test_r4(self):
        rl = toolbox.rload(
            self.fp_prov2,
            self.fp_bckgerr4,
            self.fp_cont2
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
        name_ref =\
'file://oper.inline.fr/arpege/france/oper/data/fic_day/errgrib_scr.r0'
        self.assertEqual(
            rl[0].location(), 
            name_ref
        )

        name_ref =\
'/ch/mxpt/mxpt001/arpege/france/oper/data/fic_day/errgrib_scr.r0'
        self.assertEqual(
            rl[0].locate(),
            name_ref
        )

if __name__ == '__main__':
    for test in [ UtBackgroundErrStd ]:
        x = TextTestRunner(verbosity=2).run(TestLoader().loadTestsFromTestCase(test))
        if x.errors or x.failures:
            print "Something went wrong !"
            break 
        
def get_test_class():
    return [ UtBackgroundErrStd ]
