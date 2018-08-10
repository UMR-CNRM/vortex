#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This example shows how to use the glob function in Vortex.

Ok 20180801 - GR
"""

from __future__ import print_function, division, unicode_literals, absolute_import

import pprint

import vortex
import common
from vortex import toolbox
from bronx.stdtypes.date import Time

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

# Change once again the work directory
workdirectory = '/'.join([e.HOME, "tmp", "Vortex"])
if not sh.path.isdir(workdirectory):
    sh.mkdir(workdirectory)
sh.chdir(workdirectory)

# Check what is in this directory and clean unused files and subdirectories
print("\nThe current path is: {}".format(sh.pwd()))
print("\nThe contents of the current directory is:")
pprint.pprint(sh.dir())
sh.rmall("*")

# Create a first simple file
file_name = "my_file"
file_container = toolbox.proxy.container(local=file_name, actualfmt="ascii")
file_container.write("A very simple file with nearly nothing in.")
file_container.close()

# Duplicate this file
for i in range(0, 20, 5):
    for j in range(i, 15, 3):
        sh.cp(file_name, ".".join([file_name, str(i), str(Time(j))]))

# List all the file in the directory
print("\nThe contents of the current directory is:")
pprint.pprint(sh.dir())

# Get the files of the directory
print("\nPrint the files that have a name formatted as follow: my_file.\d+.\d+:\d+")
rh_list1 = toolbox.rload(
    # Resource
    unknown = True,
    nickname = ["[glob:term]_[glob:num]"],
    # Container
    local = "my_file.{glob:num:\d+}.{glob:term:\d+:\d+}",
    # Provider
    block = "my_block",
    namespace = "vortex.cache.fr",
    experiment = "my_experiment@{}".format(e.USER),
    vapp = "my_vapp",
    vconf = "my_vconf"
)
for rh in rh_list1:
    print(" -> ".join([rh.container.filename, rh.resource.nickname]))

print("\nPrint the files that have a name formatted as follow: my_file.\d.\d+:\d+")
rh_list2 = toolbox.rload(
    # Resource
    unknown = True,
    nickname = ["[glob:term]_[glob:num]"],
    # Container
    local = "my_file.{glob:num:\d}.{glob:term:\d+:\d+}",
    # Provider
    block = "my_block",
    namespace = "vortex.cache.fr",
    experiment = "my_experiment@{}".format(e.USER),
    vapp = "my_vapp",
    vconf = "my_vconf"
)
for rh in rh_list2:
    print(" -> ".join([rh.container.filename, rh.resource.nickname]))

# Tidy the work directory
print("\nThe contents of the current directory is:")
pprint.pprint(sh.dir())
sh.rmall("*")
