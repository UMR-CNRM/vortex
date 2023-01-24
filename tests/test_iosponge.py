import io
import unittest

from vortex.util.iosponge import IoSponge


class TestFakeIo(unittest.TestCase):

    def get_string_io(self, size):
        s_io = io.BytesIO()
        s_io.write(b'0' * size)
        s_io.seek(0)
        return s_io

    def test_iosponge_basics(self):
        fio = IoSponge(self.get_string_io(2), 3, 4)
        self.assertEqual(fio.size, 2)
        self.assertEqual(fio.tell(), 0)
        self.assertEqual(fio.read(0), b'')
        self.assertEqual(fio.tell(), 0)
        self.assertEqual(fio.read(1), b'0')
        self.assertEqual(fio.tell(), 1)
        self.assertEqual(fio.read(), b'0')
        self.assertEqual(fio.tell(), 2)
        self.assertEqual(fio.read(), b'')
        self.assertEqual(fio.tell(), 2)
        self.assertEqual(fio.read(), b'')
        self.assertEqual(fio.tell(), 2)
        fio = IoSponge(self.get_string_io(10), 3, 2)
        self.assertEqual(fio.size, 3)
        self.assertEqual(fio.read(), b'0000000000')
        self.assertEqual(fio.read(), b'')
        fio = IoSponge(self.get_string_io(10), 3, 4)
        self.assertEqual(fio.size, 4)
        self.assertEqual(fio.read(2), b'00')
        self.assertEqual(fio.read(), b'00000000')
        self.assertEqual(fio.read(), b'')

        fio = IoSponge(self.get_string_io(10), 3, 4)
        self.assertEqual(fio.size, 4)
        self.assertEqual(fio.read1(2), b'00')
        self.assertEqual(fio.read1(), b'00000000')
        self.assertEqual(fio.read1(), b'')

        fio = IoSponge(self.get_string_io(10), 3, 4)
        tempb = bytearray(8)
        self.assertEqual(fio.readinto(tempb), 8)
        self.assertEqual(tempb, b'00000000')
        self.assertEqual(fio.readinto(tempb), 2)
        self.assertEqual(fio.read(), b'')

        self.assertTrue(fio.readable())
        self.assertFalse(fio.writable())


if __name__ == '__main__':
    unittest.main()
