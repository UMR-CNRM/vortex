# -*- coding: utf-8 -*-
from __future__ import print_function, absolute_import, unicode_literals, division
import six

import tempfile
import unittest

from bronx.fancies.loggers import unittestGlobalLevel

import vortex
from vortex.layout.jobs import _mkjob_opts_detect_1, _mkjob_opts_detect_2, _mkjob_opts_autoexport
from vortex.util.config import ExtendedReadOnlyConfigParser

tloglevel = 'CRITICAL'


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
                                                             mkopts=six.text_type(opts),
                                                             ** opts)

            iniparser = ExtendedReadOnlyConfigParser(inifile='@job-default.ini')
            tplconf = iniparser.as_dict()

            jobconf = dict(montest={'cutoff': 'production', 'xpid': 'FAKE', 'suitebg': 'oper',
                                    'extrapythonpath': 'blop1,blop2', 'task': 'gruik',
                                    'hasmember': True, 'auto_options_filter': 'hasmember'})

            tr_opts, auto_opts = _mkjob_opts_detect_2(self.t, tplconf, jobconf,
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
                {'appbase': fullp,
                 'auto_options_filter': 'hasmember',
                 'cutoff': 'production',
                 'defaultencoding': 'en_US.UTF-8',
                 'extrapythonpath': "'blop1','blop2',",
                 'file': 'montest.py',
                 'flow_tplsuffix': '',
                 'hasmember': True,
                 'inovativedate': '2019010100',
                 'jobconf': self.sh.path.join(fullp, 'conf', 'arpege_4dvarfr.ini'),
                 'ldlibs': '',
                 'loadedaddons': "'nwp',",
                 'loadedmods': "'common','gco','olive','common.tools.addons','common.util.usepygram',",
                 'loadedjaplugins': '',
                 'manydates': '2019010100-2019010200-PT6H',
                 'member': 1,
                 'mtool_args': '',
                 'mtool_dir': '',
                 'mtool_log': '',
                 'mtool_path': '',
                 'mtool_t_tpl': '',
                 'mtool_tpl': '',
                 'name': 'montest',
                 'newstuff': 'toto',
                 'nnodes': '1',
                 'ntasks': '1',
                 'openmp': '1',
                 'package': 'tasks',
                 'pwd': fullp,
                 'pyopts': '-u',
                 'python': self.sh.which('python'),
                 'refill': False,
                 'rootapp': '$home/vortex',
                 'rundate': "'2018010100'",
                 'rundates': '',
                 'runtime': "'00:00'",
                 'scriptencoding': 'utf-8',
                 'submitcmd': '',
                 'suitebg': "'oper'",
                 'target_appbase': fullp,
                 'task': 'gruik',
                 'taskconf': '',
                 'template': '@job-default.tpl',
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


if __name__ == "__main__":
    unittest.main(verbosity=2)
