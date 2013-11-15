#!/bin/env python
# -*- coding: utf-8 -*-

from unittest import TestCase, main

import os, shutil, tempfile, pickle
from copy import deepcopy
from weakref import WeakSet

import footprints
from footprints import util, priorities, observers, reporting, Footprint, FootprintBase, FootprintBaseMeta, UNKNOWN

# Classes to be used in module scope

class Foo(object):
    def __init__(self, **kw):
        self.__dict__.update(kw)

class FootprintTestOne(FootprintBase):
    _footprint = dict(
        info = 'Test class',
        attr = dict(
            kind = dict(
                values = [ 'hip', 'hop' ]
            ),
            somestr = dict(
                values = [ 'this', 'or', 'that'],
                optional = True,
                default = 'this'
            ),
            someint = dict(
                values = range(10),
                type = int,
            )
        )
    )

class FootprintTestTwo(FootprintTestOne):
    _footprint = dict(
        info = 'Test class',
        attr = dict(
            somefoo = dict(
                type = Foo
            )
        )
    )


# Tests for footprints util

class utDictMerge(TestCase):

    def test_dictmerge_orthogonal(self):
        rv = util.dictmerge(
            dict(a=2, c='foo'),
            dict(b=7),
        )
        self.assertDictEqual(rv, dict(a=2, b=7, c='foo'))

    def test_dictmerge_overlap1(self):
        rv = util.dictmerge(
            dict(a=2, c='foo'),
            dict(b=7, c='updatedfoo'),
        )
        self.assertDictEqual(rv, dict(a=2, b=7, c='updatedfoo'))

    def test_dictmerge_overlap2(self):
        rv = util.dictmerge(
            dict(a=2, c='foo'),
            dict(b=7, c=dict(val='updatedfoo')),
        )
        self.assertDictEqual(rv, dict(a=2, b=7, c=dict(val='updatedfoo')))

    def test_dictmerge_recursive(self):
        rv = util.dictmerge(
            dict(a=2, c=dict(val='foo', other=dict(arg='hop'))),
            dict(b=7, c=dict(val='updatedfoo', other=dict(arg='hip', foo=False))),
        )
        self.assertDictEqual(rv, dict(a=2, b=7, c=dict(val='updatedfoo', other=dict(arg='hip', foo=False))))


class utList2Dict(TestCase):

    def test_list2dict_untouch(self):
        rv = util.list2dict(
            dict(a=2, c='foo'),
            ('other', 'foo'),
        )
        self.assertDictEqual(rv, dict(a=2, c='foo'))

    def test_list2dict_notdict(self):
        rv = util.list2dict(
            dict(a=2, c='foo'),
            ('a', 'c'),
        )
        self.assertDictEqual(rv, dict(a=2, c='foo'))

    def test_list2dict_realcase(self):
        rv = util.list2dict(
            dict(attr=[dict(foo=2), dict(more='hip')], only=(dict(k1='v1'), dict(k2='v2'))),
            ('attr', 'only'),
        )
        self.assertEqual(rv, dict(attr=dict(foo=2, more='hip'), only=dict(k1='v1', k2='v2')))


class utRangex(TestCase):

    def test_rangex_basics(self):
        rv = util.rangex(2)
        self.assertListEqual(rv, [2])

        rv = util.rangex(2,5)
        self.assertListEqual(rv, [2, 3, 4, 5])

        rv = util.rangex(7,4,-1)
        self.assertListEqual(rv, [4, 5, 6, 7])

        rv = util.rangex(-9,-7, shift=2)
        self.assertListEqual(rv, [-7, -6, -5])

        rv = util.rangex(0, 12, 3, 1)
        self.assertListEqual(rv, [1, 4, 7, 10, 13])

    def test_rangex_minus(self):
        rv = util.rangex('0-30-6,36-72-12')
        self.assertListEqual(rv, [0, 6, 12, 18, 24, 30, 36, 48, 60, 72])

        rv = util.rangex('0-30-6,36', 48, 12)
        self.assertListEqual(rv, [0, 6, 12, 18, 24, 30, 36, 48])

        rv = util.rangex('0-12', step=3, shift=1)
        self.assertListEqual(rv, [1, 4, 7, 10, 13])

    def test_rangex_comma(self):
        rv = util.rangex('0,4', 12, 3, 0)
        self.assertListEqual(rv, [0, 3, 4, 6, 7, 9, 10, 12])

    def test_rangex_fmt(self):
        rv = util.rangex('2-5', fmt='%03d')
        self.assertListEqual(rv,['002', '003', '004', '005'])

        rv = util.rangex('2-5', fmt='{0:03d}')
        self.assertListEqual(rv,['002', '003', '004', '005'])

        rv = util.rangex('2-5', fmt='{2:s}({0:02d})')
        self.assertListEqual(rv,['int(02)', 'int(03)', 'int(04)', 'int(05)'])

    def test_rangex_prefix(self):
        rv = util.rangex('foo_0', 5, 2)
        self.assertListEqual(rv, ['foo_0', 'foo_2', 'foo_4',])

        rv = util.rangex('foo_0-5-2', fmt='%02d')
        self.assertListEqual(rv, ['foo_00', 'foo_02', 'foo_04',])

        rv = util.rangex(1, 7, 3, prefix='hello-')
        self.assertListEqual(rv, ['hello-1', 'hello-4', 'hello-7',])

        rv = util.rangex(1, 7, 3, prefix='hello-', shift=2, fmt='%02d')
        self.assertListEqual(rv, ['hello-03', 'hello-06', 'hello-09'])

        rv = util.rangex(1, 7, 3, prefix='value no.', fmt='{1:d} is {0:d}')
        self.assertListEqual(rv, ['value no.1 is 1', 'value no.2 is 4', 'value no.3 is 7'])


