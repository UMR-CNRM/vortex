#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This example show how to use a hook on a file get.

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


# Define a hook which will print the size of the file
def my_hook(t, rh):
    dname = rh.container.localpath()
    print("The size of the file get is: {}".format(t.sh.size(dname)))


# Define the resource
rh = toolbox.rload(
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

print(rh.complete)
print(rh.location())
print(rh.locate())
print(rh.idcard())

# Get the resource
print(rh.get())

# Use the hook defined
my_hook(t, rh)
