#!/usr/bin/env python3

import os
import unittest


def build_suite():
    """Load the test classes."""
    outsuite = unittest.TestLoader().discover('.')
    return outsuite


if __name__ == '__main__':
    # Jump into the test directory
    os.chdir(os.path.dirname(os.path.realpath(__file__)))

    suite = build_suite()
    results = unittest.TextTestRunner(verbosity=2, buffer=True).run(suite)

    if results.failures or results.errors:
        exit(1)