class utInPlace(TestCase):

    def setUp(self):
        class Foo(object):
            def __init__(self, **kw):
                self.__dict__.update(kw)
        self.foo = Foo(inside=['one', 'two'])

    def test_inplace_orthogonal(self):
        rv = util.inplace(
            dict(a=2, c='foo'),
            'other', True,
        )
        self.assertDictEqual(rv, dict(a=2, c='foo', other=True))

    def test_inplace_overlap(self):
        rv = util.inplace(
            dict(a=2, c='foo'),
            'c', True,
        )
        self.assertDictEqual(rv, dict(a=2, c=True))

    def test_inplace_deepcopy(self):
        rv = util.inplace(
            dict(a=self.foo, c='foo'),
            'c', True,
        )
        self.assertIsInstance(rv['a'], self.foo.__class__)
        self.assertIsNot(rv['a'], self.foo)
        self.assertIsNot(rv['a'].inside, self.foo.inside)

    def test_inplace_glob(self):
        rv = util.inplace(
            dict(a=2, c='foo_[glob:z]'),
            'a', True,
            globs = dict(z='bar')
        )
        self.assertDictEqual(rv, dict(a=True, c='foo_bar'))


class utExpand(TestCase):

    def test_expand_basics(self):
        rv = util.expand(dict(a=2, c='foo'))
        self.assertListEqual(rv, [ dict(a=2, c='foo') ])

    def test_expand_iters(self):
        rv = util.expand(dict(arg='hop', item=(1,2,3)))
        self.assertListEqual(sorted(rv), [
            {'arg': 'hop', 'item': 1},
            {'arg': 'hop', 'item': 2},
            {'arg': 'hop', 'item': 3}
        ])

        rv = util.expand(dict(arg='hop', item=[4,5,6]))
        self.assertListEqual(sorted(rv), [
            {'arg': 'hop', 'item': 4},
            {'arg': 'hop', 'item': 5},
            {'arg': 'hop', 'item': 6}
        ])

        rv = util.expand(dict(arg='hop', item=set([7,8,9])))
        self.assertListEqual(sorted(rv), [
            {'arg': 'hop', 'item': 7},
            {'arg': 'hop', 'item': 8},
            {'arg': 'hop', 'item': 9}
        ])

    def test_expand_strings(self):
        rv = util.expand(dict(arg='hop', item='a,b,c'))
        self.assertListEqual(sorted(rv), [
            {'arg': 'hop', 'item': 'a'},
            {'arg': 'hop', 'item': 'b'},
            {'arg': 'hop', 'item': 'c'}
        ])

        rv = util.expand(dict(arg='hop', item='range(2)'))
        self.assertListEqual(sorted(rv), [
            {'arg': 'hop', 'item': 2}
        ])

        rv = util.expand(dict(arg='hop', item='range(2,4)'))
        self.assertListEqual(sorted(rv), [
            {'arg': 'hop', 'item': 2},
            {'arg': 'hop', 'item': 3},
            {'arg': 'hop', 'item': 4}
        ])

        rv = util.expand(dict(arg='hop', item='range(1,7,3)'))
        self.assertListEqual(sorted(rv), [
            {'arg': 'hop', 'item': 1},
            {'arg': 'hop', 'item': 4},
            {'arg': 'hop', 'item': 7}
        ])

    def test_expand_glob(self):
        tmpd = tempfile.mkdtemp()
        ( tmpio,tmpf ) = tempfile.mkstemp(dir=tmpd)
        for a in ('hip', 'hop'):
            for b in range(3):
                shutil.copyfile(tmpf, '{0:s}/xx_{1:s}_{2:04d}'.format(tmpd, a, b))
        rv = util.expand(dict(
            arg='multi',
            look='xx_{glob:a:\w+}_{glob:b:\d+}',
            seta='[glob:a]',
            setb='[glob:b]'
        ))
        self.assertListEqual(sorted(rv), [])
        os.chdir(tmpd)
        rv = util.expand(dict(
            arg='multi',
            look='xx_{glob:a:\w+}_{glob:b:\d+}',
            seta='[glob:a]',
            setb='[glob:b]'
        ))
        shutil.rmtree(tmpd)
        self.assertListEqual(sorted(rv), [
            {'arg': 'multi', 'look': 'xx_hip_0000', 'seta': 'hip', 'setb': '0000'},
            {'arg': 'multi', 'look': 'xx_hip_0001', 'seta': 'hip', 'setb': '0001'},
            {'arg': 'multi', 'look': 'xx_hip_0002', 'seta': 'hip', 'setb': '0002'},
            {'arg': 'multi', 'look': 'xx_hop_0000', 'seta': 'hop', 'setb': '0000'},
            {'arg': 'multi', 'look': 'xx_hop_0001', 'seta': 'hop', 'setb': '0001'},
            {'arg': 'multi', 'look': 'xx_hop_0002', 'seta': 'hop', 'setb': '0002'}
        ])

    def test_expand_mixed(self):
        rv = util.expand(dict(
                arg='hop',
                atuple=('one', 'two'),
                alist=['a', 'b'],
                aset=set(['banana', 'orange']),
                astr='this,that',
                arange='range(1,7,3)'
        ))
        self.assertEqual(len(rv), 48)
        self.assertListEqual(sorted(rv), [
            {'atuple': 'one', 'alist': 'a', 'arange': 1, 'aset': 'banana', 'arg': 'hop', 'astr': 'that'},
            {'atuple': 'two', 'alist': 'a', 'arange': 1, 'aset': 'banana', 'arg': 'hop', 'astr': 'that'},
            {'atuple': 'one', 'alist': 'a', 'arange': 1, 'aset': 'banana', 'arg': 'hop', 'astr': 'this'},
            {'atuple': 'two', 'alist': 'a', 'arange': 1, 'aset': 'banana', 'arg': 'hop', 'astr': 'this'},
            {'atuple': 'one', 'alist': 'a', 'arange': 1, 'aset': 'orange', 'arg': 'hop', 'astr': 'that'},
            {'atuple': 'two', 'alist': 'a', 'arange': 1, 'aset': 'orange', 'arg': 'hop', 'astr': 'that'},
            {'atuple': 'one', 'alist': 'a', 'arange': 1, 'aset': 'orange', 'arg': 'hop', 'astr': 'this'},
            {'atuple': 'two', 'alist': 'a', 'arange': 1, 'aset': 'orange', 'arg': 'hop', 'astr': 'this'},
            {'atuple': 'one', 'alist': 'a', 'arange': 4, 'aset': 'banana', 'arg': 'hop', 'astr': 'that'},
            {'atuple': 'two', 'alist': 'a', 'arange': 4, 'aset': 'banana', 'arg': 'hop', 'astr': 'that'},
            {'atuple': 'one', 'alist': 'a', 'arange': 4, 'aset': 'banana', 'arg': 'hop', 'astr': 'this'},
            {'atuple': 'two', 'alist': 'a', 'arange': 4, 'aset': 'banana', 'arg': 'hop', 'astr': 'this'},
            {'atuple': 'one', 'alist': 'a', 'arange': 4, 'aset': 'orange', 'arg': 'hop', 'astr': 'that'},
            {'atuple': 'two', 'alist': 'a', 'arange': 4, 'aset': 'orange', 'arg': 'hop', 'astr': 'that'},
            {'atuple': 'one', 'alist': 'a', 'arange': 4, 'aset': 'orange', 'arg': 'hop', 'astr': 'this'},
            {'atuple': 'two', 'alist': 'a', 'arange': 4, 'aset': 'orange', 'arg': 'hop', 'astr': 'this'},
            {'atuple': 'one', 'alist': 'a', 'arange': 7, 'aset': 'banana', 'arg': 'hop', 'astr': 'that'},
            {'atuple': 'two', 'alist': 'a', 'arange': 7, 'aset': 'banana', 'arg': 'hop', 'astr': 'that'},
            {'atuple': 'one', 'alist': 'a', 'arange': 7, 'aset': 'banana', 'arg': 'hop', 'astr': 'this'},
            {'atuple': 'two', 'alist': 'a', 'arange': 7, 'aset': 'banana', 'arg': 'hop', 'astr': 'this'},
            {'atuple': 'one', 'alist': 'a', 'arange': 7, 'aset': 'orange', 'arg': 'hop', 'astr': 'that'},
            {'atuple': 'two', 'alist': 'a', 'arange': 7, 'aset': 'orange', 'arg': 'hop', 'astr': 'that'},
            {'atuple': 'one', 'alist': 'a', 'arange': 7, 'aset': 'orange', 'arg': 'hop', 'astr': 'this'},
            {'atuple': 'two', 'alist': 'a', 'arange': 7, 'aset': 'orange', 'arg': 'hop', 'astr': 'this'},
            {'atuple': 'one', 'alist': 'b', 'arange': 1, 'aset': 'banana', 'arg': 'hop', 'astr': 'that'},
            {'atuple': 'two', 'alist': 'b', 'arange': 1, 'aset': 'banana', 'arg': 'hop', 'astr': 'that'},
            {'atuple': 'one', 'alist': 'b', 'arange': 1, 'aset': 'banana', 'arg': 'hop', 'astr': 'this'},
            {'atuple': 'two', 'alist': 'b', 'arange': 1, 'aset': 'banana', 'arg': 'hop', 'astr': 'this'},
            {'atuple': 'one', 'alist': 'b', 'arange': 1, 'aset': 'orange', 'arg': 'hop', 'astr': 'that'},
            {'atuple': 'two', 'alist': 'b', 'arange': 1, 'aset': 'orange', 'arg': 'hop', 'astr': 'that'},
            {'atuple': 'one', 'alist': 'b', 'arange': 1, 'aset': 'orange', 'arg': 'hop', 'astr': 'this'},
            {'atuple': 'two', 'alist': 'b', 'arange': 1, 'aset': 'orange', 'arg': 'hop', 'astr': 'this'},
            {'atuple': 'one', 'alist': 'b', 'arange': 4, 'aset': 'banana', 'arg': 'hop', 'astr': 'that'},
            {'atuple': 'two', 'alist': 'b', 'arange': 4, 'aset': 'banana', 'arg': 'hop', 'astr': 'that'},
            {'atuple': 'one', 'alist': 'b', 'arange': 4, 'aset': 'banana', 'arg': 'hop', 'astr': 'this'},
            {'atuple': 'two', 'alist': 'b', 'arange': 4, 'aset': 'banana', 'arg': 'hop', 'astr': 'this'},
            {'atuple': 'one', 'alist': 'b', 'arange': 4, 'aset': 'orange', 'arg': 'hop', 'astr': 'that'},
            {'atuple': 'two', 'alist': 'b', 'arange': 4, 'aset': 'orange', 'arg': 'hop', 'astr': 'that'},
            {'atuple': 'one', 'alist': 'b', 'arange': 4, 'aset': 'orange', 'arg': 'hop', 'astr': 'this'},
            {'atuple': 'two', 'alist': 'b', 'arange': 4, 'aset': 'orange', 'arg': 'hop', 'astr': 'this'},
            {'atuple': 'one', 'alist': 'b', 'arange': 7, 'aset': 'banana', 'arg': 'hop', 'astr': 'that'},
            {'atuple': 'two', 'alist': 'b', 'arange': 7, 'aset': 'banana', 'arg': 'hop', 'astr': 'that'},
            {'atuple': 'one', 'alist': 'b', 'arange': 7, 'aset': 'banana', 'arg': 'hop', 'astr': 'this'},
            {'atuple': 'two', 'alist': 'b', 'arange': 7, 'aset': 'banana', 'arg': 'hop', 'astr': 'this'},
            {'atuple': 'one', 'alist': 'b', 'arange': 7, 'aset': 'orange', 'arg': 'hop', 'astr': 'that'},
            {'atuple': 'two', 'alist': 'b', 'arange': 7, 'aset': 'orange', 'arg': 'hop', 'astr': 'that'},
            {'atuple': 'one', 'alist': 'b', 'arange': 7, 'aset': 'orange', 'arg': 'hop', 'astr': 'this'},
            {'atuple': 'two', 'alist': 'b', 'arange': 7, 'aset': 'orange', 'arg': 'hop', 'astr': 'this'}
        ])


