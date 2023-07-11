"""
Strictly speaking, it is not a unit-test in a sense that it leverages most of
the Vortex package. However, it ensures that some of the most heavily used
Vortex features are working correctly.

When debugging, fix other tests first and only then look at this one !
"""

import os
import tempfile
from unittest import TestCase, main

from bronx.fancies import loggers
import footprints

import vortex
from vortex import sessions, toolbox
from vortex.data.abstractstores import CACHE_GET_INTENT_DEFAULT, MultiStore
from vortex.data.contents import TextContent
from vortex.data.flow import FlowResource
from vortex.data.handlers import HandlerError
from vortex.data.providers import VortexStd
from vortex.data.stores import _VortexCacheBaseStore, VortexPromiseStore, PromiseCacheStore
from vortex.layout.dataflow import SectionFatalError
from vortex.tools.delayedactions import AbstractFileBasedDelayedActionsHandler, d_action_status
from vortex.tools.prestaging import PrestagingTool, prestaging_p
from vortex.tools.storage import FixedEntryCache
from vortex.tools.systems import ExecutionError

MYPYFILE = os.path.abspath(__file__)

tloglevel = 'critical'


# The test cache Storage Object
class _TmpDataCache(FixedEntryCache):
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
        return self.sh.path.join(self.session.rundir, self.session.tag,
                                 'testcache', self.actual_headdir)

    def _actual_earlyretrieve(self, item, local, **kwargs):
        dirextract = kwargs.get("dirextract", False)
        tarextract = kwargs.get("tarextract", False)
        if not (dirextract or tarextract):
            return self.context.delayedactions_hub.register((self._formatted_path(item),
                                                             kwargs.get('fmt', 'foo'),
                                                             kwargs.get('intent', 'in')),
                                                            kind='testlocalcp',
                                                            goal='get')
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
class VortexCacheTmpStore(_VortexCacheBaseStore):

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
            intent=options.get('intent', CACHE_GET_INTENT_DEFAULT),
            fmt=options.get('fmt'),
            info=options.get('rhandler', None),
            tarextract=options.get('auto_tarextract', False),
            dirextract=options.get('auto_dirextract', False),
            uniquelevel_ignore=options.get('uniquelevel_ignore', True),
            silent=options.get('silent', False),
        )
        return rc

    def incachefinaliseget(self, result_id, remote, local, options):
        rc = self.cache.finaliseretrieve(
            result_id,
            remote['path'], local,
            intent=options.get('intent', CACHE_GET_INTENT_DEFAULT),
            fmt=options.get('fmt'),
            info=options.get('rhandler', None),
            tarextract=options.get('auto_tarextract', False),
            dirextract=options.get('auto_dirextract', False),
            uniquelevel_ignore=options.get('uniquelevel_ignore', True),
            silent=options.get('silent', False),
        )
        return rc and self._hash_get_check(self.incacheget, remote, local, options)

    def vortexearlyget(self, remote, local, options):
        """Proxy to :meth:`incacheget`."""
        return self.incacheearlyget(remote, local, options)

    def vortexfinaliseget(self, result_id, remote, local, options):
        """Proxy to :meth:`incacheget`."""
        return self.incachefinaliseget(result_id, remote, local, options)


class VortexCacheTmpStoreBis(_VortexCacheBaseStore):

    _footprint = dict(
        info = 'VORTEX MTOOL like Cache access (without earlyget)',
        attr = dict(
            netloc = dict(
                values  = ['vortex.testcache0.fr', ],
            ),
            strategy = dict(
                default = 'testcache',
            ),
            headdir = dict(
                default = 'fastvortex',
            )
        )
    )


class BasicTmpMultiStore(MultiStore):
    """Combined cache and archive legacy VORTEX stores.

    By '-legacy' we mean that stack resources are ignored.
    """

    _footprint = dict(
        info='VORTEX multi access',
        attr=dict(
            scheme=dict(
                values=['vortex'],
            ),
            netloc=dict(
                values=['vortex.testmulti.fr'],
            )
        )
    )

    def alternates_netloc(self):
        """Two times the same underlying store... that's ugly but."""
        return [self.netloc.firstname + d for d in ('.testcache0.fr', '.testcache.fr')]


