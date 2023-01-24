import contextlib
import os
import tempfile
import unittest

from bronx.stdtypes import date as b_date
from bronx.fancies.loggers import unittestGlobalLevel

from footprints import proxy as fpx

import vortex
from vortex.data import geometries
from vortex.layout.jobs import _mkjob_opts_detect_1, _mkjob_opts_detect_2, _mkjob_opts_autoexport
from vortex.tools.actions import actiond
import cen.tools.actions
from vortex.util.config import ExtendedReadOnlyConfigParser

assert cen.tools.actions

tloglevel = 'CRITICAL'

DATAPATHTEST = os.path.join(os.path.dirname(__file__), 'data')


@unittestGlobalLevel(tloglevel)
class TestMkjobDetect(unittest.TestCase):

    def setUp(self):
        self.t = vortex.sessions.current()
        self.sh = self.t.sh
        self.oldpwd = self.sh.pwd()
        self.tmpdir = tempfile.mkdtemp(suffix='_test_mkjob_detect')
        self.sh.cd(self.tmpdir)

    def tearDown(self):
        self.sh.cd(self.oldpwd)
        self.sh.remove(self.tmpdir)

    def test_detect1(self):
        self.sh.mkdir('BLOP@leffe/arpege/4dvarfr')
        self.sh.cd('BLOP@leffe/arpege/4dvarfr')
        fullp = self.sh.pwd()
        trdefaults = dict(appbase=fullp,
                          target_appbase=fullp,
                          xpid='BLOP@leffe',
                          vapp='arpege',
                          vconf='4dvarfr',
                          jobconf=self.sh.path.join(fullp, 'conf', 'arpege_4dvarfr.ini'),
                          taskconf='')
        for sub in ('.', 'tasks', 'jobs', 'logs'):
            with self.sh.cdcontext(sub, create=True):
                tr_opts, auto_opts, opts = _mkjob_opts_detect_1(self.t)
                self.assertDictEqual(tr_opts, trdefaults)
                self.assertDictEqual(auto_opts, dict())
                self.assertDictEqual(opts, dict())
        tr_opts, auto_opts, opts = _mkjob_opts_detect_1(self.t,
                                                        taskconf='toto',
                                                        target_appbase='truc',
                                                        xpid='ABCD')
        trloc = dict(trdefaults)
        trloc['taskconf'] = '_toto'
        trloc['jobconf'] = self.sh.path.join(fullp, 'conf', 'arpege_4dvarfr_toto.ini')
        trloc['xpid'] = 'ABCD'
        trloc['target_appbase'] = 'truc'
        self.assertDictEqual(tr_opts, trloc)
        self.assertDictEqual(opts, dict(xpid='ABCD', target_appbase='truc'))

    def test_detect2(self):
        for opts in ({'xpid': 'ABCD', 'name': 'montest_20180101T0000P_mb001',
                      'inovativedate': '2019010100', 'newstuff': 'toto',
                      'manydates': '2019010100-2019010200-PT6H'},
                     {'xpid': 'ABCD', 'name': 'montest',
                      'rundate': '2018010100', 'member': 1, 'runtime': 0,
                      'inovativedate': '2019010100', 'newstuff': 'toto',
                      'manydates': '2019010100-2019010200-PT6H'}):

            self.sh.mkdir('BLOP@leffe/arpege/4dvarfr')
            self.sh.cd('BLOP@leffe/arpege/4dvarfr')
            fullp = self.sh.pwd()
            tr_opts, auto_opts, opts1 = _mkjob_opts_detect_1(self.t,
                                                             mkopts=str(opts),
                                                             ** opts)

            iniparser = ExtendedReadOnlyConfigParser(inifile='@job-default.ini')
            tplconf = iniparser.as_dict()

            jobconf = dict(montest={'cutoff': 'production', 'xpid': 'FAKE', 'suitebg': 'oper',
                                    'extrapythonpath': 'blop1,blop2', 'task': 'gruik',
                                    'hasmember': True, 'auto_options_filter': 'hasmember'})
            jobconf_defaults = dict()

            tr_opts, auto_opts = _mkjob_opts_detect_2(self.t, tplconf, jobconf, jobconf_defaults,
                                                      tr_opts, auto_opts, ** opts1)
            del tr_opts['create']
            del tr_opts['home']
            del tr_opts['mkhost']
            del tr_opts['mkopts']
            del tr_opts['mkuser']

            # import pprint
            # pprint.pprint(tr_opts)
            # pprint.pprint(auto_opts)

            self.assertDictEqual(
                tr_opts,
                {'account': 'mxpt',
                 'alarm': 'True',
                 'appbase': fullp,
                 'auto_options_filter': 'hasmember',
                 'cutoff': 'production',
                 'defaultencoding': 'en_US.UTF-8',
                 'dmt': 'False',
                 'exclusive': 'exclusive',
                 'extrapythonpath': "'blop1','blop2',",
                 'file': 'montest.py',
                 'fullplay': 'True',
                 'hasmember': True,
                 'inovativedate': '2019010100',
                 'jeeves': 'True',
                 'jobconf': self.sh.path.join(fullp, 'conf', 'arpege_4dvarfr.ini'),
                 'ldlibs': '',
                 'loadedaddons': "'nwp',",
                 'loadedjaplugins': '',
                 'loadedmods': "'common','gco','olive','common.tools.addons','common.util.usepygram',",
                 'mail': 'False',
                 'manydates': '2019010100-2019010200-PT6H',
                 'mem': '247000',
                 'member': 1,
                 'mtool_args': '--language=python --shell=python --cleanmode=olive',
                 'mtool_dir': '--mtooldir=/scratch/mtool/{user:s}',
                 'mtool_log': '--logfile={appbase:s}/logs/{rundate:s}/{file:s}.{tstamp:s}',
                 'mtool_path': '/home/mf/dp/marp/verolive/public/mtool/bin/mtool_filter.pl',
                 'mtool_t_tpl': '@jobs_rd/job-bullx3-mtool-transfer',
                 'mtool_tpl': '@jobs_rd/job-bullx3-mtool-default',
                 'name': 'montest',
                 'newstuff': 'toto',
                 'nnodes': '1',
                 'ntasks': '1',
                 'openmp': '1',
                 'package': 'tasks',
                 'partition': 'oper',
                 'phase': 'False',
                 'pwd': fullp,
                 'pyopts': '-u',
                 'python': '/opt/softs/anaconda3/envs/Py37nomkl/bin/python',
                 'python_mkjob': self.sh.which('python'),
                 'refill': False,
                 'refill_partition': 'ft-oper',
                 'report': 'True',
                 'retry': '0',
                 'rootapp': '$pwd',
                 'rootdir': 'None',
                 'route': 'False',
                 'rundate': "'2018010100'",
                 'rundates': '',
                 'runstep': '1',
                 'runtime': "'00:00'",
                 'scriptencoding': 'utf-8',
                 'submitcmd': 'sbatch',
                 'suitebg': "'oper'",
                 'target_appbase': fullp,
                 'task': 'gruik',
                 'taskconf': '',
                 'template': '@jobs_op/opjob-test-default.tpl',
                 'time': '00:20:00',
                 'vapp': 'arpege',
                 'vconf': '4dvarfr',
                 'verbose': 'verbose',
                 'warmstart': False,
                 'xpid': 'ABCD'})

            self.assertEqual(
                auto_opts,
                {'inovativedate': '2019010100',
                 'manydates': '2019010100-2019010200-PT6H',
                 'member': 1,
                 'newstuff': 'toto',
                 'suitebg': 'oper'})

            self.assertEqual(_mkjob_opts_autoexport(auto_opts),
                             """    inovativedate=bronx.stdtypes.date.Date('2019010100'),
    manydates=bronx.stdtypes.date.daterangex('2019010100-2019010200-PT6H'),
    member=1,
    newstuff='toto',
    suitebg='oper'""")


