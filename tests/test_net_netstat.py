import os
import platform
import tempfile
import unittest

from bronx.fancies import loggers
from vortex.tools.net import LinuxNetstats, TcpConnectionStatus, UdpConnectionStatus

_LPORTS = "32768    60999\n"
_PORTS_V4 = {
    'tcp': """  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode
   0: 00000000:006F 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 15568 1 ffff983d59856040 100 0 0 10 0
   1: 00000000:0016 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 655012 1 ffff983cac620000 100 0 0 10 0
   2: 0100007F:0019 00000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 19932 1 ffff983d4b917080 100 0 0 10 20
   3: 0100007F:8628 0100007F:A62F 01 00000000:00000000 00:00000000 00000000  1000        0 440057 1 ffff983cca2df800 21 4 31 10 -1
   4: 0100007F:B8D8 0100007F:815D 01 00000000:00000000 00:00000000 00000000  1000        0 325690 1 ffff983ca40a47c0 20 4 31 10 -1
   5: 0100007F:B8BC 0100007F:B525 01 00000000:00000000 00:00000000 00000000  1000        0 440767 1 ffff983cac620780 20 0 0 10 -1
   6: 0100007F:8296 0100007F:999B 01 00000000:00000000 00:00000000 00000000  1000        0 326516 1 ffff983d598567c0 20 4 31 10 -1
""",
    'udp': """  sl  local_address rem_address   st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode ref pointer drops
   81: 00000000:8157 00000000:0000 07 00000000:00000000 00:00000000 00000000   106        0 16091 2 ffff983d57f0f840 0
  404: 00000000:029A 00000000:0000 07 00000000:00000000 00:00000000 00000000     0        0 15567 2 ffff983d57f0fc00 0
  995: 00000000:14E9 00000000:0000 07 00000000:00000000 00:00000000 00000000   106        0 16089 2 ffff983d5a0a7b80 0
 1638: 00000000:076C 00000000:0000 07 00000000:00000000 00:00000000 00000000     0        0 18571 2 ffff983d58b17400 0
 1854: 00000000:0044 00000000:0000 07 00000000:00000000 00:00000000 00000000     0        0 652958 2 ffff983d4b8f0440 0
 1897: 00000000:006F 00000000:0000 07 00000000:00000000 00:00000000 00000000     0        0 15566 2 ffff983d57f0f0c0 0
"""}
_PORTS_V6 = {
    'tcp': """  sl  local_address                         remote_address                        st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode
   0: 00000000000000000000000000000000:A62F 00000000000000000000000000000000:0000 0A 00000000:00000000 00:00000000 00000000  1000        0 440794 1 ffff983d4bb44000 100 0 0 10 0
   1: 00000000000000000000000000000000:006F 00000000000000000000000000000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 15571 1 ffff983d59857800 100 0 0 10 0
   2: 00000000000000000000000000000000:0016 00000000000000000000000000000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 655014 1 ffff983d57afd800 100 0 0 10 0
   3: 00000000000000000000000001000000:0019 00000000000000000000000000000000:0000 0A 00000000:00000000 00:00000000 00000000     0        0 19933 1 ffff983d4bb44800 100 0 0 10 20
   4: 00000000000000000000000000000000:999B 00000000000000000000000000000000:0000 0A 00000000:00000000 00:00000000 00000000  1000        0 325481 1 ffff983cbf1b1800 100 0 0 10 0
   5: 00000000000000000000000000000000:815D 00000000000000000000000000000000:0000 0A 00000000:00000000 00:00000000 00000000  1000        0 325021 1 ffff983cbf3da800 100 0 0 10 0
   6: 00000000000000000000000000000000:B525 00000000000000000000000000000000:0000 0A 00000000:00000000 00:00000000 00000000  1000        0 440585 1 ffff983ca4020800 100 0 0 10 0
   7: 0000000000000000FFFF00000100007F:815D 0000000000000000FFFF00000100007F:B8D8 01 00000000:00000000 00:00000000 00000000  1000        0 325041 1 ffff983d59857000 20 4 30 10 -1
   8: 0000000000000000FFFF00000100007F:A62F 0000000000000000FFFF00000100007F:8628 01 00000000:00000000 00:00000000 00000000  1000        0 440058 1 ffff983cac444000 20 4 26 10 -1
   9: 0000000000000000FFFF00000100007F:999B 0000000000000000FFFF00000100007F:8296 01 00000000:00000000 00:00000000 00000000  1000        0 325497 1 ffff983ca4020000 20 4 30 10 -1
  10: 0000000000000000FFFF00000100007F:B525 0000000000000000FFFF00000100007F:B8BC 01 00000000:00000000 00:00000000 00000000  1000        0 440789 1 ffff983cbf1b1000 20 0 0 10 -1
""",
    'udp': """  sl  local_address                         remote_address                        st tx_queue rx_queue tr tm->when retrnsmt   uid  timeout inode ref pointer drops
  404: 00000000000000000000000000000000:029A 00000000000000000000000000000000:0000 07 00000000:00000000 00:00000000 00000000     0        0 15570 2 ffff983d56ee4900 0
  659: 00000000000000000000000000000000:9B99 00000000000000000000000000000000:0000 07 00000000:00000000 00:00000000 00000000   106        0 16092 2 ffff983d5a6708c0 0
  995: 00000000000000000000000000000000:14E9 00000000000000000000000000000000:0000 07 00000000:00000000 00:00000000 00000000   106        0 16090 2 ffff983d5a670d00 0
 1897: 00000000000000000000000000000000:006F 00000000000000000000000000000000:0000 07 00000000:00000000 00:00000000 00000000     0        0 15569 2 ffff983d56ee4d40 0
"""}

