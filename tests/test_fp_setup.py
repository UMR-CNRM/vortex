from io import StringIO
import sys
from unittest import TestCase, main

from bronx.fancies import loggers

from footprints import reporting

from footprints.config import FootprintSetup


class Foo:
    # noinspection PyUnusedLocal
    def __init__(self, *u_args, **kw):
        self.__dict__.update(kw)


# noinspection PyPropertyAccess
class utFootprintSetup(TestCase):

    def test_footprint_setup(self):
        setup = FootprintSetup(tag='utest_fakesetup1', new=True)
        self.assertIsInstance(setup, FootprintSetup)
        self.assertIsInstance(setup.nullreport, reporting.NullReport)
        self.assertIsInstance(setup.report, int)
        self.assertIsInstance(setup.lreport_len, int)
        self.assertIsInstance(setup.extended, bool)
        self.assertIsInstance(setup.docstrings, int)
        self.assertIsInstance(setup.shortnames, bool)
        self.assertIsInstance(setup.fastmode, bool)
        self.assertIsInstance(setup.fastkeys, tuple)
        self.assertIsInstance(setup.defaults, dict)
        self.assertIsInstance(setup.proxies, set)
        self.assertIs(setup.callback, None)

        setup.defaults.update(hello='foo')
        self.assertIsInstance(setup.defaults, dict)
        self.assertDictEqual(setup.defaults, dict(hello='foo'))

        orig_out = sys.stdout
        sys.stdout = StringIO()
        setup2 = setup()
        self.assertIs(setup, setup2)
        setup2 = setup(whatever=1)
        self.assertIs(setup, setup2)
        with loggers.contextboundGlobalLevel('error'):
            setup2 = setup(tag='toto')
        self.assertIsNot(setup, setup2)
        sys.stdout = orig_out

        setup.defaults.update(BIGCASE=2)
        self.assertDictEqual(setup.defaults, dict(hello='foo', bigcase=2))

        with self.assertRaises(AttributeError):
            del setup.defaults

        self.assertIsInstance(setup.extended, bool)
        self.assertEqual(setup.extended, True)

        setup.extended = True
        self.assertIsInstance(setup.extended, bool)
        self.assertEqual(setup.extended, True)

        setup.extended = False
        self.assertIsInstance(setup.extended, bool)
        self.assertEqual(setup.extended, False)

        setup.extended = 2
        self.assertIsInstance(setup.extended, bool)
        self.assertEqual(setup.extended, True)

        with self.assertRaises(AttributeError):
            del setup.extended

        foo = Foo()
        setup.add_proxy(foo)
        self.assertTrue(hasattr(foo, 'garbage'))
        self.assertTrue(hasattr(foo, 'garbages'))

    def test_footprint_callback(self):
        setup = FootprintSetup(tag='utest_fakesetup2', new=True)
        self.assertIsInstance(setup, FootprintSetup)
        self.assertIs(setup.callback, None)

        rv = setup.extras()
        self.assertIsInstance(rv, dict)
        self.assertDictEqual(rv, dict())

        def groundvalues():
            return dict(bottomvalue=2, hello='foo')

        setup.callback = groundvalues
        self.assertIsInstance(setup.callback, type(groundvalues))

        rv = setup.extras()
        self.assertIsInstance(rv, dict)
        self.assertDictEqual(rv, dict(bottomvalue=2, hello='foo'))


if __name__ == '__main__':
    main(verbosity=2)
