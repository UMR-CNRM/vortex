from copy import deepcopy
import os
import tempfile
import unittest

from bronx.stdtypes.date import Date, Time
from bronx.fancies.loggers import unittestGlobalLevel
import footprints as fp

import vortex.data.providers  # @UnusedImport
import olive.data.providers  # @UnusedImport
from vortex.data import geometries
from vortex.syntax.stdattrs import LegacyXPid, FreeXPid
from vortex.tools.net import uriparse

DATAPATHTEST = os.path.join(os.path.dirname(__file__), 'data')

TLOGLEVEL = 9999


class DummyRessource:

    def __init__(self, realkind='dummy', bname='dummyres', cutoff='assim',
                 date=Date(2000, 1, 1, 0, 0, 0), term=0, model='arpege'):
        self.model = model
        self.date = date
        self.term = Time(term)
        self.geometry = geometries.get(tag='glob25')
        self.cutoff = cutoff
        self._bname = bname
        self.realkind = realkind
        self.mailbox = {}

    def basename(self, kind):
        actualbasename = getattr(self, kind + '_basename',
                                 self.generic_basename)
        return actualbasename()

    def pathinfo(self, kind):
        actualpathinfo = getattr(self, kind + '_pathinfo',
                                 self.generic_pathinfo)
        return actualpathinfo()

    def urlquery(self, kind):
        actualurlquery = getattr(self, kind + '_urlquery',
                                 self.vortex_urlquery)
        return actualurlquery()

    def namebuilding_info(self):
        return dict(radical=self._bname,
                    flow=[{'date': self.date}, {'shortcutoff': self.cutoff}])

    def generic_pathinfo(self):
        return dict(
            nativefmt='fa',
            model=self.model,
            date=self.date,
            cutoff=self.cutoff,
            geometry=self.geometry,)

    def generic_basename(self):
        pass

    def olive_basename(self):
        return self._bname

    def archive_basename(self):
        return self._bname

    def vortex_urlquery(self):
        return None

    def stackedstorage_resource(self):
        return None, True


class TestProviderMagic(unittest.TestCase):

    def test_magic_easy(self):
        message = "I'm doing what I want !"
        pr = fp.proxy.provider(vapp='arpege',
                               vconf='4dvar',
                               fake='True',
                               magic="I'm doing what I want !")
        dummy_res = None
        self.assertEqual(pr.uri(dummy_res), message)


class TestProviderRemote(unittest.TestCase):

    def setUp(self):
        self.fp_defaults = dict(vapp='arpege',
                                vconf='4dvar')
        self.t_protocol = ('scp', 'ftp', 'rcp')
        self.t_res = DummyRessource()

    def test_remote_basics(self):
        pr = fp.proxy.provider(remote='/home/machin/dummy',
                               ** self.fp_defaults)
        self.assertEqual(pr.scheme(None), 'file')
        self.assertEqual(pr.netloc(None), 'localhost')
        self.assertEqual(pr.pathname(self.t_res),
                         '/home/machin')
        self.assertEqual(pr.basename(self.t_res),
                         'dummy')
        self.assertEqual(pr.uri(self.t_res),
                         'file://localhost/home/machin/dummy')
        pr = fp.proxy.provider(remote='dummy', ** self.fp_defaults)
        self.assertEqual(pr.uri(self.t_res),
                         'file://localhost/dummy?relative=1')

    def test_remote_fancy(self):
        for proto in self.t_protocol:
            pr = fp.proxy.provider(tube=proto, remote='/home/machin/dummy',
                                   ** self.fp_defaults)
            self.assertEqual(pr.scheme(None), proto)
            # hostname ?
            pr = fp.proxy.provider(tube=proto, remote='/home/machin/dummy',
                                   hostname='superserver',
                                   ** self.fp_defaults)
            self.assertEqual(pr.netloc(None), 'superserver')
            pr = fp.proxy.provider(tube=proto, remote='/home/machin/dummy',
                                   hostname='superserver', username='toto',
                                   ** self.fp_defaults)
            self.assertEqual(pr.netloc(None), 'superserver')
            self.assertEqual(pr.uri(self.t_res),
                             '{}://toto@superserver/home/machin/dummy'.format(proto))


