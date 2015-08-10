#!/usr/bin/env python
# -*- coding: utf-8 -*-

from unittest import TestCase, main

import os, shutil, tempfile, pickle
import logging
import datetime
from copy import deepcopy
from weakref import WeakSet

import footprints

from footprints import \
    dump, observers, priorities, reporting, util, \
    Footprint, FootprintBase, FootprintBaseMeta, \
    FPDict, FPList, FPSet, FPTuple

from footprints.access import FootprintAttrDescriptorRXX

from footprints.config import FootprintSetup


# Classes to be used in module scope

class Foo(object):
    # noinspection PyUnusedLocal
    def __init__(self, *u_args, **kw):
        self.__dict__.update(kw)

    def justdoit(self, guess, extras):
        return 'done_' + str(len(guess))


class FootprintTestOne(FootprintBase):
    _footprint = dict(
        info = 'Test class',
        attr = dict(
            kind = dict(
                values = [ 'hip', 'hop' ],
                alias = ('stuff',),
                remap = dict(foo='hop')
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

    @property
    def realkind(self):
        return 'bigone'


class FootprintTestTwo(FootprintTestOne):
    _footprint = dict(
        info = 'Another test class',
        attr = dict(
            somefoo = dict(
                type = Foo
            ),
            someint = dict(
                outcast = (2, 7)
            )
        )
    )


class FootprintTestRWD(FootprintBase):
    _footprint = dict(
        info = 'Test attributes access',
        attr = dict(
            someint = dict(
                type = int,
                access = 'rwx',
                outcast = (2, 7)
            ),
            somefoo = dict(
                type = Foo,
                access = 'rxx'
            ),
            somestr = dict(
                access = 'rwd',
                values = ('one', 'two', 'five')
            )
        )
    )


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


# Tests for miscellaneous dumps

class utDump(TestCase):

    def test_dump_types(self):
        for x in (None, 'foo', 2, long(2), 2., 1+2j):
            self.assertTrue(dump.atomic_type(type(x)))

        self.assertFalse(dump.is_instance(Foo))
        self.assertTrue(dump.is_instance(Foo()))

        class FooBis(Foo):
            pass

        self.assertFalse(dump.is_instance(FooBis))
        self.assertTrue(dump.is_class(Foo))
        self.assertTrue(dump.is_class(FooBis))

        for x in (None, 'foo', 2, long(2), 2., 1+2j, Foo):
            self.assertTrue(dump.simple_value(x))

        for x in (Foo(),):
            self.assertFalse(dump.simple_value(x))

        for x in (range(10), tuple(range(10)), {str(i): i for i in range(5)}):
            self.assertTrue(dump.simple_value(x))

        for x in (range(11), tuple(range(11)), {str(i): i for i in range(7)}, {'foo': Foo()}, [Foo(), Foo()]):
            self.assertFalse(dump.simple_value(x))

    def test_dump_indent(self):
        self.assertEqual(dump.indent(nextline=False), '')
        self.assertEqual(dump.indent(nextline=False, level=2), '')
        self.assertEqual(dump.indent(), '\n      ')
        self.assertEqual(dump.indent(level=1), '\n          ')


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


# A pure internal usage

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


# Pseudo-int expand mechanism

class utRangex(TestCase):

    def test_rangex_basics(self):
        rv = util.rangex(2)
        self.assertListEqual(rv, [2])

        rv = util.rangex(2, 5)
        self.assertListEqual(rv, [2, 3, 4, 5])

        rv = util.rangex(7, 4, -1)
        self.assertListEqual(rv, [4, 5, 6, 7])

        rv = util.rangex(-9, -7, shift=2)
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
        self.assertListEqual(rv, ['002', '003', '004', '005'])

        rv = util.rangex('2-5', fmt='{0:03d}')
        self.assertListEqual(rv, ['002', '003', '004', '005'])

        rv = util.rangex('2-5', fmt='{2:s}({0:02d})')
        self.assertListEqual(rv, ['int(02)', 'int(03)', 'int(04)', 'int(05)'])

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


# In-place substitution in lists

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


# Generic expand mechanism

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
        ( u_tmpio, tmpf ) = tempfile.mkstemp(dir=tmpd)
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


# Base class for catalogs like objects

# noinspection PyPropertyAccess
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
        self.assertListEqual([x for x in rv], ['DEFAULT', 'TOOLBOX'])

        rv.extend('debug')
        self.assertEqual(len(rv), 3)
        self.assertIn('DEBUG', rv)
        self.assertIsInstance(rv.DEBUG, priorities.PriorityLevel)
        self.assertGreater(rv.DEBUG, rv.TOOLBOX)
        self.assertEqual(rv.DEFAULT(), 0)
        self.assertEqual(rv.TOOLBOX(), 1)
        self.assertEqual(rv.DEBUG(),   2)
        self.assertEqual(cmp(rv.DEBUG, 'bof'), -1)
        self.assertEqual(rv.DEBUG.as_dump(), "footprints.priorities.PriorityLevel('DEBUG')")

        rv.reset()
        self.assertEqual(len(rv), 2)
        self.assertNotIn('debug', rv)

        rv.extend('default')
        self.assertEqual(len(rv), 2)
        self.assertTupleEqual(rv.levels, ('TOOLBOX', 'DEFAULT'))

        rv.remove('toolbox')
        self.assertEqual(len(rv), 1)
        self.assertNotIn('toolbox', rv)

        rv.reset()
        rv.remove(rv.TOOLBOX)
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

        with self.assertRaises(ValueError):
            rv.levelindex('foo')

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

        rtag = rv.insert(None, after='toolbox')
        self.assertIsNone(rtag)

        rv.insert('hip', after='toolbox')
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'HIP', 'DEBUG'))

        rv.insert('hip', after=rv.TOOLBOX)
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'HIP', 'DEBUG'))

        rv.freeze('hip-added')
        self.assertListEqual(rv.freezed(), ['default', 'hip-added'])

        rv.insert('hop', before='debug')
        self.assertTupleEqual(rv.levels, ('DEFAULT', 'TOOLBOX', 'HIP', 'HOP', 'DEBUG'))

        rv.insert('hop', before=rv.DEBUG)
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

    def test_priorities_methods(self):
        rv = priorities.top
        self.assertIsInstance(rv, priorities.PrioritySet)

        rv = priorities.top
        self.assertTupleEqual(rv.levels, ('NONE', 'DEFAULT', 'TOOLBOX', 'DEBUG'))

        priorities.set_after('default', 'hip', 'hop')
        self.assertTupleEqual(rv.levels, ('NONE', 'DEFAULT', 'HIP', 'HOP', 'TOOLBOX', 'DEBUG'))

        rv.reset()
        self.assertTupleEqual(rv.levels, ('NONE', 'DEFAULT', 'TOOLBOX', 'DEBUG'))

        priorities.set_before('toolbox', 'hip', 'hop')
        self.assertTupleEqual(rv.levels, ('NONE', 'DEFAULT', 'HIP', 'HOP', 'TOOLBOX', 'DEBUG'))

        rv.reset()
        self.assertTupleEqual(rv.levels, ('NONE', 'DEFAULT', 'TOOLBOX', 'DEBUG'))


