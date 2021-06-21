# -*- coding: utf-8 -*-

"""
This example creates a simple namelist on the fly, and manipulates it.
It should run everywhere.

Ok 20180731 - GR
"""

from __future__ import absolute_import, division, print_function, unicode_literals

# load the packages used in this example
import pprint

import common
import vortex
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


# create a simple namelist
script = r"""
&NADIRS
    NDIFFM1=30,
    CNAMEBASE='surf',
/
&NANBOB
    NBSYNOP=20000,
    NBTESAC=400,
/
&TEST
    FILE=__FILE__,
/
"""

# write this namelist into a file using Vortex
namelist_name = "my_namelist"
namelist_container = toolbox.proxy.container(local=namelist_name, actualfmt="ascii")
namelist_container.write(script)
namelist_container.close()

# check that it has effectively been written and change the file permissions
print("The contents of the namelist is:")
pprint.pprint(sh.cat(namelist_name))
sh.wperm(namelist_name, force=True)
print("The contents of the current directory is:")
pprint.pprint(sh.dir())

# create a ResourceHandler corresponding to this namelist
namelist_rh = toolbox.rload(
    kind   = "namelist",
    model  = "arome",
    local  = "fort.4",
    remote = sh.path.join(working_directory, namelist_name)
)[0]
namelist_rh.get()

# set a macro in the namelist
namelist_rh.contents.setmacro("FILE", 'toto.txt')
namelist_rh.save()
print("The contents of the namelist is:")
pprint.pprint(sh.cat(namelist_rh.container.filename))

# add a block and a variable into the namelist
my_newblock = namelist_rh.contents.newblock(name="TEST2")
my_newblock["TEST"] = "toto"
namelist_rh.save()
print("The contents of the namelist is:")
pprint.pprint(sh.cat(namelist_rh.container.filename))

# rename a block
namelist_rh.contents.mvblock("TEST2", "TEST3")
namelist_rh.save()
print("The contents of the namelist is:")
pprint.pprint(sh.cat(namelist_rh.container.filename))

# remove a block
del namelist_rh.contents["TEST3"]
namelist_rh.save()
print("The contents of the namelist is:")
pprint.pprint(sh.cat(namelist_rh.container.filename))

# a last directory content listing
pprint.pprint(sh.dir())