class TestProviderVortexStd(unittest.TestCase):

    def setUp(self):
        self.fp_defaults = dict(vapp='arpege',
                                vconf='4dvar',
                                block='dummy',
                                experiment='VOID',
                                namespace='vortex.cache.fr')
        self.t_namespaces = ('vortex.cache.fr',
                             'vortex.archive.fr',
                             'vortex.multi.fr')
        self.t_res = DummyRessource()

    def test_vortexstd_basics(self):
        for ns in self.t_namespaces:
            fpd = dict()
            fpd.update(self.fp_defaults)
            # Namespace only
            fpd['namespace'] = ns
            pr = fp.proxy.provider(** fpd)
            self.assertEqual(pr.scheme(None), 'vortex')
            self.assertEqual(pr.netloc(None), ns)
            self.assertIs(pr.member, None)
            # Member
            fpd['member'] = 3
            pr = fp.proxy.provider(** fpd)
            self.assertEqual(pr.member, 3)
            # Expected
            fpd['expected'] = True
            pr = fp.proxy.provider(** fpd)
            self.assertEqual(pr.scheme(None), 'xvortex')

    def test_vortexstd_paths(self):
        pr = fp.proxy.provider(** self.fp_defaults)
        self.assertEqual(pr.pathname(self.t_res),
                         'arpege/4dvar/VOID/20000101T0000A/dummy')
        self.assertEqual(pr.uri(self.t_res),
                         'vortex://' + self.fp_defaults['namespace'] +
                         '/arpege/4dvar/VOID/20000101T0000A/dummy/dummyres')
        # member ?
        pr = fp.proxy.provider(member=3, ** self.fp_defaults)
        self.assertEqual(pr.pathname(self.t_res),
                         'arpege/4dvar/VOID/20000101T0000A/mb003/dummy')
        # username ?
        pr = fp.proxy.provider(username='toto', ** self.fp_defaults)
        self.assertEqual(pr.uri(self.t_res),
                         'vortex://toto@' + self.fp_defaults['namespace'] +
                         '/arpege/4dvar/VOID/20000101T0000A/dummy/dummyres')
        # set aside in various styles ?
        pr = fp.proxy.provider(vortex_set_aside=fp.stdtypes.FPDict(VOID='OPER'),
                               **self.fp_defaults)
        self.assertEqual(uriparse(pr.uri(self.t_res)),
                         uriparse('vortex://' + self.fp_defaults['namespace'] +
                                  '/arpege/4dvar/VOID/20000101T0000A/dummy/dummyres' +
                                  '?setaside_n=vsop.cache.fr' +
                                  '&setaside_p=arpege%2F4dvar%2FOPER%2F20000101T0000A%2Fdummy%2Fdummyres'))
        pr = fp.proxy.provider(vortex_set_aside=fp.stdtypes.FPDict(VOID=fp.stdtypes.FPDict(experiment='OPER')),
                               **self.fp_defaults)
        self.assertEqual(uriparse(pr.uri(self.t_res)),
                         uriparse('vortex://' + self.fp_defaults['namespace'] +
                                  '/arpege/4dvar/VOID/20000101T0000A/dummy/dummyres' +
                                  '?setaside_n=vsop.cache.fr' +
                                  '&setaside_p=arpege%2F4dvar%2FOPER%2F20000101T0000A%2Fdummy%2Fdummyres'))
        pr = fp.proxy.provider(
            vortex_set_aside=fp.stdtypes.FPDict(
                defaults=fp.stdtypes.FPDict(storage='toto.bucket.localhost'),
                edits=fp.stdtypes.FPDict(VOID=fp.stdtypes.FPDict(experiment='OPER')),
            ), **self.fp_defaults)
        self.assertEqual(uriparse(pr.uri(self.t_res)),
                         uriparse('vortex://' + self.fp_defaults['namespace'] +
                                  '/arpege/4dvar/VOID/20000101T0000A/dummy/dummyres' +
                                  '?setaside_args_storage=toto.bucket.localhost'
                                  '&setaside_n=vsop.cache.fr' +
                                  '&setaside_p=arpege%2F4dvar%2FOPER%2F20000101T0000A%2Fdummy%2Fdummyres'))
        pr = fp.proxy.provider(
            vortex_set_aside=fp.stdtypes.FPDict(
                defaults=fp.stdtypes.FPDict(storage='toto.bucket.localhost'),
                includes=('void', ),
            ), **self.fp_defaults)
        self.assertEqual(uriparse(pr.uri(self.t_res)),
                         uriparse('vortex://' + self.fp_defaults['namespace'] +
                                  '/arpege/4dvar/VOID/20000101T0000A/dummy/dummyres' +
                                  '?setaside_args_storage=toto.bucket.localhost'
                                  '&setaside_n=vortex.cache.fr' +
                                  '&setaside_p=arpege%2F4dvar%2FVOID%2F20000101T0000A%2Fdummy%2Fdummyres'))
        pr = fp.proxy.provider(
            vortex_set_aside=fp.stdtypes.FPDict(
                defaults=fp.stdtypes.FPDict(storage='toto.bucket.localhost'),
                includes=('abcd', ),
            ), **self.fp_defaults)
        self.assertEqual(uriparse(pr.uri(self.t_res)),
                         uriparse('vortex://' + self.fp_defaults['namespace'] +
                                  '/arpege/4dvar/VOID/20000101T0000A/dummy/dummyres'))
        pr = fp.proxy.provider(
            vortex_set_aside=fp.stdtypes.FPDict(
                defaults=fp.stdtypes.FPDict(storage='toto.bucket.localhost'),
                excludes=('void',),
            ), **self.fp_defaults)
        self.assertEqual(uriparse(pr.uri(self.t_res)),
                         uriparse('vortex://' + self.fp_defaults['namespace'] +
                                  '/arpege/4dvar/VOID/20000101T0000A/dummy/dummyres'))
        pr = fp.proxy.provider(
            vortex_set_aside=fp.stdtypes.FPDict(
                defaults=fp.stdtypes.FPDict(storage='toto.bucket.localhost'),
                excludes=('abcd',),
            ), **self.fp_defaults)
        self.assertEqual(uriparse(pr.uri(self.t_res)),
                         uriparse('vortex://' + self.fp_defaults['namespace'] +
                                  '/arpege/4dvar/VOID/20000101T0000A/dummy/dummyres' +
                                  '?setaside_args_storage=toto.bucket.localhost'
                                  '&setaside_n=vortex.cache.fr' +
                                  '&setaside_p=arpege%2F4dvar%2FVOID%2F20000101T0000A%2Fdummy%2Fdummyres'))


