#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Get an analysis using the Vortex provider.

The namespace used is vortex.multi.fr: if the resource is not found
in the cache, it will be retrieved from the archive and a copy will
be cached to speed up later access.

Can be launched anywhere provided that ftget/ftput (via the .netrc)
or ftserv on super-computers (via ftmotpass) are configured.

Ok 20180731 - GR
"""

from __future__ import absolute_import, division, print_function, unicode_literals


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
