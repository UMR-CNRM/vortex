# -*- coding: utf-8 -*-

"""
Get an analysis using the Olive provider.

The namespace used here is olive.multi.fr, associated to a multistore: if the
resource is not found in the cache, it will be retrieved from the archive and
a copy will be cached to speed up later access.

Can be launched anywhere provided that ftget/ftput (via the .netrc)
or ftserv on super-computers (via ftmotpass) are configured.

The experiment chosen does not always exists and should be changed in order
to describe an existing resource.


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
rundate = date.yesterday()

# define the resource
rh = toolbox.rload(
    # Ressource
    kind       = 'analysis',
    date       = rundate,
    cutoff     = "production",
    model      = "arome",
    geometry   = "franmgsp",
    # Provider
    block      = "minim",
    namespace  = 'olive.multi.fr',
    experiment = "AAAA",
    vapp       = "[model]",
    vconf      = "3dvarfr",
    # Container
    local      = "analysis.fa"
)[0]

print(rh.complete)
print(rh.location())
print(rh.locate())
print(rh.idcard())

# get the resource
print(rh.get())
