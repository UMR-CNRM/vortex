#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from unittest import TestCase, main

import copy
import os
import shutil
import tempfile
import pickle
from weakref import WeakSet

from footprints import util, FPList, FPDict


class Foo(object):
    # noinspection PyUnusedLocal
    def __init__(self, *u_args, **kw):
        self.__dict__.update(kw)


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
            dict(a=2, c=dict(val='foo', other=dict(arg='hop'), bonus=1)),
            dict(b=7, c=dict(val='updatedfoo', other=dict(arg='hip', foo=False))),
        )
        self.assertDictEqual(rv, dict(a=2, b=7, c=dict(val='updatedfoo', other=dict(arg='hip', foo=False), bonus=1)))
        # NB: FPDicts are not merged recursively
        rv = util.dictmerge(
            dict(a=2, c=dict(val='foo', other=dict(arg='hop'), bonus=1)),
            dict(b=7, c=FPDict(val='updatedfoo', other=dict(arg='hip', foo=False))),
        )
        self.assertDictEqual(rv, dict(a=2, b=7, c=FPDict(val='updatedfoo', other=dict(arg='hip', foo=False))))


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


# A pure internal usage

class utMktuple(TestCase):

    def test_mktuple_direct(self):
        self.assertTupleEqual(util.mktuple([1, 2, 3]), (1, 2, 3))
        self.assertTupleEqual(util.mktuple((1, 2, 3)), (1, 2, 3))
        self.assertSetEqual(set(util.mktuple(set([1, 2, 3]))), set((1, 2, 3)))

    def test_mktuple_weird(self):
        thefoo = Foo()
        self.assertTupleEqual(util.mktuple(thefoo), (thefoo, ))


# A pure internal usage

