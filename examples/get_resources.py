#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This example get simple resources and put it at different places using the
available providers.
"""

##### Initializations
# Load useful packages for the examples
from __future__ import print_function, division, unicode_literals, absolute_import

import pprint

import vortex
import common
from vortex import toolbox
from bronx.stdtypes import date

# Initialize environment for examples
t = vortex.ticket()
sh = t.sh
e = t.env

# Change the work directory
workdirectory = '/'.join([e.HOME, "tmp", "Vortex"])
if not sh.path.isdir(workdirectory):
    sh.mkdir(workdirectory)
sh.chdir(workdirectory)

##### Getting a resource using the Vortex provider
# Define the date
rundate = date.Date("201806200300")
# Define the resource
rh1 = toolbox.rh(
    # Ressource
    kind = 'mbsample',
    nbsample = 12,
    date=rundate,
    cutoff = "production",
    model = "arome",
    # Provider
    block = "clustering",
    namespace = 'vortex.archive.fr',
    experiment = "OPER",
    vapp = "arome",
    vconf = "pefrance",
    # Container
    local = "test1.json"
)
print(rh1.complete)
print(rh1.location())
print(rh1.locate())
print(rh1.idcard())
# Get the resource
print(rh1.get())