class utCatalog(TestCase):

    def setUp(self):
        self.o1 = Foo(inside=['a', 'b'])
        self.o2 = Foo(inside=['x', 'y'])

    def test_catalog_std(self):
        rv = util.Catalog.fullname()
        self.assertEqual(rv, 'footprints.util.Catalog')

        rv = util.Catalog(extra=2)
        self.assertIsInstance(rv, util.Catalog)
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

        rv = util.Catalog(items=[self.o1])
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
        self.assertListEqual(sorted(rv()), [2, self.o1])

        rv.discard(5)
        self.assertTrue(rv.filled)
        self.assertListEqual(sorted(rv()), [2, self.o1])

        rv.discard(2)
        self.assertTrue(rv.filled)
        self.assertListEqual(rv(), [self.o1])

        rv.discard(self.o1)
        self.assertFalse(rv.filled)

    def test_catalog_weak(self):
        rv = util.Catalog(weak=True)
        self.assertIsInstance(rv, util.Catalog)
        self.assertIsInstance(rv._items, WeakSet)
        self.assertTrue(rv.weak)
        self.assertEqual(len(rv), 0)
        self.assertFalse(rv.filled)

        # this is a property
        with self.assertRaises(AttributeError):
            rv.weak = False

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

        rv = util.Catalog(items=[self.o1], weak=True)
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

        rv.discard(self.o1)
        self.assertFalse(rv.filled)
        self.assertTrue(rv.weak)

    def test_catalog_iter(self):
        rv = util.Catalog(items=[self.o1, self.o2], weak=False)
        for x in rv:
            self.assertIsInstance(x, Foo)

    def test_catalog_freeze(self):
        rv = util.Catalog(items=[self.o1, self.o2], weak=False)
        self.assertIsInstance(rv._items, set)
        self.assertEqual(len(rv), 2)
        self.assertFalse(rv.weak)

        db = pickle.loads(pickle.dumps(rv))
        self.assertIsInstance(db, util.Catalog)
        self.assertIsInstance(db._items, set)
        self.assertEqual(len(db), 2)
        self.assertFalse(db.weak)

        rv = util.Catalog(items=[self.o1, self.o2], weak=True)
        self.assertIsInstance(rv._items, WeakSet)
        self.assertEqual(len(rv), 2)
        self.assertTrue(rv.weak)

        db = pickle.loads(pickle.dumps(rv))
        self.assertIsInstance(db, util.Catalog)
        self.assertIsInstance(db._items, WeakSet)
        self.assertEqual(len(db), 0)
        self.assertTrue(db.weak)


