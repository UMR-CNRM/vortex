import os
import unittest

from bronx.fancies import loggers

from thenamelisttool.config import TntDirective, TntStackDirective
from thenamelisttool.config import TntDirectiveUnkownError, TntDirectiveValueError, TntStackDirectiveError

tpl_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                        '../src/thenamelisttool/templates')
tpl_path = os.path.normpath(tpl_path)


class TestTntConfig(unittest.TestCase):

    def test_tnt_dir(self):
        with self.assertRaises(TntDirectiveUnkownError):
            TntDirective(scrontch='toto')
        with self.assertRaises(TntDirectiveUnkownError):
            TntDirective().hips
        with self.assertRaises(TntDirectiveValueError):
            TntDirective(keys_to_set='I believe, I can fly')
        with self.assertRaises(TntDirectiveValueError):
            TntDirective(keys_to_set=dict(toto=1))
        with self.assertRaises(TntDirectiveValueError):
            TntDirective(keys_to_set={(25, 42): 1})
        with self.assertRaises(TntDirectiveValueError):
            TntDirective(keys_to_set=dict(BLOP={1: 25}))
        for tdir in [TntDirective(keys_to_set={('BLOP', 'TRUC'): 1}),
                     TntDirective(keys_to_set=dict(BLOP={'TRUC': 1}))]:
            self.assertDictEqual(tdir.keys_to_set, {('BLOP', 'TRUC'): 1})
        with self.assertRaises(TntDirectiveValueError):
            TntDirective(blocks_to_move=1)
        with self.assertRaises(TntDirectiveValueError):
            TntDirective(blocks_to_move={'ARG': 1})
        with self.assertRaises(TntDirectiveValueError):
            TntDirective(blocks_to_move={1: 'ARG'})
        with self.assertRaises(TntDirectiveValueError):
            TntDirective(blocks_to_remove=1)
        self.assertSetEqual(TntDirective(blocks_to_remove='ARG').blocks_to_remove,
                            {'ARG'})
        self.assertSetEqual(TntDirective(blocks_to_remove=('ARG', 'BLOP')).blocks_to_remove,
                            {'ARG', 'BLOP'})
        with self.assertRaises(TntDirectiveValueError):
            TntDirective(macros='MACHIN')
        with self.assertRaises(TntDirectiveValueError):
            TntDirective(macros={1: 3})

    def test_tntstack_dir(self):
        with self.assertRaises(TntStackDirectiveError):
            TntStackDirective(tpl_path, todolist='toto')
        with self.assertRaises(TntStackDirectiveError):
            TntStackDirective(tpl_path, list(), directives='Beeeeee')
        with self.assertRaises(TntStackDirectiveError):
            TntStackDirective(tpl_path, [dict(action='truc'), ])
        with self.assertRaises(TntStackDirectiveError):
            TntStackDirective(tpl_path, [dict(namelist='machin'), ])
        with loggers.contextboundGlobalLevel('critical'):
            with self.assertRaises(TntStackDirectiveError):
                # Namelist is missing
                TntStackDirective(tpl_path, [dict(action='tnt', directive='truc'), ])
        with self.assertRaises(TntStackDirectiveError):
            TntStackDirective(tpl_path, [dict(action='tnt', namelist=1, directive='truc'), ])
        with self.assertRaises(TntStackDirectiveError):
            # machin directive is not defined
            TntStackDirective(tpl_path,
                              [dict(action='tnt', namelist='coucou', directive='machin'), ],
                              directives=dict(truc=dict()))
        tdir = TntStackDirective(tpl_path,
                                 [dict(action='tnt', namelist='coucou', directive='truc'), ],
                                 directives=dict(truc=dict()))
        self.assertDictEqual(tdir.todolist[0],
                             dict(action='tnt', namelist=['coucou', ], directive=['truc', ]))
        with loggers.contextboundGlobalLevel('critical'):
            with self.assertRaises(TntStackDirectiveError):
                # multiple target...
                TntStackDirective(tpl_path,
                                  [dict(action='create', target=['blop', 'toto', ],
                                        external='namelist_prep_template'), ])
        with self.assertRaises(TntStackDirectiveError):
            # namelist_prep_template2 do not exists
            TntStackDirective(tpl_path,
                              [dict(action='create', target='blop', external='namelist_prep_template2'), ])
        tdir = TntStackDirective(tpl_path,
                                 [dict(action='create', target='blop', external='namelist_prep_template'), ])
        self.assertDictEqual(tdir.todolist[0],
                             dict(action='create', target='blop',
                                  external=os.path.join(tpl_path, 'namelist_prep_template')))


if __name__ == "__main__":
    unittest.main(verbosity=2)
