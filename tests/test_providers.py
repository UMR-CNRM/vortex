
import unittest


import footprints as fp
import vortex.data.providers  # @UnusedImport
import olive.data.providers  # @UnusedImport
from vortex.tools.date import Date, Time
from vortex.data import geometries


class DummyRessource(object):

    def __init__(self, realkind='dummy', bname='dummyres', cutoff='assim',
                 term=0):
        self.model = 'arpege'
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
            geometry=self.geometry,
            )

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
        self.assertEqual(pr.scheme(), 'file')
        self.assertEqual(pr.netloc(), 'localhost')
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
            self.assertEqual(pr.scheme(), proto)
            # hostname ?
            pr = fp.proxy.provider(tube=proto, remote='/home/machin/dummy',
                                   hostname='superserver',
                                   ** self.fp_defaults)
            self.assertEqual(pr.netloc(), 'superserver')
            pr = fp.proxy.provider(tube=proto, remote='/home/machin/dummy',
                                   hostname='superserver', username='toto',
                                   ** self.fp_defaults)
            self.assertEqual(pr.netloc(), 'toto@superserver')
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
            self.assertEqual(pr.scheme(), 'vortex')
            self.assertEqual(pr.netloc(), ns)
            self.assertIs(pr.member, None)
            self.assertEqual(pr.nice_member(), '')
            # Member
            fpd['member'] = 3
            pr = fp.proxy.provider(** fpd)
            self.assertIs(pr.member, 3)
            self.assertEqual(pr.nice_member(), 'm0003')
            # Expected
            fpd['expected'] = True
            pr = fp.proxy.provider(** fpd)
            self.assertEqual(pr.scheme(), 'xvortex')

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
                         'arpege/4dvar/VOID/20000101T0000A/m0003/dummy')
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
            self.assertEqual(pr.netloc(), 'vsop.cache.fr')


class TestProviderOlive(unittest.TestCase):

    def setUp(self):
        self.fp_defaults = dict(vapp='arpege',
                                vconf='4dvar',
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
            self.assertEqual(pr.scheme(), 'olive')
            self.assertEqual(pr.netloc(), ns)
            self.assertIs(pr.member, None)

    def test_olive_paths(self):
        pr = fp.proxy.provider(** self.fp_defaults)
        self.assertEqual(pr.pathname(self.t_res),
                         'VOID/20000101H00A/dummy')
        self.assertEqual(pr.uri(self.t_res),
                         'olive://' + self.fp_defaults['namespace'] +
                         '/VOID/20000101H00A/dummy/dummyres')
        # username ?
        pr = fp.proxy.provider(username='toto', ** self.fp_defaults)
        self.assertEqual(pr.uri(self.t_res),
                         'olive://' + self.fp_defaults['namespace'] +
                         '/VOID/20000101H00A/dummy/dummyres')


class TestProviderOpArchive(unittest.TestCase):

    def setUp(self):
        self.fp_defaults = dict(vapp='arpege',
                                vconf='4dvar',
                                experiment='oper',
                                namespace='oper.archive.fr')
        self.t_suites = ('oper', 'dbl', 'test', 'miroir')
        self.t_res = DummyRessource()

    def test_oparchive_basics(self):
        for ns in self.t_suites:
            pr = fp.proxy.provider(suite=ns, ** self.fp_defaults)
            self.assertEqual(pr.scheme(), 'op')
            self.assertEqual(pr.netloc(), 'oper.archive.fr')
            self.assertIs(pr.member, None)

    def test_oparchive_strangenames(self):
        # Strange naming convention for historic files
        t_res = DummyRessource(realkind='historic',
                               bname='(histfix:igakey)_toto')
        # PEARP special case
        fpd = dict()
        fpd.update(self.fp_defaults)
        fpd['vconf'] = 'pearp'
        pr = fp.proxy.provider(suite='oper', ** fpd)
        self.assertEqual(pr.basename(t_res),
                         'prev_toto')
        # Others
        pr = fp.proxy.provider(suite='oper', ** self.fp_defaults)
        self.assertEqual(pr.basename(t_res),
                         'arpe_toto')

        # Strange naming convention for grib files
        t_res = DummyRessource(realkind='gridpoint',
                               bname='(gribfix:igakey)_toto')
        # PEARP special case
        fpd = dict()
        fpd.update(self.fp_defaults)
        fpd['vconf'] = 'pearp'
        pr = fp.proxy.provider(suite='oper', member=1, ** fpd)
        self.assertEqual(pr.basename(t_res),
                         'fc_00_1_GLOB25_0000_toto')
        # Others
        pr = fp.proxy.provider(suite='oper', ** self.fp_defaults)
        self.assertEqual(pr.basename(t_res),
                         'PE00000GLOB25_toto')

        # Strange naming convention for errgribvor
        fpd = dict()
        fpd.update(self.fp_defaults)
        fpd['vconf'] = 'aearp'
        resini = dict(realkind='bgstderr', bname='(errgribfix:igakey)')
        pr1 = fp.proxy.provider(suite='oper', ** self.fp_defaults)
        pr2 = fp.proxy.provider(suite='oper', inout='out', ** fpd)
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
                             'op://' + self.fp_defaults['namespace'] +
                             '/arpege/{}/assim/2000/01/01/r0/dummyres'.format(ns))
            # username ?
            pr = fp.proxy.provider(suite=ns, username='toto',
                                   ** self.fp_defaults)
            self.assertEqual(pr.uri(self.t_res),
                             'op://' + self.fp_defaults['namespace'] +
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
                                vconf='frcourt',
                                experiment='oper',
                                namespace='oper.archive.fr')
        self.t_suites = ('oper', 'dbl', 'test', 'miroir')
        self.t_res = DummyRessource()

    def test_oparchivecourt_basics(self):
        for ns in self.t_suites:
            pr = fp.proxy.provider(suite=ns, ** self.fp_defaults)
            self.assertEqual(pr.scheme(), 'op')
            self.assertEqual(pr.netloc(), 'oper.archive.fr')
            self.assertEqual(pr.pathname(self.t_res),
                             'arpege/{}/court/2000/01/01/r0'.format(ns))

if __name__ == "__main__":
    unittest.main(verbosity=2)
