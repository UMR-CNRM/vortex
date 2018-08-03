#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This example shows how to use the glob function in Vortex.

Ok 20180801 - GR
"""

from __future__ import print_function, division, unicode_literals, absolute_import

import pprint

import vortex

# Initialize environment for examples
t = vortex.ticket()
sh = t.sh
e = t.env

# Change the work directory
sh.chdir(e.HOME)

# List all files and directories in the HOME of the current server
my_files_1 = sh.glob("*")
pprint.pprint(my_files_1)

# List all files which have "tmp" in their name
my_files_2 = sh.glob("*tmp*")
pprint.pprint(my_files_2)

# List the contents of the tmp directory, if it exists
my_files_3 = sh.glob("tmp/*")
pprint.pprint(my_files_3)
