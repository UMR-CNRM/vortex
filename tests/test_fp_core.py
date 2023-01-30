from unittest import TestCase, main

from contextlib import contextmanager
import copy
from io import StringIO
import datetime
import logging
import re
import sys
import types

from bronx.fancies import loggers

import footprints
from footprints import Footprint, DecorativeFootprint, FootprintBase
from footprints import doc, priorities, reporting, collectors
from footprints.config import FootprintSetup

tloglevel = 'critical'


# Classes to be used in module scope

class Foo:
    # noinspection PyUnusedLocal
    def __init__(self, *u_args, **kw):
        self.__dict__.update(kw)

    def justdoit(self, guess, extras):
        return 'done_' + str(len(guess))

    def justanint(self, guess, extras):
        return 3

    @property
    def justprop(self):
        return 3

    def justraise(self, guess, extras):
        raise ValueError('Toto')


class FootprintTestOne(FootprintBase):
    _footprint = [
        dict(
            info='Test class',
            attr=dict(
                kind=dict(
                    values=['hip', 'hop'],
                    alias=('stuff',),
                    remap=dict(foo='hop')
                ),
                somestr=dict(
                    values=['this', 'or', 'that'],
                    optional=True,
                    default='this'
                )
            )
        ),
        dict(
            attr=dict(
                someint=dict(
                    values=list(range(10)),
                    type=int,
                ),
                someMixedCase=dict(
                    optional=True,
                    values=['why ?', 'toto'],
                )
            )
        )
    ]

    @property
    def realkind(self):
        return 'bigone'


class FootprintTestTwo(FootprintTestOne):
    _mkshort = True
    _footprint = dict(
        info='Another test class',
        attr=dict(
            kind=dict(
                values=['hip', 'hop', 'poom'],
            ),
            somefoo=dict(
                type=Foo
            ),
            someint=dict(
                outcast=(2, 7)
            )
        )
    )

    footprint_toto = 2


class FootprintTestRWD(FootprintBase):
    _footprint = dict(
        info='Test attributes access',
        attr=dict(
            someint=dict(
                type=int,
                access='rwx',
                outcast=(2, 7)
            ),
            somefoo=dict(
                type=Foo,
                access='rxx'
            ),
            somestr=dict(
                access='rwd',
                values=('one', 'two', 'five')
            )
        )
    )


class FooFP(FootprintBase):
    _footprint = dict(
        info='To test footprint class as footprint attributes (see FootprintTestFpAttr)',
        attr=dict(
            blop=dict(
                type=int,
            ),
            scrontch=dict(
            ),
        )
    )


class FootprintTestFpAttr(FootprintTestOne):
    _footprint = dict(
        info='Yet another test class',
        attr=dict(
            somefoo=dict(
                type=FooFP
            ),
            somestr=dict(
                optional=False,
                values=[1, 2],
                type=int
            )
        )
    )


def easy_decorator(cls):
    cls.easy_decorator_was_here = True
    return cls


@contextmanager
def capture(command, *args, **kwargs):
    out, sys.stdout = sys.stdout, StringIO()
    try:
        command(*args, **kwargs)
        sys.stdout.seek(0)
        yield sys.stdout.read()
    finally:
        sys.stdout = out


expected_keys = """ * att1
 * att1                     [optional]
 * att2
 * att3                     [optional]
 * blop
 * kind
 * scrontch
 * someMixedCase            [optional]
 * somefoo
 * someint
 * somestr
 * somestr                  [optional]
"""


