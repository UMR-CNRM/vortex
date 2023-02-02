import unittest

from bronx.system.numa import LibNumaNodesInfo, numa_nodes_info

try:
    import scipy.cluster.hierarchy  # @UnusedImport
    assert scipy.cluster.hierarchy
except ImportError:
    scipy_ok = False
else:
    scipy_ok = True


_BULLX3_NPS4 = dict(nodes=[[list(range(n * 16, (n + 1) * 16)), 34359738368 - n, 17179869184 - n]
                           for n in range(8)],
                    matrix={0: {0: 10, 1: 12, 2: 12, 3: 12, 4: 32, 5: 32, 6: 32, 7: 32},
                            1: {1: 10, 2: 12, 3: 12, 4: 32, 5: 32, 6: 32, 7: 32},
                            2: {2: 10, 3: 12, 4: 32, 5: 32, 6: 32, 7: 32},
                            3: {3: 10, 4: 32, 5: 32, 6: 32, 7: 32},
                            4: {4: 10, 5: 12, 6: 12, 7: 12},
                            5: {5: 10, 6: 12, 7: 12},
                            6: {6: 10, 7: 12},
                            7: {7: 10}, })

_BULLX3_NPS4_STR = """There are 8 nodes.
Node 0 description:
- cpus: 0 1 2 3 4 5 6 7 8 9 10 11 12 13 14 15
- totalsize: 34359738368 bytes
Node 1 description:
- cpus: 16 17 18 19 20 21 22 23 24 25 26 27 28 29 30 31
- totalsize: 34359738367 bytes
Node 2 description:
- cpus: 32 33 34 35 36 37 38 39 40 41 42 43 44 45 46 47
- totalsize: 34359738366 bytes
Node 3 description:
- cpus: 48 49 50 51 52 53 54 55 56 57 58 59 60 61 62 63
- totalsize: 34359738365 bytes
Node 4 description:
- cpus: 64 65 66 67 68 69 70 71 72 73 74 75 76 77 78 79
- totalsize: 34359738364 bytes
Node 5 description:
- cpus: 80 81 82 83 84 85 86 87 88 89 90 91 92 93 94 95
- totalsize: 34359738363 bytes
Node 6 description:
- cpus: 96 97 98 99 100 101 102 103 104 105 106 107 108 109 110 111
- totalsize: 34359738362 bytes
Node 7 description:
- cpus: 112 113 114 115 116 117 118 119 120 121 122 123 124 125 126 127
- totalsize: 34359738361 bytes
Distances matrix:
          0    1    2    3    4    5    6    7
   0:    10   12   12   12   32   32   32   32
   1:    12   10   12   12   32   32   32   32
   2:    12   12   10   12   32   32   32   32
   3:    12   12   12   10   32   32   32   32
   4:    32   32   32   32   10   12   12   12
   5:    32   32   32   32   12   10   12   12
   6:    32   32   32   32   12   12   10   12
   7:    32   32   32   32   12   12   12   10"""


_BULLX3_NPS4_SMT = dict(nodes=[[list(range(n * 16, (n + 1) * 16)) +
                                list(range(128 + n * 16, 128 + (n + 1) * 16)),
                                34359738368 - n, 17179869184 - n]
                               for n in range(8)],
                        matrix={0: {0: 10, 1: 12, 2: 12, 3: 12, 4: 32, 5: 32, 6: 32, 7: 32},
                                1: {1: 10, 2: 12, 3: 12, 4: 32, 5: 32, 6: 32, 7: 32},
                                2: {2: 10, 3: 12, 4: 32, 5: 32, 6: 32, 7: 32},
                                3: {3: 10, 4: 32, 5: 32, 6: 32, 7: 32},
                                4: {4: 10, 5: 12, 6: 12, 7: 12},
                                5: {5: 10, 6: 12, 7: 12},
                                6: {6: 10, 7: 12},
                                7: {7: 10}, })


_MONSTER = dict(nodes=([[list(range(n * 4, (n + 1) * 4)), 34359738368, 17179869184]
                        for n in range(2)] +
                       [[list(range(8 + n * 3, 8 + (n + 1) * 3)), 34359738368, 17179869184]
                        for n in range(2)] +
                       [[list(range(14 + n * 2, 14 + (n + 1) * 2)), 34359738368, 17179869184]
                        for n in range(2)]),
                matrix={0: {0: 10, 1: 12, 2: 20, 3: 20, 4: 32, 5: 32},
                        1: {1: 10, 2: 20, 3: 20, 4: 32, 5: 32},
                        2: {2: 10, 3: 14, 4: 25, 5: 25},
                        3: {3: 10, 4: 25, 5: 25},
                        4: {4: 10, 5: 12},
                        5: {5: 10}, })


