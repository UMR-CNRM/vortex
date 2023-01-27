#!/usr/bin/env python3

"""
Get an analysis using the remote provider.

This example gets an analysis from Hendrix using its explicit path.
The specific attributes are:
- remote: the path on the target server
- hostname: the name of the target server, if it is not the current one
- tube: the protocol to use to get the resource (ftp, scp...)

To get a resource from the current server, using its explicit path,
the only attribute needed is `remote`.

The namespace used is [suite].archive.fr, the only one available to everyone.

Can be launched anywhere provided that ftget/ftput (via the .netrc)
or ftserv on super-computers (via ftmotpass) are configured.

Ok 20180731 - GR
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
rundate = date.Date("201801010000")

# define the resource
rh = toolbox.rload(
    # Ressource
    kind     = 'analysis',
    date     = rundate,
    cutoff   = "assim",
    model    = "arome",
    geometry = "franmgsp",
    # Provider
    remote   = "/home/m/mxpt/mxpt001/arome/oper/assim/2018/01/01/r0/analyse",
    tube     = "ftp",
    hostname = "hendrix.meteo.fr",
    # Container
    local    = "analysis.fa"
)[0]

print(rh.complete)
print(rh.location())
print(rh.locate())
print(rh.idcard())

# get the resource
print(rh.get())