class utTime(TestCase):

    def test_time_basics(self):

        with self.assertRaises(ValueError):
            util.TimeInt("Toto")

        with self.assertRaises(ValueError):
            util.TimeInt(1.5)

        t = util.TimeInt(0)
        self.assertEqual(str(t), '0')
        self.assertEqual(t.str_time, '0000:00')

        t = util.TimeInt(128)
        self.assertEqual(str(t), '128')
        self.assertEqual(t.str_time, '0128:00')

        t = util.TimeInt('16:30')
        self.assertEqual(str(t), '0016:30')

        t = util.TimeInt('0007:45')
        self.assertEqual(str(t), '0007:45')

        a = util.TimeInt(48)
        b = util.TimeInt(':2880')
        self.assertEqual(a, b)

        self.assertEqual(a.realtype, 'int')
        self.assertEqual(b.realtype, 'time')

    def test_time_compute(self):
        for (lhs, rhs) in [(lambda x: util.TimeInt(x), lambda x: util.TimeInt(x)),
                           (lambda x: util.TimeInt(x), lambda x: x),
                           (lambda x: x, lambda x: util.TimeInt(x))]:
            t = lhs('07:45')
            t = t + rhs('1:22')
            self.assertEqual(str(t), '0009:07')
            t = lhs('09:07')
            t = t - rhs('9:05')
            self.assertEqual(str(t), '0000:02')
            t = lhs('00:02')
            t = t - rhs('0:04')
            self.assertEqual(str(t), '-0000:02')
            t = lhs('-00:02')
            t = t + rhs('0:04')
            self.assertEqual(str(t), '0000:02')
            t = lhs('00:02')
            t = t + rhs('1:04')
            self.assertEqual(str(t), '0001:06')
            t = lhs('07:45')
            t = t * rhs(2)
            self.assertEqual(str(t), '0015:30')
            t = lhs('07:45')
            t = t * rhs(-1)
            self.assertEqual(str(t), '-0007:45')
            t = lhs('01:30')
            t = t * rhs('0:20')
            self.assertEqual(str(t), '0000:30')

    def test_time_compare(self):
        t = util.TimeInt(6)
        self.assertFalse(t is None)
        self.assertFalse(t == 'Toto')
        self.assertTrue(t == 6)
        self.assertTrue(t >= 6)
        self.assertTrue(t <= 6)
        self.assertTrue(hash(t) == hash(util.TimeInt('6:00')))
        self.assertFalse(t > 6)
        self.assertFalse(t < 6)
        self.assertTrue(t == '06')
        self.assertTrue(t == '6:00')
        t = util.TimeInt('6:30')
        self.assertFalse(t == 6)
        self.assertFalse(hash(t) == hash(util.TimeInt('6:00')))
        self.assertTrue(t > 6)
        self.assertFalse(t < 6)
        self.assertFalse(t < '6:30')
        self.assertTrue(t < '6:31')
        self.assertTrue(t <= '6:31')
        self.assertTrue(t > '6:29')
        self.assertTrue(t >= '6:29')
        t = util.TimeInt('-6:30')
        self.assertFalse(t == -6)
        self.assertFalse(hash(t) == hash(util.TimeInt('6:00')))
        self.assertFalse(t > -6)
        self.assertTrue(t < -6)
        self.assertFalse(t < '-6:30')
        self.assertFalse(t < '-6:31')
        self.assertTrue(t < '-6:29')
        self.assertTrue(t < '6:30')


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

    def test_rangex_basics_times(self):
        rv = util.rangex('2:15')
        self.assertListEqual(rv, ['0002:15'])

        rv = util.rangex('2:15,3:45')
        self.assertListEqual(rv, ['0002:15', '0003:45'])

        rv = util.rangex('10:00', '3:10', '-:15')
        self.assertListEqual(rv, ['0003:15', '0003:30', '0003:45', '0004:00', '0004:15', '0004:30', '0004:45', '0005:00', '0005:15', '0005:30', '0005:45', '0006:00', '0006:15', '0006:30', '0006:45', '0007:00', '0007:15', '0007:30', '0007:45', '0008:00', '0008:15', '0008:30', '0008:45', '0009:00', '0009:15', '0009:30', '0009:45', '0010:00'])

        rv = util.rangex('-9:00', '-7:00', shift=2)
        self.assertListEqual(rv, [-7, -6, -5])

        rv = util.rangex('-9:10', '-7:00', shift=2)
        self.assertListEqual(rv, ['-0005:10', '-0006:10', '-0007:10'])

        rv = util.rangex('-1:10', '2:10')
        self.assertListEqual(rv, ['-0000:10', '-0001:10', '0000:50', '0001:50'])

    def test_rangex_minus(self):
        rv = util.rangex('0-30-6,36-72-12')
        self.assertListEqual(rv, [0, 6, 12, 18, 24, 30, 36, 48, 60, 72])

        rv = util.rangex(['0-30-6', '36-72-12'])
        self.assertListEqual(rv, [0, 6, 12, 18, 24, 30, 36, 48, 60, 72])

        rv = util.rangex('0-30-6,36', 48, 12)
        self.assertListEqual(rv, [0, 6, 12, 18, 24, 30, 36, 48])

        rv = util.rangex(('0-30-6', 36), 48, 12)
        self.assertListEqual(rv, [0, 6, 12, 18, 24, 30, 36, 48])

        rv = util.rangex('-30--6-6,36')
        self.assertListEqual(rv, [-30, -24, -18, -12, -6, 36])

        rv = util.rangex('0-12', step=3, shift=1)
        self.assertListEqual(rv, [1, 4, 7, 10, 13])

    def test_rangex_minus_times(self):
        rv = util.rangex('0-3-:15,3:30-6-:30')
        self.assertListEqual(rv, ['0000:00', '0000:15', '0000:30', '0000:45', '0001:00', '0001:15', '0001:30', '0001:45', '0002:00', '0002:15', '0002:30', '0002:45', '0003:00', '0003:30', '0004:00', '0004:30', '0005:00', '0005:30', '0006:00'])

        rv = util.rangex('0-3-:30,0:15', 6, '00:45')
        self.assertListEqual(rv, ['0000:00', '0000:15', '0000:30', '0001:00', '0001:30', '0001:45', '0002:00', '0002:30', '0003:00', '0003:15', '0004:00', '0004:45', '0005:30'])

        rv = util.rangex('0:30-12', step='1:00', shift=1)
        self.assertListEqual(rv, ['0001:30', '0002:30', '0003:30', '0004:30', '0005:30', '0006:30', '0007:30', '0008:30', '0009:30', '0010:30', '0011:30', '0012:30'])

        rv = util.rangex('00:30--1--:30')
        self.assertListEqual(rv, ['-0000:30', '-0001:00', '0000:00', '0000:30'])

    def test_rangex_comma(self):
        rv = util.rangex('0,4', 12, 3, 0)
        self.assertListEqual(rv, [0, 3, 4, 6, 7, 9, 10, 12])

        rv = util.rangex((0, 4), 12, 3, 0)
        self.assertListEqual(rv, [0, 3, 4, 6, 7, 9, 10, 12])

    def test_rangex_fmt(self):
        rv = util.rangex('2-5', fmt='%03d')
        self.assertListEqual(rv, ['002', '003', '004', '005'])

        rv = util.rangex('2-5', fmt='{0:03d}')
        self.assertListEqual(rv, ['002', '003', '004', '005'])

        rv = util.rangex('2-5', fmt='{2:s}({0:02d})')
        self.assertListEqual(rv, ['int(02)', 'int(03)', 'int(04)', 'int(05)'])

    def test_rangex_fmt_times(self):
        rv = util.rangex('2-3-:30', fmt='%10s')
        self.assertListEqual(rv, ['0002:00   ', '0002:30   ', '0003:00   '])

    def test_rangex_prefix(self):
        rv = util.rangex('foo_0', 5, 2)
        self.assertListEqual(rv, ['foo_0', 'foo_2', 'foo_4', ])

        rv = util.rangex('foo_0-5-2', fmt='%02d')
        self.assertListEqual(rv, ['foo_00', 'foo_02', 'foo_04', ])

        rv = util.rangex(1, 7, 3, prefix='hello-')
        self.assertListEqual(rv, ['hello-1', 'hello-4', 'hello-7', ])

        rv = util.rangex(1, 7, 3, prefix='hello-', shift=2, fmt='%02d')
        self.assertListEqual(rv, ['hello-03', 'hello-06', 'hello-09'])

        rv = util.rangex(1, 7, 3, prefix='value no.', fmt='{1:d} is {0:d}')
        self.assertListEqual(rv, ['value no.1 is 1', 'value no.2 is 4', 'value no.3 is 7'])

    def test_rangex_prefix_times(self):
        rv = util.rangex('foo_0:15', 2, ':15')
        self.assertListEqual(rv, ['foo_0000:15', 'foo_0000:30', 'foo_0000:45', 'foo_0001:00', 'foo_0001:15', 'foo_0001:30', 'foo_0001:45', 'foo_0002:00'])

        rv = util.rangex('foo_0', -2, ':15')
        self.assertListEqual(rv, [])

        rv = util.rangex('foo_0', -1, '-:15')
        self.assertListEqual(rv, ['foo_-0000:15', 'foo_-0000:30', 'foo_-0000:45', 'foo_-0001:00', 'foo_0000:00'])

        rv = util.rangex('10:00', '8:10', '-:15', prefix='toto-')
        self.assertListEqual(rv, ['toto-0008:15', 'toto-0008:30', 'toto-0008:45', 'toto-0009:00', 'toto-0009:15', 'toto-0009:30', 'toto-0009:45', 'toto-0010:00'])

        rv = util.rangex('10:00', '9:10', '-:15', prefix='toto-', shift='0:01')
        self.assertListEqual(rv, ['toto-0009:16', 'toto-0009:31', 'toto-0009:46', 'toto-0010:01'])

        rv = util.rangex('10:00', '9:10', '-:15', prefix='value no.', fmt='{1:d} is {0:s}')
        self.assertListEqual(rv, ['value no.1 is 0009:15', 'value no.2 is 0009:30', 'value no.3 is 0009:45', 'value no.4 is 0010:00'])


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
        rv = util.expand(dict(arg='hop', item=(1, 2, 3)))
        self.assertListEqual(rv, [
            {'arg': 'hop', 'item': 1},
            {'arg': 'hop', 'item': 2},
            {'arg': 'hop', 'item': 3}
        ])

        rv = util.expand(dict(arg='hop', item=[4, 5, 6]))
        self.assertListEqual(rv, [
            {'arg': 'hop', 'item': 4},
            {'arg': 'hop', 'item': 5},
            {'arg': 'hop', 'item': 6}
        ])

        rv = util.expand(dict(arg='hop', item=set([7, 8, 9])))
        rv = sorted(rv,
                    key=lambda i: '_'.join([i['arg'], str(i['item'])]))
        self.assertListEqual(rv, [
            {'arg': 'hop', 'item': 7},
            {'arg': 'hop', 'item': 8},
            {'arg': 'hop', 'item': 9}
        ])

    def test_expend_memory_wall(self):

        def recursive_item(item, depth, stuff):
            if depth >= 25:
                return stuff
            item = [recursive_item(stuff, depth + 1, stuff), ] * len(item)
            return item

        with self.assertRaises(MemoryError):
            util.expand(dict(arg='hop',
                             item=recursive_item((1, 2, ), 1, (1, ))
                             )
                        )

    def test_expand_strings(self):
        rv = util.expand(dict(arg='hop', item='a,b,c'))
        self.assertListEqual(rv, [
            {'arg': 'hop', 'item': 'a'},
            {'arg': 'hop', 'item': 'b'},
            {'arg': 'hop', 'item': 'c'}
        ])

        rv = util.expand(dict(arg='hop', item='range(2)'))
        self.assertListEqual(rv, [
            {'arg': 'hop', 'item': 2}
        ])

        rv = util.expand(dict(arg='hop', item='range(2,4)'))
        self.assertListEqual(rv, [
            {'arg': 'hop', 'item': 2},
            {'arg': 'hop', 'item': 3},
            {'arg': 'hop', 'item': 4}
        ])

        rv = util.expand(dict(arg='hop', item='range(1,7,3)'))
        self.assertListEqual(rv, [
            {'arg': 'hop', 'item': 1},
            {'arg': 'hop', 'item': 4},
            {'arg': 'hop', 'item': 7}
        ])

    def test_expand_glob(self):
        tmpd = tempfile.mkdtemp()
        (u_tmpio, tmpf) = tempfile.mkstemp(dir=tmpd)
        for a in ('hip', 'hop'):
            for b in range(3):
                shutil.copyfile(tmpf, '{0:s}/xx_{1:s}_{2:04d}'.format(tmpd, a, b))
                shutil.copyfile(tmpf, '{0:s}/xx_{1:s}_{2:04d}:{3:02d}'.format(tmpd, a, b, b * 9))
                shutil.copyfile(tmpf, '{0:s}/xx_{1:s}_{2:04d}:0'.format(tmpd, a, b))
                shutil.copyfile(tmpf, '{0:s}/xx_{1:s}_{2:04d}:tr'.format(tmpd, a, b))
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
        rv = sorted(rv,
                    key=lambda i: '_'.join([i['arg'], i['look'], i['seta'], i['setb']]))
        self.assertListEqual(rv, [
            {'arg': 'multi', 'look': 'xx_hip_0000', 'seta': 'hip', 'setb': '0000'},
            {'arg': 'multi', 'look': 'xx_hip_0001', 'seta': 'hip', 'setb': '0001'},
            {'arg': 'multi', 'look': 'xx_hip_0002', 'seta': 'hip', 'setb': '0002'},
            {'arg': 'multi', 'look': 'xx_hop_0000', 'seta': 'hop', 'setb': '0000'},
            {'arg': 'multi', 'look': 'xx_hop_0001', 'seta': 'hop', 'setb': '0001'},
            {'arg': 'multi', 'look': 'xx_hop_0002', 'seta': 'hop', 'setb': '0002'}
        ])
        rv = util.expand(dict(
            arg='multi',
            look='xx_{glob:a:\w+}_{glob:b:\d+(?::\d\d)?}',
            seta='[glob:a]',
            setb='[glob:b]'
        ))
        rv = sorted(rv,
                    key=lambda i: '_'.join([i['arg'], i['look'], i['seta'], i['setb']]))
        self.assertListEqual(rv, [
            {'arg': 'multi', 'look': 'xx_hip_0000:00', 'seta': 'hip', 'setb': '0000:00'},
            {'arg': 'multi', 'look': 'xx_hip_0000', 'seta': 'hip', 'setb': '0000'},
            {'arg': 'multi', 'look': 'xx_hip_0001:09', 'seta': 'hip', 'setb': '0001:09'},
            {'arg': 'multi', 'look': 'xx_hip_0001', 'seta': 'hip', 'setb': '0001'},
            {'arg': 'multi', 'look': 'xx_hip_0002:18', 'seta': 'hip', 'setb': '0002:18'},
            {'arg': 'multi', 'look': 'xx_hip_0002', 'seta': 'hip', 'setb': '0002'},
            {'arg': 'multi', 'look': 'xx_hop_0000:00', 'seta': 'hop', 'setb': '0000:00'},
            {'arg': 'multi', 'look': 'xx_hop_0000', 'seta': 'hop', 'setb': '0000'},
            {'arg': 'multi', 'look': 'xx_hop_0001:09', 'seta': 'hop', 'setb': '0001:09'},
            {'arg': 'multi', 'look': 'xx_hop_0001', 'seta': 'hop', 'setb': '0001'},
            {'arg': 'multi', 'look': 'xx_hop_0002:18', 'seta': 'hop', 'setb': '0002:18'},
            {'arg': 'multi', 'look': 'xx_hop_0002', 'seta': 'hop', 'setb': '0002'},
        ])
        shutil.rmtree(tmpd)

    def test_expand_mixed(self):
        rv = util.expand(dict(
            arg='hop',
            atuple=('one', 'two'),
            alist=['a', 'b'],
            aset=set(['banana', 'orange']),
            astr='this,that',
            arange='range(1,7,3)'
        ))
        rv = sorted(rv,
                    key=lambda i: '_'.join([i['alist'], str(i['arange']), i['aset'], i['astr'], i['atuple']]))
        self.assertEqual(len(rv), 48)
        self.assertListEqual(rv, [
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

    def test_expand_dict(self):
        rv = util.expand(dict(arg=('hip', 'hop'), item=dict(arg={'hip': 'hop', 'hop': 'hip'})))
        self.assertListEqual(rv, [
            {'arg': 'hip', 'item': 'hop'},
            {'arg': 'hop', 'item': 'hip'},
        ])

    def test_expand_FP(self):
        rv = util.expand(dict(arg=('hip', 'hop'), item=FPList([1, 2, 3])))
        self.assertListEqual(rv, [
            {'arg': 'hip', 'item': FPList([1, 2, 3])},
            {'arg': 'hop', 'item': FPList([1, 2, 3])},
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
        self.assertSetEqual(set(rv()), set([2, self.o1]))

        rv.discard(5)
        self.assertTrue(rv.filled)
        self.assertSetEqual(set(rv()), set([2, self.o1]))

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


# Base for Lower and UpperCaseDict objects

# noinspection PyPropertyAccess
class utCaseDict(TestCase):

    def setUp(self):
        self.tdict = {'Toto': 1, 'blop': 2, 'SCRONTCH': 3}
        self.ld = util.LowerCaseDict(self.tdict)
        self.ud = util.UpperCaseDict(self.tdict)

    def test_case_processing(self):
        self.setUp()
        for speciald in (self.ld, self.ud):
            self.assertIn('Toto', speciald)
            self.assertIn('toto', speciald)
            self.assertIn('TOTO', speciald)
            self.assertIn('toTo', speciald)
            del speciald['scrontch']
            self.assertNotIn('SRONTch', speciald)
            speciald['blop'] = 3
            speciald['bLop'] = 4
            speciald['BLOP'] = 4
            self.assertEqual(speciald['blop'], 4)
            self.assertEqual(len(speciald), 2)

    def test_special_content(self):
        self.setUp()
        self.assertDictEqual(self.ld,
                             {k.lower(): v for k, v in self.tdict.items()})
        self.assertDictEqual(self.ud,
                             {k.upper(): v for k, v in self.tdict.items()})


class utGetByTag(TestCase):

    def test_getbytag_basics(self):

        class Tag0(util.GetByTag):
            pass

        class Tag1(Tag0):
            pass

        class Tag2(Tag0):
            _tag_topcls = False

        # topcls or not...
        a = Tag0()
        b = Tag0()
        self.assertIs(a, b)
        self.assertEqual(a.tag, 'default')
        b = Tag1()
        self.assertIsNot(a, b)
        b = Tag2()
        self.assertIs(a, b)
        # With a customized tag
        b = Tag0(tag='truc')
        self.assertIsNot(a, b)
        c = Tag0('truc')
        self.assertIs(b, c)
        # Force creation
        c = Tag0(tag='truc', new=True)
        self.assertIsNot(a, b)
        # Some of the class methods
        self.assertSequenceEqual(Tag0.tag_keys(), ['default', 'truc'])
        self.assertSetEqual(set(Tag0.tag_values()), set([a, c]))
        self.assertSetEqual(set(Tag0.tag_items()), set([('default', a),
                                                        ('truc', c)]))
        self.assertSetEqual(set(Tag0.tag_classes()), set([Tag0, Tag2]))
        # Ugly copies
        self.assertIs(copy.copy(a), a)
        self.assertIs(copy.deepcopy(a), a)
        # The end
        Tag0.tag_clear()
        self.assertListEqual(Tag0.tag_values(), [])

    def test_getbytag_focus(self):

        class Tag0(util.GetByTag):

            def __init__(self):
                self.flag = 'bare'

            def focus_loose_hook(self):
                super(Tag0, self).focus_loose_hook()
                self.flag = 'sleeping'

            def focus_gain_hook(self):
                super(Tag0, self).focus_gain_hook()
                self.flag = 'focused'

            def focus_gain_allow(self):
                super(Tag0, self).focus_gain_allow()
                if self.tag == 'third':
                    raise RuntimeError('No way I will get focus')

        a = Tag0('first')
        b = Tag0('second')
        c = Tag0('third')

        for o in (a, b, c):
            self.assertEqual(o.flag, 'bare')
        # a
        a.catch_focus()
        self.assertEqual(a.flag, 'focused')
        self.assertTrue(a.has_focus())
        self.assertEqual(Tag0.tag_focus(), 'first')
        for o in (b, c):
            self.assertEqual(o.flag, 'bare')
            self.assertFalse(o.has_focus())
        # b
        Tag0.set_focus(b)
        self.assertEqual(a.flag, 'sleeping')
        self.assertFalse(a.has_focus())
        self.assertEqual(b.flag, 'focused')
        self.assertTrue(b.has_focus())
        # c
        with self.assertRaises(RuntimeError):
            # c should never be allowed to get the focus
            c.catch_focus()
        # As result nothing has changed...
        self.assertEqual(b.flag, 'focused')
        self.assertTrue(b.has_focus())
        self.assertEqual(c.flag, 'bare')
        self.assertFalse(c.has_focus())


if __name__ == '__main__':
    main(verbosity=2)