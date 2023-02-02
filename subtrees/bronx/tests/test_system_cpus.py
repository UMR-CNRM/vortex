import os
import unittest

from bronx.fancies import loggers
from bronx.system.cpus import CpusToolUnavailableError, LinuxCpusInfo

DATADIR = os.path.realpath(os.path.join(os.path.dirname(__file__), 'data'))


class LinuxCpusInfoTester(LinuxCpusInfo):

    _INFOFILE_CHECK = False

    def __new__(cls, finput):
        return super().__new__(cls)

    def __init__(self, finput):
        super().__init__()
        self._INFOFILE = os.path.join(DATADIR, finput)


class TestLinuxCpusInfo(unittest.TestCase):

    def test_bascis_mine(self):
        try:
            cinfo = LinuxCpusInfo()
        except CpusToolUnavailableError as e:
            raise self.skipTest(str(e))
        # Just ensure that the file is parseable...
        self.assertEqual(cinfo.nvirtual_cores,
                         cinfo.nphysical_cores_per_socket *
                         cinfo.nsockets *
                         cinfo.smt_threads)

    def test_basics_ht1(self):
        cinfo = LinuxCpusInfoTester("cpuinfo1_ht")
        self.assertEqual(cinfo.nsockets, 2)
        self.assertEqual(cinfo.nphysical_cores, 8)
        self.assertEqual(cinfo.nphysical_cores_per_socket, 4)
        self.assertEqual(cinfo.nvirtual_cores, 16)
        self.assertEqual(cinfo.smt_threads, 2)
        self.assertEqual(cinfo.physical_cores_smtthreads,
                         {k: [k + cinfo.nphysical_cores, ]
                          for k in range(cinfo.nphysical_cores)})
        self.assertListEqual(list(cinfo.raw_cpulist()),
                             list([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]))
        self.assertListEqual(list(cinfo.socketpacked_cpulist()),
                             list([0, 4, 1, 5, 2, 6, 3, 7, 8, 12, 9, 13, 10, 14, 11, 15]))
        self.assertListEqual(list(cinfo.socketpacked_cpulist(bsize=2)),
                             list([0, 1, 4, 5, 2, 3, 6, 7, 8, 9, 12, 13, 10, 11, 14, 15]))
        with loggers.contextboundGlobalLevel('error'):
            self.assertListEqual(list(cinfo.socketpacked_cpulist(bsize=3)),
                                 list([0, 1, 2, 4, 5, 6, 8, 9, 10, 12, 13, 14]))
        self.assertListEqual(list(cinfo.socketpacked_cpulist(bsize=4)),
                             list([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]))
        self.assertListEqual(list(cinfo.socketpacked_cpulist(bsize=5)),
                             list([0, 1, 2, 3, 8, 4, 5, 6, 7, 12]))
        self.assertListEqual(list(cinfo.socketpacked_cpulist(bsize=8)),
                             list([0, 1, 2, 3, 8, 9, 10, 11, 4, 5, 6, 7, 12, 13, 14, 15]))
        self.assertListEqual(list(cinfo.socketpacked_cpulist(bsize=12)),
                             list([0, 4, 1, 5, 2, 6, 3, 7, 8, 12, 9, 13, 10, 14, 11, 15]))

        cinfo = LinuxCpusInfoTester("cpuinfo1_ht_bis")
        self.assertEqual(cinfo.nsockets, 2)
        self.assertEqual(cinfo.nphysical_cores, 8)
        self.assertEqual(cinfo.nphysical_cores_per_socket, 4)
        self.assertEqual(cinfo.nvirtual_cores, 16)
        self.assertEqual(cinfo.smt_threads, 2)
        self.assertListEqual(list(cinfo.raw_cpulist()),
                             list([0, 2, 4, 6, 8, 10, 12, 14, 1, 3, 5, 7, 9, 11, 13, 15]))
        self.assertListEqual(list(cinfo.socketpacked_cpulist()),
                             list([0, 8, 2, 10, 4, 12, 6, 14, 1, 9, 3, 11, 5, 13, 7, 15]))
        self.assertListEqual(list(cinfo.socketpacked_cpulist(bsize=2)),
                             list([0, 2, 8, 10, 4, 6, 12, 14, 1, 3, 9, 11, 5, 7, 13, 15]))

    def test_basics_noht1(self):
        cinfo = LinuxCpusInfoTester("cpuinfo1_noht")
        self.assertEqual(cinfo.nsockets, 2)
        self.assertEqual(cinfo.nphysical_cores, 8)
        self.assertEqual(cinfo.nphysical_cores_per_socket, 4)
        self.assertEqual(cinfo.nvirtual_cores, 8)
        self.assertEqual(cinfo.smt_threads, 1)
        self.assertEqual(cinfo.physical_cores_smtthreads,
                         {k: [] for k in range(cinfo.nphysical_cores)})
        self.assertListEqual(list(cinfo.raw_cpulist()),
                             list([0, 1, 2, 3, 4, 5, 6, 7]))
        self.assertListEqual(list(cinfo.socketpacked_cpulist()),
                             list([0, 4, 1, 5, 2, 6, 3, 7]))
        self.assertListEqual(list(cinfo.socketpacked_cpulist(bsize=2)),
                             list([0, 1, 4, 5, 2, 3, 6, 7]))


if __name__ == '__main__':
    unittest.main()
