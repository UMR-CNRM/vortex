#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Get a namelist file from the Genv provider.

Can be launched anywhere where Gget or a Gget light are available
(on super-computer for instance).

Ok 20180731 - GR
"""

from __future__ import print_function, division, unicode_literals, absolute_import

# Load useful packages for the examples
import common
import olive
import vortex
from vortex import toolbox

# prevent IDEs from removing seemingly unused imports
assert any([common, olive])


# #### Initializations

# Initialize environment for examples
t = vortex.ticket()
sh = t.sh
e = t.env

# Change the work directory
workdirectory = '/'.join([e.HOME, "tmp", "Vortex"])
if not sh.path.isdir(workdirectory):
    sh.mkdir(workdirectory)
sh.chdir(workdirectory)


# #### Getting a resource using the Genv provider

# Define the resource
rh = toolbox.rload(
    # Ressource
    kind   = "namelist",
    model  = "arpege",
    source = "namelistfc",
    # Provider
    genv   = "cy42_op2.68",
    # Container
    local  = "namelistfc"
)[0]

print(rh.complete)
print(rh.location())
print(rh.locate())
print(rh.idcard())

# Get the resource
print(rh.get())