_RESTCP = [
    TcpConnectionStatus(Family=2, LocalAddr='0.0.0.0', LocalPort=111, DestAddr='0.0.0.0', DestPort=0, Status=10),
    TcpConnectionStatus(Family=2, LocalAddr='0.0.0.0', LocalPort=22, DestAddr='0.0.0.0', DestPort=0, Status=10),
    TcpConnectionStatus(Family=2, LocalAddr='127.0.0.1', LocalPort=25, DestAddr='0.0.0.0', DestPort=0, Status=10),
    TcpConnectionStatus(Family=2, LocalAddr='127.0.0.1', LocalPort=34344, DestAddr='127.0.0.1', DestPort=42543, Status=1),
    TcpConnectionStatus(Family=2, LocalAddr='127.0.0.1', LocalPort=47320, DestAddr='127.0.0.1', DestPort=33117, Status=1),
    TcpConnectionStatus(Family=2, LocalAddr='127.0.0.1', LocalPort=47292, DestAddr='127.0.0.1', DestPort=46373, Status=1),
    TcpConnectionStatus(Family=2, LocalAddr='127.0.0.1', LocalPort=33430, DestAddr='127.0.0.1', DestPort=39323, Status=1),
    TcpConnectionStatus(Family=10, LocalAddr='::', LocalPort=42543, DestAddr='::', DestPort=0, Status=10),
    TcpConnectionStatus(Family=10, LocalAddr='::', LocalPort=111, DestAddr='::', DestPort=0, Status=10),
    TcpConnectionStatus(Family=10, LocalAddr='::', LocalPort=22, DestAddr='::', DestPort=0, Status=10),
    TcpConnectionStatus(Family=10, LocalAddr='::1', LocalPort=25, DestAddr='::', DestPort=0, Status=10),
    TcpConnectionStatus(Family=10, LocalAddr='::', LocalPort=39323, DestAddr='::', DestPort=0, Status=10),
    TcpConnectionStatus(Family=10, LocalAddr='::', LocalPort=33117, DestAddr='::', DestPort=0, Status=10),
    TcpConnectionStatus(Family=10, LocalAddr='::', LocalPort=46373, DestAddr='::', DestPort=0, Status=10),
    TcpConnectionStatus(Family=10, LocalAddr='::ffff:127.0.0.1', LocalPort=33117, DestAddr='::ffff:127.0.0.1', DestPort=47320, Status=1),
    TcpConnectionStatus(Family=10, LocalAddr='::ffff:127.0.0.1', LocalPort=42543, DestAddr='::ffff:127.0.0.1', DestPort=34344, Status=1),
    TcpConnectionStatus(Family=10, LocalAddr='::ffff:127.0.0.1', LocalPort=39323, DestAddr='::ffff:127.0.0.1', DestPort=33430, Status=1),
    TcpConnectionStatus(Family=10, LocalAddr='::ffff:127.0.0.1', LocalPort=46373, DestAddr='::ffff:127.0.0.1', DestPort=47292, Status=1)]

