#!/bin/env python
# -*- coding:Utf-8 -*-


try:
    from oper_test_config import *
except ImportError, e:
    print e
    raise

#t.debug()



class UtMatFilter(TestCase):

    def setUp(self):
        self.std = SpectralGeometry(id='oper', area='france', truncation=798)
        self.glob15 = GridGeometry(id='oper', area='GLOB15', resolution=15)
        self.fabec125 = GridGeometry(id='oper', area='FABEC0125', resolution=12.5)
        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = self.std.area,
        )
        self.fp_cont = dict(
            local='matrix.fil.[scopedomain::area]'
        )
        self.fp_matfilter = dict(
            kind='matfilter',
            geometry = self.std,
            scopedomain = self.glob15,
            model='arpege'
        )

        self.fp_matfilter2 = dict(
            kind='matfilter',
            geometry = self.std,
            scopedomain = self.fabec125,
            model='arpege'
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

        mat_filter = self.fp_matfilter2
        ctlg = resources.catalog()
        res = ctlg.findbest(mat_filter)
        self.assertTrue(res.kind, 'matfilter')


    def test_rl(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_cont,
            self.fp_matfilter
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            
        self.assertEqual(rl[0].resource.kind, 'matfilter')
        self.assertEqual(rl[0].provider.realkind, 'iga')
        self.assertEqual(rl[0].container.realkind, 'file')
        self.assertEqual(
            rh.location(),
            'file://oper.inline.fr/arpege/france/oper/const/autres/matrix.fil.GLOB15'
        )
        self.assertEqual(
            rh.locate(),
            '/ch/mxpt/mxpt001/arpege/france/oper/const/autres/matrix.fil.GLOB15'
        )

    def test_r2(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_cont,
            self.fp_matfilter2,
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            
        self.assertEqual(rl[0].resource.kind, 'matfilter')
        self.assertEqual(rl[0].provider.realkind, 'iga')
        self.assertEqual(rl[0].container.realkind, 'file')
        self.assertEqual(
            rh.location(),
            'file://oper.inline.fr/arpege/france/oper/const/autres/matrix.fil.FABEC0125'
        )
        self.assertEqual(
            rh.locate(),
            '/ch/mxpt/mxpt001/arpege/france/oper/const/autres/matrix.fil.FABEC0125'
        )



if __name__ == '__main__':
    for test in [ UtMatFilter ]:
        x = TextTestRunner(verbosity=2).run(TestLoader().loadTestsFromTestCase(test))
        if x.errors or x.failures:
            print "Something went wrong !"
            break 

def get_test_class():
    return [ UtMatFilter ]