# Tests for footprints observers

class utObservers(TestCase):

    def test_observers_basics(self):
        rv = observers.keys()
        self.assertListEqual(rv, [
            '__main__.FootprintTestBuiltins',
            '__main__.FootprintTestMeta',
            '__main__.FootprintTestOne',
            '__main__.FootprintTestRWD',
            '__main__.FootprintTestTwo',
        ])


# Tests for footprints reporting

class utReporting(TestCase):

    def test_reporting_methods(self):
        rv = reporting.get()
        self.assertIsInstance(rv, reporting.FootprintLog)
        self.assertEqual(rv.tag, 'default')

        rv = reporting.keys()
        self.assertListEqual(rv, ['default', 'footprint-garbage', 'void'])

        rv = reporting.get(tag='void')
        self.assertIsInstance(rv, reporting.FootprintLog)
        self.assertEqual(rv.tag, 'void')

        rv = reporting.get(tag='footprint-garbage')
        self.assertIsInstance(rv, reporting.FootprintLog)
        self.assertEqual(rv.tag, 'footprint-garbage')

    def test_reporting_null(self):
        rv = reporting.NullReport()
        self.assertIsInstance(rv, reporting.NullReport)

        rv = reporting.NullReport(1, 2, foo=3)
        self.assertIsInstance(rv, reporting.NullReport)

        rv.add('any', 2)
        self.assertEqual(len(rv), 1)

        rv.add(foo=3)
        self.assertEqual(len(rv), 2)

        rv.add('more', extra='hello')
        self.assertEqual(len(rv), 4)

    def test_reporting_log(self):
        rv = reporting.FootprintLog(tag='void')
        self.assertEqual(rv.tag, 'void')
        self.assertTrue(rv.weak)
        self.assertEqual(rv.info(), 'Report Void:')


# Tests for footprints top module methods and objects