_SINGLE = dict(nodes=[[list(range(4)), 34359738368, 17179869184], ],
               matrix={0: {0: 10}})


_DUAL = dict(nodes=[[list(range(4)), 34359738368, 17179869184],
                    [list(range(4, 8)), 34359738368, 17179869184], ],
             matrix={0: {0: 10, 1: 12},
                     1: {0: 12, 1: 10}, })


class FakeLibnumaGateway:
    """Behaves like the real libnuma gateway class."""

    def __init__(self, nodes, matrix):
        """
        :param nodes: Something like [(list_of_cpus, totalmem, freemem), ...]
        :param matrix: A nested dictionary that represent the matrix of NUMA distances
                       between NUMA nodes (Note: The matrix is symetric, nly the
                       upper part wil be used)
        """
        self._nodes = nodes
        self._matrix = matrix
        self._ncpus = sum([len(n[0]) for n in nodes])
        self._revnodes = {c: n for n, node in enumerate(nodes) for c in node[0]}

    def numa_num_configured_cpus(self):
        return self._ncpus

    def numa_node_of_cpu(self, c):
        return self._revnodes[c]

    def numa_max_node(self):
        return len(self._nodes) - 1

    def numa_node_size64(self, n):
        return self._nodes[n][1:]

    def numa_distance(self, n1, n2):
        if n1 <= n2:
            return self._matrix[n1][n2]
        else:
            return self._matrix[n2][n1]


class FakeLibnumaNodesInfos(LibNumaNodesInfo):
    """Just use the fake gateway instead of the real one..."""

    _gateway_class = FakeLibnumaGateway


