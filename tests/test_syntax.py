
import unittest

from vortex.syntax.stdattrs import DelayedInit


class Scrontch(object):

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
        self.assertRegexpMatches(str(di), 'Not yet Initialised>$')
        self.assertRegexpMatches(repr(di), 'Not yet Initialised>$')
        self.assertEqual(di.ping(), "Ping")
        self.assertEqual(str(di), "Hey !")
        self.assertRegexpMatches(repr(di), 'proxied=<.*\.Scrontch')
        scrontch = Scrontch("Hi !")
        di = DelayedInit(scrontch, _initialise_scrontch)
        self.assertEqual(str(di), "Hi !")
        self.assertRegexpMatches(repr(di), 'proxied=<.*\.Scrontch')
        self.assertEqual(di.ping(), "Ping")


if __name__ == "__main__":
    unittest.main(verbosity=2)