_RESUDP = [
    UdpConnectionStatus(Family=2, LocalAddr='0.0.0.0', LocalPort=33111, DestAddr='0.0.0.0', DestPort=0, Status=7),
    UdpConnectionStatus(Family=2, LocalAddr='0.0.0.0', LocalPort=666, DestAddr='0.0.0.0', DestPort=0, Status=7),
    UdpConnectionStatus(Family=2, LocalAddr='0.0.0.0', LocalPort=5353, DestAddr='0.0.0.0', DestPort=0, Status=7),
    UdpConnectionStatus(Family=2, LocalAddr='0.0.0.0', LocalPort=1900, DestAddr='0.0.0.0', DestPort=0, Status=7),
    UdpConnectionStatus(Family=2, LocalAddr='0.0.0.0', LocalPort=68, DestAddr='0.0.0.0', DestPort=0, Status=7),
    UdpConnectionStatus(Family=2, LocalAddr='0.0.0.0', LocalPort=111, DestAddr='0.0.0.0', DestPort=0, Status=7),
    UdpConnectionStatus(Family=10, LocalAddr='::', LocalPort=666, DestAddr='::', DestPort=0, Status=7),
    UdpConnectionStatus(Family=10, LocalAddr='::', LocalPort=39833, DestAddr='::', DestPort=0, Status=7),
    UdpConnectionStatus(Family=10, LocalAddr='::', LocalPort=5353, DestAddr='::', DestPort=0, Status=7),
    UdpConnectionStatus(Family=10, LocalAddr='::', LocalPort=111, DestAddr='::', DestPort=0, Status=7)]

tloglevel = 'INFO'


@unittest.skipUnless(platform.system() == 'Linux',
                     'Linux system check')
@loggers.unittestGlobalLevel(tloglevel)
class TestRealLinuxNetstat(unittest.TestCase):

    def test_linux_netstat(self):
        ns = LinuxNetstats()
        self.assertIsInstance(ns.unprivileged_ports, list)
        self.assertIsInstance(ns.tcp_netstats(), list)
        self.assertIsInstance(ns.udp_netstats(), list)


@unittest.skipUnless(platform.system() == 'Linux',
                     'Linux system check')
class TestFakeLinuxNetstat(unittest.TestCase):

    def setUp(self):
        self.lports_f = tempfile.mkstemp(prefix='test_net_lports_')[1]
        with open(self.lports_f, 'w') as fh:
            fh.write(_LPORTS)
        self.ports_v4_f = dict(
            tcp=tempfile.mkstemp(prefix='test_net_tcpv4_')[1],
            udp=tempfile.mkstemp(prefix='test_net_udpv4_')[1])
        self.ports_v6_f = dict(
            tcp=tempfile.mkstemp(prefix='test_net_tcpv6_')[1],
            udp=tempfile.mkstemp(prefix='test_net_udpv6_')[1])
        for proto in ('tcp', 'udp'):
            with open(self.ports_v4_f[proto], 'w') as fh:
                fh.write(_PORTS_V4[proto])
            with open(self.ports_v6_f[proto], 'w') as fh:
                fh.write(_PORTS_V6[proto])

        class FakeLinuxNetstats(LinuxNetstats):

            _LINUX_LPORT = self.lports_f
            _LINUX_PORTS_V4 = self.ports_v4_f
            _LINUX_PORTS_V6 = self.ports_v6_f
            _LINUX_AF_INET4 = 2
            _LINUX_AF_INET6 = 10

        self.testcls = FakeLinuxNetstats

    def tearDown(self):
        os.unlink(self.lports_f)
        for proto in ('tcp', 'udp'):
            os.unlink(self.ports_v4_f[proto])
            os.unlink(self.ports_v6_f[proto])

    def test_linux_netstat(self):
        ns = self.testcls()
        self.assertListEqual(ns.unprivileged_ports,
                             list(range(5001, 32768)) +
                             list(range(61000, 65536)))
        self.assertListEqual(ns.tcp_netstats(), _RESTCP)
        self.assertListEqual(ns.udp_netstats(), _RESUDP)
        self.assertFalse(ns.check_localport(5354))
        self.assertTrue(ns.check_localport(5353))
        self.assertIsInstance(ns.available_localport(), int)


if __name__ == '__main__':
    unittest.main()