class TmpPromiseCacheStore(PromiseCacheStore):
    """Some kind of vortex cache for demo expected resources."""

    _footprint = dict(
        info = 'EXPECTED cache access',
        attr = dict(
            netloc = dict(
                values  = ['promise.testcache.fr'],
            ),
            headdir = dict(
                default = 'promise',
                outcast = ['xp', 'vortex'],
            ),
            strategy=dict(
                default='testcache',
            ),
        )
    )


class VortexTmpPromiseStore(VortexPromiseStore):
    """Combine a Promise Store for expected resources and a Demo VORTEX Store."""

    _footprint = dict(
        info = 'VORTEX promise store',
        attr = dict(
            scheme = dict(
                values = ['xvortex'],
            ),
            prstorename=dict(
                optional=True,
                default='promise.testcache.fr',
            ),
            netloc = dict(
                outcast = [],
                values = ['vortex.testcache.fr', 'vortex.testmulti.fr'],
            ),
        )
    )


# A test delayed action... (it's just a cp)
class TmpLocalCpDelayedGetHandler(AbstractFileBasedDelayedActionsHandler):

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
class VortexTmp(VortexStd):
    """Standard Vortex provider (any experiment with an Olive id)."""

    _footprint = dict(
        info = 'Vortex provider for casual experiments with an Olive XPID',
        attr = dict(
            namespace = dict(
                values   = ['vortex.testcache.fr', 'vortex.testmulti.fr'],
            )
        ),
    )


# In order to test prestaging

class TmpCachePrestagingTool(PrestagingTool):

    _footprint = dict(
        info = "Process testcache pre-staging requests.",
        attr = dict(
            issuerkind = dict(
                values = ['cachestore', ]
            ),
            strategy = dict(
                values = ['testcache'],
            ),
            scheme = dict(),
        )
    )

    def flush(self, email=None):
        """Actually fake prestaging."""
        if len(self):
            with open('prestaging_req_{0.strategy:s}_pri{0.priority:d}.txt'.format(self),
                      mode='w') as fh_req:
                fh_req.write('\n'.join(sorted(self.items())))
        return True


# Test resources

class AbstractTmpResource(FlowResource):

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


class TmpResource1(AbstractTmpResource):

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


class TmpResource2(AbstractTmpResource):

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


class TmpResource9(AbstractTmpResource):

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


