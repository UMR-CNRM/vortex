#!/bin/env python
# -*- coding:Utf-8 -*-


try:
    from oper_test_config import *
except ImportError, e:
    print e
    raise

#t.debug()



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
        )
        self.fp_cont = dict(
            local='const.clim.[geometry::area]'
        )
        self.fp_climbdap_1 = dict(
            kind='clim_bdap',
            month = today().month,
            geometry = self.glob15,
            model = 'arpege'
        )
        self.fp_climbdap_2 = dict(
            kind='clim_bdap',
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



if __name__ == '__main__':
    for test in [ UtClimGlobal, UtClimLAM, UtClimBDAPLAM, UtClimBDAP ]:
        x = TextTestRunner(verbosity=2).run(TestLoader().loadTestsFromTestCase(test))
        if x.errors or x.failures:
            print "Something went wrong !"
            break 

def get_test_class():
        return [ UtClimGlobal, UtClimBDAP, UtClimGlobal, UtClimLAM ]
