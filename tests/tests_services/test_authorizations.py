#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from vortex.utilities import authorizations
from unittest import TestCase, main


class UtConstants(TestCase):

    def setUp(self):
        self.grpact = dict(
            root=dict(alarm=True, mail=True, sendbdap=False, routing=False),
            low=dict(alarm=False, mail=True, sendbdap=False, routing=False)
        )

        self.grpusr = dict(
            root=['mxpt001', 'root', 'adm', 'oper', 'olive'],
            low=['research', 'tourist']
        )

    def tearDown(self):
        del self.grpact
        del self.grpusr

    def test_constgrpactusr(self):
        grpact = authorizations.ConstGrpActConfigParser()
        dico_res = grpact.as_dict()
        for grp in dico_res:
            for act in dico_res[grp]:
                self.assertEquals(dico_res[grp][act], self.grpact[grp][act])
        grpusr = authorizations.ConstGrpUsrConfigParser()
        dico_res = grpusr.as_dict()
        for grp in dico_res:
            for usr in dico_res[grp]:
                self.assertTrue(usr in self.grpusr[grp])
        for grp in self.grpusr:
            for usr in self.grpusr[grp]:
                self.assertTrue(usr in dico_res[grp])

        print "test constgrpactusr OK"

    def test_group_hdl(self):
        gphdl = authorizations.GroupHandler()
        #('root', 'low')
        self.assertEquals(
            sorted(gphdl.get_grp_permis_fields()), 
            sorted(self.grpact.keys())
        )

        #('root', 'low')
        self.assertEquals(
            sorted(gphdl.get_grp_users_fields()), 
            sorted(self.grpusr.keys())
        )
        for grp in self.grpusr.keys():
            #root : ['oper', 'mxpt001', 'olive', 'adm', 'root']
            #low : ['tourist', 'research']
            self.assertEquals(
                sorted(gphdl.get_grp_users(grp)),
                sorted(self.grpusr[grp])
            )
            #root: {'mail': True, 'alarm': True, 'sendbdap': False, 'routing': False}
            #low:{'mail': True, 'alarm': False, 'sendbdap': False, 'routing': False}
            dico_res =  gphdl.get_grp_permis(grp)
            for act in dico_res:
                self.assertEquals(dico_res[act], self.grpact[grp][act])
        print "test_group_hdl ok"

if __name__ == '__main__':
    main()
