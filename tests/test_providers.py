from __future__ import print_function, absolute_import, unicode_literals, division

from copy import deepcopy
import unittest

from bronx.stdtypes.date import Date, Time
import footprints as fp

import vortex.data.providers  # @UnusedImport
import olive.data.providers  # @UnusedImport
from vortex.data import geometries


class DummyRessource(object):

    def __init__(self, realkind='dummy', bname='dummyres', cutoff='assim',
                 term=0, model='arpege'):
        self.model = model
        self.date = Date(2000, 1, 1, 0, 0, 0)
        self.term = Time(term)
        self.geometry = geometries.get(tag='glob25')
        self.cutoff = cutoff
        self._bname = bname
        self.realkind = realkind
        self.mailbox = {}

    def basename(self, kind):
        actualbasename = getattr(self, kind + '_basename',
                                 self.vortex_basename)
        return actualbasename()

    def pathinfo(self, kind):
        actualpathinfo = getattr(self, kind + '_pathinfo',
                                 self.vortex_pathinfo)
        return actualpathinfo()

    def urlquery(self, kind):
        actualurlquery = getattr(self, kind + '_urlquery',
                                 self.vortex_urlquery)
        return actualurlquery()

    def vortex_pathinfo(self):
        return dict(
            nativefmt='fa',
            model=self.model,
            date=self.date,
            cutoff=self.cutoff,
            geometry=self.geometry,)

    def basename_info(self):
        return dict(radical=self._bname)

    def vortex_basename(self):
        pass

    def olive_basename(self):
        return self._bname

    def archive_basename(self):
        return self._bname

    def vortex_urlquery(self):
        return None


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
            self.assertEqual(pr.netloc(None), 'toto@superserver')
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
            self.assertEqual(pr.nice_member(), '')
            # Member
            fpd['member'] = 3
            pr = fp.proxy.provider(** fpd)
            self.assertEqual(pr.member, 3)
            self.assertEqual(pr.nice_member(), 'mb003')
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
                         'vortex://' + self.fp_defaults['namespace'] +
                         '/arpege/4dvar/VOID/20000101T0000A/dummy/dummyres')


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
                         'olive://' + self.fp_defaults['namespace'] +
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
                             'op://{}.archive.fr'.format(self.s_remap.get(ns, ns)) +
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
            # Uggly things for the production cutoff :-(
            t_res = DummyRessource(realkind='gridpoint', cutoff='production',
                                   bname='(gribfix:igakey)_toto')
            pr = fp.proxy.provider(suite='oper', vconf=nc, ** self.fp_defaults)
            self.assertEqual(pr.basename(t_res),
                             'PECM000GLOB25_toto')


if __name__ == "__main__":
    unittest.main(verbosity=2)
