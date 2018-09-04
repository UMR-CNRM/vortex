#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This example get simple resources and put it at different places using the
available providers.

Ok 20180801 - GR
"""

from __future__ import print_function, division, unicode_literals, absolute_import


# Load useful packages for the examples
import common
import vortex
from bronx.stdtypes import date
from vortex import toolbox

# prevent IDEs from removing seemingly unused imports
assert any([common, ])


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


# #### Getting a resource using the Vortex provider

# Define the date
rundate = date.yesterday() + date.Period("PT3H")

# Define the resource
rh1 = toolbox.rload(
    # Ressource
    kind       = 'mbsample',
    nbsample   = 12,
    date       = rundate,
    cutoff     = "production",
    model      = "arome",
    # Provider
    block      = "clustering",
    namespace  = 'vortex.archive.fr',
    experiment = "OPER",
    vapp       = "arome",
    vconf      = "pefrance",
    # Container
    local      = "test.json"
)[0]

print(rh1.complete)
print(rh1.location())
print(rh1.locate())
print(rh1.idcard())

# Get the resource
print(rh1.get())


# Put the resource in the Olive tree of files
rh2 = toolbox.rload(
    # Ressource
    kind       = 'mbsample',
    nbsample   = 12,
    date       = rundate,
    cutoff     = "production",
    model      = "arome",
    # Provider
    block      = "clustering",
    namespace  = 'vortex.cache.fr',
    experiment = "0000",
    vapp       = "arome",
    vconf      = "pefrance",
    # Container
    local      = "test.json"
)[0]

print(rh2.put())
