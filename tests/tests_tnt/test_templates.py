from __future__ import print_function, absolute_import, unicode_literals, division

import io
import os
import unittest

import tnt

tpl_path = os.path.join(os.path.realpath(__file__), '../../../site/tnt/templates')
tpl_path = os.path.normpath(tpl_path)

tntstack_todo_ref = [
    {'action': 'tnt', u'namelist': [u'namelist_screen*'], u'directive': [u'dfi', u'geo499c1']},
    {'action': 'tnt', u'namelist': [u'namelist_previ_sfx', u'namelist_surf'], u'directive': [u'surfexdiags']},
    {'action': 'create', u'copy': u'namelist_screening1', u'target': u'namelist_screening3'},
    {'action': 'create', u'namelist': u'namelist_fp1', u'target': u'namelist_fp2', u'directive': [u'geo499c1', u'surfexdiags']},
    {'action': 'create', u'target': u'namelist_prep', u'external': os.path.join(tpl_path, u'namelist_prep_template')},
    {'action': 'delete', u'namelist': [u'something_useless[12]', u'something_strange']},
    {'action': 'link', u'namelist': u'namelist_prep', u'target': u'namelist_fp3'},
    {'action': 'move', u'namelist': u'namelist_surf', u'target': u'namelist_surfex'},
    {'action': 'touch', u'namelist': [u'unknown_namelist', u'namelist_fp*']},
    {'action': 'clean_untouched'}]


def test_yaml():
    rc = True
    try:
        import yaml  # @UnusedImport
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

    @unittest.skipUnless(test_yaml(), "pyyaml is unavailable")
    def test_tnt_tpl_yaml(self):
        tplyaml = tnt.config.read_directives(os.path.join(tpl_path,
                                                          'tnt-directive.tpl.yaml'))
        self.assertDictEqual(tplyaml.keys_to_set,
                             {('NAMBLOCK2', 'KEY2(1:3)'): [5, 6, 7],
                              ('NAMBLOCK3', 'KEY3(50)'): -50,
                              ('NAMBLOCK1', 'KEY1'): 46.5})

    @unittest.skipUnless(test_yaml(), "pyyaml is unavailable")
    def test_tntstack_tpl_yaml(self):
        # Read the yaml file
        import yaml
        with io.open(os.path.join(tpl_path, 'tntstack-directive.tpl.yaml')) as fhy:
            dirdict = yaml.load(fhy, Loader=yaml.SafeLoader)
        # Process it
        tplyaml = tnt.config.TntStackDirective(basedir=tpl_path, **dirdict)
        self.assertListEqual(tplyaml.todolist, tntstack_todo_ref)
        self.assertSetEqual(set(tplyaml.directives.keys()),
                            set(['surfexdiags', 'geo499c1', 'dfi']))


if __name__ == "__main__":
    unittest.main(verbosity=2)
