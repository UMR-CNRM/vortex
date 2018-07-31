#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Get an analysis using the remote provider.
This example get an analysis from Hendrix using its explicit path.
The different attributes used are:
- remote: the path on the target server
- hostname: the name of the target server, if it is not the current one
- tube: the tube used to get the resource (ft, scp...)
To get a resource from the current server using its explicit path, the only attribute needed is remote.

The namespace used is [suite].archive.fr, only this one is available for everyone.

Can be launched anywhere provided that ftget/ftput (via the .netrc)
or ftserv on super-computers (via ftmotpass) are configured).

Ok 20180731 - GR
"""

##### Initializations
# Load useful packages for the examples
from __future__ import print_function, division, unicode_literals, absolute_import


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
rundate = date.Date("201801010000")
# Define the resource
rh = toolbox.rload(
    # Ressource
    kind = 'analysis',
    date=rundate,
    cutoff = "assim",
    model = "arome",
    geometry="franmgsp",
    # Provider
    remote="/home/m/mxpt/mxpt001/arome/oper/assim/2018/01/01/r0/analyse",
    tube="ftp",
    hostname="hendrix.meteo.fr",
    # Container
    local = "analysis.fa"
)
print(rh.complete)
print(rh.location())
print(rh.locate())
print(rh.idcard())
# Get the resource
print(rh.get())
