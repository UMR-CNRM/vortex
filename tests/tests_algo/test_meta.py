from __future__ import print_function, absolute_import, unicode_literals, division

import tempfile
import unittest

from bronx.fancies.loggers import unittestGlobalLevel
import footprints

import vortex
from vortex.algo.components import AlgoComponent, AlgoComponentDecoMixin, algo_component_deco_mixin_autodoc

tloglevel = 'ERROR'


class BaseTestAlgoComponentForMeta(AlgoComponent):

    _footprint = dict(attr = dict(
        kind = dict(values = ['base_test_algo_for_meta', ]),
    ))

    def __init__(self, *kargs, **kwargs):
        super(BaseTestAlgoComponentForMeta, self).__init__(*kargs, **kwargs)
        self.prepare_stack = []
        self.execute_stack = []
        self.postfix_stack = []

    def prepare(self, rh, opts):
        self.prepare_stack.append('base')
        super(BaseTestAlgoComponentForMeta, self).prepare(rh, opts)

    def execute(self, rh, opts):
        self.execute_stack.append('base')
        super(BaseTestAlgoComponentForMeta, self).execute(rh, opts)

    def postfix(self, rh, opts):
        self.postfix_stack.append('base')
        super(BaseTestAlgoComponentForMeta, self).postfix(rh, opts)

    def postfix_post_dirlisting(self):
        pass

    def spawn_command_options(self):
        rv = super(BaseTestAlgoComponentForMeta, self).spawn_command_options()
        rv['base'] = True
        return rv


@algo_component_deco_mixin_autodoc
class BaseTestMixin(AlgoComponentDecoMixin):

    def _prepare_hook(self, rh, opts):
        self.prepare_stack.append('mix')

    def _mixin_execute(self, rh, opts):
        self.execute_stack.append('mix')
        super(self.__class__, self).execute(rh, opts)
        self.execute_stack.append('mix')

    def _postfix_hook(self, rh, opts):
        self.postfix_stack.append('mix')

    def _cli_extend(self, prev):
        prev['hacked'] = True
        return prev

    _MIXIN_PREPARE_HOOKS = (_prepare_hook, )
    _MIXIN_POSTFIX_HOOKS = (_postfix_hook, )
    _MIXIN_EXECUTE_OVERWRITE = _mixin_execute
    _MIXIN_CLI_OPTS_EXTEND = (_cli_extend, )


@unittestGlobalLevel(tloglevel)
class TestAlgoMetaClass(unittest.TestCase):

    def test_metasanity(self):
        # Not instantiable
        with self.assertRaises(RuntimeError):
            BaseTestMixin()
        # Variaous sanity checks

        class A_TestMixin(BaseTestMixin):

            MIXIN_AUTO_DECO = False
            _MIXIN_EXTRA_FOOTPRINTS = ['blop']  # Will fail

        with self.assertRaises(AssertionError):
            # Because _MIXIN_EXTRA_FOOTPRINTS is not a valid footprints
            class A_TestAlgoComponentForMeta(BaseTestAlgoComponentForMeta, A_TestMixin):
                _footprint = dict(attr=dict(
                    kind=dict(values=['a_base_test_algo_for_meta', ]),
                ))

        A_TestMixin.MIXIN_AUTO_FPTWEAK = False

        with self.assertRaises(RuntimeError):
            # Because two mixin class with _MIXIN_EXECUTE_OVERWRITE are provided
            class B_TestAlgoComponentForMeta(BaseTestAlgoComponentForMeta, A_TestMixin, BaseTestMixin):
                _footprint = dict(attr=dict(
                    kind=dict(values=['b_base_test_algo_for_meta', ]),
                ))

        with self.assertRaises(RuntimeError):
            # Because execute is already defined
            class C_TestAlgoComponentForMeta(BaseTestAlgoComponentForMeta, A_TestMixin):
                _footprint = dict(attr=dict(
                    kind=dict(values=['c_base_test_algo_for_meta', ]),
                ))

                def execute(self, rh, opts):
                    pass

        class Fake(object):
            pass

        with self.assertRaises(RuntimeError):
            # Fake is not an AlgoComponent
            A_TestMixin.mixin_algo_deco(Fake)

    @staticmethod
    def _run_algo(algot):
        # Generate a temporary directory
        sh = vortex.sessions.current().system()
        tmpdir = tempfile.mkdtemp(suffix='_test_algo_meta_class')
        oldpwd = sh.pwd()
        sh.cd(tmpdir)
        try:
            algot.run()
        finally:
            sh.cd(oldpwd)
            sh.remove(tmpdir)

    def test_metafine(self):

        class Full_TestMixin(BaseTestMixin):

            _MIXIN_EXTRA_FOOTPRINTS = [
                footprints.Footprint(
                    attr=dict(
                        fakeattr=dict()
                    )
                )
            ]

        class Full_TestAlgoComponentForMeta(BaseTestAlgoComponentForMeta, Full_TestMixin):

            _footprint = dict(attr=dict(
                kind=dict(values=['full_base_test_algo_for_meta', ]),
            ))

            def prepare(self, rh, opts):
                super(Full_TestAlgoComponentForMeta, self).prepare(rh, opts)
                self.prepare_stack.append('inter')

        algot = Full_TestAlgoComponentForMeta(kind='full_base_test_algo_for_meta',
                                              engine='algo',
                                              fakeattr='gruik')
        self.assertTrue(hasattr(algot, 'fakeattr'))
        self.assertTrue('fakeattr' in algot.footprint_retrieve().attr)
        self.assertEqual(algot.fakeattr, 'gruik')

        self._run_algo(algot)

        self.assertEqual(algot.prepare_stack, ['base', 'inter', 'mix'])
        self.assertEqual(algot.execute_stack, ['mix', 'base', 'mix'])
        self.assertEqual(algot.postfix_stack, ['base', 'mix'])
        self.assertTrue(algot.spawn_command_options()['hacked'])
        self.assertTrue(algot.spawn_command_options()['base'])

        class Half_TestMixin(BaseTestMixin):

            MIXIN_AUTO_DECO = False

        class Half_TestAlgoComponentForMeta(BaseTestAlgoComponentForMeta, Half_TestMixin):

            _footprint = dict(attr=dict(
                kind=dict(values=['half_base_test_algo_for_meta', ]),
            ))

        algot = Half_TestAlgoComponentForMeta(kind='half_base_test_algo_for_meta',
                                              engine='algo',
                                              fakeattr='gruik')
        self.assertTrue(not hasattr(algot, 'fakeattr'))

        self._run_algo(algot)

        self.assertEqual(algot.prepare_stack, ['base', ])
        self.assertEqual(algot.execute_stack, ['mix', 'base', 'mix'])
        self.assertEqual(algot.postfix_stack, ['base', ])
        self.assertTrue('hacked' not in algot.spawn_command_options())
        self.assertTrue(algot.spawn_command_options()['base'])


if __name__ == "__main__":
    unittest.main(verbosity=2)