@unittestGlobalLevel(TLOGLEVEL)
class TestProviderVortexFree(unittest.TestCase):

    def setUp(self):
        # Generate a temporary directory
        self.t = vortex.sessions.current()
        self.sh = self.t.system()
        self.sh.target(hostname='unittest', inetname='unittest',
                       inifile=os.path.join(DATAPATHTEST, 'target-test.ini'),
                       sysname='Local')  # Trick the vortex's system !
        self.tmpdir = self.sh.path.realpath(tempfile.mkdtemp(suffix='_test_providers'))
        self.oldpwd = self.sh.pwd()
        self.sh.cd(self.tmpdir)
        # various utility things
        self.t_res = DummyRessource()

        self.sh.symlink(self.sh.path.join(DATAPATHTEST, 'provider-vortex-free_ok.ini'),
                        'provider-vortex-free_ok.ini')
        for i in range(4):
            self.sh.symlink(self.sh.path.join(DATAPATHTEST,
                                              'provider-vortex-free_ko{:d}.ini'.format(i + 1)),
                            'provider-vortex-free_ko{:d}.ini'.format(i + 1))
        self.sh.touch('provider-vortex-free_empty.ini')

        self.sh.symlink(self.sh.path.join(DATAPATHTEST, 'test_provider_vtx_free0.ini'),
                        'test_provider_vtx_free0.ini')
        #
        vortex.data.providers.logger.setLevel('DEBUG')

    def tearDown(self):
        self.sh.target()
        self.sh.cd(self.oldpwd)
        self.sh.remove(self.tmpdir)

    @staticmethod
    def deal(**kwargs):
        p_opts = dict(vapp='arpege',
                      vconf='4dvar',
                      block='dummy',
                      experiment='GRUIK@unittestonly',
                      namespace='vortex.cache.fr',
                      provider_global_config='provider-vortex-free_ok.ini')
        p_opts.update(kwargs)
        return fp.proxy.provider(** p_opts)

    def ds_check(self, data=None, **kwargs):
        d_id = vortex.data.providers.VortexFreeStd._datastore_id
        self.assertTrue(self.t.datastore.check(d_id, kwargs))
        if data is not None:
            self.assertEqual(self.t.datastore.get(d_id, kwargs), data)

    def test_vortex_free_configuration_parser(self):
        # Empty configuration file
        pr = self.deal(provider_global_config='provider-vortex-free_empty.ini')
        self.assertEqual(pr.experiment_conf, dict())
        # The data store should be fed
        self.ds_check(data=list(), conf_target='provider-vortex-free_empty.ini')

        # Configuration file with a default section -> forbidden
        pr = self.deal(provider_global_config='provider-vortex-free_ko1.ini')
        with self.assertRaises(ValueError):
            pr.experiment_conf

        # Configuration file with a failing regex -> the corresponding section is ignored
        pr = self.deal(provider_global_config='provider-vortex-free_ko2.ini')
        self.assertEqual(pr.experiment_conf, dict())
        # The data store should be fed
        self.ds_check(data=list(), conf_target='provider-vortex-free_ko2.ini')

        # Configuration file with a failing regex -> the remote configuration file is missing
        pr = self.deal(provider_global_config='provider-vortex-free_ko3.ini')
        with self.assertRaises(OSError):
            self.assertEqual(pr.experiment_conf, dict())

        # Configuration file with a default section -> no generic_restrict
        pr = self.deal(provider_global_config='provider-vortex-free_ko4.ini')
        with self.assertRaises(ValueError):
            pr.experiment_conf

    def test_vortex_free_configurable_paths(self):
        # 4dvar baseline
        pr = self.deal()
        self.assertEqual(pr.actual_experiment(self.t_res), 'DBLE')
        self.ds_check(conf_target='provider-vortex-free_ok.ini',
                      experiment='GRUIK@unittestonly')
        self.assertEqual(pr.netloc(self.t_res), 'vsop.cache.fr')
        r_prod = DummyRessource(cutoff='production')
        self.assertEqual(pr.actual_experiment(r_prod), 'ABC1')
        self.assertEqual(pr.netloc(r_prod), 'vortex.cache.fr')
        r_prod = DummyRessource(cutoff='production', date=Date(2005, 1, 1))
        self.assertEqual(pr.actual_experiment(r_prod), 'ABC2')
        self.assertEqual(pr.netloc(r_prod), 'vortex.cache.fr')
        with self.assertRaises(ValueError):
            # No suitable configuration for very old things
            self.assertEqual(pr.netloc(DummyRessource(date=Date(1990, 1, 1))), 'vsop.cache.fr')

        # Unlisted experiment
        pr = self.deal(experiment='unlisted@unittestonly')
        self.assertEqual(pr.actual_experiment(self.t_res), 'unlisted@unittestonly')

        # Dump/Undump the datastore (check that everything is picklable)
        self.t.datastore.pickle_dump()
        self.t.datastore.pickle_load()
        # Check the list os redirections stored in the pickled datastore
        xp_conf = self.t.datastore.get(
            vortex.data.providers.VortexFreeStd._datastore_id,
            dict(conf_target='provider-vortex-free_ok.ini',
                 experiment='GRUIK@unittestonly')
        )
        redirections = set()
        for redirection_d in xp_conf.values():
            redirections.update(redirection_d.keys())
        self.assertSetEqual(redirections,
                            {LegacyXPid('DBLE'),
                             LegacyXPid('ABC1'), LegacyXPid('ABC2'),
                             LegacyXPid('ENS1'), LegacyXPid('ENS2'),
                             FreeXPid('ENS1@special'), FreeXPid('ENS2@special'),
                             FreeXPid('ENS1@ko')})

        # Arpege ensembles
        pr = self.deal(vconf='pearp')
        self.assertEqual(pr.actual_experiment(self.t_res), 'ENS1')
        self.assertEqual(pr.netloc(self.t_res), 'vortex.cache.fr')
        # Very old stuff
        self.assertEqual(pr.actual_experiment(DummyRessource(date=Date(1990, 1, 1))), 'ENS1')
        # PEAPR member 0
        pr = self.deal(vconf='pearp', member=0)
        self.assertEqual(pr.actual_experiment(self.t_res), 'ENS1@special')
        self.assertEqual(pr.netloc(self.t_res), 'vortex-free.cache.fr')
        # AEARP
        pr = self.deal(vconf='aearp', member=0)
        self.assertEqual(pr.actual_experiment(self.t_res), 'ENS1')
        self.assertEqual(pr.netloc(self.t_res), 'vortex.cache.fr')

        # Arome ensembles
        pr = self.deal(vapp='arome', vconf='pefrance')
        self.assertEqual(pr.actual_experiment(self.t_res), 'ENS2')
        self.assertEqual(pr.netloc(self.t_res), 'vortex.cache.fr')
        pr = self.deal(vapp='arome', vconf='pefrance', block='other')
        self.assertEqual(pr.actual_experiment(self.t_res), 'ENS2@special')
        self.assertEqual(pr.netloc(self.t_res), 'vortex-free.cache.fr')