# Tests for footprints priorities

class utPriorities(TestCase):

    def test_priorities_basics(self):
        rv = priorities.PrioritySet()
        self.assertIsInstance(rv, priorities.PrioritySet)
        self.assertEqual(len(rv), 0)
        self.assertIsInstance(rv(), tuple)
        self.assertNotIn('debug', rv)

        rv.extend('default', 'toolbox', 'debug')
        self.assertEqual(len(rv), 3)
        self.assertIn('default', rv)
        self.assertIn('toolbox', rv)
        self.assertIn('debug', rv)
        self.assertIsInstance(rv.DEBUG, priorities.PriorityLevel)
        self.assertIs(rv.DEFAULT, rv.level('default'))
        self.assertIs(rv.TOOLBOX, rv.level('toolbox'))
        self.assertIs(rv.DEBUG,   rv.level('debug'))

        rv = priorities.PrioritySet(levels=['default', 'toolbox'])
        self.assertIsInstance(rv, priorities.PrioritySet)
        self.assertEqual(len(rv), 2)
        self.assertIn('Default', rv)
        self.assertIsInstance(rv.levels, tuple)
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX'))

        rv.extend('debug')
        self.assertEqual(len(rv), 3)
        self.assertIn('DEBUG', rv)
        self.assertIsInstance(rv.DEBUG, priorities.PriorityLevel)
        self.assertGreater(rv.DEBUG, rv.TOOLBOX)

        rv.reset()
        self.assertEqual(len(rv), 2)
        self.assertNotIn('debug', rv)

        rv.remove('toolbox')
        self.assertEqual(len(rv), 1)
        self.assertNotIn('toolbox', rv)

        rv.reset()
        self.assertEqual(len(rv), 2)
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX'))

        rv.TOOLBOX.delete()
        self.assertEqual(len(rv), 1)
        self.assertTupleEqual(rv.levels, ('DEFAULT',))

    def test_priorities_compare(self):
        rv = priorities.PrioritySet(levels=['default', 'toolbox', 'debug'])
        self.assertGreater(rv.DEBUG, rv.TOOLBOX)
        self.assertGreater(rv.TOOLBOX, rv.DEFAULT)
        self.assertEqual(rv.DEFAULT.rank, 0)
        self.assertEqual(rv.TOOLBOX.rank, 1)
        self.assertEqual(rv.DEBUG.rank,   2)
        self.assertEqual(rv.levelindex('default'), 0)
        self.assertEqual(rv.levelindex('toolbox'), 1)
        self.assertEqual(rv.levelindex('debug'),   2)
        self.assertEqual(rv.levelbyindex(0), rv.DEFAULT)
        self.assertEqual(rv.levelbyindex(1), rv.TOOLBOX)
        self.assertEqual(rv.levelbyindex(2), rv.DEBUG)

        rv = priorities.top
        self.assertTrue(rv.NONE < rv.DEFAULT < rv.TOOLBOX < rv.DEBUG)
        self.assertTrue(rv.DEBUG   > 'toolbox')
        self.assertTrue(rv.DEFAULT < 'toolbox')
        self.assertIsNone(rv.DEBUG.nextlevel())
        self.assertIsNone(rv.NONE.prevlevel())

    def test_priorities_reorder(self):
        rv = priorities.PrioritySet(levels=['default', 'toolbox', 'debug'])
        self.assertTrue(rv.DEBUG > 'toolbox')

        rv.rerank('toolbox', 1)
        self.assertFalse(rv.DEBUG > 'toolbox')

        rv.rerank('default', 999)
        self.assertFalse(rv.DEBUG > 'default')
        self.assertTupleEqual(rv.levels, ('DEBUG', 'TOOLBOX', 'DEFAULT'))

        rv.DEBUG.top()
        self.assertTrue(rv.DEBUG > 'default')
        self.assertTupleEqual(rv.levels, ('TOOLBOX', 'DEFAULT', 'DEBUG'))

        rv.DEFAULT.bottom()
        self.assertTrue(rv.TOOLBOX > 'default')
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'DEBUG'))

        rv.DEBUG.up()
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'DEBUG'))

        rv.DEFAULT.down()
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'DEBUG'))

        rv.TOOLBOX.up()
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'DEBUG', 'TOOLBOX'))

        rv.reset()
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'DEBUG'))

        rv.TOOLBOX.down()
        self.assertTupleEqual(rv.levels, ('TOOLBOX', 'DEFAULT', 'DEBUG'))

        rv.reset()
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'DEBUG'))

        rv.TOOLBOX.addafter('foo')
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'FOO', 'DEBUG'))

        rv.DEBUG.addafter('top')
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'FOO', 'DEBUG', 'TOP'))

        rv.reset()
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'DEBUG'))

        rv.TOOLBOX.addbefore('foo')
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'FOO', 'TOOLBOX', 'DEBUG'))

        rv.DEFAULT.addbefore('scratch')
        self.assertTupleEqual(rv.levels, ('SCRATCH', 'DEFAULT', 'FOO', 'TOOLBOX', 'DEBUG'))

    def test_priorities_freeze(self):
        rv = priorities.PrioritySet(levels=['default', 'toolbox', 'debug'])
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'DEBUG'))
        self.assertListEqual(rv.freezed(), ['default'])

        rv.insert('hip', after='toolbox')
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'HIP', 'DEBUG'))

        rv.freeze('hip-added')
        self.assertListEqual(rv.freezed(), ['default', 'hip-added'])

        rv.insert('hop', before='debug')
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'HIP', 'HOP', 'DEBUG'))

        rv.freeze('hop-added')
        self.assertListEqual(rv.freezed(), ['default', 'hip-added', 'hop-added'])

        rv.reset()
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'DEBUG'))

        rv.restore('hop-added')
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'HIP', 'HOP', 'DEBUG'))

        rv.remove('hip')
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'HOP', 'DEBUG'))

        rv.restore('hip-added')
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'HIP', 'DEBUG'))
        self.assertTrue(rv.TOOLBOX < rv.HIP < rv.DEBUG)

        with self.assertRaises(ValueError):
            rv.freeze('default')

