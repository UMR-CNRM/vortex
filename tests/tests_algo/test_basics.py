import sys
import unittest

from bronx.fancies.loggers import unittestGlobalLevel

import vortex
from vortex.algo.components import Expresso, AlgoComponentError

tloglevel = 'ERROR'


@unittestGlobalLevel(tloglevel)
class TestAlgoBasicsClass(unittest.TestCase):

    @staticmethod
    def _algo_fixup(algo):
        algo.ticket = vortex.sessions.current()
        algo.context = algo.ticket.context
        algo.system = algo.context.system

    def _new_expresso(self, ** kwargs):
        exp = Expresso(engine="exec", **kwargs)
        self._algo_fixup(exp)
        return exp

    def test_expresso(self):
        exp1 = self._new_expresso(interpreter='python')
        self.assertEqual(exp1._actual_interpreter, 'python')
        exp1 = self._new_expresso(interpreter='current')
        self.assertEqual(exp1._actual_interpreter, sys.executable)
        exp1 = self._new_expresso(interpreter='current',
                                  interpreter_path='/tmp/not_existing_file_jfgyfu19a4')
        with self.assertRaises(ValueError):
            self.assertEqual(exp1._actual_interpreter, '')
        exp1 = self._new_expresso(interpreter='python',
                                  interpreter_path='/tmp/not_existing_file_jfgyfu19a4')
        with self.assertRaises(AlgoComponentError):
            self.assertEqual(exp1._actual_interpreter,
                             '/tmp/not_existing_file_jfgyfu19a4')
        exp1 = self._new_expresso(interpreter='python',
                                  interpreter_path=sys.executable)
        self.assertEqual(exp1._actual_interpreter, sys.executable)


if __name__ == "__main__":
    unittest.main(verbosity=2)
