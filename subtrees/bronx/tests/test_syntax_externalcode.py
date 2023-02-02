import unittest

from bronx.fancies import loggers
from bronx.syntax.externalcode import ExternalCodeImportChecker, ExternalCodeUnavailableError


class TestExternalCodeImport(unittest.TestCase):

    def test_externalcode_bascis_ok(self):
        # If the import works fine
        ec_checker = ExternalCodeImportChecker()
        with ec_checker:
            import datetime  # @UnusedImport
            assert datetime
        self.assertTrue(ec_checker.is_available())

        @ec_checker.disabled_if_unavailable
        def test_func1():
            return True
        self.assertTrue(test_func1())

        @ec_checker.disabled_if_unavailable
        class test_cls1:

            def toto(self):
                return True
        self.assertTrue(test_cls1().toto())

    @loggers.fdecoGlobalLevel('error')
    def test_externalcode_bascis_fails(self):
        # If the import works fine
        ec_checker = ExternalCodeImportChecker('a_very_unlikely_package_name')
        with ec_checker:
            import a_very_unlikely_package_name  # @UnusedImport @UnresolvedImport
            assert a_very_unlikely_package_name
        self.assertFalse(ec_checker.is_available())

        @ec_checker.disabled_if_unavailable
        def test_func1():
            return True
        with self.assertRaises(ExternalCodeUnavailableError):
            test_func1()

        @ec_checker.disabled_if_unavailable
        class test_cls2:

            def toto(self):
                return True
        with self.assertRaises(ExternalCodeUnavailableError):
            test_cls2().toto()

    def test_externalcode_extras(self):
        # If the import works fine but extra requirement are added
        ec_checker = ExternalCodeImportChecker()
        with self.assertRaises(RuntimeError):
            ec_checker.is_available()
        with ec_checker as ec_register:
            import datetime  # @UnusedImport
            assert datetime
            ec_register.update(version='1.0.0', other='gruik')
        self.assertTrue(ec_checker.is_available())
        self.assertTrue(ec_checker.is_available(version='0.9.0'))
        self.assertTrue(ec_checker.is_available(version='0.9.0', other='gruik'))
        self.assertFalse(ec_checker.is_available(version='1.9.0', other='gruik'))
        self.assertFalse(ec_checker.is_available(version='0.9.0', other='toto'))

        @ec_checker.disabled_if_unavailable(version='0.9.0')
        def test_func1():
            return True
        self.assertTrue(test_func1())

        @ec_checker.disabled_if_unavailable(version='1.9.0')
        class test_cls1:

            def toto(self):
                return True
        with self.assertRaises(ExternalCodeUnavailableError):
            test_cls1().toto()

        # Version not defined...
        ec_checker = ExternalCodeImportChecker()
        with ec_checker:
            import collections  # @UnusedImport
            assert collections

        with self.assertRaises(RuntimeError):
            self.assertTrue(ec_checker.is_available(version='0.9.0'))

        with self.assertRaises(RuntimeError):
            self.assertTrue(ec_checker.is_available(machin=True))

        # Other exceptions
        with self.assertRaises(ValueError):
            ec_checker = ExternalCodeImportChecker()
            with ec_checker:
                raise ValueError()
        with self.assertRaises(RuntimeError):
            ec_checker.is_available()


if __name__ == '__main__':
    unittest.main()
