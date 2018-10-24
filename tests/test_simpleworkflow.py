#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

"""
Strictly speaking, it is not a unit-test in a sense that it leverages most of
the Vortex package. However, it ensures that some of the most heavily used
Vortex features are working correctly.

When debugging, fix other tests first and only then look at this one !
"""

import tempfile
from unittest import TestCase, main


import vortex
from vortex import sessions, toolbox
from vortex.data.contents import TextContent
from vortex.data.flow import FlowResource
from vortex.data.providers import VortexStd
from vortex.data.stores import _VortexCacheBaseStore, _CACHE_GET_INTENT_DEFAULT
from vortex.tools.delayedactions import AbstractFileBasedDelayedActionsHandler, d_action_status
from vortex.tools.storage import Cache


# The test cache Storage Object
class TestDataCache(Cache):
    """Cache items for the MTOOL jobs (or any job that acts like it)."""

    _footprint = dict(
        info = 'MTOOL like Cache',
        attr = dict(
            kind = dict(
                values   = ['testcache', ],
            ),
            headdir = dict(
                optional = True,
                default  = 'vortex',
            ),
        )
    )

    @property
    def entry(self):
        """Tries to figure out what could be the actual entry point for cache space."""
        testsdir = self.sh.path.dirname(__file__)
        return self.sh.path.join(testsdir, 'data', 'testcache', self.actual_headdir)

    def _actual_earlyretrieve(self, item, local, **kwargs):
        dirextract = kwargs.get("dirextract", False)
        tarextract = kwargs.get("tarextract", False)
        if not dirextract or tarextract:
            return self.context.delayedactions_hub.register((self._formatted_path(item),
                                                             kwargs.get('fmt', 'foo'),
                                                             kwargs.get('intent', 'in')),
                                                            kind = 'testlocalcp',
                                                            goal = 'get')
        else:
            return None

    def _actual_finaliseretrieve(self, retrieve_id, item, local, **kwargs):
        intent = kwargs.get("intent", "in")
        fmt = kwargs.get("fmt", "foo")
        extras = dict(fmt=fmt, intent=intent)
        tmplocal = self.context.delayedactions_hub.retrieve(retrieve_id)
        if tmplocal:
            rc = self.sh.mv(tmplocal, local, fmt=fmt)
            self._recursive_touch(rc, item)
        else:
            rc = False
        return rc, extras


# The test Vortex Store
class VortexCacheTestStore(_VortexCacheBaseStore):

    _footprint = dict(
        info = 'VORTEX MTOOL like Cache access',
        attr = dict(
            netloc = dict(
                values  = ['vortex.testcache.fr', ],
            ),
            strategy = dict(
                default = 'testcache',
            ),
        )
    )

    def incacheearlyget(self, remote, local, options):
        rc = self.cache.earlyretrieve(
            remote['path'], local,
            intent             = options.get('intent', _CACHE_GET_INTENT_DEFAULT),
            fmt                = options.get('fmt'),
            info               = options.get('rhandler', None),
            tarextract         = options.get('auto_tarextract', False),
            dirextract         = options.get('auto_dirextract', False),
            uniquelevel_ignore = options.get('uniquelevel_ignore', True),
            silent             = options.get('silent', False),
        )
        return rc

    def incachefinaliseget(self, result_id, remote, local, options):
        rc = self.cache.finaliseretrieve(
            result_id,
            remote['path'], local,
            intent             = options.get('intent', _CACHE_GET_INTENT_DEFAULT),
            fmt                = options.get('fmt'),
            info               = options.get('rhandler', None),
            tarextract         = options.get('auto_tarextract', False),
            dirextract         = options.get('auto_dirextract', False),
            uniquelevel_ignore = options.get('uniquelevel_ignore', True),
            silent             = options.get('silent', False),
        )
        return rc and self._hash_get_check(self.incacheget, remote, local, options)

    def vortexearlyget(self, remote, local, options):
        """Proxy to :meth:`incacheget`."""
        return self.incacheearlyget(remote, local, options)

    def vortexfinaliseget(self, result_id, remote, local, options):
        """Proxy to :meth:`incacheget`."""
        return self.incachefinaliseget(result_id, remote, local, options)