# noinspection PyPropertyAccess
class utFootprint(TestCase):

    def setUp(self):
        self.fp = dict(
            attr=dict(),
            bind=[],
            info='Not documented',
            only=dict(),
            priority=dict(
                level=priorities.top.DEFAULT
            ),
        )

        self.fpbis = Footprint(
            attr=dict(
                stuff1=dict(
                    alias=('arg1',)
                ),
                stuff2=dict(
                    optional=True,
                    default='foo'
                ),
            ),
            info='Some nice stuff'
        )

        self.fpter = DecorativeFootprint(
            attr=dict(
                stuff1=dict(
                    alias=('arg1',)
                ),
                stuff2=dict(
                    type=int,
                    optional=True,
                    default=1
                ),
            ),
            info='Some nice stuff',
            decorator=easy_decorator
        )

    def test_footprint_basics(self):
        fp = Footprint(nodefault=True)
        self.assertIsInstance(fp, Footprint)
        self.assertIsInstance(fp.as_dict(), dict)
        self.assertDictEqual(fp.as_dict(), dict(attr=dict()))
        self.assertEqual(str(fp), '{}')

        fp = Footprint(dict(
            info='Some stuff there',
            attr=dict(stuff=dict(remap=dict(autoremap='no')))
        ))
        self.assertIsInstance(fp, Footprint)
        self.assertEqual(fp.info, 'Some stuff there')
        self.assertDictEqual(fp.attr, dict(
            stuff=dict(
                access='rxx',
                alias=set(),
                default=None,
                optional=False,
                remap=dict(),
                values=set(),
                outcast=set(),
                doc_visibility=doc.visibility.DEFAULT,
                doc_zorder=0,
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
                        attr=dict(stuff=dict(values=['hip', 'hop'],
                                             remap=dict(autoremap='first'))),
                        priority=dict(level=priorities.top.DEBUG)
                        )
        self.assertEqual(fp2.info, 'Other stuff')
        self.assertEqual(fp2.priority['level'], priorities.top.DEBUG)
        self.assertSequenceEqual(list(fp2.attr.keys()), ['stuff'])
        self.assertDictEqual(fp2.as_dict(), {
            'attr': {
                'stuff': {
                    'access': 'rxx',
                    'alias': set(),
                    'default': None,
                    'optional': False,
                    'remap': {'hop': 'hip'},
                    'values': {'hip', 'hop'},
                    'outcast': set(),
                    'doc_visibility': doc.visibility.DEFAULT,
                    'doc_zorder': 0,
                }
            },
            'bind': [],
            'info': 'Other stuff',
            'only': {},
            'priority': {'level': priorities.top.DEBUG},
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
            attr=dict(
                stuff=dict(
                    type=int,
                    values=list(range(2)),
                    default=1,
                    optional=True
                )
            ),
            info='Some nice stuff'
        )

        fp2 = copy.deepcopy(fp1)
        self.assertDictEqual(fp1.as_dict(), fp2.as_dict())
        self.assertSetEqual(fp2.attr['stuff']['values'], {0, 1})
        self.assertIsNot(fp1.attr['stuff']['values'], fp2.attr['stuff']['values'])

        fp2 = Footprint(fp1)
        self.assertDictEqual(fp1.as_dict(), fp2.as_dict())
        self.assertSetEqual(fp2.attr['stuff']['values'], {0, 1})
        self.assertIsNot(fp1.attr['stuff']['values'], fp2.attr['stuff']['values'])

    def test_footprint_optional(self):
        fp = self.fpbis
        self.assertIsInstance(fp, Footprint)
        self.assertSetEqual(fp.as_opts(), {'arg1', 'stuff1', 'stuff2'})
        self.assertFalse(fp.optional('stuff1'))
        self.assertTrue(fp.optional('stuff2'))
        self.assertListEqual(fp.mandatory(), ['stuff1'])
        self.assertSetEqual(set(fp.track(dict(arg1=1, stuff2='hello', stuff3=3))),
                            {'arg1', 'stuff2'})

        with self.assertRaises(KeyError):
            self.assertTrue(fp.optional('stuff3'))

    def test_footprint_firstguess(self):
        fp = self.fpbis
        guess, inputattr = fp._firstguess(dict(weird='hello'))
        self.assertSetEqual(inputattr, set())
        self.assertDictEqual(guess, dict(
            stuff1=None,
            stuff2='foo',
        ))

        guess, inputattr = fp._firstguess(dict(stuff1='hello'))
        self.assertSetEqual(inputattr, {'stuff1'})
        self.assertDictEqual(guess, dict(
            stuff1='hello',
            stuff2='foo',
        ))

        guess, inputattr = fp._firstguess(dict(arg1='hello'))
        self.assertSetEqual(inputattr, {'stuff1'})
        self.assertDictEqual(guess, dict(
            stuff1='hello',
            stuff2='foo',
        ))
        olddflt = copy.copy(footprints.setup.defaults)
        try:
            footprints.setup.defaults['stuff1'] = 'hello'
            guess, inputattr = fp._firstguess(dict())
            self.assertSetEqual(inputattr, {'stuff1'})
            self.assertDictEqual(guess, dict(
                stuff1='hello',
                stuff2='foo',
            ))
        finally:
            footprints.setup.defaults = olddflt

    def test_footprint_extras(self):
        fp = self.fpbis
        self.assertIsInstance(footprints.setup, FootprintSetup)
        callback_ori = footprints.setup.callback

        def groundvalues():
            return dict(cool=2)

        try:
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
            self.assertDictEqual(rv, dict(cool=2, kind='hop', someMixedCase=None,
                                          someint=7, somestr='this'))

        finally:
            footprints.setup.callback = callback_ori

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
            fp._replacement(nbpass, 'hip', True, guess, extras, list(guess.keys()), list(), set())

        rv = fp._replacement(nbpass, 'nothing', True, guess, extras, list(guess.keys()), list(), set())
        self.assertTrue(rv)
        self.assertDictEqual(guess, dict(nothing='void'))

        guess = dict(nothing='void', stuff1='misc_[stuff2]')
        footprints.logger.setLevel(logging.CRITICAL)
        try:
            with self.assertRaises(footprints.FootprintUnreachableAttr):
                fp._replacement(nbpass, 'stuff1', True, guess, extras, list(guess.keys()), list(), set())
        finally:
            footprints.logger.setLevel(logging.WARNING)

        guess = dict(nothing='void', stuff1='misc_[stuff2#0]')
        rv = fp._replacement(nbpass, 'stuff1', True, guess, extras, list(guess.keys()), list(), set())
        self.assertDictEqual(guess, dict(stuff1='misc_0', nothing='void'))

        guess, u_inputattr = fp._firstguess(dict(stuff1='misc_[stuff2]'))
        todo = list(guess.keys())
        self.assertDictEqual(guess, dict(stuff1='misc_[stuff2]', stuff2='foo'))
        self.assertSetEqual(set(todo), {'stuff1', 'stuff2'})
        rv = fp._replacement(nbpass, 'stuff1', True, guess, extras, todo, list(), set())
        self.assertFalse(rv)
        self.assertDictEqual(guess, dict(stuff1='misc_[stuff2]', stuff2='foo'))

        todo.remove('stuff2')
        rv = fp._replacement(nbpass, 'stuff1', True, guess, extras, todo, list(), set())
        self.assertTrue(rv)
        self.assertDictEqual(guess, dict(stuff1='misc_foo', stuff2='foo'))

        guess, u_inputattr = fp._firstguess(dict(stuff1='misc_[stuff2]_and_[more]', more=2))
        todo = list(guess.keys())
        self.assertDictEqual(guess, dict(stuff1='misc_[stuff2]_and_[more]', stuff2='foo'))
        self.assertSetEqual(set(todo), {'stuff1', 'stuff2'})
        todo.remove('stuff2')
        extras = dict(more=2)
        rv = fp._replacement(nbpass, 'stuff1', True, guess, extras, todo, list(), set())
        self.assertTrue(rv)
        self.assertDictEqual(guess, dict(stuff1='misc_foo_and_2', stuff2='foo'))

    def test_footprint_replattr(self):
        fp = Footprint(self.fpbis, dict(
            attr=dict(
                somefoo=dict(
                    type=Foo,
                )
            )
        ))
        nbpass = 0
        extras = dict()

        guess, u_inputattr = fp._firstguess(dict(stuff1='misc_[somefoo:value]'))
        todo = set(guess.keys())
        self.assertDictEqual(guess, dict(stuff1='misc_[somefoo:value]', stuff2='foo', somefoo=None))
        self.assertSetEqual(todo, {'stuff1', 'stuff2', 'somefoo'})

        thisfoo = Foo(value=2)
        guess, u_inputattr = fp._firstguess(dict(stuff1='misc_[somefoo:value]', somefoo=thisfoo))
        todo = set(guess.keys())
        self.assertDictEqual(guess, dict(stuff1='misc_[somefoo:value]', stuff2='foo', somefoo=thisfoo))
        self.assertSetEqual(todo, {'stuff1', 'stuff2', 'somefoo'})

        todo = ['stuff1']
        rv = fp._replacement(nbpass, 'stuff1', True, guess, extras, todo, list(), set())
        self.assertTrue(rv)
        self.assertDictEqual(guess, dict(stuff1='misc_2', stuff2='foo', somefoo=thisfoo))

        guess, u_inputattr = fp._firstguess(dict(stuff1='misc_[somefoo:justprop]', somefoo=thisfoo))
        rv = fp._replacement(nbpass, 'stuff1', True, guess, extras, todo, list(), set())
        self.assertDictEqual(guess, dict(stuff1='misc_3', stuff2='foo', somefoo=thisfoo))

        # What if the function doesn't exists ?
        guess, u_inputattr = fp._firstguess(dict(stuff1='misc_[somefoo:missing]', somefoo=thisfoo))
        rv = fp._replacement(nbpass, 'stuff1', True, guess, extras, todo, list(), set())
        self.assertDictEqual(guess, dict(stuff1=None, stuff2='foo', somefoo=thisfoo))

        # With a built-in method
        guess, u_inputattr = fp._firstguess(dict(stuff2='[fake:upper]', somefoo=thisfoo))
        rv = fp._replacement(nbpass, 'stuff2', True, guess, dict(fake='misc'), todo, list(), set())
        self.assertDictEqual(guess, dict(stuff1=None, stuff2='MISC', somefoo=thisfoo))

        guess, u_inputattr = fp._firstguess(dict(stuff2='misc_[otherfoo:value]', somefoo=thisfoo))
        rv = fp._replacement(nbpass, 'stuff2', True, guess, dict(otherfoo=thisfoo), todo, list(), set())
        self.assertDictEqual(guess, dict(stuff1=None, stuff2='misc_2', somefoo=thisfoo))

        # Mix of attributes and methods
        thisfoo = Foo(value='ToTo')
        guess, u_inputattr = fp._firstguess(dict(stuff1='misc_[somefoo:value::lower]', somefoo=thisfoo))
        rv = fp._replacement(nbpass, 'stuff1', True, guess, extras, todo, list(), set())
        self.assertDictEqual(guess, dict(stuff1='misc_toto', stuff2='foo', somefoo=thisfoo))

    def test_footprint_replmethod(self):
        fp = self.fpbis
        nbpass = 0
        thisfoo = Foo(value=2)
        extras = dict(somefoo=thisfoo)

        guess, u_inputattr = fp._firstguess(dict(stuff1='misc_[somefoo:justdoit]', somefoo=thisfoo))
        todo = set(guess.keys())
        self.assertDictEqual(guess, dict(stuff1='misc_[somefoo:justdoit]', stuff2='foo'))
        self.assertSetEqual(todo, {'stuff1', 'stuff2'})

        todo = ['stuff1']
        rv = fp._replacement(nbpass, 'stuff1', True, guess, extras, todo, list(), set())
        self.assertTrue(rv)
        self.assertDictEqual(guess, dict(stuff1='misc_done_2', stuff2='foo'))

        guess, u_inputattr = fp._firstguess(dict(stuff1='misc_[somefoo:justdoit:upper]', somefoo=thisfoo))
        todo = ['stuff1']
        rv = fp._replacement(nbpass, 'stuff1', True, guess, extras, todo, list(), set())
        self.assertTrue(rv)
        self.assertDictEqual(guess, dict(stuff1='misc_DONE_2', stuff2='foo'))

        with loggers.contextboundGlobalLevel(9999):  # This is extremely quiet...
            guess, u_inputattr = fp._firstguess(dict(stuff1='misc_[somefoo:justraise]', somefoo=thisfoo))
            rv = fp._replacement(nbpass, 'stuff1', True, guess, extras, todo, list(), set())
            self.assertFalse(rv)
            self.assertDictEqual(guess, dict(stuff1='misc_[somefoo:justraise]', stuff2='foo'))

            guess, u_inputattr = fp._firstguess(dict(stuff1='misc_[somefoo:justraise:upper]', somefoo=thisfoo))
            rv = fp._replacement(nbpass, 'stuff1', True, guess, extras, todo, list(), set())
            self.assertFalse(rv)
            self.assertDictEqual(guess, dict(stuff1='misc_[somefoo:justraise:upper]', stuff2='foo'))

    def test_footprint_replacementfmt(self):
        fp = self.fpbis
        nbpass = 0
        extras = dict()

        guess = dict(nothing='void', stuff1='misc_[stuff2#0%03d]')
        rv = fp._replacement(nbpass, 'stuff1', True, guess, extras, list(guess.keys()), list(), set())
        self.assertDictEqual(guess, dict(stuff1='misc_0', nothing='void'))

        guess, u_inputattr = fp._firstguess(dict(stuff1='misc_[stuff2%03d]'))
        self.assertDictEqual(guess, dict(stuff1='misc_[stuff2%03d]', stuff2='foo'))
        todo = ['stuff1', ]
        footprints.logger.setLevel(logging.CRITICAL)
        try:
            with self.assertRaises(ValueError):
                rv = fp._replacement(nbpass, 'stuff1', True, guess, extras, todo, list(), set())
        finally:
            footprints.logger.setLevel(logging.WARNING)

        # If the replacement target is in extras
        guess, u_inputattr = fp._firstguess(dict(stuff1='misc_[stuff2]_and_[more%02d]', more=2))
        self.assertDictEqual(guess, dict(stuff1='misc_[stuff2]_and_[more%02d]', stuff2='foo'))
        todo = ['stuff1', ]
        extras = dict(more=2)
        rv = fp._replacement(nbpass, 'stuff1', True, guess, extras, todo, list(), set())
        self.assertTrue(rv)
        self.assertDictEqual(guess, dict(stuff1='misc_foo_and_02', stuff2='foo'))

        thisfoo = Foo(value=2)
        extras = dict(somefoo=thisfoo)
        guess, u_inputattr = fp._firstguess(dict(stuff1='misc_[somefoo:justanint%02d]', somefoo=thisfoo))
        self.assertDictEqual(guess, dict(stuff1='misc_[somefoo:justanint%02d]', stuff2='foo'))
        todo = ['stuff1', ]
        rv = fp._replacement(nbpass, 'stuff1', True, guess, extras, todo, list(), set())
        self.assertTrue(rv)
        self.assertDictEqual(guess, dict(stuff1='misc_03', stuff2='foo'))

        # If the replacement target is in guess
        fp = self.fpter
        guess, u_inputattr = fp._firstguess(dict(stuff1='misc_[stuff2%02d]_and_[more%02d]', more=2))
        self.assertDictEqual(guess, dict(stuff1='misc_[stuff2%02d]_and_[more%02d]', stuff2=1))
        todo = ['stuff1', ]
        extras = dict(more=2)
        rv = fp._replacement(nbpass, 'stuff1', True, guess, extras, todo, list(), set())
        self.assertTrue(rv)
        self.assertDictEqual(guess, dict(stuff1='misc_01_and_02', stuff2=1))

        # With a full "format" syntax
        fp = self.fpter
        guess, u_inputattr = fp._firstguess(dict(stuff1='misc_[stuff2%02d]_and_[more%.upper:s]', more='toto'))
        todo = ['stuff1', ]
        extras = dict(more='toto')
        rv = fp._replacement(nbpass, 'stuff1', True, guess, extras, todo, list(), set())
        self.assertTrue(rv)
        self.assertDictEqual(guess, dict(stuff1='misc_01_and_TOTO', stuff2=1))

    def test_resolve_unknown(self):
        fp = Footprint(self.fpbis, dict(
            attr=dict(
                someint=dict(
                    type=int,
                    optional=True,
                    default=None,
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

        with loggers.contextboundGlobalLevel(tloglevel):
            with self.assertRaises(footprints.FootprintMaxIter):
                cycling = dict(stuff1='[stuff2]', stuff2='[stuff1]')
                fp.resolve(cycling, fatal=False)

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(), fatal=False)
        self.assertTrue(rv)
        self.assertDictEqual(rv, dict(stuff1=None, stuff2='foo'))

    def test_resolve_fast(self):
        fp = Footprint(self.fpbis, dict(
            attr=dict(
                kind=dict(type=int)
            )
        ))

        rv, attr_input, attr_seen = fp.resolve(dict(stuff1='misc', kind='deux'), fast=False, fatal=False)
        self.assertDictEqual(rv, dict(stuff1='misc', stuff2='foo', kind=None))
        self.assertSetEqual(attr_input, {'stuff1'})
        self.assertSetEqual(attr_seen, {'kind'})

        rv, attr_input, attr_seen = fp.resolve(dict(stuff1='misc', kind='deux'), fast=True, fatal=False)
        self.assertDictEqual(rv, dict(stuff1='misc', stuff2='foo', kind=None))
        self.assertSetEqual(attr_input, {'stuff1'})
        self.assertSetEqual(attr_seen, {'kind'})

        fp = Footprint(self.fpbis, dict(
            attr=dict(
                stuff3=dict(type=int)
            )
        ))

        rv, attr_input, attr_seen = fp.resolve(dict(stuff1='misc', stuff3='deux'), fast=False, fatal=False)
        self.assertDictEqual(rv, dict(stuff1='misc', stuff2='foo', stuff3=None))
        self.assertSetEqual(attr_input, {'stuff1'})
        self.assertSetEqual(attr_seen, {'stuff1', 'stuff2', 'stuff3'})

        rv, attr_input, attr_seen = fp.resolve(dict(stuff1='misc', stuff3='deux'), fast=True, fatal=False)
        self.assertDictEqual(rv, dict(stuff1='misc', stuff2='foo', stuff3=None))
        self.assertSetEqual(attr_input, {'stuff1'})
        self.assertIn('stuff3', attr_seen)

        freezed_keys = footprints.setup.fastkeys
        footprints.setup.fastkeys = ('stuff3', 'stuff4')

        rv, attr_input, attr_seen = fp.resolve(dict(stuff1='misc', stuff3='deux'), fast=True, fatal=False)
        self.assertDictEqual(rv, dict(stuff1='misc', stuff2='foo', stuff3=None))
        self.assertSetEqual(attr_input, {'stuff1'})
        self.assertSetEqual(attr_seen, {'stuff3'})

        footprints.setup.fastkeys = freezed_keys

    def test_resolve_reclass(self):
        fp = self.fpbis

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1=2))
        self.assertDictEqual(rv, dict(stuff1='2', stuff2='foo'))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1=True))
        self.assertDictEqual(rv, dict(stuff1='True', stuff2='foo'))

        fp = Footprint(self.fpbis, dict(
            attr=dict(
                stuff3=dict(type=Foo)
            )
        ))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='misc', stuff3=2))
        self.assertIsInstance(rv['stuff3'], Foo)

    def test_resolve_remap(self):
        fp = Footprint(self.fpbis, dict(
            attr=dict(
                stuff1=dict(
                    remap=dict(two='four')
                )
            )
        ))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='one'))
        self.assertDictEqual(rv, dict(stuff1='one', stuff2='foo'))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='two'))
        self.assertDictEqual(rv, dict(stuff1='four', stuff2='foo'))

        fp = Footprint(self.fpbis, dict(
            attr=dict(
                stuff1=dict(
                    remap=dict(two='four', four='six')
                )
            )
        ))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rv, dict(stuff1='six', stuff2='foo'))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='two'))
        self.assertDictEqual(rv, dict(stuff1='six', stuff2='foo'))

    def test_resolve_isclass(self):
        fp = Footprint(self.fpbis, dict(
            attr=dict(
                stuff3=dict(
                    type=Foo,
                    isclass=True,
                )
            )
        ))

        class MoreFoo(Foo):
            pass

        class FakeFoo:
            pass

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='one', stuff3=FakeFoo), fatal=False)
        self.assertDictEqual(rv, dict(stuff1='one', stuff2='foo', stuff3=None))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='one', stuff3=MoreFoo))
        self.assertDictEqual(rv, dict(stuff1='one', stuff2='foo', stuff3=MoreFoo))

    def test_resolve_values(self):
        fp = Footprint(self.fpbis, dict(
            attr=dict(
                stuff1=dict(
                    values=('one', 'two'),
                )
            )
        ))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'), fatal=False)
        self.assertDictEqual(rv, dict(stuff1=None, stuff2='foo'))

        fp.attr['stuff1']['values'].add('four')
        self.assertSetEqual(fp.attr['stuff1']['values'], {'one', 'two', 'four'})

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'), fatal=False)
        self.assertDictEqual(rv, dict(stuff1='four', stuff2='foo'))

    def test_resolve_outcast(self):
        fp = Footprint(self.fpbis, dict(
            attr=dict(
                stuff1=dict(
                    outcast=['one', 'two'],
                )
            )
        ))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'), fatal=False)
        self.assertDictEqual(rv, dict(stuff1='four', stuff2='foo'))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='one'), fatal=False)
        self.assertDictEqual(rv, dict(stuff1=None, stuff2='foo'))

        fp = Footprint(self.fpbis, dict(
            attr=dict(
                stuff1=dict(
                    values=['one', 'four'],
                    outcast=['one', 'two'],
                )
            )
        ))

        self.assertSetEqual(fp.attr['stuff1']['values'], {'one', 'four'})
        self.assertSetEqual(fp.attr['stuff1']['outcast'], {'one', 'two'})

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='six'), fatal=False)
        self.assertDictEqual(rv, dict(stuff1=None, stuff2='foo'))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='two'), fatal=False)
        self.assertDictEqual(rv, dict(stuff1=None, stuff2='foo'))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'), fatal=False)
        self.assertDictEqual(rv, dict(stuff1='four', stuff2='foo'))

        rv, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='one'), fatal=False)
        self.assertDictEqual(rv, dict(stuff1=None, stuff2='foo'))

    def test_resolve_only(self):
        # Only -> exact match
        fp = Footprint(self.fpbis, dict(
            only=dict(
                rdate=datetime.date(2013, 11, 2)
            )
        ))

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertFalse(rv)

        footprints.setup.defaults.update(rdate=datetime.date(2013, 11, 1))

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertFalse(rv)

        footprints.setup.defaults.update(rdate=datetime.date(2013, 11, 2))

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertTrue(rv)

        fp = Footprint(self.fpbis, dict(
            only=dict(
                rdate=(datetime.date(2013, 11, 2), datetime.date(2013, 11, 5))
            )
        ))

        footprints.setup.defaults.update(rdate=datetime.date(2013, 11, 2))

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertTrue(rv)

        footprints.setup.defaults.update(rdate=datetime.date(2013, 11, 5))

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertTrue(rv)

        footprints.setup.defaults.update(rdate=datetime.date(2013, 11, 4))

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertFalse(rv)

        # Only -> 'after' match
        fp = Footprint(self.fpbis, dict(
            only=dict(
                after_rdate=datetime.date(2013, 11, 2)
            )
        ))

        footprints.setup.defaults.update(rdate=datetime.date(2013, 11, 1))

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertFalse(rv)

        footprints.setup.defaults.update(rdate=datetime.date(2013, 12, 3))

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertTrue(rv)

        # Only -> 'before' match
        fp = Footprint(self.fpbis, dict(
            only=dict(
                before_rdate=datetime.date(2013, 11, 2)
            )
        ))

        footprints.setup.defaults.update(rdate=datetime.date(2013, 11, 1))

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertTrue(rv)

        footprints.setup.defaults.update(rdate=datetime.date(2013, 12, 3))

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertFalse(rv)

        # Only -> 'after' and 'before' match
        fp = Footprint(self.fpbis, dict(
            only=dict(
                after_rdate=datetime.date(2013, 11, 2),
                before_rdate=datetime.date(2013, 11, 28)
            )
        ))

        footprints.setup.defaults.update(rdate=datetime.date(2013, 11, 1))

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertFalse(rv)

        footprints.setup.defaults.update(rdate=datetime.date(2013, 11, 29))

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertFalse(rv)

        footprints.setup.defaults.update(rdate=datetime.date(2013, 11, 15))

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertTrue(rv)

        # Only -> 'regex' match
        fp = Footprint(self.fpbis, dict(
            only=dict(
                stuff1=[footprints.FPRegex(r'toto\d\.txt'),
                        footprints.FPRegex(r'machine?\.txt')]
            )
        ))

        for tstuff in ('four', 'toto11.txt'):
            rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1=tstuff))
            self.assertDictEqual(rd, dict(stuff1=tstuff, stuff2='foo'))
            rv = fp.checkonly(rd)
            self.assertFalse(rv)

        for tstuff in ('toto1.txt', 'toto5.txt', 'machine.txt', 'machin.txt'):
            rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1=tstuff))
            self.assertDictEqual(rd, dict(stuff1=tstuff, stuff2='foo'))
            rv = fp.checkonly(rd)
            self.assertTrue(rv)

        fp = Footprint(self.fpbis, dict(
            only=dict(
                rstuff1=footprints.FPRegex(r'toto\d\.txt')
            )
        ))

        footprints.setup.defaults.update(rstuff1='toto1.txt')

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertTrue(rv)

        footprints.setup.defaults.update(rstuff1='toto11.txt')

        rd, u_attr_input, u_attr_seen = fp.resolve(dict(stuff1='four'))
        self.assertDictEqual(rd, dict(stuff1='four', stuff2='foo'))
        rv = fp.checkonly(rd)
        self.assertFalse(rv)

    def test_decorative(self):
        self.assertListEqual(self.fpter.decorators, [easy_decorator, ])
        fptmp = self.fpter.as_footprint()
        self.assertIsInstance(fptmp, Footprint)
        self.assertEqual(fptmp.as_dict(), self.fpter.as_dict())
        # Decorative but useless...
        fpuseless = DecorativeFootprint(
            attr=dict(
                stuff1=dict(
                ),
            ),
            info='Some nice stuff',
        )
        self.assertListEqual(fpuseless.decorators, [])
        # Not cool...
        with self.assertRaises(ValueError):
            DecorativeFootprint(
                attr=dict(
                    stuff1=dict(
                    ),
                ),
                info='Some nice stuff',
                decorator=[easy_decorator, 'toto', ]
            )


