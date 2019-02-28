# -*- coding: utf-8 -*-

"""
A Unit-Test facility that creates a large number of ResourceHandlers and checks
that the generated location are unchanged compared to a reference run.

* The YAML ResourceHandlers definitions are stored under: tests/data/namestest
* A dump of a few Genv needed in some case are stored under: tests/data/namestest_register
* The reference data are stored under: tests/data/namestest_results.

The idea is to mimic the Olive/DSI behaviour: Therefore the usual footprint's
defaults are used (date, cutoff, ...).

In the ResourceHandlers definition files, the footprints.util.expand method
is used in order to create a large number of footprints.

This package can be run as a Python's unittest using nose. Otherwise, a
command-line is provided (project/bin/test_names_cli.py). The command-line
utility allows to generate the reference data.
"""

from __future__ import print_function, division, absolute_import, unicode_literals
