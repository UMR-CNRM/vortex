#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This example create a simple namelist on-the-fly and modify it.
It should run everywhere.

Ok 20180731 - GR
"""

# Load useful packages for the examples
from __future__ import print_function, division, unicode_literals, absolute_import

import pprint

import vortex
import common
from vortex import toolbox


# Initialize environment for examples
t = vortex.ticket()
sh = t.sh
e = t.env

# Change the work directory
workdirectory = '/'.join([e.HOME, "tmp", "Vortex"])
if not sh.path.isdir(workdirectory):
    sh.mkdir(workdirectory)
sh.chdir(workdirectory)

# Check what is in this directory and clean unused files and subdirectories
print("The current path is: {}".format(sh.pwd()))
print("The content of the current directory is:")
pprint.pprint(sh.dir())
sh.rmall("*")

# Create a simple namelist
script = r"""
&NADIRS
    NDIFFM1=30,
    CNAMEBASE='surf',
/
&NANBOB
    NBSYNOP=20000,
    NBTESAC=400,
/
&TEST
    FILE=__FILE__,
/
"""

# Write this namelist into a file using Vortex
namelist_name = "my_namelist"
namelist_container = toolbox.proxy.container(local=namelist_name, actualfmt="ascii")
namelist_container.write(script)
namelist_container.close()

# Check that it has trully been writen and change its rights
print("The content of the namelist is:")
pprint.pprint(sh.cat(namelist_name))
sh.wperm(namelist_name, force=True)
print("The content of the current directory is:")
pprint.pprint(sh.dir())

# Create a ResourceHandler corresponding to this namelist
namelist_rh = toolbox.rload(
    kind="namelist",
    model="arome",
    local="fort.4",
    remote= "/".join([workdirectory, namelist_name])
)[0]
namelist_rh.get()

# Set a macro in the namelist
namelist_rh.contents.setmacro("FILE", 'toto.txt')
namelist_rh.save()
print("The content of the namelist is:")
pprint.pprint(sh.cat(namelist_rh.container.filename))

# Add a block and a variable in to the namelist
my_newblock = namelist_rh.contents.newblock(name="TEST2")
my_newblock["TEST"] = "toto"
namelist_rh.save()
print("The content of the namelist is:")
pprint.pprint(sh.cat(namelist_rh.container.filename))

# Rename a block
namelist_rh.contents.mvblock("TEST2", "TEST3")
namelist_rh.save()
print("The content of the namelist is:")
pprint.pprint(sh.cat(namelist_rh.container.filename))

# Remove a block
del namelist_rh.contents["TEST3"]
namelist_rh.save()
print("The content of the namelist is:")
pprint.pprint(sh.cat(namelist_rh.container.filename))

# Tidy the work directory
pprint.pprint(sh.dir())
sh.rmall("*")
