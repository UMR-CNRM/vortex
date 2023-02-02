import unittest

from bronx.compat import random


class TestCompatRandom(unittest.TestCase):

    _REFS = {
        0: dict(
            randrange=844,
            choice=3,
            shuffle=[5, 'a', 1, 'x', 6, 't', 'c', 3, 2],
            sample=[2, 'c', 'x'], ),
        1434979: dict(
            randrange=236,
            choice=6,
            shuffle=['c', 6, 't', 'a', 2, 'x', 5, 3, 1],
            sample=[1, 2, 'x'], ),
    }

    _ITEMS = ('a', 1, 'c', 2, 5, 6, 3, 't', 'x')

    def test_random_gen(self):
        rgen = random.Random()
        for seed, refs in self._REFS.items():
            rgen.seed(seed)
            self.assertEqual(rgen.randrange(1, 1000), refs['randrange'])
            self.assertEqual(rgen.choice(self._ITEMS), refs['choice'])
            self.assertEqual(rgen.sample(self._ITEMS, 3), refs['sample'])
            blop = list(self._ITEMS)
            rgen.shuffle(blop)
            self.assertListEqual(blop, refs['shuffle'])


if __name__ == "__main__":
    unittest.main()
