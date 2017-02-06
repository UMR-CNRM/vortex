#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from unittest import TestCase, main

from footprints import loggers


class utLogger(TestCase):

    def test_logger_slurp(self):
        l = loggers.getLogger('a_very_strange_test_only_logger_12345')
        l.setLevel('INFO')
        stack = list()
        sl = loggers.SlurpHandler(stack)
        l.addHandler(sl)
        l.info("Will this be replayed ???")
        l.removeHandler(sl)
        l.info("This should not be replayed")
        self.assertEqual(len(stack), 1)
        for r in stack:
            l.handle(r)

if __name__ == '__main__':
    main(verbosity=2)
