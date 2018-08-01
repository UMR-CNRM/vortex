#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This example aims at dealing with glob function using via Vortex.

Ok 20180801 - GR
"""

# Load useful packages for the examples
from __future__ import print_function, division, unicode_literals, absolute_import

import pprint

import vortex


# Initialize environment for examples
t = vortex.ticket()
sh = t.sh
e = t.env

# Change the work directory
sh.chdir(e.HOME)

# Print all the files and directories that are in the HOME of the current server
my_files_1 = sh.glob("*")
pprint.pprint(my_files_1)

# Print all the files which have "tmp" in their names
my_files_2 = sh.glob("*tmp*")
pprint.pprint(my_files_2)

# Print the content of the tmp directory, if it exists
my_files_3 = sh.glob("tmp/*")
pprint.pprint(my_files_3)