# noinspection PyPropertyAccess
class utFootprintSetup(TestCase):

    def test_footprint_setup(self):
        setup = FootprintSetup(new=True)
        self.assertIsInstance(setup, FootprintSetup)
        self.assertIsInstance(setup.nullreport, reporting.NullReport)
        self.assertIsInstance(setup.report, bool)
        self.assertIsInstance(setup.extended, bool)
        self.assertIsInstance(setup.docstrings, bool)
        self.assertIsInstance(setup.shortnames, bool)
        self.assertIsInstance(setup.fastmode, bool)
        self.assertIsInstance(setup.fastkeys, tuple)
        self.assertIsInstance(setup.defaults, dict)
        self.assertIsInstance(setup.proxies, set)
        self.assertIs(setup.callback, None)

        setup.defaults.update(hello='foo')
        self.assertIsInstance(setup.defaults, dict)
        self.assertDictEqual(setup.defaults, dict(hello='foo'))

        setup.defaults.update(BIGCASE=2)
        self.assertDictEqual(setup.defaults, dict(hello='foo', bigcase=2))

        with self.assertRaises(AttributeError):
            del setup.defaults

        self.assertIsInstance(setup.extended, bool)
        self.assertEqual(setup.extended, True)

        setup.extended = True
        self.assertIsInstance(setup.extended, bool)
        self.assertEqual(setup.extended, True)

        setup.extended = False
        self.assertIsInstance(setup.extended, bool)
        self.assertEqual(setup.extended, False)

        setup.extended = 2
        self.assertIsInstance(setup.extended, bool)
        self.assertEqual(setup.extended, True)

        with self.assertRaises(AttributeError):
            del setup.extended

        foo = Foo()
        setup.add_proxy(foo)
        self.assertTrue(hasattr(foo, 'garbage'))
        self.assertTrue(hasattr(foo, 'garbages'))

    def test_footprint_callback(self):
        setup = FootprintSetup(new=True)
        self.assertIsInstance(setup, FootprintSetup)
        self.assertIs(setup.callback, None)

        rv = setup.extras()
        self.assertIsInstance(rv, dict)
        self.assertDictEqual(rv, dict())

        def groundvalues():
            return dict(bottomvalue=2, hello='foo')

        setup.callback = groundvalues
        self.assertIsInstance(setup.callback, type(groundvalues))

        rv = setup.extras()
        self.assertIsInstance(rv, dict)
        self.assertDictEqual(rv, dict(bottomvalue=2, hello='foo'))


# Everything (hopefuly) for the basic footprint mechanisms

