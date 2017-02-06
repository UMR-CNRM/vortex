#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from unittest import TestCase, main

import footprints
from footprints import FootprintBase, FPDict, FPList, FPSet, FPTuple


class FootprintTestBuiltins(FootprintBase):
    _footprint = dict(
        info = 'Test builtins wrappers as attributes',
        attr = dict(
            thedict = dict(
                type = FPDict,
            ),
            thelist = dict(
                type = FPList,
            ),
            theset = dict(
                type = FPSet,
            ),
            thetuple = dict(
                type = FPTuple,
            )
        )
    )


class utFootprintBuiltins(TestCase):

    def test_builtins_baseclass(self):
        d = FPDict(foo=2)
        self.assertIsInstance(d, FPDict)
        self.assertIsInstance(d, dict)
        self.assertSequenceEqual(list(d.items()), [('foo', 2)])
        self.assertEqual(d['foo'], 2)
        self.assertSequenceEqual(list(d.keys()), ['foo'])

        l = FPList(['one', 'two', 3])
        self.assertIsInstance(l, FPList)
        self.assertIsInstance(l, list)
        self.assertListEqual(l, ['one', 'two', 3])
        self.assertSequenceEqual(l.items(), ['one', 'two', 3])
        self.assertEqual(l[1], 'two')
        l.append(4)
        self.assertListEqual(l[:], ['one', 'two', 3, 4])

        l = FPList([3])
        self.assertIsInstance(l, FPList)
        self.assertIsInstance(l, list)
        self.assertListEqual(l, [3])

        s = FPSet(['one', 'two', 3])
        self.assertIsInstance(s, FPSet)
        self.assertIsInstance(s, set)
        self.assertSetEqual(s, set(['one', 'two', 3]))
        self.assertSetEqual(set(s.items()), set((3, 'two', 'one')))
        s.remove(3)
        s.add(4)
        self.assertSetEqual(set(s.items()), set((4, 'two', 'one')))

        t = FPTuple((3, 5, 7))
        self.assertIsInstance(t, FPTuple)
        self.assertIsInstance(t, tuple)
        self.assertTupleEqual(t, (3, 5, 7))
        self.assertSequenceEqual(list(t.items()), [3, 5, 7])

    def test_builtins_usage(self):
        rv = footprints.proxy.garbage(
            thedict  = FPDict(foo=2),
            thelist  = FPList(['one', 'two', 3]),
            theset   = FPSet([1, 2, 'three']),
            thetuple = FPTuple(('one', 'two', 3))
        )

        self.assertIsInstance(rv, FootprintTestBuiltins)

        self.assertIsInstance(rv.thedict, FPDict)
        self.assertIsInstance(rv.thedict, dict)
        self.assertDictEqual(rv.thedict, dict(foo=2))
        self.assertSequenceEqual(list(rv.thedict.items()), [('foo', 2)])

        self.assertIsInstance(rv.thelist, FPList)
        self.assertIsInstance(rv.thelist, list)
        self.assertListEqual(rv.thelist, ['one', 'two', 3])
        self.assertSequenceEqual(rv.thelist.items(), ['one', 'two', 3])

        self.assertIsInstance(rv.theset, FPSet)
        self.assertIsInstance(rv.theset, set)
        self.assertSetEqual(rv.theset, set([1, 2, 'three']))
        self.assertSetEqual(set(rv.theset.items()), set((1, 2, 'three')))

        self.assertIsInstance(rv.thetuple, FPTuple)
        self.assertIsInstance(rv.thetuple, tuple)
        self.assertTupleEqual(rv.thetuple, ('one', 'two', 3))
        self.assertSequenceEqual(rv.thetuple.items(), ['one', 'two', 3])


if __name__ == '__main__':
    main(verbosity=2)