class TestProviderVortexOp(unittest.TestCase):

    def setUp(self):
        self.fp_defaults = dict(vapp='arpege',
                                vconf='4dvar',
                                block='dummy',
                                experiment='oper',
                                namespace='vortex.cache.fr')
        self.t_suites = ('OPER', 'DBLE', 'TEST', 'OP01', 'MIRR',
                         'oper', 'dble', 'test', 'op01', 'mirr')

    def test_vortexop_vsop(self):
        for ns in self.t_suites:
            fpd = dict()
            fpd.update(self.fp_defaults)
            fpd['experiment'] = ns
            pr = fp.proxy.provider(** fpd)
            self.assertEqual(pr.netloc(None), 'vsop.cache.fr')


class TestProviderOlive(unittest.TestCase):

    def setUp(self):
        self.fp_defaults = dict(vapp='arpege',
                                block='dummy',
                                experiment='VOID',
                                namespace='olive.cache.fr')
        self.t_namespaces = ('olive.cache.fr',
                             'olive.archive.fr',
                             'olive.multi.fr')
        self.t_res = DummyRessource()

    def test_olive_basics(self):
        for ns in self.t_namespaces:
            fpd = dict()
            fpd.update(self.fp_defaults)
            # Namespace only
            fpd['namespace'] = ns
            pr = fp.proxy.provider(** fpd)
            self.assertEqual(pr.scheme(None), 'olive')
            self.assertEqual(pr.netloc(None), ns)
            self.assertIs(pr.member, None)

    def test_olive_paths(self):
        pr = fp.proxy.provider(vconf='4dvar', ** self.fp_defaults)
        self.assertEqual(pr.pathname(self.t_res),
                         'VOID/20000101H00A/dummy')
        self.assertEqual(pr.uri(self.t_res),
                         'olive://' + self.fp_defaults['namespace'] +
                         '/VOID/20000101H00A/dummy/dummyres')
        # username ?
        pr = fp.proxy.provider(username='toto', vconf='4dvar', ** self.fp_defaults)
        self.assertEqual(pr.uri(self.t_res),
                         'olive://toto@' + self.fp_defaults['namespace'] +
                         '/VOID/20000101H00A/dummy/dummyres')
        # member ?
        pr = fp.proxy.provider(member=1, vconf='4dvar', ** self.fp_defaults)
        self.assertEqual(pr.uri(self.t_res),
                         'olive://' + self.fp_defaults['namespace'] +
                         '/VOID/20000101H00A/dummy/dummyres')
        pr = fp.proxy.provider(member=1, vconf='pearp', ** self.fp_defaults)
        self.assertEqual(pr.uri(self.t_res),
                         'olive://' + self.fp_defaults['namespace'] +
                         '/VOID/20000101H00A/fc_001/dummy/dummyres')
        pr = fp.proxy.provider(member=1, vconf='aearp', ** self.fp_defaults)
        self.assertEqual(pr.uri(self.t_res),
                         'olive://' + self.fp_defaults['namespace'] +
                         '/VOID/20000101H00A/member_001/dummy/dummyres')


