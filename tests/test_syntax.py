import unittest

from bronx.syntax import dictmerge, mktuple


class Foo:
    pass


class utDictMerge(unittest.TestCase):

    def test_dictmerge_orthogonal(self):
        rv = dictmerge(
            dict(a=2, c='foo'),
            dict(b=7),
        )
        self.assertDictEqual(rv, dict(a=2, b=7, c='foo'))

    def test_dictmerge_overlap1(self):
        rv = dictmerge(
            dict(a=2, c='foo'),
            dict(b=7, c='updatedfoo'),
        )
        self.assertDictEqual(rv, dict(a=2, b=7, c='updatedfoo'))

    def test_dictmerge_overlap2(self):
        rv = dictmerge(
            dict(a=2, c='foo'),
            dict(b=7, c=dict(val='updatedfoo')),
        )
        self.assertDictEqual(rv, dict(a=2, b=7, c=dict(val='updatedfoo')))

    def test_dictmerge_recursive(self):
        rv = dictmerge(
            dict(a=2, c=dict(val='foo', other=dict(arg='hop'), bonus=1)),
            dict(b=7, c=dict(val='updatedfoo', other=dict(arg='hip', foo=False))),
        )
        self.assertDictEqual(rv, dict(a=2, b=7, c=dict(val='updatedfoo', other=dict(arg='hip', foo=False), bonus=1)))


class utMktuple(unittest.TestCase):

    def test_mktuple_direct(self):
        self.assertTupleEqual(mktuple([1, 2, 3]), (1, 2, 3))
        self.assertTupleEqual(mktuple((1, 2, 3)), (1, 2, 3))
        self.assertSetEqual(set(mktuple({1, 2, 3})), {1, 2, 3})

    def test_mktuple_weird(self):
        thefoo = Foo()
        self.assertTupleEqual(mktuple(thefoo), (thefoo, ))


if __name__ == '__main__':
    unittest.main()