# A test delayed action... (it's just a cp)
class TestLocalCpDelayedGetHandler(AbstractFileBasedDelayedActionsHandler):

    _footprint = dict(
        info = "Just copy the data...",
        attr = dict(
            kind = dict(
                values = ['testlocalcp', ],
            ),
            goal = dict(
                values = ['get', ]
            ),
        )
    )

    @property
    def resultid_stamp(self):
        return 'testlocalcp_'

    def finalise(self, *r_ids):  # @UnusedVariable
        """Given a **r_ids** list of delayed action IDs, wait upon actions completion."""
        for k in [r_id for r_id in r_ids
                  if self._resultsmap[r_id].status == d_action_status.void]:
            rc = self.system.cp(self._resultsmap[k].request[0], self._resultsmap[k].result,
                                fmt=self._resultsmap[k].request[1],
                                intent=self._resultsmap[k].request[2])
            if rc:
                self._resultsmap[k].mark_as_done()
            else:
                self._resultsmap[k].mark_as_failed()
        return rc


# The test Vortex provider
class VortexTest(VortexStd):
    """Standard Vortex provider (any experiment with an Olive id)."""

    _footprint = dict(
        info = 'Vortex provider for casual experiments with an Olive XPID',
        attr = dict(
            namespace = dict(
                values   = ['vortex.testcache.fr', ],
            )
        ),
    )


# Test resources

class AbstractTestResource(FlowResource):

    _abstract = True
    _footprint = dict(
        info = 'TestResource',
        attr = dict(
            nativefmt = dict(
                values   = ['txt', ],
                default  = 'txt',
            ),
            clscontents = dict(
                default = TextContent,
            )
        )
    )


class TestResource1(AbstractTestResource):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values   = ['utest1', ],
            ),
        )
    )

    @property
    def realkind(self):
        return 'utest1'


class TestResource2(AbstractTestResource):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values   = ['utest2', ],
            ),
        )
    )

    @property
    def realkind(self):
        return 'utest2'


class TestResource9(AbstractTestResource):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values   = ['utest9', ],
            ),
        )
    )

    @property
    def realkind(self):
        return 'utest9'


# A test hook function that leverage a Content object
def toto_hook(t, rh, msg='Toto was here...'):
    rh.container.updfill(True)  # Mandatory for put hooks...
    rh.contents.data.append((msg, ))
    rh.save()