class TestProviderOpArchive(unittest.TestCase):

    def setUp(self):
        self.fp_defaults = dict(vapp='arpege',
                                vconf='4dvar',
                                namespace='[suite].archive.fr')
        self.t_suites = ('oper', 'dbl', 'miroir')
        self.t_res = DummyRessource()
        self.s_remap = dict(dbl='dble', miroir='mirr')

    def _get_provider(self, **kwargs):
        fpd = deepcopy(self.fp_defaults)
        fpd.update(kwargs)
        return fp.proxy.provider(** fpd)

    @staticmethod
    def _get_historic(**kwargs):
        return DummyRessource(
            realkind='historic',
            bname='(icmshfix:modelkey)(histfix:igakey)(termfix:modelkey)(suffix:modelkey)',
            **kwargs
        )

    def test_oparchive_basics(self):
        for ns in self.t_suites:
            pr = fp.proxy.provider(suite=ns, ** self.fp_defaults)
            self.assertEqual(pr.scheme(None), 'op')
            self.assertEqual(pr.netloc(None), '{:s}.archive.fr'.format(self.s_remap.get(ns, ns)))
            self.assertIs(pr.member, None)

    def test_oparchive_strangenames(self):
        # Strange naming convention for historic files
        # PEARP
        pr = self._get_provider(suite='oper', vconf='pearp')
        self.assertEqual(pr.basename(self._get_historic()), 'icmshprev+0000')
        # Arpege 4D / Arpege Court
        for vconf in ('4dvarfr', 'courtfr'):
            pr = self._get_provider(suite='oper', vconf=vconf)
            self.assertEqual(pr.basename(self._get_historic()),
                             'icmsharpe+0000')
            self.assertEqual(pr.basename(self._get_historic(model='surfex')),
                             'icmsharpe+0000.sfx')
        # AEARP
        # no block
        pr = self._get_provider(suite='oper', vconf='aearp')
        self.assertEqual(pr.basename(self._get_historic()),
                         'icmsharpe+0000')
        self.assertEqual(pr.basename(self._get_historic(model='surfex')),
                         'icmsharpe+0000.sfx')
        # block=forecast_infl
        pr = self._get_provider(suite='oper', vconf='aearp', block='forecast_infl')
        self.assertEqual(pr.basename(self._get_historic()),
                         'icmsharpe+0000')
        self.assertEqual(pr.basename(self._get_historic(model='surfex')),
                         'icmsharpe+0000.sfx_infl')
        # block=forecast
        pr = self._get_provider(suite='oper', vconf='aearp', block='forecast')
        self.assertEqual(pr.basename(self._get_historic()),
                         'icmsharpe+0000_noninfl')
        self.assertEqual(pr.basename(self._get_historic(model='surfex')),
                         'icmsharpe+0000.sfx')
        # AROME 3D
        pr = self._get_provider(suite='oper', vapp='arome', vconf='3dvarfr')
        self.assertEqual(pr.basename(self._get_historic(model='arome')),
                         'ICMSHAROM+0000')
        self.assertEqual(pr.basename(self._get_historic(model='surfex')),
                         'ICMSHSURF+0000')
        pr = self._get_provider(suite='oper', vapp='arome', vconf='3dvarfr', block='coupling_fc')
        self.assertEqual(pr.basename(self._get_historic(model='arome')),
                         'guess_coupling_fc')

        # Strange naming convention for grib files
        t_res = DummyRessource(realkind='gridpoint',
                               bname='(gribfix:igakey)_toto')
        # PEARP special case
        pr = self._get_provider(suite='oper', vconf='pearp', member=1)
        self.assertEqual(pr.basename(t_res),
                         'fc_00_1_GLOB25_0000_toto')
        # Others
        pr = self._get_provider(suite='oper')
        self.assertEqual(pr.basename(t_res),
                         'PE00000GLOB25_toto')
        # Even uglier things for the production cutoff :-(
        t_res = DummyRessource(realkind='gridpoint', cutoff='production',
                               bname='(gribfix:igakey)_toto')
        pr = self._get_provider(suite='oper')
        self.assertEqual(pr.basename(t_res),
                         'PEAM000GLOB25_toto')

        # Strange naming convention for errgribvor
        resini = dict(realkind='bgstderr', bname='(errgribfix:igakey)')
        pr1 = self._get_provider(suite='oper')
        pr2 = self._get_provider(suite='oper', vconf='aearp', inout='out')
        t_res = DummyRessource(term=3, ** resini)
        self.assertEqual(pr1.basename(t_res), 'errgribvor')
        self.assertEqual(pr2.basename(t_res), 'errgribvor_assim.out')
        t_res = DummyRessource(term=9, ** resini)
        self.assertEqual(pr1.basename(t_res), 'errgribvor')
        self.assertEqual(pr2.basename(t_res), 'errgribvor_production.out')
        t_res = DummyRessource(term=12, ** resini)
        self.assertEqual(pr1.basename(t_res), 'errgribvor_production_dsbscr')
        self.assertEqual(pr2.basename(t_res), 'errgribvor_production_dsbscr.out')

    def test_oparchive_paths(self):
        for ns in self.t_suites:
            pr = fp.proxy.provider(suite=ns, ** self.fp_defaults)
            self.assertEqual(pr.pathname(self.t_res),
                             'arpege/{}/assim/2000/01/01/r0'.format(ns))
            self.assertEqual(pr.uri(self.t_res),
                             'op://{}.archive.fr'.format(self.s_remap.get(ns, ns)) +
                             '/arpege/{}/assim/2000/01/01/r0/dummyres'.format(ns))
            # username ?
            pr = fp.proxy.provider(suite=ns, username='toto',
                                   ** self.fp_defaults)
            self.assertEqual(pr.uri(self.t_res),
                             'op://toto@{}.archive.fr'.format(self.s_remap.get(ns, ns)) +
                             '/arpege/{}/assim/2000/01/01/r0/dummyres'.format(ns))
            # Member ?
            pr = fp.proxy.provider(suite=ns, member=1, ** self.fp_defaults)
            self.assertEqual(pr.pathname(self.t_res),
                             'arpege/{}/assim/2000/01/01/r0/RUN1'.format(ns))
            # Member PEARP ?
            fpd = dict()
            fpd.update(self.fp_defaults)
            fpd['vconf'] = 'pearp'
            t_res = DummyRessource(realkind='gridpoint')
            pr = fp.proxy.provider(suite=ns, member=1, ** fpd)
            self.assertEqual(pr.pathname(t_res),
                             'pearp/{}/01/r0'.format(ns))


