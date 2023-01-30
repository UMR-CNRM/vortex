from unittest import TestCase, main

import footprints
from footprints import FootprintBase, FPDict, FPList, FPSet, FPTuple


class FootprintTestBuiltins(FootprintBase):
    _footprint = dict(
        info='Test builtins wrappers as attributes',
        attr=dict(
            thedict=dict(
                type=FPDict,
            ),
            thelist=dict(
                type=FPList,
            ),
            theset=dict(
                type=FPSet,
            ),
            thetuple=dict(
                type=FPTuple,
            ),
            thedefaultdict=dict(
                type=FPDict,
                optional=True,
                default=dict(),
            ),
            thedefaultfpdict=dict(
                type=FPDict,
                optional=True,
                default=FPDict(),
            ),
            thenodefaultdict=dict(
                type=FPDict,
                optional=True,
            ),
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

        fpl = FPList(['one', 'two', 3])
        self.assertIsInstance(fpl, FPList)
        self.assertIsInstance(fpl, list)
        self.assertListEqual(fpl, ['one', 'two', 3])
        self.assertSequenceEqual(fpl.items(), ['one', 'two', 3])
        self.assertEqual(fpl[1], 'two')
        fpl.append(4)
        self.assertListEqual(fpl[:], ['one', 'two', 3, 4])

        fpl = FPList([3])
        self.assertIsInstance(fpl, FPList)
        self.assertIsInstance(fpl, list)
        self.assertListEqual(fpl, [3])

        s = FPSet(['one', 'two', 3])
        self.assertIsInstance(s, FPSet)
        self.assertIsInstance(s, set)
        self.assertSetEqual(s, {'one', 'two', 3})
        self.assertSetEqual(set(s.items()), {3, 'two', 'one'})
        s.remove(3)
        s.add(4)
        self.assertSetEqual(set(s.items()), {4, 'two', 'one'})

        t = FPTuple((3, 5, 7))
        self.assertIsInstance(t, FPTuple)
        self.assertIsInstance(t, tuple)
        self.assertTupleEqual(t, (3, 5, 7))
        self.assertSequenceEqual(list(t.items()), [3, 5, 7])

    def test_builtins_usage(self):
        rv = footprints.proxy.garbage(
            thedict=FPDict(foo=2),
            thelist=FPList(['one', 'two', 3]),
            theset=FPSet([1, 2, 'three']),
            thetuple=FPTuple(('one', 'two', 3))
        )

        self.assertIsInstance(rv, FootprintTestBuiltins)

        self.assertIsInstance(rv.thedict, FPDict)
        self.assertIsInstance(rv.thedict, dict)
        self.assertDictEqual(rv.thedict, dict(foo=2))
        self.assertSequenceEqual(list(rv.thedict.items()), [('foo', 2)])

        self.assertIsInstance(rv.thedefaultdict, FPDict)
        self.assertIsInstance(rv.thedefaultdict, dict)
        self.assertDictEqual(rv.thedefaultdict, dict())
        self.assertSequenceEqual(list(rv.thedefaultdict.items()), [])

        self.assertIsInstance(rv.thedefaultfpdict, FPDict)
        self.assertIsInstance(rv.thedefaultfpdict, dict)
        self.assertDictEqual(rv.thedefaultfpdict, dict())
        self.assertSequenceEqual(list(rv.thedefaultfpdict.items()), [])

        self.assertEqual(rv.thenodefaultdict, None)

        rv.thedefaultdict['TUTU'] = 1
        rv.thedefaultfpdict['TOTO'] = 1
        # rv.thenodefaultdict is readonly unless explicitely messing with permissions

        rv2 = footprints.proxy.garbage(
            thedict=FPDict(foo=2),
            thelist=FPList(['one', 'two', 3]),
            theset=FPSet([1, 2, 'three']),
            thetuple=FPTuple(('one', 'two', 3))
        )
        self.assertDictEqual(rv2.thedefaultdict, dict())
        self.assertDictEqual(rv2.thedefaultfpdict, dict(TOTO=1))
        self.assertEqual(rv2.thenodefaultdict, None)

        self.assertIsInstance(rv.thelist, FPList)
        self.assertIsInstance(rv.thelist, list)
        self.assertListEqual(rv.thelist, ['one', 'two', 3])
        self.assertSequenceEqual(rv.thelist.items(), ['one', 'two', 3])

        self.assertIsInstance(rv.theset, FPSet)
        self.assertIsInstance(rv.theset, set)
        self.assertSetEqual(rv.theset, {1, 2, 'three'})
        self.assertSetEqual(set(rv.theset.items()), {1, 2, 'three'})

        self.assertIsInstance(rv.thetuple, FPTuple)
        self.assertIsInstance(rv.thetuple, tuple)
        self.assertTupleEqual(rv.thetuple, ('one', 'two', 3))
        self.assertSequenceEqual(rv.thetuple.items(), ['one', 'two', 3])


if __name__ == '__main__':
    main(verbosity=2)
