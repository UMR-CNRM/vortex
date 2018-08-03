#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This example show how to use a hook on a file get.

Ok 20180801 - GR
"""

from __future__ import print_function, division, unicode_literals, absolute_import

# Load useful packages for the examples

from bronx.stdtypes import date
import footprints as fp

import vortex
from vortex import toolbox
import common

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
    # This is a very simple example. Of course, one can achieve many things
    # working with **t** (the current session) and **rh** (the "hooked" 
    # ResourceHandler object)...
    dname = rh.container.localpath()
    print("The size of the file get is: {}".format(t.sh.size(dname)))


# Define the resource handler
print('Example #1')
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
    local      = "test1.json"
)[0]

print('Complete ?', rh.complete)
print('Location :', rh.location())
print('Locate :  ', rh.locate())
print('IdCard:')
print(rh.idcard())

# Get the resource
print('Get ?', rh.get())

# Use the hook defined above
print('MyHook Test:')
my_hook(t, rh)

# The other way, define the resource handler and automatically call the hook

# Define the resource handler
print()
print('Example #2')
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
    local      = "test2.json",
    # Hooks
    hook_size  = fp.FPTuple([my_hook, ()])  # No extra arguments provided
)[0]

print('IdCard (with hook):')
print(rh.idcard())

# Get the resource
print('Get (with hook) ?', rh.get())
# The Hook was automatically called during get

# Using toolbox.input + now =True, the syntax is simpler

# Define the resource handler
print()
print('Example #3')
print('Using toolbox.input')
rh = toolbox.input(
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
    local      = "test3.json",
    # Hooks
    hook_size  = (my_hook, ),  # No extra arguments provided
    # Input options
    now        = True,  # The get will be done automatically
    verbose    = True,  # Nice prints...
)[0]
