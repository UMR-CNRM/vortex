#!/bin/env python
# -*- coding:Utf-8 -*-

from copy import deepcopy
import logging
from unittest import TestCase, TestLoader, TextTestRunner
from vortex.syntax import Footprint, BFootprint
from vortex.syntax.footprint import MFootprint, UNKNOWN
from vortex.data.containers import Virtual

logging.basicConfig(level=logging.DEBUG)

class UtFootprint(TestCase):

    def setUp(self):
        self.res = {
            'info': 'Not documented',
            'name': 'empty',
            'bind': [],
            'attr': {},
            'only': {},
            'priority': {'level': 20}
        }

    def test_init_vide(self):
        ft1 = Footprint()
        for cle, value in ft1._fp.iteritems():
            self.assertEquals(value, self.res[cle])
        print "Test __init__ vide Ok"

    def test_init_ftvide(self):
        ft1 = Footprint()
        ft2 = Footprint(ft1)
        for cle, value in ft2._fp.iteritems():
            self.assertEquals(value, self.res[cle])
        print "Test __init__ ftvide Ok"

    def test_init_argsdict(self):
        args = (
            {
            'name': 'alerte'
            },
            {
            'attr': {'model': {'values': ['mocchim']}}
            }
        )
        ft1 = Footprint(*args)
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
            'only': {},
            'priority': {'level': 20}
        }
        for cle, value in ft1._fp.iteritems():
            self.assertEquals(value, res[cle])

    def test_init_kwdict(self):
        kw = {
            'name': 'myname',
            'attr': {'model': {'values': ['mocchim']}}
        }
        ft1 = Footprint(**kw)
        res = {
            'info': 'Not documented',
            'name': 'myname',
            'attr': {
                'model': {
                    'default': None,
                    'alias': (),
                    'remap': {},
                    'values': ['mocchim'],
                    'optional': False
                }
            },
            'only': {},
            'priority': {'level':20}
        }
        for cle, value in ft1._fp.iteritems():
            self.assertEquals(value, res[cle])

    def test_init_argskw(self):
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
            'only': {},
            'priority': {'level': 20}
        }
        for cle, value in ft1._fp.iteritems():
            self.assertEquals(value, res[cle])

        ft2 = Footprint(ft1)
        for cle, value in ft2._fp.iteritems():
            self.assertEquals(value, res[cle])

        ft2 = Footprint(ft1, attr={'model': {'optional': True}})
        res['attr']['model']['optional'] = True
        for cle, value in ft2._fp.iteritems():
            self.assertEquals(value, res[cle])

    def test_deepcopy(self):
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
            'only': {},
            'priority': {'level': 20}
        }
        ft2 = deepcopy(ft1)
        self.assertFalse(ft2._fp is ft1._fp)
        for key, value in ft2._fp.iteritems():
            self.assertEquals(value, res[key])

    def test_firstguess_optional(self):
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
        guess = ft._firstguess(dict(real='hello'))
        result = dict(
            real = 'hello',
            foo = UNKNOWN,
            two = '2',
            bof = 2,
        )
        for key, value in result.iteritems():
            self.assertEquals(value, guess[key])

    def test_firstguess_alias(self):
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
        guess = ft._firstguess(dict(real='hello', fuzzy=2))
        result = dict(
            real = 'hello',
            foo = 2,
        )
        for key, value in result.iteritems():
            self.assertEquals(value, guess[key])

    def test_findextras_empty(self):
        ft = Footprint(self.res)
        extras = ft._findextras(dict(real='hello', fuzzy=2))
        self.assertEquals(extras, {})

    def test_findextras_container(self):
        ft = Footprint(self.res)
        mycont = Virtual()
        extras = ft._findextras(dict(real='hello', fuzzy=2, container=mycont))
        self.assertTrue(extras)
        self.assertTrue(len(extras) == 2)
        self.assertTrue(extras['incore'] == True)

    def test_replacement_internal(self):
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
                    default = 'clim_[model]_t[truncation]'
                ),
            )
        )
        guess = ft._firstguess(dict(model = 'arpege', truncation=798))
        done = ft._replacement(1, 'gvar', guess, [], [ 'model' ])
        self.assertFalse(done)
        self.assertEquals('clim_[model]_t[truncation]', guess['gvar'])
        done = ft._replacement(1, 'gvar', guess, [], [])
        self.assertTrue(done)
        self.assertEquals('clim_arpege_t798', guess['gvar'])

class UtMFootprint(TestCase):

    def test_new_vide(self):
        res = {
            'info': 'Not documented',
            'name': 'empty',
            'attr': {},
            'only': {},
            'priority': {'level': 20}
        }
        MyBFtp = MFootprint('MyBFtp', (), {})
        for cle, value in MyBFtp._footprint._fp.iteritems():
            self.assertEquals(value, res[cle])

    def test_new_withdict(self):
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
            'only': {},
            'priority': {'level': 20}
        }
        MyBFtp = MFootprint('MyBFtp', (), args)
        for cle, value in MyBFtp._footprint._fp.iteritems():
            self.assertEquals(value, res[cle])

    def test_new_withbaseft(self):
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
            'only': {},
            'priority': {'level': 20}
        }
        MyBFtp = MFootprint('MyBFtp', (), {'_footprint': ft1})
        for cle, value in MyBFtp._footprint._fp.iteritems():
            self.assertEquals(value, res[cle])


class TestBFootprint(BFootprint):

    _footprint = dict(
       info = 'Test',
       attr = dict(
           kind = dict(
               values = [ 'testun', 'testdeux', 'testtrois' ]
           ),
           info_un = dict(
               values = [ 'str_only'],
               optional = True,
           ),
           info_deux = dict(
               values = [ 'surface', 'surf', 'atmospheric', 'atm', 'full' ],
           )
        )
    )


class UtBFootprint(TestCase):

    def setUp(self):
        self.res = {
            'info': 'Not documented',
            'name': 'empty',
            'bind': [],
            'attr': {},
            'only': {},
        }

    def test_new_vide(self):
        self.assertTrue(isinstance(BFootprint._footprint, Footprint))
        for cle, value in BFootprint._footprint._fp.iteritems():
            if cle == 'priority': continue
            self.assertEquals(value, self.res[cle])
        self.assertEquals(vars(BFootprint._footprint._fp['priority']['level']), {'tag': 'TOOLBOX'})

    def test_init_vide(self):
        mybft = BFootprint()
        self.assertFalse(mybft._instfp is mybft._footprint._fp)
        for cle, value in mybft._footprint._fp.iteritems():
            if cle == 'priority': continue
            self.assertEquals(value, self.res[cle])
        self.assertEquals(vars(BFootprint._footprint._fp['priority']['level']), {'tag': 'TOOLBOX'})

    def test_couldbe(self):
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
        pseudo_ctlg = [ TestBFootprint ]
        for bf in pseudo_ctlg:
            self.assertEqual(bf.couldbe(rd), (False, set(['kind'])))
            self.assertEqual(bf.couldbe(rd2), (res_rd2, set(['kind', 'info_deux'])))
        
    def test_firstguess(self):
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
        fp = TestBFootprint.footprint()
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
    action = TestLoader().loadTestsFromTestCase
    #tests = [UtFootprint, UtMFootprint, UtBFootprint]
    tests = [UtBFootprint]
    suites = [action(elmt) for elmt in tests]
    for suite in suites:
        TextTestRunner(verbosity=2).run(suite)

