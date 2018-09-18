#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Get an analysis using the Vortex provider.

The namespace used is vortex.multi.fr: if the resource is not in the cache,
it will be searched for in the archive and a copy will be put in the cache.

Can be launched anywhere provided that ftget/ftput (via the .netrc)
or ftserv on super-computers (via ftmotpass) are configured).

Ok 20180731 - GR
"""

from __future__ import print_function, division, unicode_literals, absolute_import


# #### Initializations

# Load useful packages for the examples
import common
import vortex
from bronx.stdtypes import date
from vortex import toolbox

# prevent IDEs from removing seemingly unused imports
assert any([common, ])

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
rundate = date.yesterday()

# Define the resource
rh = toolbox.rload(
    # Ressource
    kind       = 'analysis',
    date       = rundate,
    cutoff     = "production",
    model      = "arome",
    geometry   = "franmgsp",
    # Provider
    block      = "minim",
    namespace  = 'vortex.multi.fr',
    experiment = "OPER",
    vapp       = "[model]",
    vconf      = "pifrance",
    # Container
    local      = "analysis.fa"
)[0]

print(rh.complete)
print(rh.location())
print(rh.locate())
print(rh.idcard())

# Get the resource
print(rh.get())
