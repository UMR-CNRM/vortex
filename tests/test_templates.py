import os
import unittest

import thenamelisttool as tnt

tloglevel = 9999

tpl_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                        '../src/thenamelisttool/templates')
tpl_path = os.path.normpath(tpl_path)

data_path = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'data')
data_path = os.path.normpath(data_path)

tntstack_todo_ref = [
    {'action': 'tnt', 'namelist': ['namelist_screen*'],
     'directive': ['dfi', 'geo499c1']},
    {'action': 'tnt', 'namelist': ['namelist_previ_sfx', 'namelist_surf'],
     'directive': ['surfexdiags']},
    {'action': 'create', 'copy': 'namelist_screening1', 'target': 'namelist_screening3'},
    {'action': 'create', 'namelist': 'namelist_fp1', 'target': 'namelist_fp2',
     'directive': ['geo499c1', 'surfexdiags']},
    {'action': 'create', 'target': 'namelist_prep', 'external': os.path.join(tpl_path, 'namelist_prep_template')},
    {'action': 'delete', 'namelist': ['something_useless[12]', 'something_strange']},
    {'action': 'link', 'namelist': 'namelist_prep', 'target': 'namelist_fp3'},
    {'action': 'move', 'namelist': 'namelist_surf', 'target': 'namelist_surfex'},
    {'action': 'touch', 'namelist': ['unknown_namelist', 'namelist_fp*']},
    {'action': 'clean_untouched'}]

COMPOSED_NAM = """\
 &NAERAD
 /
 &NAMCT0
   LECMWF=.FALSE.,
 /
 &NAMDIM
   NPROMA=-24,
 /
 &NAMDYN
   LNHDYN=.TRUE.,
 /
 &NAMEMPTY
 /
 &NAMFA
   NBITCS=16,
   NBITPG=24,
   NVGRIB=123,
 /
 &NAMINI
   NSTEP=8,
 /
 &NAMKEPT
   USELESS='YES',
 /
 &NAMOBJ
   L_OOPS=.TRUE.,
 /
 &NAMOBS
   LOLDPP=.TRUE.,
 /
 &NAMRIP
   CSTOP='h1',
 /
"""


def checklib_yaml():
    rc = True
    try:
        import yaml  # @UnusedImport
        assert yaml
    except ImportError:
        rc = False
    return rc


class TestTntTemplate(unittest.TestCase):

    def test_tnt_tpl_py(self):
        tplpy = tnt.config.read_directives(os.path.join(tpl_path,
                                                        'tnt-directive.tpl.py'))
        self.assertDictEqual(tplpy.keys_to_set,
                             {('NAMBLOCK2', 'KEY2(1:3)'): [5, 6, 7],
                              ('NAMBLOCK1', 'KEY1'): 46.5,
                              ('NAMBLOCK3', 'KEY3(50)'): -50})

    @unittest.skipUnless(checklib_yaml(), "pyyaml is unavailable")
    def test_tnt_tpl_yaml(self):
        tplyaml = tnt.config.read_directives(os.path.join(tpl_path,
                                                          'tnt-directive.tpl.yaml'))
        self.assertDictEqual(tplyaml.keys_to_set,
                             {('NAMBLOCK2', 'KEY2(1:3)'): [5, 6, 7],
                              ('NAMBLOCK3', 'KEY3(50)'): -50,
                              ('NAMBLOCK1', 'KEY1'): 46.5})

    @unittest.skipUnless(checklib_yaml(), "pyyaml is unavailable")
    def test_tntstack_tpl_yaml(self):
        # Read the yaml file
        import yaml
        with open(os.path.join(tpl_path, 'tntstack-directive.tpl.yaml')) as fhy:
            dirdict = yaml.load(fhy, Loader=yaml.SafeLoader)
        # Process it
        tplyaml = tnt.config.TntStackDirective(basedir=tpl_path, **dirdict)
        self.assertListEqual(tplyaml.todolist, tntstack_todo_ref)
        self.assertSetEqual(set(tplyaml.directives.keys()),
                            {'surfexdiags', 'geo499c1', 'dfi'})


@unittest.skipUnless(checklib_yaml(), "pyyaml is unavailable")
class TestTntRecipe(unittest.TestCase):

    def test_recipe_yaml(self):
        from bronx.datagrip.namelist import FIRST_ORDER_SORTING
        recipe = tnt.config.TntRecipe(os.path.join(tpl_path, 'tntcompose-recipe.tpl.yaml'),
                                      sourcenam_directory=data_path)
        nam = recipe.ingredients[0]
        for ingredient in recipe.ingredients[1:]:
            nam.merge(ingredient)
        self.assertEqual(nam.dumps(sorting=FIRST_ORDER_SORTING), COMPOSED_NAM)

    def _assert_syntax_error(self, recipe):
        with tnt.util.set_verbose(False, 'ko/recipe_ko1.yaml'):
            with self.assertRaises(tnt.config.TntRecipeSyntaxError):
                tnt.config.TntRecipe(os.path.join(data_path, 'ko', recipe),
                                     sourcenam_directory=data_path)

    def test_recipe_syntax(self):
        self._assert_syntax_error('recipe_ko1.yaml')
        self._assert_syntax_error('recipe_ko2.yaml')
        self._assert_syntax_error('recipe_ko3.yaml')
        self._assert_syntax_error('recipe_ko5.yaml')
        self._assert_syntax_error('recipe_ko6.yaml')
        self._assert_syntax_error('recipe_ko7.yaml')


if __name__ == "__main__":
    unittest.main(verbosity=2)