# Base class for footprint classes

class FpTmpA(FootprintBase):
    _footprint = dict(
        attr=dict(
            att1=dict(default='toto',
                      optional=True,
                      values=['toto', 'titi']),
            att2=dict(type=int),
        )
    )


fpatt3 = Footprint(
    info='Abstract att1',
    attr=dict(
        att3=dict(default='scrontch', optional=True),
    )
)


fpatt3_deco = DecorativeFootprint(fpatt3, decorator=[easy_decorator, ])


class FpTmpB(FootprintBase):
    _footprint = [
        fpatt3_deco,
        dict(
            attr=dict(
                att1=dict(default='titi'),
            )
        )
    ]


class FpTmpC(FpTmpB, FpTmpA):
    _footprint = dict(
        attr=dict(
            att2=dict(values=[1, 2, 3])
        )
    )


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
        self.assertEqual(FootprintTestMeta.fullname(), __name__ + '.FootprintTestMeta')
        self.assertEqual(FootprintTestMeta.__doc__, 'Not documented yet.')
        self.assertListEqual(FootprintTestMeta.footprint_mandatory(), list())
        self.assertDictEqual(FootprintTestMeta._footprint.as_dict(), dict(
            attr=dict(),
            bind=list(),
            info='Not documented',
            only=dict(),
            priority=dict(level=priorities.top.DEFAULT)
        ))

        with self.assertRaises(KeyError):
            self.assertTrue(FootprintTestMeta.footprint_optional('foo'))

        with self.assertRaises(KeyError):
            self.assertTrue(FootprintTestMeta.footprint_values('foo'))

        with self.assertRaises(footprints.FootprintInvalidDefinition):
            FootprintTestMeta()

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
        self.assertDictEqual(ftm.footprint_as_shallow_dict(), dict())
        self.assertDictEqual(ftm.footprint_export(), dict())
        self.assertEqual(ftm.footprint_clsname(), 'FootprintTestMeta')
        self.assertEqual(ftm.footprint_info, 'Not documented')

        del FootprintTestMeta

    def test_metaclass_inheritance_and_merging(self):

        self.assertEqual(FpTmpC._footprint.attr['att1']['default'], 'titi')
        self.assertEqual(FpTmpC._footprint.attr['att1']['optional'], False)
        self.assertEqual(FpTmpC._footprint.attr['att1']['values'], set())
        self.assertEqual(FpTmpC._footprint.attr['att2']['type'], int)
        self.assertEqual(FpTmpC._footprint.attr['att2']['values'], {1, 2, 3})
        self.assertEqual(FpTmpC._footprint.attr['att3']['default'], 'scrontch')
        self.assertEqual(FpTmpC._footprint.attr['att3']['optional'], True)

        # Decorator effect...
        self.assertTrue(FpTmpB.easy_decorator_was_here)
        self.assertTrue(FpTmpC.easy_decorator_was_here)  # Because of the MRO
        self.assertNotIn('easy_decorator_was_here', FpTmpC.__dict__)  # But actually not defined in testC

    def test_baseclass_fp1(self):
        self.assertFalse(FootprintTestOne.footprint_abstract())
        self.assertSetEqual(set(FootprintTestOne.footprint_mandatory()),
                            {'someint', 'kind'})
        self.assertTrue(FootprintTestOne.footprint_optional('somestr'))
        self.assertTrue(FootprintTestOne.footprint_optional('someMixedCase'))
        self.assertSetEqual(set(FootprintTestOne.footprint_values('kind')),
                            {'hip', 'hop'})
        self.assertSetEqual(
            FootprintTestOne.footprint_retrieve().as_opts(),
            {'someint', 'somestr', 'kind', 'stuff', 'someMixedCase'}
        )

        footprints.logger.setLevel(logging.CRITICAL)
        try:
            with self.assertRaises(footprints.FootprintFatalError):
                FootprintTestOne(kind='hip')

            with self.assertRaises(footprints.FootprintFatalError):
                FootprintTestOne(kind='hip', someint=13)
        finally:
            footprints.logger.setLevel(logging.WARNING)

        fp1 = FootprintTestOne(kind='hip', someint=7)
        self.assertIsInstance(fp1, FootprintTestOne)
        self.assertEqual(fp1.realkind, 'bigone')
        self.assertListEqual(fp1.footprint_attributes,
                             ['kind', 'someMixedCase', 'someint', 'somestr', ])
        self.assertEqual(fp1.footprint_info, 'Test class')

        fp1 = FootprintTestOne(stuff='hip', someint=7, someMixedCase='why ?')
        self.assertIsInstance(fp1, FootprintTestOne)
        self.assertListEqual(fp1.footprint_attributes,
                             ['kind', 'someMixedCase', 'someint', 'somestr'])
        self.assertDictEqual(fp1.footprint_as_shallow_dict(), dict(
            kind='hip',
            someint=7,
            somestr='this',
            someMixedCase='why ?',
        ))
        self.assertTrue(fp1.footprint_compatible(dict(
            kind='hip',
            someint=7,
            somestr='this',
            someMixedCase='why ?',
        )))
        self.assertFalse(fp1.footprint_compatible(dict(
            kind='hip',
            someint=7,
        )))
        self.assertFalse(fp1.footprint_compatible(dict(
            kind='hip',
            someint=7,
            someMixedCase='not possible',
        )))
        self.assertFalse(fp1.footprint_compatible(dict(
            kind='hip',
            nope=True,
        )))
        self.assertFalse(fp1.footprint_compatible(dict(
            kind='hip',
            someint=8,
        )))

        fp1 = FootprintTestOne(stuff='foo', someint='7')
        self.assertDictEqual(fp1.footprint_as_shallow_dict(), dict(
            kind='hop',
            someint=7,
            somestr='this',
            someMixedCase=None,
        ))

        footprints.logger.setLevel(logging.CRITICAL)
        try:
            with self.assertRaises(AttributeError):
                fp1 = FootprintTestOne(stuff='foo', someint='7', checked=True)
                self.assertDictEqual(fp1.footprint_as_shallow_dict(), dict(
                    stuff='foo',
                    someint='7',
                ))
        finally:
            footprints.logger.setLevel(logging.WARNING)

        fp1 = FootprintTestOne(kind='foo', someint='7', checked=True)
        self.assertDictEqual(fp1.footprint_as_shallow_dict(), dict(
            kind='foo',
            someint='7',
        ))

    def test_baseclass_fp2(self):
        self.assertFalse(FootprintTestTwo.footprint_abstract())
        self.assertSetEqual(set(FootprintTestTwo.footprint_mandatory()),
                            {'someint', 'kind', 'somefoo'})
        self.assertTrue(FootprintTestTwo.footprint_optional('somestr'))
        self.assertSetEqual(set(FootprintTestTwo.footprint_values('kind')),
                            {'hip', 'hop', 'poom'})
        self.assertSetEqual(
            FootprintTestTwo.footprint_retrieve().as_opts(),
            {'someint', 'somestr', 'kind', 'stuff', 'somefoo', 'someMixedCase'}
        )

        thefoo = Foo(inside=2)

        footprints.logger.setLevel(logging.CRITICAL)
        try:
            with self.assertRaises(footprints.FootprintFatalError):
                FootprintTestTwo(kind='hip', somefoo=thefoo)

            with self.assertRaises(footprints.FootprintFatalError):
                FootprintTestTwo(kind='hip', somefoo=thefoo, someint=13)

            with self.assertRaises(footprints.FootprintFatalError):
                FootprintTestTwo(kind='hip', somefoo=thefoo, someint=7)
        finally:
            footprints.logger.setLevel(logging.WARNING)

        fp2 = FootprintTestTwo(kind='hip', somefoo=thefoo, someint=5)
        self.assertIsInstance(fp2, FootprintTestTwo)
        self.assertListEqual(fp2.footprint_attributes,
                             ['kind', 'someMixedCase', 'somefoo', 'someint', 'somestr'])
        self.assertEqual(fp2.footprint_info, 'Another test class')
        self.assertDictEqual(fp2.footprint_as_shallow_dict(), dict(
            kind='hip',
            someint=5,
            somestr='this',
            somefoo=thefoo,
            someMixedCase=None,
        ))
        # Because of mkshort
        self.assertEqual(fp2.toto, 2)

    def test_deepcopy(self):
        # Base object
        thefoo = Foo(inside=2)
        fp0 = FootprintTestTwo(kind='hip', somefoo=thefoo, someint=5)
        exp_dict = fp0.footprint_as_shallow_dict()
        # Pure dict is a shallow copy...
        self.assertIs(exp_dict['somefoo'], fp0.somefoo)
        # Copied object
        fpc = copy.deepcopy(fp0)
        exp_dict_c = fpc.footprint_as_shallow_dict()
        # Is the new Pure dict fine ?
        self.assertIs(exp_dict_c['somefoo'], fpc.somefoo)
        # Check that the deep copy works by playing with the mutable somefoo
        self.assertIsNot(fp0.somefoo, fpc.somefoo)
        fpc.somefoo.inside = 3
        self.assertEqual(fpc.somefoo.inside, 3)
        self.assertEqual(fp0.somefoo.inside, 2)
        # Check that the collector knows about the copied class
        col = collectors.get()
        self.assertIn(fp0, col.instances)
        self.assertIn(fpc, col.instances)

    def test_as_shallow_dict(self):
        # Base object
        thefoo = Foo(inside=2)
        fp0 = FootprintTestTwo(kind='hip', somefoo=thefoo, someint=5)
        # Shallow copy
        exp1 = fp0.footprint_as_shallow_dict()
        exp2 = fp0.footprint_as_shallow_dict()
        self.assertIsNot(exp1, exp2)
        self.assertIs(exp1['somefoo'], exp2['somefoo'])

    def test_as_dict(self):
        # Base object
        thefoo = Foo(inside=2)
        fp0 = FootprintTestTwo(kind='hip', somefoo=thefoo, someint=5)
        # Deepcopy
        exp1 = fp0.footprint_as_dict()
        exp2 = fp0.footprint_as_dict()
        self.assertIsNot(exp1, exp2)
        self.assertIsNot(exp1['somefoo'], exp2['somefoo'])

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
        self.assertIsInstance(x.somestr, (str,))

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
        self.assertSetEqual(attr_input, {'kind'})

        report = reporting.get(tag='void')
        self.assertIsInstance(report, reporting.FootprintLog)
        report.clear()
        self.assertDictEqual(report.as_dict(), dict())

        rv, attr_input = FootprintTestOne.footprint_couldbe(dict(kind='hip'), mkreport=True)
        self.assertFalse(rv)
        self.assertSetEqual(attr_input, {'kind'})
        self.assertDictEqual(report.last.as_dict(), {
            __name__ + '.FootprintTestOne': {'someint': {'why': 'Missing value'}}
        })

        rv, attr_input = FootprintTestOne.footprint_couldbe(dict(kind='hip', someint=12), mkreport=True)
        self.assertFalse(rv)
        self.assertSetEqual(attr_input, {'kind'})
        self.assertDictEqual(report.last.as_dict(), {
            __name__ + '.FootprintTestOne': {'someint': {'why': 'Not in values', 'args': 12}}
        })

        rv, attr_input = FootprintTestOne.footprint_couldbe(dict(kind='hip', someint=2), mkreport=True)
        self.assertTrue(rv)
        self.assertSetEqual(attr_input, {'kind', 'someint'})
        self.assertDictEqual(report.last.as_dict(), {
            __name__ + '.FootprintTestOne': {}
        })

        rv, attr_input = FootprintTestTwo.footprint_couldbe(dict(kind='hip', someint=1, somefoo=Foo(1)), mkreport=True)
        self.assertTrue(rv)
        self.assertSetEqual(attr_input, {'kind', 'someint', 'somefoo'})
        self.assertDictEqual(report.last.as_dict(), {
            __name__ + '.FootprintTestTwo': {}
        })

        rv, attr_input = FootprintTestTwo.footprint_couldbe(dict(kind='hip', someint=1, somefoo=1), mkreport=True)
        self.assertTrue(rv)
        self.assertSetEqual(attr_input, {'kind', 'someint', 'somefoo'})
        self.assertDictEqual(report.last.as_dict(), {
            __name__ + '.FootprintTestTwo': {}
        })

        rv, attr_input = FootprintTestFpAttr.footprint_couldbe(dict(kind='hip',
                                                                    someint=1,
                                                                    somestr=1,
                                                                    somefoo=FooFP(blop=1, scrontch='hello')),
                                                               mkreport=True)
        self.assertTrue(rv)
        self.assertSetEqual(attr_input, {'kind', 'someint', 'somestr', 'somefoo'})
        self.assertDictEqual(report.last.as_dict(), {
            __name__ + '.FootprintTestFpAttr': {}
        })

        # How does it react when somefoo can not be reclassed inte a FooFP type ?
        a_foo = Foo(1)
        rv, attr_input = FootprintTestFpAttr.footprint_couldbe(dict(kind='hip',
                                                                    someint=1,
                                                                    somestr=1,
                                                                    somefoo=a_foo),
                                                               mkreport=True)
        self.assertFalse(rv)
        self.assertSetEqual(attr_input, {'kind', 'someint', 'somestr'})
        self.assertDictEqual(report.last.as_dict(), {
            __name__ + '.FootprintTestFpAttr': {'somefoo': {'args': ('FooFP', repr(a_foo)),
                                                'why': 'Could not reclass'}}
        })