# Tests for footprints observers

class utObservers(TestCase):

    def test_observers_basics(self):
        rv = observers.getbyname()
        self.assertListEqual(rv, ['__main__.FootprintTestOne', '__main__.FootprintTestTwo'])

# Tests for footprints reporting

# Tests for footprints top module methods and objects

class utFootprint(TestCase):

    def setUp(self):
        self.fp = dict(
            attr = dict(),
            bind = [],
            info = 'Not documented',
            only = dict(),
            priority = dict(
                level = priorities.top.TOOLBOX
            )
        )

    def test_footprint_basics(self):
        fp = Footprint(nodefault=True)
        self.assertIsInstance(fp, Footprint)
        self.assertIsInstance(fp.as_dict(), dict)
        self.assertDictEqual(fp.as_dict(), dict(attr = dict()))
        self.assertEqual(str(fp), '{}')

        fp = Footprint(dict(
            info = 'Some stuff there',
            attr = dict(stuff = dict())
        ))
        self.assertIsInstance(fp, Footprint)
        self.assertEqual(fp.info, 'Some stuff there')
        self.assertDictEqual(fp.attr, dict(
            stuff = dict(
                alias = (),
                default = None,
                optional = False,
                remap = dict()
            )
        ))

        fp1 = Footprint()
        self.assertIsInstance(fp1, Footprint)
        self.assertDictEqual(fp1.as_dict(), self.fp)

        fp2 = Footprint()
        self.assertIsInstance(fp2, Footprint)
        self.assertDictEqual(fp1.as_dict(), fp2.as_dict())

        fp2 = Footprint(fp,
            info='Other stuff',
            attr=dict(stuff=dict(values=['hip', 'hop'])),
            priority=dict(level=priorities.top.DEBUG)
        )
        self.assertEqual(fp2.info, 'Other stuff')
        self.assertEqual(fp2.priority['level'], priorities.top.DEBUG)
        self.assertListEqual(fp2.attr.keys(), ['stuff'])
        self.assertDictEqual(fp2.as_dict(), {
            'attr': {
                'stuff': {
                    'alias': (),
                    'default': None,
                    'optional': False,
                    'remap': {},
                    'values': ['hip', 'hop']
                }
            },
            'bind': [],
            'info': 'Other stuff',
            'only': {},
            'priority': {'level': priorities.top.DEBUG}
       })

    def test_footprint_readonly(self):
        fp = Footprint()

        with self.assertRaises(AttributeError):
            fp.attr = dict()

        with self.assertRaises(AttributeError):
            fp.bind = list()

        with self.assertRaises(AttributeError):
            fp.info = 'Hello'

        with self.assertRaises(AttributeError):
            fp.only = dict()

        with self.assertRaises(AttributeError):
            fp.priority = dict()

    def test_footprint_deepcopy(self):
        fp1 = Footprint(
            attr = dict(
                stuff = dict(
                    type = int,
                    values = range(2),
                    default = 1,
                    optional = True
                )
            ),
            info = 'Some nice stuff'
        )
        fp2 = deepcopy(fp1)
        self.assertDictEqual(fp1.as_dict(), fp2.as_dict())
        self.assertListEqual(fp2.attr['stuff']['values'], [0, 1])
        self.assertIsNot(fp1.attr['stuff']['values'], fp2.attr['stuff']['values'])

        fp2 = Footprint(fp1)
        self.assertDictEqual(fp1.as_dict(), fp2.as_dict())
        self.assertListEqual(fp2.attr['stuff']['values'], [0, 1])
        self.assertIsNot(fp1.attr['stuff']['values'], fp2.attr['stuff']['values'])

    def test_footprint_optional(self):
        fp = Footprint(
            attr = dict(
                stuff1 = dict(
                    alias = ('arg1',)
                ),
                stuff2 = dict(
                    optional = True,
                    default = 'foo'
                ),
            ),
            info = 'Some nice stuff'
        )
        self.assertIsInstance(fp, Footprint)
        self.assertSetEqual(fp.as_opts(), set(['arg1', 'stuff1', 'stuff2']))
        self.assertFalse(fp.optional('stuff1'))
        self.assertTrue(fp.optional('stuff2'))
        self.assertListEqual(fp.mandatory(), ['stuff1'])
        self.assertListEqual(fp.track(dict(arg1=1, stuff2='hello', stuff3=3)), ['arg1', 'stuff2'])

        with self.assertRaises(KeyError):
            self.assertTrue(fp.optional('stuff3'))

    def xtest_firstguess_optional(self):
        ft = Footprint(
            self.res,
            attr = dict(
                real = dict(
                    optional = False,
                ),
                foo = dict(
                    optional = True,
                ),
                two = dict(
                    optional = True,
                    default = '2'
                ),
                bof = dict(
                    optional = True,
                    type = int,
                    default = 2
                )
            )
        )
        guess, set_guess = ft._firstguess(dict(real='hello'))
        result = dict(
            real = 'hello',
            foo = UNKNOWN,
            two = '2',
            bof = 2,
        )
        for key, value in result.iteritems():
            self.assertEquals(value, guess[key])
        self.assertEquals(set_guess, set(['real']))

    def xtest_firstguess_alias(self):
        ft = Footprint(
            self.res,
            attr = dict(
                real = dict(
                    optional = False,
                ),
                foo = dict(
                    alias = [ 'fuzzy' ],
                ),
            )
        )
        guess, set_guess = ft._firstguess(dict(real='hello', fuzzy=2))
        result = dict(
            real = 'hello',
            foo = 2,
        )
        for key, value in result.iteritems():
            self.assertEquals(value, guess[key])
        self.assertEquals(set_guess, set(['real', 'foo']))

    def xtest_findextras_empty(self):
        ft = Footprint(self.res)
        extras = ft._findextras(dict(real='hello', fuzzy=2))
        self.assertEquals(extras.keys(), [])

    def xtest_findextras_container(self):
        ft = Footprint(self.res)
        #mycont = InCore()
        mycont = True
        extras = ft._findextras(dict(real='hello', fuzzy=2, container=mycont))
        self.assertIsInstance(extras, dict)
        self.assertEqual(len(extras), 4)
        self.assertTrue(extras['incore'] == True)
        self.assertTrue(extras['prefix'] == 'vortex.tmp.')
        self.assertTrue(extras['maxsize'] == 65536)

    def xtest_replacement_internal(self):
        ft = Footprint(
            self.res,
            attr = dict(
                model = dict(
                    values = [ 'arpege', 'aladin' ]
                ),
                truncation = dict(
                    type = int
                ),
                gvar = dict(
                    optional = True,
                    default = 'clim_[model]_t[truncation]'
                ),
            )
        )
        guess, set_guess = ft._firstguess(dict(model = 'arpege', truncation=798))
        done = ft._replacement(1, 'gvar', guess, [], [ 'model' ])
        self.assertFalse(done)
        self.assertEquals('clim_[model]_t[truncation]', guess['gvar'])
        done = ft._replacement(1, 'gvar', guess, [], [])
        self.assertTrue(done)
        self.assertEquals('clim_arpege_t798', guess['gvar'])


