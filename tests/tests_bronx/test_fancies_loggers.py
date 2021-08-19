# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from unittest import TestCase, main

from bronx.fancies import loggers


class utLogger(TestCase):

    def test_logger_slurp(self):
        lg = loggers.getLogger('a_very_strange_test_only_logger_12345')
        lg.setLevel('INFO')
        stack = list()
        sl = loggers.SlurpHandler(stack)
        lg.addHandler(sl)
        try:
            clevel = loggers.console.level
            loggers.console.setLevel('WARNING')
            lg.info("Will this be replayed ???")
            lg.removeHandler(sl)
            lg.info("This should not be replayed")
            self.assertEqual(len(stack), 1)
            for r in stack:
                lg.handle(r)
        finally:
            loggers.console.setLevel(clevel)


if __name__ == '__main__':
    main(verbosity=2)