class UtSimpleWorkflow(TestCase):

    @staticmethod
    def _givetag():
        """Return the first available sessions name."""
        i = 1
        while 'simpleworkflow_test_{:d}'.format(i) in sessions.keys():
            i += 1
        return 'simpleworkflow_test_{:d}'.format(i)

    def setUp(self):
        self.rootsession = sessions.current()
        self.rootsh = self.rootsession.system()
        self.oldpwd = self.rootsh.pwd()
        self.tmpdir = self.rootsh.path.realpath(tempfile.mkdtemp(prefix='simpleworkflow_test_'))
        # Create a dedicated test
        self.cursession = sessions.get(tag=self._givetag(),
                                       topenv=vortex.rootenv,
                                       glove=self.rootsession.glove)
        self.cursession.activate()
        # self.cursession.error()   # Decrease loglevel
        self.cursession.rundir = self.tmpdir
        self.cursession.context.cocoon()
        self.cursession.glove.vapp = 'arpege'
        self.cursession.glove.vconf = '4dvarfr'

    def tearDown(self):
        self.cursession.exit()
        self.rootsession.activate()
        self.rootsh.cd(self.oldpwd)
        self.rootsh.remove(self.tmpdir)

    @property
    def sequence(self):
        return self.cursession.context.sequence

    @property
    def sh(self):
        return self.cursession.sh

    @property
    def default_fp_stuff(self):
        return dict(model='[glove:vapp]', date='2018010100', cutoff='assim',
                    namespace='vortex.testcache.fr', block='forecast', experiment='ABC1',)

    def assertIntegrity(self, rh, finalstatement='#end'):
        self.assertTrue(rh.complete)
        with open(rh.container.iotarget(), 'r') as fhin:
            lines = fhin.readlines()
            self.assertEqual(lines[0], '{:s}\n'.format(rh.resource.kind))
            i = 1
            while not lines[-i].rstrip('\n'):
                i += 1
            self.assertEqual(lines[-i], finalstatement)

    def test_simpleget_and_put(self):
        desc = self.default_fp_stuff
        desc.update(kind=['utest1', 'utest2'], local = '[kind]_get')
        descO = self.default_fp_stuff
        del descO['namespace']
        del descO['experiment']
        descO.update(kind=['utest1', 'utest2'], local = '[kind]_get',
                     remote=self.sh.path.join(self.sh.pwd(), 'testput', '[local]'))
        descdiff = self.default_fp_stuff
        descdiff.update(kind=['utest1', 'utest2'], local = '[kind]_get', experiment='ABC2')
        for batch in [True, False]:
            # Input
            rhs = toolbox.input(now=True, verbose=False, batch=batch,
                                **desc)
            rcdiff = toolbox.diff(**descdiff)
            self.assertTrue(all(rcdiff))
            for rh in rhs:
                self.assertIntegrity(rh)
            # Output
            rhsO = toolbox.output(now=True, verbose=False, batch=batch,
                                  **descO)
            for rh in rhsO:
                self.assertTrue(self.sh.path.exists(rh.provider.remote))
                self.assertIntegrity(rh)
                rh.delete()
            for rh in rhs:
                rh.clear()

    def test_hookedget_and_put(self):
        desc = self.default_fp_stuff
        desc.update(kind=['utest1', 'utest2'], local = '[kind]_get')
        descO = self.default_fp_stuff
        del descO['namespace']
        del descO['experiment']
        descO.update(kind=['utest1', 'utest2'], local = '[kind]_get',
                     remote=self.sh.path.join(self.sh.pwd(), 'testput', '[local]'))
        for batch in [True, False]:
            rhs = toolbox.input(now=True, verbose=True, intent='inout', batch=batch,
                                hook_toto=(toto_hook, ),
                                **desc)
            for rh in rhs:
                self.assertIntegrity(rh, finalstatement='Toto was here...\n')
            print(self.sh.ll())
            rhsO = toolbox.output(now=True, verbose=True, batch=batch,
                                  hook_toto=(toto_hook, 'Toto wrote here...\n'),
                                  **descO)
            for rh in rhsO:
                self.assertTrue(self.sh.path.exists(rh.provider.remote))
                self.assertIntegrity(rh, finalstatement='Toto wrote here...\n')
                rh.delete()
            for rh in rhs:
                rh.clear()

    def test_rh_check_delayed_get(self):
        desc1 = self.default_fp_stuff
        desc1.update(kind='utest1', local = 'utest1_get', )
        rh1 = toolbox.rh(**desc1)
        desc2 = self.default_fp_stuff
        desc2.update(kind='utest2', local = 'utest2_get', )
        rh2 = toolbox.rh(**desc1)
        # Check
        self.assertTrue(rh1.check())
        self.assertTrue(rh2.check())
        # Delayed get
        self.assertTrue(rh1.earlyget(intent='in'))
        self.assertTrue(rh2.earlyget(intent='in'))
        self.assertTrue(rh1.finaliseget())
        self.assertTrue(rh2.finaliseget())
        # IS it ok
        self.assertIntegrity(rh1)
        self.assertIntegrity(rh2)

    def test_simpleinsitu(self):
        desc = self.default_fp_stuff
        desc.update(kind='utest1', local = 'utest1_get', )
        for batch in [True, False]:
            rhs = toolbox.input(now=True, verbose=False, batch=batch, **desc)
            self.assertIntegrity(rhs[0])
            rhsbis = toolbox.input(now=True, insitu=True, batch=batch, **desc)
            self.assertIntegrity(rhsbis[0])
            desc2 = self.default_fp_stuff
            desc2.update(kind='utest1', local = 'utest1_getbis', )
            rhster = toolbox.input(now=True, insitu=True, verbose=False, batch=batch, **desc2)
            self.assertIntegrity(rhster[0])
            for rh in [rhs[0], rhster[0]]:
                rh.clear()

    def test_simplealternate_and_missing(self):
        for i, batch in enumerate([True, False]):
            therole = 'Toto{:d}'.format(i)
            # Missing
            descM = self.default_fp_stuff
            descM.update(kind='utest1', local = 'utestM_get{:d}'.format(i), model='mocage')
            rhsM = toolbox.input(role=therole, now=True, fatal=False, verbose=False, batch=batch, **descM)
            self.assertFalse(rhsM)
            # Alternate
            desc = self.default_fp_stuff
            desc.update(kind='utest1', local = 'utest1_get{:d}'.format(i), model='arome')
            rhs0 = toolbox.input(role=therole, now=True, fatal=False, verbose=False, batch=batch, **desc)
            self.assertFalse(rhs0)
            desc.update(kind='utest1', local = 'utest1_get{:d}'.format(i), model='arpege')
            rhs1 = toolbox.input(alternate=therole, now=True, fatal=False, verbose=False, batch=batch, **desc)
            self.assertIntegrity(rhs1[0])
            desc.update(kind='utest1', local = 'utest1_get{:d}'.format(i), model='safran')
            rhs2 = toolbox.input(alternate=therole, now=True, fatal=True, verbose=False, batch=batch, **desc)
            self.assertTrue(rhs2)
            efftoto = self.sequence.effective_inputs(role=therole)
            self.assertEqual(len(efftoto), 1)
            self.assertEqual(efftoto[0].rh.resource.model, 'arpege')
            # Reporting
            a_report = self.sequence.inputs_report()
            a_alternate = a_report.active_alternates()
            self.assertIs(a_alternate['utest1_get{:d}'.format(i)][0], rhs1[0])
            a_missing = a_report.missing_resources()
            self.assertEqual(a_missing['utestM_get{:d}'.format(i)].container.filename,
                             'utestM_get{:d}'.format(i))
            # Cleaning...
            rhs1[0].clear()

    def test_coherentget(self):
        desc = self.default_fp_stuff
        rh0a = toolbox.input(now=True, verbose=True, coherentgroup='toto,titi,tata',
                             kind='utest1', local = 'utest1_get0a', **desc)
        rh0b = toolbox.input(now=True, verbose=True, coherentgroup='toto,titi',
                             kind='utest1', local = 'utest1_get0b', **desc)
        rh1 = toolbox.input(now=True, verbose=True, coherentgroup='toto',
                            kind='utest1', local = 'utest1_get1', **desc)
        rh2 = toolbox.input(now=True, verbose=True, fatal=False, coherentgroup='toto',
                            kind='utest1,utest9,utest2', local = '[kind]_get2', **desc)
        rh3 = toolbox.input(now=True, verbose=True, fatal=False, coherentgroup='toto',
                            kind='utest1', local = 'utest1_get3', **desc)
        rh3b = toolbox.input(now=True, verbose=True, fatal=False, coherentgroup='titi',
                             kind='utest9', local = 'utest9_get3b', **desc)
        rh4 = toolbox.input(now=True, verbose=True,
                            kind='utest1', local = 'utest1_get4', **desc)
        self.assertEqual(len(rh0a), 1)
        self.assertEqual(len(rh0b), 1)
        self.assertEqual(len(rh1), 1)
        self.assertListEqual(rh2, list())
        self.assertListEqual(rh3, list())
        self.assertListEqual(rh3b, list())
        self.assertEqual(len(rh4), 1)

        for sec in self.sequence.rinputs():
            if sec.rh.container.basename in ('utest1_get0b', 'utest1_get1', 'utest1_get2'):
                self.assertEqual(sec.stage, 'checked')
            if sec.rh.container.basename in ('utest2_get2', 'utest1_get3'):
                self.assertEqual(sec.stage, 'load')
            if sec.rh.container.basename in ('utest9_get2', 'utest9_get3b'):
                self.assertEqual(sec.stage, 'void')
            if sec.rh.container.basename in ('utest1_get0a', 'utest1_get4'):
                self.assertEqual(sec.stage, 'get')

        self.assertListEqual([s.rh for s in self.sequence.effective_inputs()], rh0a + rh4)


if __name__ == '__main__':
    main(verbosity=2)
