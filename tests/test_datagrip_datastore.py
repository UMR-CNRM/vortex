import tempfile
import shutil
import unittest

from bronx.datagrip.datastore import DataStore


class Parasite:

    def __init__(self, **kwargs):
        self.mydata = kwargs

    def datastore_inplace_overwrite(self, other):
        self.mydata = other.mydata


class TestDataStore(unittest.TestCase):

    def setUp(self):
        self.ds = DataStore()

    def test_datastore_basics(self):
        # Insert/Get sequence
        self.ds.insert('vortex_free_store', dict(storage='alose.meteo.fr'),
                       dict(scrontch=4), readonly=True)
        hst1 = self.ds.get('vortex_free_store', dict(storage='alose.meteo.fr'))
        self.assertEqual(hst1['scrontch'], 4)
        with self.assertRaises(RuntimeError):
            self.ds.insert('vortex_free_store', dict(storage='alose.meteo.fr'),
                           'anything', readonly=True)
        # Eroneous get
        with self.assertRaises(KeyError):
            self.ds.get('vortex_free_store', dict(storage='hendrix.meteo.fr'))
        # Get with automatic create
        hst2 = self.ds.get('vortex_free_store', dict(storage='hendrix.meteo.fr'),
                           default_payload=dict(blabla=9), readonly=True)
        hst2['akey'] = 1
        del hst2
        hst2 = self.ds.get('vortex_free_store', dict(storage='hendrix.meteo.fr'))
        self.assertEqual(hst2['akey'], 1)
        # Check
        self.assertTrue(self.ds.check('vortex_free_store', dict(storage='hendrix.meteo.fr')))
        self.assertFalse(self.ds.check('vortex_free_store', dict()))
        # Grep
        # Create two fake entries
        hst3 = self.ds.get('vortex_free_store', dict(storage='alose.meteo.fr', trick=True),
                           default_payload=dict(blop=5), readonly=True)
        self.ds.insert('some_stuff', dict(), dict(), readonly=True)
        # Let's grep it
        grep = self.ds.grep('vortex_free_store', dict())
        self.assertIn(hst1, grep.values())
        self.assertIn(hst2, grep.values())
        self.assertIn(hst3, grep.values())
        grep = self.ds.grep('vortex_free_store', dict(storage='hendrix.meteo.fr'))
        self.assertIn(hst2, grep.values())
        grep = self.ds.grep('vortex_free_store', dict(storage='alose.meteo.fr'))
        self.assertIn(hst1, grep.values())
        self.assertIn(hst3, grep.values())
        # Other stuff
        self.assertEqual(len(self.ds), 4)
        self.assertListEqual(sorted([k.kind for k in self.ds.keys()]),
                             ['some_stuff', ] + ['vortex_free_store', ] * 3)
        # Del
        with self.assertRaises(RuntimeError):
            self.ds.delete('vortex_free_store', dict(storage='alose.meteo.fr', trick=True))
        self.ds.delete('vortex_free_store', dict(storage='alose.meteo.fr', trick=True),
                       force=True)
        self.assertEqual(len(self.ds), 3)
        grep = self.ds.grep('vortex_free_store', dict(storage='alose.meteo.fr'))
        self.assertIn(hst1, grep.values())
        self.ds.grep_delete('vortex_free_store', dict(), force=True)
        self.assertEqual(len(self.ds), 1)
        grep = self.ds.grep('vortex_free_store', dict())
        self.assertEqual(len(grep), 0)

    def test_datastore_pickle(self):
        # Populate the DS
        self.ds.insert('vortex_free_store', dict(storage='alose.meteo.fr'),
                       dict(blabla=4), readonly=True)
        self.ds.insert('vortex_free_store', dict(storage='hendrix.meteo.fr'),
                       dict(blabla=9), readonly=False)
        self.ds.insert('parasite', dict(), Parasite(toto='is here'))
        # Pickle/Unpickle
        tmpdir = tempfile.mkdtemp(suffix='test_datastore_pickle')
        try:
            self.ds.pickle_dump(tmpdir + '/toto.pickled')
            ds2 = DataStore(default_picklefile=tmpdir + '/toto.pickled')
            ds2.insert('parasite', dict(), Parasite(toto='is here'))
            para_one = ds2.get('parasite', dict())
            ds2.pickle_load()
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)
        # Are all keys and dictionary equal ?
        self.assertSetEqual(set(self.ds.keys()), set(ds2.keys()))
        for k, v in self.ds:
            if isinstance(v, dict):
                self.assertDictEqual(v, ds2.get(k.kind, dict(storage=k.storage)))
        # Was the Parasite class modified inplace ?
        self.assertIs(ds2.get('parasite', dict()), para_one)
        # ReadOnly=False should be preserved
        t1 = ds2.get('vortex_free_store', dict(storage='hendrix.meteo.fr'))
        self.assertEqual(t1['blabla'], 9)
        ds2.insert('vortex_free_store', dict(storage='hendrix.meteo.fr'), dict(blabla=8))
        t1 = ds2.get('vortex_free_store', dict(storage='hendrix.meteo.fr'))
        self.assertEqual(t1['blabla'], 8)
        # The same goes for ReadOnly=True
        with self.assertRaises(RuntimeError):
            ds2.insert('parasite', dict(), Parasite(toto='is here'))


if __name__ == "__main__":
    unittest.main(verbosity=2)