# noinspection PyPropertyAccess
class utFootprint(TestCase):

    def setUp(self):
        self.fp = dict(
            attr = dict(),
            bind = [],
            info = 'Not documented',
            only = dict(),
            priority = dict(
                level = priorities.top.DEFAULT
            )
        )

        self.fpbis = Footprint(
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
                access = 'rxx',
                alias = set(),
                default = None,
                optional = False,
                remap = dict(),
                values = set(),
                outcast = set(),
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
                    'access': 'rxx',
                    'alias': set(),
                    'default': None,
                    'optional': False,
                    'remap': {},
                    'values': set(['hip', 'hop']),
                    'outcast': set(),
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
        self.assertSetEqual(fp2.attr['stuff']['values'], set([0, 1]))
        self.assertIsNot(fp1.attr['stuff']['values'], fp2.attr['stuff']['values'])

        fp2 = Footprint(fp1)
        self.assertDictEqual(fp1.as_dict(), fp2.as_dict())
        self.assertSetEqual(fp2.attr['stuff']['values'], set([0, 1]))
        self.assertIsNot(fp1.attr['stuff']['values'], fp2.attr['stuff']['values'])

    def test_footprint_optional(self):
        fp = self.fpbis
        self.assertIsInstance(fp, Footprint)
        self.assertSetEqual(fp.as_opts(), set(['arg1', 'stuff1', 'stuff2']))
        self.assertFalse(fp.optional('stuff1'))
        self.assertTrue(fp.optional('stuff2'))
        self.assertListEqual(fp.mandatory(), ['stuff1'])
        self.assertListEqual(fp.track(dict(arg1=1, stuff2='hello', stuff3=3)), ['arg1', 'stuff2'])

        with self.assertRaises(KeyError):
            self.assertTrue(fp.optional('stuff3'))

    def test_footprint_firstguess(self):
        fp = self.fpbis
        guess, inputattr = fp._firstguess(dict(weird='hello'))
        self.assertSetEqual(inputattr, set())
        self.assertDictEqual(guess, dict(
            stuff1 = None,
            stuff2 = 'foo',
        ))

        guess, inputattr = fp._firstguess(dict(stuff1='hello'))
        self.assertSetEqual(inputattr, set(['stuff1']))
        self.assertDictEqual(guess, dict(
            stuff1 = 'hello',
            stuff2 = 'foo',
        ))

        guess, inputattr = fp._firstguess(dict(arg1='hello'))
        self.assertSetEqual(inputattr, set(['stuff1']))
        self.assertDictEqual(guess, dict(
            stuff1 = 'hello',
            stuff2 = 'foo',
        ))

    def test_footprint_extras(self):
        fp = self.fpbis
        self.assertIsInstance(footprints.setup, FootprintSetup)
        self.assertIs(footprints.setup.callback, None)

        rv = fp._findextras(dict())
        self.assertIsInstance(rv, dict)
        self.assertDictEqual(rv, dict())

        def groundvalues():
            return dict(cool=2)

        footprints.setup.callback = groundvalues
        self.assertIsInstance(footprints.setup.callback, type(groundvalues))

        rv = fp._findextras(dict())
        self.assertIsInstance(rv, dict)
        self.assertDictEqual(rv, dict(cool=2))

        rv = fp._findextras(dict(foo='notused'))
        self.assertIsInstance(rv, dict)
        self.assertDictEqual(rv, dict(cool=2))

        obj = FootprintTestOne(kind='hop', someint=7)
        self.assertIsInstance(obj, FootprintTestOne)

        rv = fp._findextras(dict(foo='notused', good=obj))
        self.assertIsInstance(rv, dict)
        self.assertDictEqual(rv, dict(cool=2, kind='hop', someint=7, somestr='this'))

    def test_footprint_addextras(self):
        fp = self.fpbis
        self.assertIsInstance(footprints.setup, FootprintSetup)

        extras = dict()
        fp._addextras(extras, dict(), dict())
        self.assertDictEqual(extras, dict())

        extras = dict(foo=1)
        fp._addextras(extras, dict(), dict(cool=2))
        self.assertDictEqual(extras, dict(foo=1, cool=2))

        extras = dict(foo=1)
        fp._addextras(extras, dict(cool=2), dict(cool=2))
        self.assertDictEqual(extras, dict(foo=1))

        extras = dict(foo=1)
        fp._addextras(extras, dict(cool=2), dict(foo=2))
        self.assertDictEqual(extras, dict(foo=1))

    def test_footprint_replacement(self):
        fp = self.fpbis
        nbpass = 0
        guess = dict(nothing='void')
        extras = dict()

        with self.assertRaises(KeyError):
            u_rv = fp._replacement(nbpass, 'hip', guess, extras, guess.keys())

        rv = fp._replacement(nbpass, 'nothing', guess, extras, guess.keys())
        self.assertTrue(rv)
        self.assertDictEqual(guess, dict(nothing='void'))

        guess = dict(nothing='void', stuff1='misc_[stuff2]')

        footprints.logger.setLevel(logging.CRITICAL)
        with self.assertRaises(footprints.FootprintUnreachableAttr):
            u_rv = fp._replacement(nbpass, 'stuff1', guess, extras, guess.keys())
        footprints.logger.setLevel(logging.WARNING)

        guess, u_inputattr = fp._firstguess(dict(stuff1='misc_[stuff2]'))
        todo = guess.keys()
        self.assertDictEqual(guess, dict(stuff1='misc_[stuff2]', stuff2='foo'))
        self.assertListEqual(todo, ['stuff1', 'stuff2'])
        rv = fp._replacement(nbpass, 'stuff1', guess, extras, todo)
        self.assertFalse(rv)
        self.assertDictEqual(guess, dict(stuff1='misc_[stuff2]', stuff2='foo'))

        todo.remove('stuff2')
        rv = fp._replacement(nbpass, 'stuff1', guess, extras, todo)
        self.assertTrue(rv)
        self.assertDictEqual(guess, dict(stuff1='misc_foo', stuff2='foo'))

        guess, u_inputattr = fp._firstguess(dict(stuff1='misc_[stuff2]_and_[more]', more=2))
        todo = guess.keys()
        self.assertDictEqual(guess, dict(stuff1='misc_[stuff2]_and_[more]', stuff2='foo'))
        self.assertListEqual(todo, ['stuff1', 'stuff2'])
        todo.remove('stuff2')
        extras = dict(more=2)
        rv = fp._replacement(nbpass, 'stuff1', guess, extras, todo)
        self.assertTrue(rv)
        self.assertDictEqual(guess, dict(stuff1='misc_foo_and_2', stuff2='foo'))

    def test_footprint_replattr(self):
        fp = Footprint(self.fpbis, dict(
            attr = dict(
                somefoo = dict(
                    type = Foo,
                )
            )
        ))
        nbpass = 0
        extras = dict()

        guess, u_inputattr = fp._firstguess(dict(stuff1='misc_[somefoo:value]'))
        todo = guess.keys()
        self.assertDictEqual(guess, dict(stuff1='misc_[somefoo:value]', stuff2='foo', somefoo=None))
        self.assertListEqual(todo, ['stuff1', 'stuff2', 'somefoo'])

        thisfoo = Foo(value=2)
        guess, u_inputattr = fp._firstguess(dict(stuff1='misc_[somefoo:value]', somefoo=thisfoo))
        todo = guess.keys()
        self.assertDictEqual(guess, dict(stuff1='misc_[somefoo:value]', stuff2='foo', somefoo=thisfoo))
        self.assertListEqual(todo, ['stuff1', 'stuff2', 'somefoo'])

        todo = [ 'stuff1' ]
        rv = fp._replacement(nbpass, 'stuff1', guess, extras, todo)
        self.assertTrue(rv)
        self.assertDictEqual(guess, dict(stuff1='misc_2', stuff2='foo', somefoo=thisfoo))

    def test_footprint_replmethod(self):
        fp = self.fpbis
        nbpass = 0
        thisfoo = Foo(value=2)
        extras = dict(somefoo=thisfoo)

        guess, u_inputattr = fp._firstguess(dict(stuff1='misc_[somefoo:justdoit]', somefoo=thisfoo))
        todo = guess.keys()
        self.assertDictEqual(guess, dict(stuff1='misc_[somefoo:justdoit]', stuff2='foo'))
        self.assertListEqual(todo, ['stuff1', 'stuff2'])

        todo = [ 'stuff1' ]
        rv = fp._replacement(nbpass, 'stuff1', guess, extras, todo)
        self.assertTrue(rv)
        self.assertDictEqual(guess, dict(stuff1='misc_done_2', stuff2='foo'))

    def test_resolve_unknown(self):
        fp = Footprint(self.fpbis, dict(
            attr = dict(
                someint = dict(
                    type = int,
                    optional = True,
                    default = None,
                )
            )
        ))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='misc_[stuff2]'))
        self.assertTrue(rv)
        self.assertIsNot(footprints.UNKNOWN, None)
        self.assertDictEqual(rv, dict(stuff1='misc_foo', stuff2='foo', someint=footprints.UNKNOWN))

    def test_resolve_fatal(self):
        fp = self.fpbis

        with self.assertRaises(footprints.FootprintFatalError):
            u_rv, u_attr_input, u_attr_seen = fp.resolve(dict())

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(), fatal=False)
        self.assertTrue(rv)
        self.assertDictEqual(rv, dict(stuff1=None, stuff2='foo'))

    def test_resolve_fast(self):
        fp = Footprint(self.fpbis, dict(
            attr = dict(
                kind = dict(type=int)
            )
        ))

        rv, attr_input, attr_seen = fp.resolve(dict(stuff1='misc', kind='deux'), fast=False, fatal=False)
        self.assertDictEqual(rv, dict(stuff1='misc', stuff2='foo', kind=None))
        self.assertSetEqual(attr_input, set(['stuff1']))
        self.assertSetEqual(attr_seen, set(['kind']))

        rv, attr_input, attr_seen = fp.resolve(dict(stuff1='misc', kind='deux'), fast=True, fatal=False)
        self.assertDictEqual(rv, dict(stuff1='misc', stuff2='foo', kind=None))
        self.assertSetEqual(attr_input, set(['stuff1']))
        self.assertSetEqual(attr_seen, set(['kind']))

        fp = Footprint(self.fpbis, dict(
            attr = dict(
                stuff3 = dict(type=int)
            )
        ))

        rv, attr_input, attr_seen = fp.resolve(dict(stuff1='misc', stuff3='deux'), fast=False, fatal=False)
        self.assertDictEqual(rv, dict(stuff1='misc', stuff2='foo', stuff3=None))
        self.assertSetEqual(attr_input, set(['stuff1']))
        self.assertSetEqual(attr_seen, set(['stuff1', 'stuff2', 'stuff3']))

        rv, attr_input, attr_seen = fp.resolve(dict(stuff1='misc', stuff3='deux'), fast=True, fatal=False)
        self.assertDictEqual(rv, dict(stuff1='misc', stuff2='foo', stuff3=None))
        self.assertSetEqual(attr_input, set(['stuff1']))
        self.assertSetEqual(attr_seen, set(['stuff1', 'stuff2', 'stuff3']))

        freezed_keys = footprints.setup.fastkeys
        footprints.setup.fastkeys = ('stuff3', 'stuff4')

        rv, attr_input, attr_seen = fp.resolve(dict(stuff1='misc', stuff3='deux'), fast=True, fatal=False)
        self.assertDictEqual(rv, dict(stuff1='misc', stuff2='foo', stuff3=None))
        self.assertSetEqual(attr_input, set(['stuff1']))
        self.assertSetEqual(attr_seen, set(['stuff3']))

        footprints.setup.fastkeys = freezed_keys

    def test_resolve_reclass(self):
        fp = self.fpbis

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1=2))
        self.assertDictEqual(rv, dict(stuff1='2', stuff2='foo'))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1=True))
        self.assertDictEqual(rv, dict(stuff1='True', stuff2='foo'))

        fp = Footprint(self.fpbis, dict(
            attr = dict(
                stuff3 = dict(type=Foo)
            )
        ))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='misc', stuff3=2))
        self.assertIsInstance(rv['stuff3'], Foo)

    def test_resolve_remap(self):
        fp = Footprint(self.fpbis, dict(
            attr = dict(
                stuff1 = dict(
                    remap = dict(two='four')
                )
            )
        ))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='one'))
        self.assertDictEqual(rv, dict(stuff1='one', stuff2='foo'))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='two'))
        self.assertDictEqual(rv, dict(stuff1='four', stuff2='foo'))

        fp = Footprint(self.fpbis, dict(
            attr = dict(
                stuff1 = dict(
                    remap = dict(two='four', four='six')
                )
            )
        ))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rv, dict(stuff1='six', stuff2='foo'))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='two'))
        self.assertDictEqual(rv, dict(stuff1='six', stuff2='foo'))

    def test_resolve_isclass(self):
        fp = Footprint(self.fpbis, dict(
            attr = dict(
                stuff3 = dict(
                    type = Foo,
                    isclass = True,
                )
            )
        ))
        class MoreFoo(Foo):
            pass
        class FakeFoo(object):
            pass

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='one', stuff3=FakeFoo), fatal=False)
        self.assertDictEqual(rv, dict(stuff1='one', stuff2='foo', stuff3=None))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='one', stuff3=MoreFoo))
        self.assertDictEqual(rv, dict(stuff1='one', stuff2='foo', stuff3=MoreFoo))

    def test_resolve_values(self):
        fp = Footprint(self.fpbis, dict(
            attr = dict(
                stuff1 = dict(
                    values = ('one', 'two'),
                )
            )
        ))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'), fatal=False)
        self.assertDictEqual(rv, dict(stuff1=None, stuff2='foo'))

        fp.attr['stuff1']['values'].add('four')
        self.assertSetEqual(fp.attr['stuff1']['values'], set(['one', 'two', 'four']))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'), fatal=False)
        self.assertDictEqual(rv, dict(stuff1='four', stuff2='foo'))

    def test_resolve_outcast(self):
        fp = Footprint(self.fpbis, dict(
            attr = dict(
                stuff1 = dict(
                    outcast = ['one', 'two'],
                )
            )
        ))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'), fatal=False)
        self.assertDictEqual(rv, dict(stuff1='four', stuff2='foo'))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='one'), fatal=False)
        self.assertDictEqual(rv, dict(stuff1=None, stuff2='foo'))

        fp = Footprint(self.fpbis, dict(
            attr = dict(
                stuff1 = dict(
                    values = ['one', 'four'],
                    outcast = ['one', 'two'],
                )
            )
        ))

        self.assertSetEqual(fp.attr['stuff1']['values'], set(['one', 'four']))
        self.assertSetEqual(fp.attr['stuff1']['outcast'], set(['one', 'two']))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='six'), fatal=False)
        self.assertDictEqual(rv, dict(stuff1=None, stuff2='foo'))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='two'), fatal=False)
        self.assertDictEqual(rv, dict(stuff1=None, stuff2='foo'))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'), fatal=False)
        self.assertDictEqual(rv, dict(stuff1='four', stuff2='foo'))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='one'), fatal=False)
        self.assertDictEqual(rv, dict(stuff1=None, stuff2='foo'))

    def test_resolve_only(self):
        fp = Footprint(self.fpbis, dict(
            only = dict(
                rdate = datetime.date(2013,11,02)
            )
        ))

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertFalse(rv)

        footprints.setup.defaults.update(rdate=datetime.date(2013,11,01))

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertFalse(rv)

        footprints.setup.defaults.update(rdate=datetime.date(2013,11,02))

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertTrue(rv)

        fp = Footprint(self.fpbis, dict(
            only = dict(
                rdate = (datetime.date(2013,11,02), datetime.date(2013,11,05))
            )
        ))

        footprints.setup.defaults.update(rdate=datetime.date(2013,11,02))

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertTrue(rv)

        footprints.setup.defaults.update(rdate=datetime.date(2013,11,05))

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertTrue(rv)

        footprints.setup.defaults.update(rdate=datetime.date(2013,11,04))

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertFalse(rv)

        fp = Footprint(self.fpbis, dict(
            only = dict(
                after_rdate = datetime.date(2013,11,02)
            )
        ))

        footprints.setup.defaults.update(rdate=datetime.date(2013,11,01))

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertFalse(rv)

        footprints.setup.defaults.update(rdate=datetime.date(2013,12,03))

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertTrue(rv)

        fp = Footprint(self.fpbis, dict(
            only = dict(
                before_rdate = datetime.date(2013,11,02)
            )
        ))

        footprints.setup.defaults.update(rdate=datetime.date(2013,11,01))

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertTrue(rv)

        footprints.setup.defaults.update(rdate=datetime.date(2013,12,03))

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertFalse(rv)

        fp = Footprint(self.fpbis, dict(
            only = dict(
                after_rdate = datetime.date(2013,11,02),
                before_rdate = datetime.date(2013,11,28)
            )
        ))

        footprints.setup.defaults.update(rdate=datetime.date(2013,11,01))

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertFalse(rv)

        footprints.setup.defaults.update(rdate=datetime.date(2013,11,29))

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertFalse(rv)

        footprints.setup.defaults.update(rdate=datetime.date(2013,11,15))

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertTrue(rv)


