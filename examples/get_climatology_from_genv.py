#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Get a climatology file from the Genv provider.

Can be launched anywhere where Gget or a Gget light are available
(on super-computer for instance).

Ok 20180731 - GR
"""

from __future__ import print_function, division, unicode_literals, absolute_import


# #### Initializations

# Load useful packages for the examples
import common
import olive
import vortex
from bronx.stdtypes import date
from vortex import toolbox

# prevent IDEs from removing seemingly unused imports
assert any([common, olive])

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

runmonth = date.Month("201801010000")

# Define the resource
rh = toolbox.rload(
    # Ressource
    kind     = 'clim_bdap',
    month    = runmonth,
    geometry = "EURW1S40",
    model    = "arome",
    # Provider
    genv     = "cy42_op2.68",
    # Container
    local    = "Const.clim.[geometry::area].[month]"
)[0]

print(rh.complete)
print(rh.location())
print(rh.locate())
print(rh.idcard())

# Get the resource
print(rh.get())
