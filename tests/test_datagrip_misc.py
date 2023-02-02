import tempfile
import os
import unittest

from bronx.syntax.externalcode import ExternalCodeImportChecker

# Yaml is not mandatory
y_checker = ExternalCodeImportChecker('yaml')
with y_checker as npregister:
    import yaml

if y_checker.is_available():
    assert yaml
    from bronx.datagrip.misc import read_dict_in_CSV


@unittest.skipUnless(y_checker.is_available(), "Yaml is not available")
class TestDictCSV(unittest.TestCase):

    def setUp(self):
        self.testfilename = tempfile.mkstemp()[1]
        with open(self.testfilename, 'w') as f:
            f.write(';\n')
            f.write('main\n')
            f.write('a:1;b:ok\n')
            f.write('a:2;b:not ok;c:why?\n')
            f.close()

    def test_read_dict_in_CSV(self):
        self.assertEqual(read_dict_in_CSV(self.testfilename),
                         ([{'a': 1, 'b': 'ok'},
                           {'a': 2, 'c': 'why?', 'b': 'not ok'}],
                          'main')
                         )

    def tearDown(self):
        os.remove(self.testfilename)


if __name__ == "__main__":
    unittest.main(verbosity=2)
