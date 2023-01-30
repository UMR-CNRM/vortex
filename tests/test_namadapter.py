import os
import unittest

from thenamelisttool.namadapter import BronxNamelistAdapter, NO_SORTING

tpl_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                        '../src/thenamelisttool/templates')
tpl_path = os.path.normpath(tpl_path)


TEST_FINALREF = """ &NAM_FILENAMES
   HPGDFILE='PGDFILE',
 /
 &NAM_IO
   CSURF_FILETYPE='LFI   ',
   GLURP='PREP2',
   CPGDFILE='PGD2',
   CINIFILEBIS='INIT_SURF',
   NPRINT=1,
 /
 &NAM_ISBAN
   LGLACIER=.FALSE.,
 /
 &NAM_PREP_SEAFLUX
 /
 &NAM_PREP_SURF_ATM
   CFILETYPE='LFI   ',
   CFILE='PREP1',
   CFILEPGDTYPE='LFI   ',
   CFILEPGD=55.6,
 /
 &NAM_PREP_WATFLUX
   LWAT_SBL=.FALSE.,
 /
 &NAM_TOTO
 /
 &NAM_WRITE_SURF_ATM
 /
"""


class TestTntNamAdapter(unittest.TestCase):

    def test_bronx_adapter(self):
        nampath = os.path.join(tpl_path, 'namelist_prep_template')
        nadapt = BronxNamelistAdapter(nampath)
        nadapt.remove_blocks(['nam_PREP_ISBA', ])
        nadapt.add_blocks(['NAM_TOTO'])
        nadapt.move_blocks({'NAM_FILE_NAMES': 'NAM_FILENAMES',
                            'NAM_IO_OFFLINE': 'NAM_IO'})
        nadapt.move_keys({('NAM_FILENAMES', 'CINIFILE'): ('NAM_IO', 'CINIFILEBIS')})
        nadapt.move_keys({('NAM_IO', 'LPRINT'): ('NAM_IO', 'NPRINT')}, doctor=True)
        nadapt.move_keys({('NAM_IO', 'CPREPFILE'): ('NAM_IO', 'GLURP')}, keep_index=True)
        with self.assertRaises(KeyError):
            nadapt.add_keys({('NAMTOTO', 'TRUC'): 1})
        nadapt.add_keys({('NAM_ISBAN', 'LGLACIER'): False,
                         ('NAM_PREP_SURF_ATM', 'CFILEPGD'): 55.6, })
        nadapt.remove_keys([('NAM_WRITE_SURF_ATM', 'LNOWRITE_TEXFILE'),
                            ('NAM_PREP_SEAFLUX', 'LSEA_SBL'), ])
        self.assertEqual(nadapt.dumps(sorting=NO_SORTING), TEST_FINALREF)
        self.assertSetEqual(
            {'NAM_IO', 'NAM_IO_OFFLINE', 'NAM_FILE_NAMES', 'NAM_FILENAMES', 'NAM_TOTO', 'NAM_PREP_ISBA'},
            nadapt.check_blocks(nampath)
        )
        nadapt.merge(BronxNamelistAdapter('&NAM_PREP_WATFLUX LWAT_SBL=T, /'))
        self.assertIs(nadapt['NAM_PREP_WATFLUX']['LWAT_SBL'], True)
        self.assertIn('NAM_TOTO', nadapt)
        nadapt.squeeze()
        self.assertNotIn('NAM_TOTO', nadapt)


if __name__ == "__main__":
    unittest.main(verbosity=2)