@unittestGlobalLevel(tloglevel)
class TestJobAssistant(unittest.TestCase):

    @staticmethod
    def _givetag():
        """Return the first available sessions name."""
        i = 1
        while 'job_assistant_test{:d}'.format(i) in vortex.sessions.keys():
            i += 1
        return 'job_assistant_test{:d}'.format(i)

    def setUp(self):
        self.rootsession = vortex.sessions.current()
        self.rootsh = self.rootsession.system()
        self.oldpwd = self.rootsh.pwd()
        self.tmpdir = self.rootsh.path.realpath(tempfile.mkdtemp(prefix='jobassistant_test_'))
        # Create a dedicated test
        self.cursession = vortex.sessions.get(tag=self._givetag(),
                                              topenv=vortex.rootenv,
                                              glove=fpx.glove())
        self.cursession.activate()
        # Tb settings
        self._tb_verbose = vortex.toolbox.active_verbose
        self._tb_active = vortex.toolbox.active_now
        self._tb_clear = vortex.toolbox.active_clear
        vortex.toolbox.active_verbose = False
        vortex.toolbox.active_now = False
        vortex.toolbox.active_clear = False

    def tearDown(self):
        # Reset tb setting
        vortex.toolbox.active_verbose = self._tb_verbose
        vortex.toolbox.active_now = self._tb_active
        vortex.toolbox.active_clear = self._tb_clear
        # Reset the session
        self.cursession.exit()
        self.rootsession.activate()
        self.rootsh.cd(self.oldpwd)
        self.rootsh.remove(self.tmpdir)

    @contextlib.contextmanager
    def _safe_ja_setup(self, ja, *kargs, **kwargs):
        t, e, sh = ja.setup(*kargs, **kwargs)
        try:
            yield t, e, sh
        finally:
            ja.finalise()
            ja.close()

    def test_bare_ja1(self):
        ja = fpx.jobassistant(kind='generic',
                              modules=('vortex.tools.folder', ),
                              addons=('allfolders', ),
                              special_prefix="fake_")

        actual_data = dict(vapp='arpege',
                           vconf='future',
                           cutoff='assim',
                           rundate=b_date.Date('2021010100'),
                           xpid='test1@unit-tester',
                           jobname='testjob1',
                           iniconf=os.path.join(DATAPATHTEST, 'ja_test_conf.ini'))
        actual = {'fake_' + k: v for k, v in actual_data.items()}
        actual['fake_XPID'] = actual.pop('fake_xpid')
        actual['trap_number1'] = 1
        auto_options = dict(member=1)
        with self._safe_ja_setup(ja, actual=actual, auto_options=auto_options) as (t, e, sh):
            self.assertIs(t, self.cursession)
            # Special variables detection
            specials = actual_data.copy()
            specials.update(auto_options)
            self.assertDictEqual(ja.special_variables, specials)
            # Configuration file reading
            conf = specials.copy()
            conf['geometry'] = geometries.get(tag='global798')
            conf['model'] = 'arpege'
            conf['cycle'] = 'uenv:pp_pearp.01@demo'
            conf['ftuser'] = 'toto'
            self.assertDictEqual(dict(ja.conf), conf)
            # Early glove setting
            self.assertEqual(t.glove.vapp, 'arpege')
            self.assertEqual(t.glove.vconf, 'future')
            # Environment update according to special variables
            for k, v in specials.items():
                self.assertEqual(e['FAKE_' + k], v)
            # Loaded addons
            from vortex.tools.folder import available_foldershells
            self.assertSetEqual(set(sh.loaded_addons()),
                                set(available_foldershells))
            # ftuser
            self.assertEqual(t.glove.getftuser('any.host.com'), 'toto')
            # Toolbox defaults
            self.assertTrue(vortex.toolbox.active_verbose)
            self.assertTrue(vortex.toolbox.active_now)
            self.assertTrue(vortex.toolbox.active_clear)
            # Mail is not activated bye default
            self.assertListEqual(actiond.cenmail_status(), [False, ])
            # Just to see if it works...
            ja.complete()

    def test_bare_ja2(self):
        ja = fpx.jobassistant(kind='generic',
                              special_prefix="fake_")

        actual_data = dict(jobname='testjob2',
                           iniconf=os.path.join(DATAPATHTEST, 'ja_test_conf.ini'))
        actual = {'fake_' + k: v for k, v in actual_data.items()}
        with self._safe_ja_setup(ja, actual=actual) as (t, e, sh):
            # ftuser
            self.assertEqual(t.glove.getftuser('any.host.com'), 'toto')
            self.assertEqual(t.glove.getftuser('other.host.com'), 'titi')

    def test_japlugin_mail(self):
        ja = fpx.jobassistant(kind='generic',
                              special_prefix="fake_")
        ja.add_plugin('rd_mail_setup')

        actual_data = dict(jobname='testjob3',
                           iniconf=os.path.join(DATAPATHTEST, 'ja_test_conf.ini'))
        actual = {'fake_' + k: v for k, v in actual_data.items()}
        try:
            with self._safe_ja_setup(ja, actual=actual):
                self.assertListEqual(actiond.cenmail_status(), [True, ])
        finally:
            actiond.cenmail_off()


if __name__ == "__main__":
    unittest.main(verbosity=2)