# Base class for footprint classes

class utFootprintBase(TestCase):

    def test_metaclass_abstract(self):
        class FootprintTestMeta(FootprintBase):
            _abstract = True

        self.assertTrue(issubclass(FootprintTestMeta, FootprintBase))
        self.assertIsInstance(FootprintTestMeta._footprint, Footprint)
        self.assertTrue(FootprintTestMeta._abstract)
        self.assertTrue(FootprintTestMeta._explicit)
        self.assertTrue(FootprintTestMeta.footprint_abstract())
        self.assertTupleEqual(FootprintTestMeta._collector, ('garbage',))
        self.assertEqual(FootprintTestMeta.fullname(), '__main__.FootprintTestMeta')
        self.assertEqual(FootprintTestMeta.__doc__, 'Not documented yet.')
        self.assertListEqual(FootprintTestMeta.footprint_mandatory(), list())
        self.assertDictEqual(FootprintTestMeta._footprint.as_dict(), dict(
            attr = dict(),
            bind = list(),
            info = 'Not documented',
            only = dict(),
            priority = dict( level = priorities.top.DEFAULT )
        ))

        with self.assertRaises(KeyError):
            self.assertTrue(FootprintTestMeta.footprint_optional('foo'))

        with self.assertRaises(KeyError):
            self.assertTrue(FootprintTestMeta.footprint_values('foo'))

        with self.assertRaises(footprints.FootprintInvalidDefinition):
            u_ftm = FootprintTestMeta()

    def test_metaclass_empty(self):
        with self.assertRaises(footprints.FootprintInvalidDefinition):
            class FootprintTestMeta(FootprintBase):
                _abstract = False

    def test_metaclass_real(self):
        class FootprintTestMeta(FootprintBase):
            _abstract = False
            _explicit = False

        ftm = FootprintTestMeta()
        self.assertIsInstance(ftm._footprint, Footprint)
        self.assertListEqual(ftm.footprint_attributes, list())
        self.assertDictEqual(ftm.footprint_as_dict(), dict())
        self.assertDictEqual(ftm.footprint_export(), dict())
        self.assertEqual(ftm.footprint_clsname(), 'FootprintTestMeta')
        self.assertEqual(ftm.footprint_info, 'Not documented')

        del FootprintTestMeta

    def test_baseclass_fp1(self):
        self.assertFalse(FootprintTestOne.footprint_abstract())
        self.assertListEqual(FootprintTestOne.footprint_mandatory(), ['someint', 'kind'])
        self.assertTrue(FootprintTestOne.footprint_optional('somestr'))
        self.assertListEqual(FootprintTestOne.footprint_values('kind'), ['hip', 'hop'])
        self.assertSetEqual(
            FootprintTestOne.footprint_retrieve().as_opts(),
            set(['someint', 'somestr', 'kind', 'stuff'])
        )

        with self.assertRaises(footprints.FootprintFatalError):
            u_fp1 = FootprintTestOne(kind='hip')

        with self.assertRaises(footprints.FootprintFatalError):
            u_fp1 = FootprintTestOne(kind='hip', someint=13)

        fp1 = FootprintTestOne(kind='hip', someint=7)
        self.assertIsInstance(fp1, FootprintTestOne)
        self.assertEqual(fp1.realkind, 'bigone')
        self.assertListEqual(fp1.footprint_attributes, ['kind', 'someint', 'somestr'])
        self.assertEqual(fp1.footprint_info, 'Test class')

        fp1 = FootprintTestOne(stuff='hip', someint=7)
        self.assertIsInstance(fp1, FootprintTestOne)
        self.assertListEqual(fp1.footprint_attributes, ['kind', 'someint', 'somestr'])
        self.assertDictEqual(fp1.footprint_as_dict(), dict(
            kind = 'hip',
            someint = 7,
            somestr = 'this',
        ))

        fp1 = FootprintTestOne(stuff='foo', someint='7')
        self.assertDictEqual(fp1.footprint_as_dict(), dict(
            kind = 'hop',
            someint = 7,
            somestr = 'this',
        ))

        with self.assertRaises(AttributeError):
            fp1 = FootprintTestOne(stuff='foo', someint='7', checked=True)
            self.assertDictEqual(fp1.footprint_as_dict(), dict(
                stuff = 'foo',
                someint = '7',
            ))

        fp1 = FootprintTestOne(kind='foo', someint='7', checked=True)
        self.assertDictEqual(fp1.footprint_as_dict(), dict(
            kind = 'foo',
            someint = '7',
        ))

    def test_baseclass_fp2(self):
        self.assertFalse(FootprintTestTwo.footprint_abstract())
        self.assertListEqual(FootprintTestTwo.footprint_mandatory(), ['someint', 'kind', 'somefoo'])
        self.assertTrue(FootprintTestTwo.footprint_optional('somestr'))
        self.assertListEqual(FootprintTestTwo.footprint_values('kind'), ['hip', 'hop'])
        self.assertSetEqual(
            FootprintTestTwo.footprint_retrieve().as_opts(),
            set(['someint', 'somestr', 'kind', 'stuff', 'somefoo'])
        )

        thefoo = Foo(inside=2)

        with self.assertRaises(footprints.FootprintFatalError):
            u_fp2 = FootprintTestTwo(kind='hip', somefoo=thefoo)

        with self.assertRaises(footprints.FootprintFatalError):
            u_fp2 = FootprintTestTwo(kind='hip', somefoo=thefoo, someint=13)

        with self.assertRaises(footprints.FootprintFatalError):
            u_fp2 = FootprintTestTwo(kind='hip', somefoo=thefoo, someint=7)

        fp2 = FootprintTestTwo(kind='hip', somefoo=thefoo, someint=5)
        self.assertIsInstance(fp2, FootprintTestTwo)
        self.assertListEqual(fp2.footprint_attributes, ['kind', 'somefoo', 'someint', 'somestr'])
        self.assertEqual(fp2.footprint_info, 'Another test class')
        self.assertDictEqual(fp2.footprint_as_dict(), dict(
            kind = 'hip',
            someint = 5,
            somestr = 'this',
            somefoo = thefoo
        ))

    def test_baseclass_rwd(self):
        x = FootprintTestRWD(somefoo=Foo(inside=2), someint=4, somestr='two')
        self.assertIsInstance(x, FootprintTestRWD)
        fprwd = x.footprint
        self.assertIsInstance(fprwd, Footprint)

        self.assertEqual(fprwd.attr['someint']['access'], 'rwx')
        self.assertEqual(fprwd.attr['somefoo']['access'], 'rxx')
        self.assertEqual(fprwd.attr['somestr']['access'], 'rwd')

        self.assertEqual(x.footprint_access('someint'), 'rwx')
        self.assertEqual(x.footprint_access('somefoo'), 'rxx')
        self.assertEqual(x.footprint_access('somestr'), 'rwd')

        self.assertIsInstance(x.someint, int)
        self.assertIsInstance(x.somefoo, Foo)
        self.assertIsInstance(x.somestr, str)

        x.someint = 4
        self.assertEqual(x.someint, 4)

        x.someint = '004'
        self.assertEqual(x.someint, 4)

        with self.assertRaises(ValueError):
            x.someint = 2

        with self.assertRaises(AttributeError):
            del x.someint

        with self.assertRaises(AttributeError):
            x.somefoo = 2

        with self.assertRaises(AttributeError):
            del x.somefoo

        x.somestr = 'one'
        self.assertEqual(x.somestr, 'one')

        with self.assertRaises(ValueError):
            x.somestr = 'bof'

        delattr(x, 'somestr')
        self.assertFalse(hasattr(x, 'somestr'))

    def test_baseclass_couldbe(self):
        rv, attr_input = FootprintTestOne.footprint_couldbe(dict(kind='hip'), mkreport=False)
        self.assertFalse(rv)
        self.assertSetEqual(attr_input, set(['kind']))

        report = reporting.get(tag='void')
        self.assertIsInstance(report, reporting.FootprintLog)
        report.clear()
        self.assertDictEqual(report.as_dict(), dict())

        rv, attr_input = FootprintTestOne.footprint_couldbe(dict(kind='hip'), mkreport=True)
        self.assertFalse(rv)
        self.assertSetEqual(attr_input, set(['kind']))
        self.assertDictEqual(report.last.as_dict(), {
            '__main__.FootprintTestOne': {'someint': {'why': 'Missing value'}}
        })

        rv, attr_input = FootprintTestOne.footprint_couldbe(dict(kind='hip', someint=12), mkreport=True)
        self.assertFalse(rv)
        self.assertSetEqual(attr_input, set(['kind']))
        self.assertDictEqual(report.last.as_dict(), {
            '__main__.FootprintTestOne': {'someint': {'why': 'Not in values', 'args': 12}}
        })

        rv, attr_input = FootprintTestOne.footprint_couldbe(dict(kind='hip', someint=2), mkreport=True)
        self.assertTrue(rv)
        self.assertSetEqual(attr_input, set(['kind', 'someint']))
        self.assertDictEqual(report.last.as_dict(), {
            '__main__.FootprintTestOne': {}
        })

