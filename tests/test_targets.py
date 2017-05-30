
import os
import unittest

import footprints as fp

import vortex
from vortex import sessions

DATAPATHTEST = os.path.join(os.path.dirname(__file__), 'data')


class TestTargetsResearch(unittest.TestCase):

    def setUp(self):
        self.testconf = os.path.join(DATAPATHTEST, 'target-test.ini')
        self.tg = fp.proxy.target(hostname='unittestlogin001',
                                  inetname='unittest',
                                  sysname='Linux',
                                  inifile=self.testconf)

    def test_target_config(self):
        self.assertTrue(self.tg.is_anonymous)
        self.assertEqual(self.tg.get('stores:storage'),
                         'hendrix.meteo.fr')
        self.assertEqual(self.tg.get('stores:fakekey1'),
                         'tourist')
        self.assertSetEqual(set(self.tg.options('stores')),
                            set(('storage', 'fakekey1')))

    def test_target_nodes(self):
        self.assertListEqual(self.tg.loginnodes,
                             ['unittestlogin000', 'unittestlogin001', 'unittestlogin002', ])
        self.assertListEqual(self.tg.loginproxies, self.tg.loginnodes)
        self.assertListEqual(self.tg.totonodes, [])
        self.assertListEqual(self.tg.totoproxies, [])
        self.assertListEqual(self.tg.networknodes,
                             ['unittestlogin000', 'unittestlogin001', 'unittestlogin002',
                              'unittesttransfert0', 'unittesttransfert1', ])
        self.assertListEqual(self.tg.networkproxies, self.tg.loginnodes)
        # Aliases
        self.assertListEqual(self.tg.pizzanodes, self.tg.networknodes)
        self.assertListEqual(self.tg.coffeenodes, self.tg.networknodes)
        self.assertListEqual(self.tg.pizzaproxies, self.tg.networkproxies)
        self.assertListEqual(self.tg.coffeeproxies, self.tg.networkproxies)
        # Interrogative form...
        self.assertTrue(self.tg.isloginnode)
        self.assertTrue(self.tg.istotonode)
        self.assertTrue(self.tg.isnetworknode)
        self.assertFalse(self.tg.istransfertnode)


class TestTargetsOp(unittest.TestCase):

    def setUp(self):
        self.testconf = os.path.join(DATAPATHTEST, 'target-test.ini')
        self.tg = fp.proxy.target(hostname='unittestlogin001',
                                  inetname='unittest',
                                  sysname='Linux',
                                  inifile=self.testconf)
        self._oldsession = sessions.current()
        gl = sessions.getglove(profile='oper', user='mxpt001')
        ns = sessions.get(tag='targes_test_view',
                          topenv=vortex.rootenv, glove=gl)
        ns.activate()

    def tearDown(self):
        self._oldsession.activate()

    def test_target_config(self):
        self.assertTrue(self.tg.is_anonymous)
        self.assertEqual(self.tg.get('stores:storage'),
                         'hendrixg2.meteo.fr')
        self.assertEqual(self.tg.get('stores:fakekey1'),
                         '1')
        self.assertSetEqual(set(self.tg.options('stores')),
                            set(('storage', 'fakekey1', 'fakekey2')))

    def test_target_nodes(self):
        self.assertListEqual(self.tg.loginproxies, ['unittestoper-int'])
        self.assertListEqual(self.tg.totonodes, [])
        self.assertListEqual(self.tg.totoproxies, [])
        self.assertListEqual(self.tg.networkproxies, ['unittestoper-int'])
        # Interrogative form...
        self.assertTrue(self.tg.isloginnode)
        self.assertTrue(self.tg.istotonode)
        self.assertTrue(self.tg.isnetworknode)
        self.assertFalse(self.tg.istransfertnode)

if __name__ == "__main__":
    unittest.main(verbosity=2)
