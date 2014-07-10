#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import footprints

try:
    from oper_test_config import *
except ImportError, e:
    print e
    raise

#t.debug()

class UtNamelist(TestCase):

    def setUp(self):

        self.fp_prov1 = dict(
            username = 'mxpt001',
            suite = 'oper',
            igakey = 'france',
        )
        self.liste_fp_namel = []
        self.namelistes = [
            'namel_analyse_sst', 'namel_ext_sst', 'namelistcans1',
            'namelistcans2', 'namelist_diag_sigmab', 'namelistfc',
            'namelistfcp', 'namelisth2l107', 'namelisth2l224', 'namelisth2l323',
            'namelistiasi314', 'namelistl2h', 'namelistmin1311',
            'namelistmin1312', 'namelistmin1312_basse',
            'namelistmin1312_hausse', 'namelistscreen', 'namelistscreen_basse',
            'namelistscreen_hausse', 'namelisttraj1', 'namelisttraj2'
        ]
        for name in self.namelistes:
            self.liste_fp_namel.append(
                dict(
                    kind = 'namelist',
                    model = 'arpege',
                    source = name
                )
            )

        self.fp_cont1 = dict(
            local='namelist_alpha'
        )

        self.fp_namsel1 = dict(
            kind = 'namselect',
            term = 6,
            model = 'arpege',
            source = '[helper::xxtselect]',
            helper = IgaHelperSelect()
        )
        self.fp_namsel = dict(
            kind = 'namselect',
            term = (6,12,18),
            model = 'arpege',
            source = '[helper::xxtselect]',
            helper = IgaHelperSelect()
        )

        self.fp_cont2 = dict(
            local = '[helper::xxt]',
            helper = IgaHelperSelect()
        )

        self.fp_namsel3 = dict(
            kind = 'namselect',
            term = (20,22,36),
            model = 'arome',
            source = '[helper::xxtselect]',
            helper = IgaHelperSelect()
        )

        self.fp_cont2 = dict(
            local = '[helper::xxt]',
            helper = IgaHelperSelect()
        )


    def test_ctlg1(self):
        ctlg = footprints.proxy.resources
        for fp in self.liste_fp_namel:
            res = ctlg.find_best(fp)
            self.assertTrue(res.kind, 'namelist')

    def test_v1(self):
        cpt = 0
        for fp in self.liste_fp_namel:
            rl = toolbox.rload(
                self.fp_prov1,
                self.fp_cont1,
                fp
            )
            for rh in rl:
                self.assertTrue(rh.complete)
                print ' > ', rh.location()
            self.assertEqual(
                rl[0].location(), 
                'file://oper.inline.fr/arpege/france/oper/namel/' + self.namelistes[cpt]
            )
            self.assertEqual(
                rl[0].locate(),
                datadir + '/arpege/france/oper/namel/' + self.namelistes[cpt]
            )
            cpt += 1
            #uniquement sur Nec oper
            if t.env['HOSTNAME'] == 'kumo':
                self.assertTrue(os.stat(rl[0].locate()))

    def test_ctlg2(self):
        ctlg = footprints.proxy.resources
        res = ctlg.find_best(self.fp_namsel1)
        self.assertTrue(res.kind, 'namselect')

    def test_v2(self):
        rl = toolbox.rload(
            self.fp_prov1,
            self.fp_cont2,
            self.fp_namsel
        )
        ref_name = ['select5_p6', 'select5_p6', 'select5_p6b']
        ref_xxt = ['xxt00000600', 'xxt00001200', 'xxt00001800']
        cpt = 0
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
            self.assertEqual(
                rh.location(), 
                'file://oper.inline.fr/arpege/france/oper/namel/'\
+ref_name[cpt]
            )
            self.assertEqual(
                rh.locate(),
                datadir + '/arpege/france/oper/namel/'\
+ref_name[cpt]
            )
            self.assertEqual(
                rh.container.file,
                ref_xxt[cpt]
            )
            cpt += 1

    def test_v3(self):
        """docstring for test_v3"""
        rl = toolbox.rload(
            self.fp_prov1,
            self.fp_cont2,
            self.fp_namsel3
        )
        ref_name = ['select_frangp_fp', 'select_frangp_fp', 'select_frangp_fp']
        ref_xxt = ['xxt00002000', 'xxt00002200', 'xxt00011200']
        cpt = 0
        for rh in rl:
            self.assertTrue(rh.complete)
            print ' > ', rh.location()
            self.assertEqual(
                rh.location(), 
                'file://oper.inline.fr/arome/france/oper/namel/'\
+ref_name[cpt]
            )
            self.assertEqual(
                rh.locate(),
                datadir + '/arome/france/oper/namel/'\
+ref_name[cpt]
            )
            self.assertEqual(
                rh.container.file,
                ref_xxt[cpt]
            )
            cpt += 1


if __name__ == '__main__':
    for test in [ UtNamelist ]:
        x = TextTestRunner(verbosity=2).run(TestLoader().loadTestsFromTestCase(test))
        if x.errors or x.failures:
            print "Something went wrong !"
            break 

def get_test_class():
    return [ UtNamelist, ]
