import ast
import itertools
import unittest

import bronx.syntax.minieval as minie


class TestMiniEval(unittest.TestCase):

    def setUp(self):
        unittest.TestCase.setUp(self)
        self.sls = minie.SingleLineStatement()

    def assert_parsing_exc(self, statement, **kwargs):
        with self.assertRaises(minie.SingleLineStatementParsingError):
            self.sls.check(statement, **kwargs)

    def assert_security_exc(self, statement, **kwargs):
        with self.assertRaises(minie.SingleLineStatementSecurityError):
            self.sls.check(statement, **kwargs)

    def assert_eval_exc(self, statement, **kwargs):
        with self.assertRaises(minie.SingleLineStatementEvalError):
            self.sls(statement, **kwargs)

    def assert_check(self, statement, **kwargs):
        self.assertIsInstance(self.sls.check(statement, **kwargs), ast.Expression)

    def assert_eval(self, statement, ref, **kwargs):
        self.assertEqual(self.sls(statement, **kwargs), ref)

    def test_rejections(self):
        self.assert_parsing_exc('z = 1')
        self.assert_parsing_exc('import inject')
        self.assert_parsing_exc('del stuff.a', stuff=self)
        self.assert_security_exc('globals()[1].clear()')
        self.assert_parsing_exc('del stuff.a', stuff=self)
        self.assert_security_exc('stuff.__dict__.clear()', stuff=self)
        self.assert_security_exc('set([a, b])')
        self.assert_security_exc('list([a, stuff.__truc])', stuff=self)
        self.assert_eval_exc('set([1, stuff.totoattr])', stuff=self)

    def test_ok(self):
        self.assert_eval('"{:s}".format("Toto")', 'Toto')
        self.assert_eval('None', None)
        self.assert_eval('set([1 + 2, 4])', {3, 4})
        self.assert_eval('sorted([(1, 2), (2, 0), (3, 1)], key=lambda x: x[1])',
                         [(2, 0), (3, 1), (1, 2)])
        self.assert_eval('sorted([(1, 2), (2, 0), (3, 1)], key=lambda x, d=1: x[d])',
                         [(2, 0), (3, 1), (1, 2)])
        self.assert_eval('list(zip(* t))', [('a', 1), ('b', 2)], t=[['a', 'b'], [1, 2]])
        self.assert_eval('["Member{:02d}".format(m) for m in members if m < 2]',
                         ['Member00', 'Member01'],
                         members=range(0, 3))
        self.assert_eval('{"Member{:02d}".format(m) if m % 2 == 0 else "strange" for m in members}',
                         {'strange', 'Member02', 'Member00'},
                         members=range(0, 4))
        self.assert_eval('{m: dict(physic="P{:02d}".format(p)) for m, p in zip(members, physics) if p == 0}',
                         {0: {'physic': 'P00'}, 2: {'physic': 'P00'}},
                         members=range(0, 3), physics=itertools.cycle([0, 1]))
        self.assert_eval('["Run: {:02d}, Member{:02d}".format(r, m) for m in members if m < 2 for r in runs]',
                         ['Run: 00, Member00', 'Run: 01, Member00',
                          'Run: 00, Member01', 'Run: 01, Member01', ],
                         members=range(0, 3), runs=[0, 1])


if __name__ == '__main__':
    unittest.main()
