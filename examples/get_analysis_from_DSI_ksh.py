# -*- coding: utf-8 -*-

"""
Get an analysis using the Old DSI ksh provider.

The namespace used is [suite].archive.fr, the only one available to everyone.

Can be launched anywhere provided that ftget/ftput (via the .netrc)
or ftserv on super-computers (via ftmotpass) are configured.

Ok 20180731 - GR
"""

from __future__ import absolute_import, division, print_function, unicode_literals


# load the packages used in this example
import common
import olive
import vortex
from bronx.stdtypes import date
from vortex import toolbox

# prevent IDEs from removing seemingly unused imports
assert any([common, olive])


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
    kind      = 'analysis',
    date      = rundate,
    cutoff    = "assim",
    model     = "arome",
    geometry  = "franmgsp",
    # Provider
    namespace = '[suite].multi.fr',
    suite     = "oper",
    vapp      = "[model]",
    vconf     = "3dvarfr",
    # Container
    local     = "analysis.fa"
)[0]

print(rh.complete)
print(rh.location())
print(rh.locate())
print(rh.idcard())

# get the resource
print(rh.get())