@loggers.unittestGlobalLevel(tloglevel)
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
                                       glove=footprints.proxy.glove())
        self.cursession.activate()
        self.cursession.rundir = self.tmpdir
        self.cursession.context.cocoon()
        self.cursession.glove.vapp = 'arpege'
        self.cursession.glove.vconf = '4dvarfr'
        cache_4d = self.sh.path.join('testcache', 'vortex', 'arpege', '4dvarfr')
        tests_dir = self.sh.path.dirname(MYPYFILE)
        self.sh.mkdir(cache_4d)
        for xp_input in ('ABC1', 'ABC2'):
            self.sh.softlink(self.sh.path.join(tests_dir, 'data', cache_4d, xp_input),
                             self.sh.path.join(cache_4d, xp_input))

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
        with open(rh.container.iotarget()) as fhin:
            lines = fhin.readlines()
            self.assertEqual(lines[0], '{:s}\n'.format(rh.resource.kind))
            i = 1
            while not lines[-i].rstrip('\n'):
                i += 1
            self.assertEqual(lines[-i], finalstatement)

    def test_simpleget_and_put(self):
        desc = self.default_fp_stuff
        desc.update(kind=['utest1', 'utest2'], local='[kind]_get')
        del desc['namespace']
        descO = desc.copy()
        descO.update(experiment='CBA1')
        descdiff = desc.copy()
        descdiff.update(experiment='ABC2')
        voiddescdiff = desc.copy()
        voiddescdiff.update(experiment=None)
        for namespace in ('vortex.testcache.fr', 'vortex.testmulti.fr'):
            for batch in [True, False]:
                # Input
                rhs = toolbox.input(now=True, verbose=False, batch=batch, namespace=namespace,
                                    **desc)
                rcdiff = toolbox.diff(namespace=namespace, **descdiff)
                self.assertTrue(all(rcdiff))
                # If namespace or experiment is None, the diff is ignored
                rcdiff = toolbox.diff(namespace=None, **descdiff)
                self.assertListEqual(rcdiff, [])
                rcdiff = toolbox.diff(namespace=namespace, **voiddescdiff)
                self.assertListEqual(rcdiff, [])
                for rh in rhs:
                    self.assertIntegrity(rh)
                # Output
                rhsO = toolbox.output(now=True, verbose=False, batch=batch, namespace=namespace,
                                      **descO)
                for rh in rhsO:
                    xloc = rh.locate().split(';')
                    self.assertTrue(xloc)
                    for loc in xloc:
                        self.assertTrue(self.sh.path.exists(loc))
                    self.assertIntegrity(rh)
                    rh.delete()
                for rh in rhs:
                    rh.clear()

    def test_simple_promises(self):
        for batch in [True, False]:
            desc_i1 = self.default_fp_stuff
            desc_i1.update(kind='utest1', local='[kind]_get')
            desc_o1 = self.default_fp_stuff
            desc_o1.update(kind=['utest1', 'utest2'], local='[kind]_get', experiment='CBA1')
            desc_i2 = self.default_fp_stuff
            desc_i2.update(kind=['utest1', 'utest2'], local='[kind]_getbis', experiment='CBA1')
            desc_i3 = self.default_fp_stuff
            desc_i3.update(kind=['utest1', 'utest2'], local='[kind]_getter', experiment='CBA1')
            # Promises
            rhs_p = toolbox.promise(now=True, verbose=True, role='PromiseTester',
                                    **desc_o1)
            whitness = rhs_p[0].check()
            # This should have not effect since the promise already exists
            rhs_pbis = toolbox.promise(now=True, verbose=False, role='PromiseTester',
                                       **desc_o1)
            self.assertEqual(rhs_pbis[0].check().st_mtime, whitness.st_mtime)
            # Input (promised files)
            rhs_2 = toolbox.input(now=True, verbose=False, expected=True, batch=batch,
                                  **desc_i2)
            rhs_3 = toolbox.input(now=True, verbose=False, expected=True, batch=batch,
                                  **desc_i3)
            for rh in rhs_2:
                self.assertTrue(rh.is_expected())
                self.assertFalse(rh.is_grabable())
            with self.assertRaises(HandlerError):
                rhs_2[0].wait(sleep=0.1, timeout=0.2, fatal=True)
            self.assertFalse(rhs_2[1].wait(sleep=0.1, timeout=0.2, fatal=False))
            # Test the Arome/Arpege script based sync system
            pr_getter_file0 = rhs_3[0].mkgetpr()
            self.assertTrue(self.sh.path.exists(pr_getter_file0))
            pr_getter_file1 = rhs_3[1].mkgetpr()
            self.assertTrue(self.sh.path.exists(pr_getter_file1))
            # Input (original files)
            rhs_1 = toolbox.input(now=True, verbose=False,
                                  **desc_i1)
            for rh in rhs_1:
                self.assertIntegrity(rh)
            # Put the first file, delete the second
            rhs_p[0].put()
            rhs_p[1].delete()
            # Effect on expected files
            for rh in rhs_2:
                self.assertTrue(rh.is_expected())
            self.assertTrue(rhs_2[0].is_grabable())
            self.assertTrue(rhs_2[0].is_grabable(check_exists=True))
            self.assertTrue(rhs_2[1].is_grabable())
            self.assertFalse(rhs_2[1].is_grabable(check_exists=True))
            self.assertTrue(rhs_2[0].wait())
            self.assertFalse(rhs_2[1].wait())
            for rh in rhs_2:
                self.assertTrue(rh.is_expected())
            self.assertTrue(rhs_2[0].get())
            self.assertFalse(rhs_2[1].get())
            for rh in rhs_2:
                self.assertFalse(rh.is_expected())
            self.assertTrue(self.sh.diff(rhs_1[0].container.localpath(),
                                         rhs_2[0].container.localpath()))
            # Effect on the sync scripts
            self.sh.spawn(['./' + pr_getter_file0, ])
            self.assertTrue(self.sh.path.exists(rhs_3[0].container.localpath()))
            self.assertTrue(self.sh.readlink(rhs_3[0].container.localpath()))
            self.assertIntegrity(rhs_3[0])
            with self.assertRaises(ExecutionError):
                self.sh.spawn(['./' + pr_getter_file1, ])
            self.assertTrue(self.sh.rclast, 2)
            # Some cleaning for the next iteration
            self.sh.remove(pr_getter_file0)
            self.sh.remove(pr_getter_file1)
            # Cleaning
            for rh in rhs_1:
                rh.clear()
            for rh in rhs_2:
                rh.clear()
            rhs_p[0].delete()

    def test_prestage(self):
        desc = self.default_fp_stuff
        desc.update(kind=['utest1', 'utest2'], local='[kind]_get')
        # Input
        rhs = toolbox.rload(**desc)
        for rh in rhs:
            rh.prestage()
            # Do it twice (it should do nothing)
            rh.prestage()
        rhs[0].prestage(priority=prestaging_p.low)
        rhs[1].prestage(priority=prestaging_p.urgent)
        loc0 = rhs[0].locate().split(';')[0]
        loc1 = rhs[1].locate().split(';')[0]
        phub = self.cursession.context.prestaging_hub
        self.assertEqual(len(phub._get_ptools()), 3)
        self.assertEqual(len(phub._get_ptools(priority_threshold=prestaging_p.normal)), 2)
        for urgent_one in phub._get_ptools(priority_threshold=prestaging_p.urgent):
            self.assertEqual(len(urgent_one), 1)
        phub.clear(priority_threshold=prestaging_p.urgent)
        for urgent_one in phub._get_ptools(priority_threshold=prestaging_p.urgent):
            self.assertEqual(len(urgent_one), 0)
        verb_description = str(phub)
        self.assertIn(loc0, verb_description)
        self.assertIn(loc1, verb_description)
        phub.flush(priority_threshold=prestaging_p.normal)
        self.assertTrue(self.sh.path.exists('prestaging_req_testcache_pri{:d}.txt'
                                            .format(prestaging_p.normal)))
        self.assertFalse(self.sh.path.exists('prestaging_req_testcache_pri{:d}.txt'
                                             .format(prestaging_p.urgent)))
        self.assertFalse(self.sh.path.exists('prestaging_req_testcache_pri{:d}.txt'
                                             .format(prestaging_p.low)))
        with open('prestaging_req_testcache_pri{:d}.txt'.format(prestaging_p.normal)) as fh_req:
            self.assertEqual(fh_req.read(), '\n'.join(sorted([loc0, loc1])))
        verb_description = str(phub)
        self.assertIn(loc0, verb_description)
        self.assertNotIn(loc1, verb_description)

    def test_hookedget_and_put(self):
        desc = self.default_fp_stuff
        desc.update(kind=['utest1', 'utest2'], local='[kind]_get')
        descO = desc.copy()
        descO['namespace'] = 'vortex.testmulti.fr'
        descO['experiment'] = 'CBA1'
        for batch in [True, False]:
            rhs = toolbox.input(now=True, verbose=True, intent='inout', batch=batch,
                                hook_toto=(toto_hook, ),
                                **desc)
            for rh in rhs:
                self.assertIntegrity(rh, finalstatement='Toto was here...\n')
            print(self.sh.ll())
            toolbox.output(now=True, verbose=False, batch=batch,
                           hook_toto=(toto_hook, 'Toto wrote here...\n'),
                           **descO)
            # Tis should have no effect sinc toto_hook as already been executed
            rhsO = toolbox.output(now=True, verbose=False, batch=batch,
                                  hook_toto=(toto_hook, 'Toto wrote here a second time...\n'),
                                  **descO)
            for rh in rhsO:
                xloc = rh.locate().split(';')
                self.assertTrue(xloc)
                for loc in xloc:
                    self.assertTrue(self.sh.path.exists(loc))
                self.assertIntegrity(rh, finalstatement='Toto wrote here...\n')
                rh.delete()
            for rh in rhs:
                rh.clear()

    def test_rh_check_delayed_get(self):
        for namespace in ('vortex.testcache.fr', 'vortex.testmulti.fr'):
            desc1 = self.default_fp_stuff
            desc1.update(kind='utest1', local='utest1_get', namespace=namespace)
            rh1 = toolbox.rh(**desc1)
            desc2 = self.default_fp_stuff
            desc2.update(kind='utest2', local='utest2_get', namespace=namespace)
            rh2 = toolbox.rh(**desc2)
            # Check
            self.assertTrue(rh1.check())
            self.assertTrue(rh2.check())
            # Delayed get
            self.assertTrue(rh1.earlyget(intent='in'))
            self.assertTrue(rh2.earlyget(intent='in'))
            self.assertTrue(rh1.finaliseget())
            self.assertTrue(rh2.finaliseget())
            # Is it ok
            self.assertIntegrity(rh1)
            self.assertIntegrity(rh2)
            # Some cleaning
            rh1.clear()
            rh2.clear()

    def test_simpleinsitu(self):
        desc = self.default_fp_stuff
        desc.update(kind='utest1', local='utest1_get', )
        for batch in [True, False]:
            rhs = toolbox.rload(**desc)
            for rh in rhs:
                rh.get()
                self.assertIntegrity(rh)
            rhsbis_bare = toolbox.rload(insitu=True, **desc)
            for rh in rhsbis_bare:
                rh.get()
            rhsbis = toolbox.input(now=True, insitu=True, batch=batch, **desc)
            self.assertIntegrity(rhsbis[0])
            desc2 = self.default_fp_stuff
            desc2.update(kind='utest2', local='utest1_get', )
            with self.assertRaises(SectionFatalError):
                toolbox.input(now=True, insitu=True, batch=batch, **desc2)
            desc3 = self.default_fp_stuff
            desc3.update(kind='utest2', local='utest2_get', )
            rhsquad = toolbox.input(now=True, insitu=True, batch=batch, **desc3)
            self.assertIntegrity(rhsquad[0])
            for rh in [rhs[0], rhsquad[0]]:
                rh.clear()

    def test_simplealternate_and_missing(self):
        for i, batch in enumerate([True, False]):
            therole = 'Toto{:d}'.format(i)
            # Missing
            descM = self.default_fp_stuff
            descM.update(kind='utest1', local='utestM_get{:d}'.format(i), model='mocage')
            rhsM = toolbox.input(role=therole, now=True, fatal=False, verbose=False, batch=batch, **descM)
            self.assertFalse(rhsM)
            # Alternate
            desc = self.default_fp_stuff
            desc.update(kind='utest1', local='utest1_get{:d}'.format(i), model='arome')
            rhs0 = toolbox.input(role=therole, now=True, fatal=False, verbose=False, batch=batch, **desc)
            self.assertFalse(rhs0)
            rhs0_bis = toolbox.input(alternate=therole, now=True, fatal=False, verbose=False, batch=batch, **desc)
            self.assertFalse(rhs0_bis)
            desc.update(kind='utest1', local='utest1_get{:d}'.format(i), model='arpege')
            rhs1 = toolbox.input(alternate=therole, now=True, fatal=False, verbose=False, batch=batch, **desc)
            self.assertIntegrity(rhs1[0])
            rhs1bis = toolbox.input(alternate=therole, now=True, fatal=False, verbose=False, batch=batch, **desc)
            self.assertTrue(rhs1bis)
            self.assertFalse(rhs1bis[0].container.filled)
            desc.update(kind='utest1', local='utest1_get{:d}'.format(i), model='safran')
            rhs2 = toolbox.input(alternate=therole, now=True, fatal=True, verbose=False, batch=batch, **desc)
            self.assertTrue(rhs2)
            nominaltoto = list(self.sequence.filtered_inputs(role=therole, no_alternates=True))
            self.assertEqual(len(nominaltoto), 2)
            alltoto = list(self.sequence.filtered_inputs(role=therole))
            self.assertEqual(len(alltoto), 6)
            for s in alltoto:
                if s.role is not None:
                    if s.rh.container.localpath() == 'utest1_get{:d}'.format(i):
                        self.assertIs(self.sequence.is_somehow_viable(s).rh, rhs1[0])
                    else:
                        self.assertIs(self.sequence.is_somehow_viable(s), None)
                else:
                    with self.assertRaises(ValueError):
                        self.sequence.is_somehow_viable(s)
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
        self.cursession.context.localtracker.json_dump()
        # Now test the insitu stuff
        self.cursession.context.newcontext('insitutest', focus=True)
        self.cursession.context.cocoon()
        for i in range(0, 2):
            self.sh.mv('../utest1_get{:d}'.format(i), './utest1_get{:d}'.format(i))
        self.sh.mv('../local-tracker-state.json', 'local-tracker-state.json')
        self.cursession.context.localtracker.json_load()
        for i, batch in enumerate([True, False]):
            therole = 'Toto{:d}'.format(i)
            # Missing
            descM = self.default_fp_stuff
            descM.update(kind='utest1', local='utestM_get{:d}'.format(i), model='mocage')
            rhsM = toolbox.input(role=therole, now=True, insitu=True, fatal=False, verbose=False, batch=batch, **descM)
            self.assertFalse(rhsM)
            # Alternate
            desc = self.default_fp_stuff
            desc.update(kind='utest1', local='utest1_get{:d}'.format(i), model='arome')
            rhs0 = toolbox.input(role=therole, now=True, insitu=True, fatal=False, verbose=False, batch=batch, **desc)
            self.assertFalse(rhs0)
            rhs0_bis = toolbox.input(alternate=therole, now=True, insitu=True, fatal=False, verbose=False, batch=batch,
                                     **desc)
            self.assertFalse(rhs0_bis)
            desc.update(kind='utest1', local='utest1_get{:d}'.format(i), model='arpege')
            rhs1 = toolbox.input(alternate=therole, now=True, insitu=True, fatal=False, verbose=False, batch=batch, **desc)
            self.assertIntegrity(rhs1[0])
            rhs1bis = toolbox.input(alternate=therole, now=True, insitu=True, fatal=False, verbose=False, batch=batch, **desc)
            self.assertTrue(rhs1bis)
            self.assertFalse(rhs1bis[0].container.filled)
            rhs1ter = toolbox.rload(insitu=True, **desc)
            self.assertTrue(rhs1ter[0].get(alternate=True))
            desc.update(kind='utest1', local='utest1_get{:d}'.format(i), model='safran')
            rhs2 = toolbox.input(alternate=therole, now=True, insitu=True, fatal=True, verbose=False, batch=batch, **desc)
            self.assertTrue(rhs2)
            efftoto = self.sequence.effective_inputs(role=therole)
            self.assertEqual(len(efftoto), 1)
            self.assertEqual(efftoto[0].rh.resource.model, 'arpege')
            # Cleaning
            rhs1[0].clear()

    def test_coherentget(self):
        desc = self.default_fp_stuff
        vswitch = False
        rh0a = toolbox.input(now=True, verbose=vswitch, coherentgroup='toto,titi,tata_[cutoff]',
                             kind='utest1', local='utest1_get0a', **desc)
        rh0b = toolbox.input(now=True, verbose=vswitch, coherentgroup='toto,titi',
                             kind='utest1', local='utest1_get0b', **desc)
        rh1 = toolbox.input(now=True, verbose=vswitch, coherentgroup='toto',
                            kind='utest1', local='utest1_get1', **desc)
        rh2 = toolbox.input(now=True, verbose=vswitch, fatal=False, coherentgroup='[failer]',
                            kind='utest1,utest9,utest2', local='[kind]_get2', failer='toto',
                            **desc)
        rh3 = toolbox.input(role='TOTO', now=True, verbose=vswitch, fatal=False, coherentgroup='[role:lower]',
                            kind='utest1', local='utest1_get3', **desc)
        rh3b = toolbox.input(now=True, verbose=vswitch, fatal=False, coherentgroup='titi',
                             kind='utest9', local='utest9_get3b', **desc)
        rh4 = toolbox.input(now=True, verbose=vswitch,
                            kind='utest1', local='utest1_get4', **desc)
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
