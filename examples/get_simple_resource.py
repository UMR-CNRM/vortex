#!/usr/bin/env python3

"""
This example gets a simple resource and puts it at a different place
in the cache by changing the provider.

Ok 20180801 - GR
"""

# load the packages used in this example
import common
import vortex
from bronx.stdtypes import date
from vortex import toolbox

# prevent IDEs from removing seemingly unused imports
assert any([common, ])


# set up the Vortex environment
t = vortex.ticket()
sh = t.sh
e = t.env

# change the working directory
working_directory = sh.path.join(e.HOME, "tmp", "vortex_examples_tmpdir")
sh.cd(working_directory, create=True)

# define the date
rundate = date.yesterday() + date.Period("PT3H")


# #### Getting a resource using the Vortex provider

# define the resource
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

# get the resource
print(rh1.get())


# put the resource in the cache under another experiment id
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
