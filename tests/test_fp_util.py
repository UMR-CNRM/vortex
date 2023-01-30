from unittest import TestCase, main

import os
import shutil
import tempfile

from bronx.fancies import loggers

from footprints import util, FPList


class Foo:
    # noinspection PyUnusedLocal
    def __init__(self, *u_args, **kw):
        self.__dict__.update(kw)


# Tests for footprints util

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


# In-place substitution in lists

class utInPlace(TestCase):

    def setUp(self):
        class Foo:
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
            globs=dict(z='bar')
        )
        self.assertDictEqual(rv, dict(a=True, c='foo_bar'))


# Generic expand mechanism

class utExpand(TestCase):

    def test_expand_basics(self):
        rv = util.expand(dict(a=2, c='foo'))
        self.assertListEqual(rv, [dict(a=2, c='foo', index_expansion=1), ])

    def test_expand_iters(self):
        rv = util.expand(dict(arg='hop', item=(1, 2, 3)))
        self.assertListEqual(rv, [
            {'arg': 'hop', 'item': 1, 'index_expansion': 1},
            {'arg': 'hop', 'item': 2, 'index_expansion': 2},
            {'arg': 'hop', 'item': 3, 'index_expansion': 3}
        ])

        rv = util.expand(dict(arg='hop', item=[4, 5, 6]))
        self.assertListEqual(rv, [
            {'arg': 'hop', 'item': 4, 'index_expansion': 1},
            {'arg': 'hop', 'item': 5, 'index_expansion': 2},
            {'arg': 'hop', 'item': 6, 'index_expansion': 3}
        ])

        rv = util.expand(dict(arg='hop', item={7, 8, 9}))
        rv = sorted(rv,
                    key=lambda i: '_'.join([i['arg'], str(i['item'])]))
        self.assertListEqual(
            [{k: v for k, v in rvi.items() if k not in ('index_expansion', )}
             for rvi in rv],
            [
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

        with loggers.contextboundGlobalLevel('critical'):
            with self.assertRaises(MemoryError):
                util.expand(dict(arg='hop',
                                 item=recursive_item((1, 2, ), 1, (1, ))
                                 )
                            )

    def test_expand_strings(self):
        rv = util.expand(dict(arg='hop', item='a,b,c'))
        self.assertListEqual(rv, [
            {'arg': 'hop', 'item': 'a', 'index_expansion': 1},
            {'arg': 'hop', 'item': 'b', 'index_expansion': 2},
            {'arg': 'hop', 'item': 'c', 'index_expansion': 3}
        ])

        rv = util.expand(dict(arg='hop', item='range(2)'))
        self.assertListEqual(rv, [
            {'arg': 'hop', 'item': 2, 'index_expansion': 1}
        ])

        rv = util.expand(dict(arg='hop', item='range(2,4)'))
        self.assertListEqual(rv, [
            {'arg': 'hop', 'item': 2, 'index_expansion': 1},
            {'arg': 'hop', 'item': 3, 'index_expansion': 2},
            {'arg': 'hop', 'item': 4, 'index_expansion': 3}
        ])

        rv = util.expand(dict(arg='hop', item='range(1,7,3)'))
        self.assertListEqual(rv, [
            {'arg': 'hop', 'item': 1, 'index_expansion': 1},
            {'arg': 'hop', 'item': 4, 'index_expansion': 2},
            {'arg': 'hop', 'item': 7, 'index_expansion': 3}
        ])

    def test_expand_glob(self):
        tmpd = tempfile.mkdtemp()
        try:
            (tmpio, tmpf) = tempfile.mkstemp(dir=tmpd)
            for a in ('hip', 'hop'):
                for b in range(3):
                    shutil.copyfile(tmpf, '{:s}/xx_{:s}_{:04d}'.format(tmpd, a, b))
                    shutil.copyfile(tmpf, '{:s}/xx_{:s}_{:04d}:{:02d}'.format(tmpd, a, b, b * 9))
                    shutil.copyfile(tmpf, '{:s}/xx_{:s}_{:04d}:0'.format(tmpd, a, b))
                    shutil.copyfile(tmpf, '{:s}/xx_{:s}_{:04d}:tr'.format(tmpd, a, b))
            os.close(tmpio)
            os.unlink(tmpf)
            # No match
            rv = util.expand(dict(
                arg='multi',
                look=r'xx_{glob:a:\w+}_{glob:b:\d+}',
                seta='[glob:a]',
                setb='[glob:b]'
            ))
            self.assertListEqual(sorted(rv), [])
            # Match a complex directory
            rv = util.expand(dict(
                arg='multi',
                look=tmpd + r'/*_{glob:a:\w+}_{glob:b:\d+}',
                seta='[glob:a]',
                setb='[glob:b]'
            ))
            self.assertListEqual(rv, [
                {'arg': 'multi', 'look': tmpd + '/xx_hip_0000', 'seta': 'hip', 'setb': '0000', 'index_expansion': 1},
                {'arg': 'multi', 'look': tmpd + '/xx_hip_0001', 'seta': 'hip', 'setb': '0001', 'index_expansion': 2},
                {'arg': 'multi', 'look': tmpd + '/xx_hip_0002', 'seta': 'hip', 'setb': '0002', 'index_expansion': 3},
                {'arg': 'multi', 'look': tmpd + '/xx_hop_0000', 'seta': 'hop', 'setb': '0000', 'index_expansion': 4},
                {'arg': 'multi', 'look': tmpd + '/xx_hop_0001', 'seta': 'hop', 'setb': '0001', 'index_expansion': 5},
                {'arg': 'multi', 'look': tmpd + '/xx_hop_0002', 'seta': 'hop', 'setb': '0002', 'index_expansion': 6}
            ])
            # Jump to the tmp directory
            curdir = os.getcwd()
            try:
                os.chdir(tmpd)
                rv = util.expand(dict(
                    arg='multi',
                    look=r'xx_{glob:a:\w+}_{glob:b:\d+}',
                    seta='[glob:a]',
                    setb='[glob:b]'
                ))
                self.assertListEqual(rv, [
                    {'arg': 'multi', 'look': 'xx_hip_0000', 'seta': 'hip', 'setb': '0000', 'index_expansion': 1},
                    {'arg': 'multi', 'look': 'xx_hip_0001', 'seta': 'hip', 'setb': '0001', 'index_expansion': 2},
                    {'arg': 'multi', 'look': 'xx_hip_0002', 'seta': 'hip', 'setb': '0002', 'index_expansion': 3},
                    {'arg': 'multi', 'look': 'xx_hop_0000', 'seta': 'hop', 'setb': '0000', 'index_expansion': 4},
                    {'arg': 'multi', 'look': 'xx_hop_0001', 'seta': 'hop', 'setb': '0001', 'index_expansion': 5},
                    {'arg': 'multi', 'look': 'xx_hop_0002', 'seta': 'hop', 'setb': '0002', 'index_expansion': 6}
                ])
                rv = util.expand(dict(
                    arg='multi',
                    look=r'x?_{glob:a:\w+}_{glob:b:\d{4}(?::\d{2})?}',
                    seta='[glob:a]',
                    setb='[glob:b]'
                ))
                self.assertListEqual(
                    rv,
                    [
                        {'arg': 'multi', 'look': 'xx_hip_0000', 'seta': 'hip', 'setb': '0000',
                         'index_expansion': 1},
                        {'arg': 'multi', 'look': 'xx_hip_0000:00', 'seta': 'hip', 'setb': '0000:00',
                         'index_expansion': 2},
                        {'arg': 'multi', 'look': 'xx_hip_0001', 'seta': 'hip', 'setb': '0001',
                         'index_expansion': 3},
                        {'arg': 'multi', 'look': 'xx_hip_0001:09', 'seta': 'hip', 'setb': '0001:09',
                         'index_expansion': 4},
                        {'arg': 'multi', 'look': 'xx_hip_0002', 'seta': 'hip', 'setb': '0002',
                         'index_expansion': 5},
                        {'arg': 'multi', 'look': 'xx_hip_0002:18', 'seta': 'hip', 'setb': '0002:18',
                         'index_expansion': 6},
                        {'arg': 'multi', 'look': 'xx_hop_0000', 'seta': 'hop', 'setb': '0000',
                         'index_expansion': 7},
                        {'arg': 'multi', 'look': 'xx_hop_0000:00', 'seta': 'hop', 'setb': '0000:00',
                         'index_expansion': 8},
                        {'arg': 'multi', 'look': 'xx_hop_0001', 'seta': 'hop', 'setb': '0001',
                         'index_expansion': 9},
                        {'arg': 'multi', 'look': 'xx_hop_0001:09', 'seta': 'hop', 'setb': '0001:09',
                         'index_expansion': 10},
                        {'arg': 'multi', 'look': 'xx_hop_0002', 'seta': 'hop', 'setb': '0002',
                         'index_expansion': 11},
                        {'arg': 'multi', 'look': 'xx_hop_0002:18', 'seta': 'hop', 'setb': '0002:18',
                         'index_expansion': 12},
                    ]
                )
                with self.assertRaises(ValueError):
                    rv = util.expand(dict(
                        look=r'x?_{glob:a:\w+}_{glob:b:\d{4}(?::\d{2)?}',  # Unbalanced
                    ))
                with self.assertRaises(ValueError):
                    rv = util.expand(dict(
                        look=r'xx_{glob:a:\w+}_{glob:b:[\d+}',  # Compilation error
                    ))
            finally:
                os.chdir(curdir)
        finally:
            shutil.rmtree(tmpd)

    def test_expand_mixed(self):
        rv = util.expand(dict(
            arg='hop',
            atuple=('one', 'two'),
            alist=['a', 'b'],
            aset={'banana', 'orange'},
            astr='this,that',
            arange='range(1,7,3)'
        ))
        rv = sorted(rv,
                    key=lambda i: '_'.join([i['alist'], str(i['arange']), i['aset'], i['astr'], i['atuple']]))
        self.assertEqual(len(rv), 48)
        self.assertListEqual(
            [{k: v for k, v in rvi.items() if k not in ('index_expansion',)}
             for rvi in rv],
            [
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
            ]
        )

    def test_expand_dict(self):
        rv = util.expand(dict(arg=('hip', 'hop'), item=dict(arg={'hip': 'hop', 'hop': 'hip'})))
        self.assertListEqual(rv, [
            {'arg': 'hip', 'item': 'hop', 'index_expansion': 1},
            {'arg': 'hop', 'item': 'hip', 'index_expansion': 2},
        ])

    def test_expand_FP(self):
        rv = util.expand(dict(arg=('hip', 'hop'), item=FPList([1, 2, 3])))
        self.assertListEqual(rv, [
            {'arg': 'hip', 'item': FPList([1, 2, 3]), 'index_expansion': 1},
            {'arg': 'hop', 'item': FPList([1, 2, 3]), 'index_expansion': 2},
        ])


if __name__ == '__main__':
    main(verbosity=2)