class UtFootprintBaseMeta(TestCase):

    def xtest_new_vide(self):
        res = {
            'info': 'Not documented',
            'name': 'empty',
            'attr': {},
            'bind': [],
            'only': {},
            'priority': {'level': 20}
        }
        #TODO MyBFtp = FootprintBaseMeta('MyBFtp', ( FootprintBase, ), {})
        #for cle, value in MyBFtp._footprint._fp.iteritems():
        #    if cle != 'priority':
        #        self.assertEquals(value, res[cle])

    def xtest_new_withdict(self):
        args = {
            '_footprint': {
                'info': 'documented',
                'name': 'withdict'
            }
        }
        res = {
            'info': 'documented',
            'name': 'withdict',
            'attr': {},
            'bind': [],
            'only': {},
            'priority': {'level': 20}
        }
        #TODO MyBFtp = FootprintBaseMeta('MyBFtp', ( FootprintBase, ), args)
        #for key, value in MyBFtp._footprint._fp.iteritems():
        #    if key != 'priority':
        #        self.assertEquals(value, res[key])

    def xtest_new_withbaseft(self):
        args = (
            {
            'name': 'alerte'
            },
        )
        kw = {
            'attr': {'model': {'values': ['mocchim']}}
        }
        ft1 = Footprint(*args, **kw)
        res = {
            'info': 'Not documented',
            'name': 'alerte',
            'attr': {
                'model': {
                    'default': None,
                    'alias': (),
                    'remap': {},
                    'values': ['mocchim'],
                    'optional': False
                }
            },
            'bind': [],
            'only': {},
            'priority': {'level': 20}
        }
        #MyBFtp = FootprintBaseMeta('MyBFtp', ( FootprintBase, ), {'_footprint': ft1})
        #for cle, value in MyBFtp._footprint._fp.iteritems():
        #    if cle != 'priority':
        #        self.assertEquals(value, res[cle])


