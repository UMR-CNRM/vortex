#!/bin/env python
# -*- coding: utf-8 -*-


try:
    from oper_test_config import *
except ImportError, e:
    print e
    raise

#t.debug()


class UtRtCoef(TestCase):

    def setUp(self):
        self.std = SpectralGeometry(id='oper', area='france', truncation=798)
        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = self.std.area,
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
        ctlg = footprints.proxy.resources
        res = ctlg.findbest(self.fp_rtcoef)

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
        self.assertEqual(rl[0].provider.realkind, 'iga')
        self.assertEqual(rl[0].container.realkind, 'file')
        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arpege/france/oper/const/autres/rtcoef.tar'
        )
        self.assertEqual(
            rl[0].locate(),
            '/ch/mxpt/mxpt001/arpege/france/oper/const/autres/rtcoef.tar'
        )
        if t.env['HOSTNAME'] == 'kumo':
            self.assertTrue(os.stat(rl[0].locate()))

class UtBcor(TestCase):

    def setUp(self):
        self.fp_prov = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'france',
        )
        self.fp_cont = dict(
            local='bcor_[satbias].dat'
        )
        self.fp_bcor = dict(
            kind='bcor',
            model='arpege',
            date=today(),
            cutoff='production',
            satbias=['noaa','ssmi','mtop']
        )

    def tearDown(self):
        """docstring for tearDown"""
        del self.fp_bcor

    def test_ctlg(self):
        ctlg = footprints.proxy.resources
        for cat in ['noaa','ssmi','mtop']:
            bcor = self.fp_bcor
            bcor['satbias'] = cat
            res = ctlg.findbest(bcor)
            self.assertTrue(res.kind, 'rtcoef')

    def test_r1(self):
        rl = toolbox.rload(
            self.fp_prov,
            self.fp_bcor,
            self.fp_cont
        )
        for rh in rl:
            self.assertTrue(rh.complete)
            self.assertEqual(rh.resource.kind, 'bcor')
            self.assertEqual(rh.provider.realkind, 'iga')
            self.assertEqual(rh.container.realkind, 'file')

        self.assertEqual(
            rl[0].location(),
            'file://oper.inline.fr/arpege/france/oper/const/autres/bcor_noaa.dat'
        )
        self.assertEqual(
            rl[0].locate(),
            '/ch/mxpt/mxpt001/arpege/france/oper/const/autres/bcor_noaa.dat'
        )

        self.assertEqual(
            rl[1].location(),
            'file://oper.inline.fr/arpege/france/oper/const/autres/bcor_ssmi.dat'
        )
        self.assertEqual(
            rl[1].locate(),
            '/ch/mxpt/mxpt001/arpege/france/oper/const/autres/bcor_ssmi.dat'
        )

        self.assertEqual(
            rl[2].location(),
            'file://oper.inline.fr/arpege/france/oper/const/autres/bcor_mtop.dat'
        )
        self.assertEqual(
            rl[2].locate(),
            '/ch/mxpt/mxpt001/arpege/france/oper/const/autres/bcor_mtop.dat'
        )

if __name__ == '__main__':
    for test in [ UtRtCoef, UtBcor ]:
        x = TextTestRunner(verbosity=2).run(TestLoader().loadTestsFromTestCase(test))
        if x.errors or x.failures:
            print "Something went wrong !"
            break

def get_test_class():
        return [ UtRtCoef, UtBcor ]

