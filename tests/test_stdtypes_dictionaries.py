from unittest import TestCase, main

from bronx.stdtypes import dictionaries


# Base for Lower and UpperCaseDict objects

# noinspection PyPropertyAccess
class utCaseDict(TestCase):

    def setUp(self):
        self.tdict = {'Toto': 1, 'blop': 2, 'SCRONTCH': 3}
        self.ld = dictionaries.LowerCaseDict(self.tdict)
        self.ud = dictionaries.UpperCaseDict(self.tdict)

    def test_case_processing(self):
        self.setUp()
        for speciald in (self.ld, self.ud):
            self.assertIn('Toto', speciald)
            self.assertIn('toto', speciald)
            self.assertIn('TOTO', speciald)
            self.assertIn('toTo', speciald)
            del speciald['scrontch']
            self.assertNotIn('SRONTch', speciald)
            speciald['blop'] = 3
            speciald['bLop'] = 4
            speciald['BLOP'] = 4
            self.assertEqual(speciald['blop'], 4)
            self.assertEqual(len(speciald), 2)

    def test_special_content(self):
        self.setUp()
        self.assertDictEqual(self.ld,
                             {k.lower(): v for k, v in self.tdict.items()})
        self.assertDictEqual(self.ud,
                             {k.upper(): v for k, v in self.tdict.items()})


if __name__ == '__main__':
    main(verbosity=2)