class UtFootprintBase(TestCase):

    def setUp(self):
        self.res = {
            'info': 'Not documented',
            'name': 'empty',
            'bind': [],
            'attr': {},
            'only': {},
        }

    def xtest_new_vide(self):
        self.assertTrue(isinstance(FootprintBase._footprint, Footprint))
        for cle, value in FootprintBase._footprint._fp.iteritems():
            if cle == 'priority': continue
            self.assertEquals(value, self.res[cle])
        dp = { k:v for k,v in vars(FootprintBase._footprint._fp['priority']['level']).items() if not k.startswith('_') }
        #TODO self.assertEquals(dp, {'tag': 'TOOLBOX'})

    def xtest_init_vide(self):
        mybft = FootprintBase()
        self.assertFalse(mybft._instfp is mybft._footprint._fp)
        for cle, value in mybft._footprint._fp.iteritems():
            if cle == 'priority': continue
            self.assertEquals(value, self.res[cle])
        dp = { k:v for k,v in vars(FootprintBase._footprint._fp['priority']['level']).items() if not k.startswith('_') }
        #TODO self.assertEquals(dp, {'tag': 'TOOLBOX'})

    def xtest_couldbe(self):
        rd = dict(
            kind = 'testun'
        )
        rd2 = dict(
            kind = 'testun',
            info_deux = 'surface'
        )
        res_rd2 = dict(
            kind = 'testun',
            info_deux = 'surface',
            info_un = '__unknown__'
        )
        pseudo_ctlg = [ FootprintTest ]
        for bf in pseudo_ctlg:
            self.assertEqual(bf.couldbe(rd), (False, set(['kind'])))
            self.assertEqual(bf.couldbe(rd2), (res_rd2, set(['kind', 'info_deux'])))

    def xtest_firstguess(self):
        rd = {
            1: dict(
                kind = 'testun'
            ),
            2 : dict(
                kind = 'testun',
                info_deux = 'surface'
            ),
            3 : dict(
                kind = 'testun',
                info_deux = 'surface',
                info_un = 'str_only'
            )
        }
        fp = FootprintTest.footprint()
        self.assertEqual(sorted(fp.attr.keys()), sorted(['kind', 'info_un',
                                                         'info_deux']))
        ref_guess = {
            1: dict(
                kind = 'testun',
                info_deux = None,
                info_un = '__unknown__'
            ),
            2: dict(
                kind = 'testun',
                info_deux = 'surface',
                info_un = '__unknown__'
            ),
            3 : dict(
                kind = 'testun',
                info_deux = 'surface',
                info_un = 'str_only'
            )

        }
        for cas in ref_guess:
            guess, input = fp._firstguess(rd[cas])
            self.assertEqual(sorted(guess.keys()), sorted(ref_guess[cas].keys()))
            for k in guess.keys():
                self.assertEqual(guess[k], ref_guess[cas][k])


if __name__ == '__main__':
    main(verbosity=2)
    vortex.exit()
