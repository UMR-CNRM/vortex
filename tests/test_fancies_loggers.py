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
            clevel = loggers.default_console.level
            loggers.default_console.setLevel('WARNING')
            lg.info("Will this be replayed ???")
            lg.removeHandler(sl)
            lg.info("This should not be replayed")
            self.assertEqual(len(stack), 1)
            for r in stack:
                lg.handle(r)
        finally:
            loggers.default_console.setLevel(clevel)


if __name__ == '__main__':
    main(verbosity=2)
