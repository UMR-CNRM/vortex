import pickle
from unittest import TestCase, main
from weakref import WeakSet

from bronx.stdtypes.catalog import Catalog


class Foo:
    # noinspection PyUnusedLocal
    def __init__(self, *u_args, **kw):
        self.__dict__.update(kw)


# Base class for catalogs like objects

# noinspection PyPropertyAccess
class utCatalog(TestCase):

    def setUp(self):
        self.o1 = Foo(inside=['a', 'b'])
        self.o2 = Foo(inside=['x', 'y'])

    def test_catalog_std(self):
        rv = Catalog.fullname()
        self.assertEqual(rv, 'bronx.stdtypes.catalog.Catalog')

        rv = Catalog(extra=2)
        self.assertIsInstance(rv, Catalog)
        self.assertIsInstance(rv._items, set)
        self.assertFalse(rv.weak)
        self.assertEqual(len(rv), 0)
        self.assertFalse(rv.filled)
        self.assertEqual(rv.extra, 2)

        with self.assertRaises(AttributeError):
            rv.filled = True

        rv.clear()
        self.assertIsInstance(rv._items, set)
        self.assertFalse(rv.filled)

        rv = Catalog(items=[self.o1])
        self.assertIsInstance(rv._items, set)
        self.assertEqual(len(rv), 1)
        self.assertTrue(rv.filled)
        self.assertListEqual(rv(), [self.o1])
        self.assertIn(self.o1, rv)

        rv.clear()
        self.assertIsInstance(rv._items, set)
        self.assertFalse(rv.filled)

        rv.add(self.o1)
        self.assertTrue(rv.filled)
        self.assertListEqual(rv(), [self.o1])

        rv.add(2)
        self.assertTrue(rv.filled)
        self.assertSetEqual(set(rv()), {2, self.o1})

        rv.discard(5)
        self.assertTrue(rv.filled)
        self.assertSetEqual(set(rv()), {2, self.o1})

        rv.discard(2)
        self.assertTrue(rv.filled)
        self.assertListEqual(rv(), [self.o1])

        rv.discard(self.o1)
        self.assertFalse(rv.filled)

    def test_catalog_weak(self):
        rv = Catalog(weak=True)
        self.assertIsInstance(rv, Catalog)
        self.assertIsInstance(rv._items, WeakSet)
        self.assertTrue(rv.weak)
        self.assertEqual(len(rv), 0)
        self.assertFalse(rv.filled)

        # could not create a weak ref to 'int' object
        with self.assertRaises(TypeError):
            rv.add(2)

        # could not create a weak ref to 'str' object
        with self.assertRaises(TypeError):
            rv.add('foo')

        rv.clear()
        self.assertIsInstance(rv._items, WeakSet)
        self.assertFalse(rv.filled)
        self.assertTrue(rv.weak)

        rv = Catalog(items=[self.o1], weak=True)
        self.assertIsInstance(rv._items, WeakSet)
        self.assertEqual(len(rv), 1)
        self.assertTrue(rv.weak)
        self.assertTrue(rv.filled)
        self.assertListEqual(rv(), [self.o1])

        rv.clear()
        self.assertIsInstance(rv._items, WeakSet)
        self.assertTrue(rv.weak)
        self.assertFalse(rv.filled)

        rv.add(self.o1)
        self.assertTrue(rv.filled)
        self.assertEqual(rv(), [self.o1])

        rv.add(self.o2)
        self.assertTrue(rv.filled)
        self.assertEqual(len(rv), 2)
        self.assertIn(self.o1, rv)
        self.assertIn(self.o2, rv)

        rv.discard(self.o2)
        self.assertTrue(rv.filled)
        self.assertListEqual(rv(), [self.o1])

        o1l = rv.pop()
        self.assertIs(o1l, self.o1)
        self.assertFalse(rv.filled)
        self.assertTrue(rv.weak)

    def test_catalog_iter(self):
        rv = Catalog(items=[self.o1, self.o2], weak=False)
        for x in rv:
            self.assertIsInstance(x, Foo)

    def test_catalog_freeze(self):
        rv = Catalog(items=[self.o1, self.o2], weak=False)
        self.assertIsInstance(rv._items, set)
        self.assertEqual(len(rv), 2)
        self.assertFalse(rv.weak)

        db = pickle.loads(pickle.dumps(rv))
        self.assertIsInstance(db, Catalog)
        self.assertIsInstance(db._items, set)
        self.assertEqual(len(db), 2)
        self.assertFalse(db.weak)

        rv = Catalog(items=[self.o1, self.o2], weak=True)
        self.assertIsInstance(rv._items, WeakSet)
        self.assertEqual(len(rv), 2)
        self.assertTrue(rv.weak)

        db = pickle.loads(pickle.dumps(rv))
        self.assertIsInstance(db, Catalog)
        self.assertIsInstance(db._items, WeakSet)
        self.assertEqual(len(db), 0)
        self.assertTrue(db.weak)


if __name__ == '__main__':
    main(verbosity=2)
