#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import re, importlib
import vortex
from unittest import TestCase, main


class utImport(TestCase):

    def test_pyVersion(self):
        sh = vortex.sh()
        self.assertTrue(sh.python > '2.7')

    def test_importModules(self):
        sh = vortex.sh()
        for modname in sh.vortex_modules():
            print '>', modname
            self.assertTrue(importlib.import_module(modname))


if __name__ == '__main__':
    main()
    vortex.exit()


def get_test_class():
    return [ utImport ]
