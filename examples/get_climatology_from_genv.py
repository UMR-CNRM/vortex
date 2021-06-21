# -*- coding: utf-8 -*-

"""
Get a climatology file from the Genv provider.

Can be launched anywhere where Gget or Gget light is available
(on super-computer for instance).

Ok 20200114 - NM + PL
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

# extract the month from a Date
runmonth = date.Month("201801010000")

# define the resource
rh = toolbox.rload(
    # Ressource
    kind      = 'clim_bdap',
    month     = runmonth,
    geometry  = "EURAT1S20",
    model     = "arome",
    # Provider
    genv      = "cy43t2_op2.15",
    gautofill = "True",
    # Container
    local     = "Const.clim.[geometry::area].[month]"
)[0]

print(rh.complete)
print(rh.location())
print(rh.locate())
print(rh.idcard())

# get the resource
print(rh.get())