@loggers.unittestGlobalLevel(tloglevel)
class utCollector(TestCase):

    def test_collector_basic(self):
        self._internal_test_collector_basic()

    def test_collector_fasttrack(self):
        col = collectors.get()
        for ftracklist in (['kind', ],
                           ['blop', ],
                           ['somefoo', ],
                           ['someint', ],
                           ['kind', 'somefoo'],
                           ['kind', 'someint'],
                           ['kind', 'somestr']):
            oldfasttrack = col.fasttrack
            try:
                col.fasttrack = ftracklist
                self._internal_test_collector_basic()
            finally:
                col.fasttrack = oldfasttrack

    def _internal_test_collector_basic(self):
        col = collectors.get()
        bc = col.find_all(dict(kind='hip', someint=4, somefoo=Foo()))
        self.assertTrue(all([obj[0] in (FootprintTestOne, FootprintTestTwo)
                             for obj in bc]))
        bc = col.find_all(dict(kind='?????'))
        self.assertListEqual(bc, [])
        obj = col.find_any(dict(kind='hip', someint=4, somefoo=Foo()))
        self.assertTrue(isinstance(obj, (FootprintTestOne, FootprintTestTwo)))
        obj = col.find_any(dict(kind='?????'))
        self.assertIs(obj, None)
        obj = col.find_best(dict(kind='hip', someint=4, somefoo=Foo()))
        self.assertTrue(isinstance(obj, FootprintTestTwo))
        obj = col.find_best(dict(kind='?????'))
        self.assertIs(obj, None)
        ingest = dict(kind='????', _report=False)
        ingest = col.pickup(ingest)
        self.assertDictEqual(ingest, dict(kind='????', garbage=None))
        ingest = dict(kind='hip', someint=2, somefoo=Foo(), _trash=1)
        ingest = col.pickup(ingest)
        obj = ingest['garbage']
        self.assertTrue(isinstance(obj, FootprintTestOne))
        self.assertSetEqual(set(ingest.keys()), {'somefoo', 'garbage'})
        ingest = col.pickup(ingest)
        self.assertTrue(ingest['garbage'], obj)
        self.assertSetEqual(set(ingest.keys()), {'somefoo', 'garbage'})
        # Reuse some of the instances
        obj2 = col.default(kind='hip', someint=2, somefoo=Foo())
        self.assertIs(obj, obj2)
        obj2 = col.default(kind='hip', someint=2, somefoo=Foo(), someMixedCase='why ?')
        self.assertIsNot(obj, obj2)
        self.assertTrue(isinstance(obj2, FootprintTestOne))
        # grep among instances
        self.assertSetEqual(set(col.instances), {obj, obj2})
        self.assertListEqual(col.grep(someMixedCase='why ?'), [obj2, ])
        self.assertListEqual(col.grep(someMixedCase='nope'), [])

    def test_collector_methods(self):
        col = collectors.get()
        with capture(col.show_attrkeys) as output:
            self.assertEqual("\n".join([line.rstrip(' ') for line in output.split("\n")
                                        if not re.search(r' (the|very)', line)]),
                             expected_keys)


class utProxy(TestCase):

    def test_proxy_basic(self):
        col = collectors.get()
        self.assertIs(footprints.proxy.garbages, col)
        self.assertIs(footprints.proxy._garbages, None)
        self.assertIs(footprints.proxy.oops, None)
        self.assertIs(footprints.proxy.getitem('garbage'), col)
        self.assertIs(footprints.proxy.getitem('oops'), None)
        self.assertIsInstance(footprints.proxy.garbage, types.MethodType)
        self.assertIn('garbage', footprints.proxy)
        self.assertIn('garbages', footprints.proxy)


if __name__ == '__main__':
    main(verbosity=2)
