import json
import logging
import os

from unittest import TestCase, main

from common.data.modelstates import Analysis3D
from vortex.data import geometries
from vortex.tools.env import Environment

logging.basicConfig(level=logging.ERROR)


class UtEnv(TestCase):

    def setUp(self):
        self.res = Analysis3D(
            geometry=geometries.get(tag='global798'),
            model='arpege',
            date='201304231500',
            cutoff='prod',
            kind='analysis',
        )

    def test_basic(self):
        e = Environment()
        self.assertTrue('LOGNAME' in e)
        self.assertTrue('SHELL' in e)

        e['toto'] = 2
        self.assertEqual(e['toto'], 2)
        self.assertEqual(e['TOTO'], 2)
        self.assertEqual(e.native('TOTO'), '2')
        e.ToTo = 3
        self.assertEqual(e['toto'], 3)
        del e.toto
        self.assertNotIn('toto', e)

        e._surprise = 0
        with self.assertRaises(AttributeError):
            e._surprise

    def test_basicplus(self):
        e = Environment()
        # Default and Update
        e.default(dict(SHELL='machin'), TOTO=1)
        self.assertNotEqual(e.SHELL, 'machin')
        self.assertEqual(e.TOTO, 1)
        e.update(dict(SHELL='machin'), TOTO=2)
        self.assertEqual(e.SHELL, 'machin')
        self.assertEqual(e.TOTO, 2)
        # True/False
        for txt in ('1', 'ok', 'on', 'yes'):
            e.bool = txt
            self.assertTrue(e.true('bool'))
            self.assertFalse(e.false('bool'))
        for txt in ('0', 'no', None):
            e.bool = txt
            self.assertFalse(e.true('bool'))
            self.assertTrue(e.false('bool'))
        # Paths
        e.setgenericpath('thepath', 'machin')
        e.setgenericpath('thepath', 'bidule')
        e.setgenericpath('thepath', 'truc')
        self.assertEqual(e.thepath, 'machin:bidule:truc')
        e.setgenericpath('thepath', 'super', 0)
        self.assertEqual(e.thepath, 'super:machin:bidule:truc')
        e.rmgenericpath('thepath', 'bidule')
        self.assertEqual(e.thepath, 'super:machin:truc')
        e.setgenericpath('thepath', 'bidule', 2)
        self.assertEqual(e.thepath, 'super:machin:bidule:truc')
        e.setgenericpath('thepath', 'super')
        self.assertEqual(e.thepath, 'machin:bidule:truc:super')

    def test_activate(self):
        e = Environment()
        self.assertFalse(e.active())

        e.active(True)
        self.assertTrue(e.active())
        self.assertTrue(e.osbound())
        e['toto'] = 2
        self.assertEqual(os.environ['TOTO'], '2')
        e.active(False)
        e['toto'] = 42
        self.assertEqual(e.toto, 42)
        self.assertFalse('TOTO' in os.environ)

        e.active(True)
        e['bidon'] = 'bof'
        z = Environment(env=e)
        self.assertTrue(e.active())
        self.assertTrue(e.osbound())
        self.assertFalse(z.active())
        self.assertFalse(z.osbound())
        self.assertEqual(z['toto'], 42)

        z = Environment(env=e, active=True)
        self.assertTrue(z.active())
        self.assertTrue(z.osbound())
        self.assertFalse(e.active())
        self.assertFalse(e.osbound())
        self.assertEqual(os.environ['TOTO'], '42')
        z['bidon'] = 'coucou'
        self.assertEqual(e['bidon'], 'bof')

        # Cleanup !
        z.active(False)
        del z
        e.active(False)

        # Too much clones ?
        e = Environment(active=True)
        e1 = e.clone()
        e2 = e.clone()
        e1_1 = e1.clone()
        self.assertListEqual(e1.osstack(), e.osstack() + [e, ])
        self.assertListEqual(e1_1.osstack(), e.osstack() + [e, e1])
        e2.active(True)
        self.assertTrue(e2.osbound())
        self.assertFalse(e.osbound())
        e1_1.active(True)
        self.assertTrue(e1_1.osbound())
        self.assertFalse(e2.osbound())
        e1_1.active(False)
        # Here the focus goes to the prvious ancestor...
        self.assertTrue(e1.osbound())
        self.assertFalse(e1_1.osbound())

        # A very cool way of using clone clone
        with e1.clone() as newactive:
            newactive.scrontch = 2
            self.assertEqual(os.environ['SCRONTCH'], '2')
        self.assertNotIn('SCRONTCH', os.environ)
        self.assertTrue(e1.osbound())

        # Cleanup !
        e.active(False)
        del e

    def test_encoding(self):
        e = Environment(active=True)
        e['toto'] = list(range(1, 4))
        self.assertEqual(os.environ['TOTO'], '[1, 2, 3]')
        e['toto'] = dict(toto=2, fun='coucou')
        self.assertEqual(json.loads(os.environ['TOTO']),
                         dict(toto=2, fun='coucou'))
        e['toto'] = self.res
        self.assertEqual(
            json.loads(os.environ['TOTO']),
            json.loads(json.dumps(self.res.footprint_export())))
        e.active(False)

    def test_delta(self):
        e = Environment()
        e['toto'] = list(range(1, 4))
        e.delta(titi='truc')
        self.assertIn('toto', e)
        self.assertIn('titi', e)
        e.delta(toto='titi')
        self.assertEqual(e.TOTO, 'titi')
        self.assertEqual(e.TITI, 'truc')
        e.rewind()
        self.assertEqual(e.TOTO, list(range(1, 4)))
        self.assertEqual(e.TITI, 'truc')
        e.rewind()
        self.assertNotIn('titi', e)
        with self.assertRaises(RuntimeError):
            e.rewind()
        # With a context
        with e.delta_context(titi='truc'):
            self.assertIn('toto', e)
            self.assertIn('titi', e)
            e.delta(toto='titi')
            self.assertEqual(e.TOTO, 'titi')
            self.assertEqual(e.TITI, 'truc')
            e.rewind()
            self.assertEqual(e.TOTO, list(range(1, 4)))
            self.assertEqual(e.TITI, 'truc')
        self.assertNotIn('titi', e)
        with self.assertRaises(RuntimeError):
            e.rewind()


if __name__ == '__main__':
    main(verbosity=2)
