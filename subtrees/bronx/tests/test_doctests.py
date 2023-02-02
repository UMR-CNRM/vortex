import doctest
import unittest

from bronx.datagrip import namelist, varbcheaders
from bronx.fancies import display, language, loggers
from bronx.patterns import getbytag, observer
from bronx.stdtypes import date, history, tracking, xtemplates
from bronx import syntax as b_syntax_init
from bronx.syntax import externalcode, iterators, minieval, parsing

# Numpy is not mandatory
npchecker = externalcode.ExternalCodeImportChecker('numpy')
with npchecker as npregister:
    import numpy as np
    assert np

# NetCDF4 is not mandatory
nc4checker = externalcode.ExternalCodeImportChecker('netdcf4')
with nc4checker as npregister:
    import netCDF4
    assert netCDF4


class utDocTests(unittest.TestCase):

    def assert_doctests(self, module, **kwargs):
        rc = doctest.testmod(module, **kwargs)
        self.assertEqual(rc[0], 0,  # The error count should be 0
                         'Doctests errors {!s} for {!r}'.format(rc, module))

    def test_doctests(self):
        self.assert_doctests(namelist)
        self.assert_doctests(varbcheaders)
        self.assert_doctests(display)
        self.assert_doctests(language)
        self.assert_doctests(loggers)
        self.assert_doctests(getbytag)
        self.assert_doctests(observer)
        self.assert_doctests(date)
        self.assert_doctests(history)
        self.assert_doctests(tracking)
        self.assert_doctests(xtemplates)
        self.assert_doctests(iterators)
        self.assert_doctests(minieval)
        self.assert_doctests(parsing)
        self.assert_doctests(b_syntax_init)

    @unittest.skipUnless(npchecker.is_available(), "The numpy package is unavailable.")
    def test_doctests_w_numpy(self):
        from bronx.meteo import thermo
        self.assert_doctests(thermo)

    @unittest.skipUnless(npchecker.is_available() and
                         nc4checker.is_available(),
                         "The numpy or netCDF4 package is unavailable.")
    def test_doctests_w_numpy_netcdf4(self):
        from bronx.datagrip import netcdf
        self.assert_doctests(netcdf)


if __name__ == '__main__':
    unittest.main(verbosity=2)
