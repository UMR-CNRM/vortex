import threading
import unittest

from bronx.compat import functools as py_functools


class CachedCostItem:
    _cost = 1

    def __init__(self):
        self.lock = threading.RLock()

    @py_functools.cached_property
    def cost(self):
        """The cost of the item."""
        with self.lock:
            self._cost += 1
        return self._cost


class OptionallyCachedCostItem:
    _cost = 1

    def get_cost(self):
        """The cost of the item."""
        self._cost += 1
        return self._cost

    cached_cost = py_functools.cached_property(get_cost)


class TestCachedProperty(unittest.TestCase):

    def test_cached(self):
        item = CachedCostItem()
        self.assertEqual(item.cost, 2)
        self.assertEqual(item.cost, 2)  # not 3

    def test_cached_attribute_name_differs_from_func_name(self):
        item = OptionallyCachedCostItem()
        self.assertEqual(item.get_cost(), 2)
        self.assertEqual(item.cached_cost, 3)
        self.assertEqual(item.get_cost(), 4)
        self.assertEqual(item.cached_cost, 3)

    def test_access_from_class(self):
        self.assertIsInstance(CachedCostItem.cost, py_functools.cached_property)

    def test_doc(self):
        self.assertEqual(CachedCostItem.cost.__doc__, "The cost of the item.")


if __name__ == "__main__":
    unittest.main()