class TestNumaNodesInfos(unittest.TestCase):

    def test_bare_libnuma(self):
        try:
            ninfo = LibNumaNodesInfo()
            self.assertTrue(len(ninfo) > 0)
        except (OSError, NotImplementedError):
            self.skipTest('Apparently the libnuma is missing')

    def test_factory_method(self):
        try:
            ninfo = numa_nodes_info()
        except (OSError, NotImplementedError):
            self.skipTest('Apparently the libnuma is missing')
        self.assertTrue(len(ninfo) > 0)

    @unittest.skipUnless(scipy_ok, 'SciPy is unavailable')
    def test_clustering(self):
        ninfo = FakeLibnumaNodesInfos(** _BULLX3_NPS4)
        self.assertEqual(ninfo._inhouse_nodes_clustering(),
                         ninfo._scipy_nodes_clustering())
        ninfo = FakeLibnumaNodesInfos(** _MONSTER)
        self.assertEqual(ninfo._inhouse_nodes_clustering(),
                         ninfo._scipy_nodes_clustering())

    def test_single(self):
        ninfo = FakeLibnumaNodesInfos(** _SINGLE)
        # First, try to read some informations
        self.assertEqual(len(ninfo), 1)
        self.assertEqual(ninfo.numapacked_cpulist(2),
                         [[0, 1], [2, 3]])
        self.assertEqual(ninfo.numabalanced_cpulist(2),
                         [[0, 1], [2, 3]])

    def test_dual(self):
        ninfo = FakeLibnumaNodesInfos(** _DUAL)
        # First, try to read some informations
        self.assertEqual(len(ninfo), 2)
        self.assertEqual(ninfo.numapacked_cpulist(2),
                         [[0, 1], [4, 5], [2, 3], [6, 7]])
        self.assertEqual(ninfo.numabalanced_cpulist(2),
                         [[0, 4], [1, 5], [2, 6], [3, 7]])
        # Try the dispencer object
        disp = ninfo.numapacked_cpu_dispenser()
        what = [disp(1), disp(3)]
        self.assertEqual(what, [[0], [4, 5, 6]])
        disp = ninfo.numabalanced_cpu_dispenser()
        what = [disp(1), disp(3)]
        self.assertEqual(what, [[0], [1, 4, 5]])

    def test_bullx3_nps4(self):
        ninfo = FakeLibnumaNodesInfos(** _BULLX3_NPS4)
        # First, try to read some informations
        self.assertEqual(len(ninfo), 8)
        self.assertEqual(ninfo[4].totalsize, 34359738368 - 4)
        self.assertEqual(str(ninfo), _BULLX3_NPS4_STR)
        self.assertEqual(ninfo.freesize(4), 17179869184 - 4)
        with self.assertRaises(KeyError):
            ninfo.freesize(99)
        # No crash for any partitioning + number of expected block ok + no CPU
        # ids duplication.
        for bs in range(1, 129):
            bdist = ninfo.numapacked_cpulist(bs)
            expected = 128 // bs
            self.assertEqual(len(bdist), expected)
            self.assertEqual(len(set(sum(bdist, list()))), expected * bs)
        with self.assertRaises(ValueError):
            ninfo.numapacked_cpulist(129)
        with self.assertRaises(ValueError):
            ninfo.numapacked_cpulist(0)
        # Check for obvious distributions...
        for bs in (1, 2, 4, 8, 15, 16):
            # With a hint on sockets...
            rdist = list()
            for i in range(0, 16 - bs + 1, bs):
                for n in range(4):
                    rdist.append([i + n * 16 + b for b in range(bs)])
                    rdist.append([i + (n + 4) * 16 + b for b in range(bs)])
            self.assertEqual(ninfo.numapacked_cpulist(bs),
                             rdist)
        bs = 5
        rdist = list()
        for i in range(0, 16 - bs + 1, bs):
            for n in range(4):
                rdist.append([i + n * 16 + b for b in range(bs)])
                rdist.append([i + (n + 4) * 16 + b for b in range(bs)])
        rdist += [[15, 31, 47, 63, 79], ]
        self.assertEqual(ninfo.numapacked_cpulist(bs), rdist)
        # Test with a void smtlayout
        self.assertEqual(ninfo.numapacked_cpulist(bs, {k: [] for k in range(128)}), rdist)
        bs = 3
        rdist = list()
        for i in range(0, 16 - bs + 1, bs):
            for n in range(4):
                rdist.append([i + n * 16 + b for b in range(bs)])
                rdist.append([i + (n + 4) * 16 + b for b in range(bs)])
        rdist += [[15, 31, 47, ], [79, 95, 111], ]
        self.assertEqual(ninfo.numapacked_cpulist(bs), rdist)
        bs = 6
        rdist = list()
        for i in range(0, 16 - bs + 1, bs):
            for n in range(4):
                rdist.append([i + n * 16 + b for b in range(bs)])
                rdist.append([i + (n + 4) * 16 + b for b in range(bs)])
        rdist += [[12, 13, 28, 29, 44, 60], [76, 77, 92, 93, 108, 124],
                  [14, 30, 45, 46, 61, 62], [78, 94, 109, 110, 125, 126],
                  [15, 31, 47, 63, 79, 95]]
        self.assertEqual(ninfo.numapacked_cpulist(bs), rdist)
        bs = 7
        rdist = list()
        for i in range(0, 16 - bs + 1, bs):
            for n in range(4):
                rdist.append([i + n * 16 + b for b in range(bs)])
                rdist.append([i + (n + 4) * 16 + b for b in range(bs)])
        rdist += [[14, 15, 30, 31, 46, 47, 62], [78, 79, 94, 95, 110, 111, 126]]
        self.assertEqual(ninfo.numapacked_cpulist(bs), rdist)
        bs = 32
        rdist = [sum([[n * 16 + b for b in range(8)] for n in range(4)], list()),
                 sum([[64 + n * 16 + b for b in range(8)] for n in range(4)], list()),
                 sum([[8 + n * 16 + b for b in range(8)] for n in range(4)], list()),
                 sum([[72 + n * 16 + b for b in range(8)] for n in range(4)], list())]
        self.assertEqual(ninfo.numapacked_cpulist(bs), rdist)
        bs = 42
        rdist = [(list(range(0, 11)) +
                  list(range(16, 16 + 11)) +
                  list(range(32, 32 + 10)) +
                  list(range(48, 48 + 10))),
                 (list(range(64, 64 + 11)) +
                  list(range(80, 80 + 11)) +
                  list(range(96, 96 + 10)) +
                  list(range(112, 112 + 10))),
                 [11, 12, 13, 14, 15,
                  27, 28, 29, 30, 31,
                  42, 43, 44, 45, 46, 47,
                  58, 59, 60, 61, 62, 63,
                  75, 76, 77, 78, 79,
                  91, 92, 93, 94, 95,
                  106, 107, 108, 109, 110,
                  122, 123, 124, 125, 126]]
        self.assertEqual(ninfo.numapacked_cpulist(bs), rdist)
        bs = 64
        rdist = [sum([[n * 16 + b for b in range(16)] for n in range(4)], list()),
                 sum([[64 + n * 16 + b for b in range(16)] for n in range(4)], list()), ]
        self.assertEqual(ninfo.numapacked_cpulist(bs), rdist)
        # Dispenser test
        disp = ninfo.numapacked_cpu_dispenser()
        what = [disp(1), disp(9), disp(9), disp(9), disp(9), disp(9), disp(9)]
        self.assertEqual(what, [[0, ],
                                list(range(64, 73)),
                                list(range(16, 25)),
                                list(range(80, 89)),
                                list(range(32, 41)),
                                list(range(96, 105)),
                                list(range(48, 57)), ])

    def test_bullx3_nps4_smt(self):
        ninfo = FakeLibnumaNodesInfos(** _BULLX3_NPS4_SMT)
        with self.assertRaises(ValueError):
            ninfo.numapacked_cpulist(257)
        with self.assertRaises(ValueError):
            ninfo.numapacked_cpulist(1, {k: [k + 128, ] for k in range(129)})
        smtlayout = {k: [k + 128, ] for k in range(128)}
        # Check for obvious distributions...
        for bs in (1, 2, 4, 8, 15, 16):
            rdist = list()
            for i in range(0, 16 - bs + 1, bs):
                for n in range(4):
                    rdist.append([i + n * 16 + b for b in range(bs)])
                    rdist.append([i + (n + 4) * 16 + b for b in range(bs)])
            self.assertEqual(ninfo.numapacked_cpulist(bs, smtlayout=smtlayout),
                             rdist +
                             [[128 + c for c in b] for b in rdist])
        bs = 5
        rdist = list()
        for i in range(0, 16 - bs + 1, bs):
            for n in range(4):
                rdist.append([i + n * 16 + b for b in range(bs)])
                rdist.append([i + (n + 4) * 16 + b for b in range(bs)])
        rdist += [[15, 31, 47, 63, 79], ]
        self.assertEqual(ninfo.numapacked_cpulist(bs, smtlayout),
                         rdist + [[128 + c for c in b] for b in rdist])
        bs = 3
        rdist = list()
        for i in range(0, 16 - bs + 1, bs):
            for n in range(4):
                rdist.append([i + n * 16 + b for b in range(bs)])
                rdist.append([i + (n + 4) * 16 + b for b in range(bs)])
        rdist += [[15, 31, 47, ], [79, 95, 111], ]
        self.assertEqual(ninfo.numapacked_cpulist(bs, smtlayout),
                         rdist + [[128 + c for c in b] for b in rdist])
        bs = 32
        rdist = [sum([[n * 16 + b for b in range(8)] for n in range(4)], list()),
                 sum([[64 + n * 16 + b for b in range(8)] for n in range(4)], list()),
                 sum([[8 + n * 16 + b for b in range(8)] for n in range(4)], list()),
                 sum([[72 + n * 16 + b for b in range(8)] for n in range(4)], list())]
        self.assertEqual(ninfo.numapacked_cpulist(bs, smtlayout),
                         rdist + [[128 + c for c in b] for b in rdist])

    def test_monster(self):
        ninfo = FakeLibnumaNodesInfos(** _MONSTER)
        # First, try to read some informations
        self.assertEqual(len(ninfo), 6)
        # No crash for any partitioning + number of expected block ok + no CPU
        # ids duplication.
        for bs in range(1, 19):
            bdist = ninfo.numapacked_cpulist(bs)
            expected = 18 // bs
            self.assertEqual(len(bdist), expected)
            self.assertEqual(len(set(sum(bdist, list()))), expected * bs)
        rdist = [[0, 8], [11, 14], [4, 16], [1, 9], [12, 15], [5, 17], [2, 10],
                 [13, 6], [3, 7]]
        self.assertEqual(ninfo.numabalanced_cpulist(2), rdist)
        rdist = [[0, 1], [8, 9], [11, 12], [14, 15], [4, 5], [16, 17],
                 [2, 3], [6, 7],
                 [10, 13]]
        self.assertEqual(ninfo.numapacked_cpulist(2), rdist)
        rdist = [[0, 1, 2], [8, 9, 10], [11, 12, 13], [4, 5, 6],
                 [14, 15, 16], [3, 7, 17]]
        self.assertEqual(ninfo.numapacked_cpulist(3), rdist)
        rdist = [[0, 1, 2, 3], [4, 5, 6, 7],
                 [14, 15, 16, 17],
                 [8, 9, 11, 12]]
        self.assertEqual(ninfo.numapacked_cpulist(4), rdist)
        rdist = [[0, 1, 2, 4, 5, 8, 9, 11, 12],
                 [3, 6, 7, 10, 13, 14, 15, 16, 17], ]
        self.assertEqual(ninfo.numapacked_cpulist(9), rdist)


if __name__ == '__main__':
    unittest.main()
