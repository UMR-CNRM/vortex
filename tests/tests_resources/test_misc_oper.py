#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import footprints

try:
    from oper_test_config import *
except ImportError, e:
    print e
    raise


class UtMatFilter(TestCase):

    def setUp(self):
        self.std = SpectralGeometry(id='oper', area='france', truncation=798, stretching=2.4, lam=False)
        self.glob15 = GridGeometry(id='oper', area='GLOB15', resolution=1.5)
        self.fabec125 = GridGeometry(id='oper', area='FABEC0125', resolution=0.125)
        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = self.std.area,
        )
        self.fp_cont = dict(
            local='matrix.fil.[scope::area]'
        )
        self.fp_matfilter = dict(
            kind='matfilter',
            geometry = self.std,
            scope = self.glob15,
            model='arpege'
        )

        self.fp_matfilter2 = dict(
            kind='matfilter',
            geometry = self.std,
            scope = self.fabec125,
            model='arpege'
        )

    def tearDown(self):
        del self.std
        del self.glob15
        del self.fp_prov

    def test_ctlg(self):
        ctlg = footprints.proxy.resources

        mat_filter = self.fp_matfilter
        res = ctlg.find_best(mat_filter)
        self.assertTrue(res.kind, 'matfilter')

        mat_filter = self.fp_matfilter2
        res = ctlg.find_best(mat_filter)
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
            datadir + '/arpege/france/oper/const/autres/matrix.fil.GLOB15'
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
            datadir + '/arpege/france/oper/const/autres/matrix.fil.FABEC0125'
        )


if __name__ == '__main__':
    for test in [ UtMatFilter ]:
        x = TextTestRunner(verbosity=2).run(TestLoader().loadTestsFromTestCase(test))
        if x.errors or x.failures:
            print "Something went wrong !"
            break 


def get_test_class():
    return [ UtMatFilter ]