# Classes usint builins wrappers as attributes

class utFootprintBuiltins(TestCase):

    def test_builtins_baseclass(self):
        d = FPDict(foo=2)
        self.assertIsInstance(d, FPDict)
        self.assertIsInstance(d, dict)
        self.assertListEqual(d.items(), [('foo', 2)])
        self.assertEqual(d['foo'], 2)
        self.assertListEqual(d.keys(), ['foo'])

        l = FPList(['one', 'two', 3])
        self.assertIsInstance(l, FPList)
        self.assertIsInstance(l, list)
        self.assertListEqual(l, ['one', 'two', 3])
        self.assertListEqual(l.items(), ['one', 'two', 3])
        self.assertEqual(l[1], 'two')
        l.append(4)
        self.assertListEqual(l[:], ['one', 'two', 3, 4])

        s = FPSet(['one', 'two', 3])
        self.assertIsInstance(s, FPSet)
        self.assertIsInstance(s, set)
        self.assertSetEqual(s, set(['one', 'two', 3]))
        self.assertTupleEqual(s.items(), (3, 'two', 'one'))
        self.assertEqual(s.pop(), 3)
        s.add(4)
        self.assertTupleEqual(s.items(), (4, 'two', 'one'))

        t = FPTuple((3, 5, 7))
        self.assertIsInstance(t, FPTuple)
        self.assertIsInstance(t, tuple)
        self.assertTupleEqual(t, (3, 5, 7))
        self.assertListEqual(t.items(), [3, 5, 7])

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
        self.assertListEqual(rv.thedict.items(), [('foo', 2)])

        self.assertIsInstance(rv.thelist, FPList)
        self.assertIsInstance(rv.thelist, list)
        self.assertListEqual(rv.thelist, ['one', 'two', 3])
        self.assertListEqual(rv.thelist.items(), ['one', 'two', 3])

        self.assertIsInstance(rv.theset, FPSet)
        self.assertIsInstance(rv.theset, set)
        self.assertSetEqual(rv.theset, set([1, 2, 'three']))
        self.assertTupleEqual(rv.theset.items(), (1, 2, 'three'))

        self.assertIsInstance(rv.thetuple, FPTuple)
        self.assertIsInstance(rv.thetuple, tuple)
        self.assertTupleEqual(rv.thetuple, ('one', 'two', 3))
        self.assertListEqual(rv.thetuple.items(), ['one', 'two', 3])


class utCollector(TestCase):

    def test_collector_basics(self):
        pass


if __name__ == '__main__':
    main(verbosity=2)
    vortex.exit()