class TestProviderOpArchiveCourt(unittest.TestCase):

    def setUp(self):
        self.fp_defaults = dict(vapp='arpege',
                                experiment='oper',
                                namespace='oper.archive.fr')
        self.t_suites = ('oper', 'dbl', 'test', 'miroir')
        self.t_vconfs = ('frcourt', 'courtfr', 'court')
        self.t_res = DummyRessource()

    def test_oparchivecourt_basics(self):
        for ns in self.t_suites:
            for nc in self.t_vconfs:
                pr = fp.proxy.provider(suite=ns, vconf=nc, ** self.fp_defaults)
                self.assertEqual(pr.scheme(None), 'op')
                self.assertEqual(pr.netloc(None), 'oper.archive.fr')
                self.assertEqual(pr.pathname(self.t_res),
                                 'arpege/{}/court/2000/01/01/r0'.format(ns))

    def test_oparchivecourt_strangenames(self):
        for nc in self.t_vconfs:
            # Ugly things for the production cutoff :-(
            t_res = DummyRessource(realkind='gridpoint', cutoff='production',
                                   bname='(gribfix:igakey)_toto')
            pr = fp.proxy.provider(suite='oper', vconf=nc, ** self.fp_defaults)
            self.assertEqual(pr.basename(t_res),
                             'PECM000GLOB25_toto')


if __name__ == "__main__":
    unittest.main(verbosity=2)
