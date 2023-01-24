import unittest

from vortex.syntax.stdattrs import DelayedInit, Latitude, Longitude


class Scrontch:

    def __init__(self, msg):
        self._msg = msg

    def ping(self):
        return "Ping"

    def __str__(self):
        return self._msg


def _initialise_scrontch():
    return Scrontch("Hey !")


class TestDelayedInit(unittest.TestCase):

    def test_delayed_init_basics(self):
        scrontch = None
        di = DelayedInit(scrontch, _initialise_scrontch)
        self.assertRegex(str(di), r'Not yet Initialised>$')
        self.assertRegex(repr(di), r'Not yet Initialised>$')
        self.assertEqual(di.ping(), "Ping")
        self.assertEqual(str(di), "Hey !")
        self.assertRegex(repr(di), r'proxied=<.*\.Scrontch')
        scrontch = Scrontch("Hi !")
        di = DelayedInit(scrontch, _initialise_scrontch)
        self.assertEqual(str(di), "Hi !")
        self.assertRegex(repr(di), r'proxied=<.*\.Scrontch')
        self.assertEqual(di.ping(), "Ping")


class TestLatLon(unittest.TestCase):

    def test_latitude(self):
        rv = Latitude(42)
        self.assertEqual(rv, 42.0)
        self.assertEqual(str(rv), '42.0')
        self.assertEqual(rv.nice(), '42.0N')
        self.assertEqual(rv.hemisphere, 'North')
        rv = Latitude('42N')
        self.assertEqual(rv, 42.0)
        self.assertEqual(str(rv), '42.0')
        self.assertEqual(rv.nice(), '42.0N')
        self.assertEqual(rv.hemisphere, 'North')
        rv = Latitude(-12.3)
        self.assertEqual(rv, -12.3)
        self.assertEqual(str(rv), '-12.3')
        self.assertEqual(rv.nice(), '12.3S')
        self.assertEqual(rv.hemisphere, 'South')
        rv = Latitude('12.3S')
        self.assertEqual(rv, -12.3)
        self.assertEqual(str(rv), '-12.3')
        self.assertEqual(rv.nice(), '12.3S')
        self.assertEqual(rv.hemisphere, 'South')
        with self.assertRaises(ValueError):
            rv = Latitude(90.1)
        with self.assertRaises(ValueError):
            rv = Latitude('91N')
        with self.assertRaises(ValueError):
            rv = Latitude(-90.1)
        with self.assertRaises(ValueError):
            rv = Latitude('91S')

    def test_longitude(self):
        rv = Longitude(142)
        self.assertEqual(rv, 142.0)
        self.assertEqual(str(rv), '142.0')
        self.assertEqual(rv.nice(), '142.0E')
        self.assertEqual(rv.hemisphere, 'East')
        rv = Longitude('142E')
        self.assertEqual(rv, 142.0)
        self.assertEqual(str(rv), '142.0')
        self.assertEqual(rv.nice(), '142.0E')
        self.assertEqual(rv.hemisphere, 'East')
        rv = Longitude(-142.3)
        self.assertEqual(rv, -142.3)
        self.assertEqual(str(rv), '-142.3')
        self.assertEqual(rv.nice(), '142.3W')
        self.assertEqual(rv.hemisphere, 'West')
        rv = Longitude('142.3W')
        self.assertEqual(rv, -142.3)
        self.assertEqual(str(rv), '-142.3')
        self.assertEqual(rv.nice(), '142.3W')
        self.assertEqual(rv.hemisphere, 'West')
        with self.assertRaises(ValueError):
            rv = Longitude(180.1)
        with self.assertRaises(ValueError):
            rv = Longitude('181E')
        with self.assertRaises(ValueError):
            rv = Longitude(-180.1)
        with self.assertRaises(ValueError):
            rv = Longitude('181W')


if __name__ == "__main__":
    unittest.main(verbosity=2)
