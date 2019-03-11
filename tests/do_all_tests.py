#!/usr/bin/env python
# -*- coding: utf-8 -*-

# The default interpreter is used but feel free to run this with either Python2.7
# or Python3.5 (and above)

from __future__ import print_function, absolute_import, unicode_literals, division
import six

import codecs
import os
import sys
import unittest


def build_suite():
    """Load the test classes."""
    outsuite = unittest.TestLoader().discover('.')
    return outsuite


if __name__ == '__main__':
    # Jump into the test directory
    os.chdir(os.path.dirname(os.path.realpath(__file__)))

    if six.PY2:
        # Ensure that stdout is fine...
        sys.stdout = codecs.getwriter('utf8')(sys.stdout)

    suite = build_suite()
    results = unittest.TextTestRunner(verbosity=2, buffer=True).run(suite)

    if results.failures or results.errors:
        exit(1)
