#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This example run a simple Hello world script, created on the fly.
It should run everywhere.

Ok 20180731 - GR
"""

# Load useful packages for the examples
from __future__ import print_function, division, unicode_literals, absolute_import

import pprint

import vortex
import common
from vortex import toolbox


# Initialize environment for examples
t = vortex.ticket()
sh = t.sh
e = t.env

# Change the work directory
workdirectory = '/'.join([e.HOME, "tmp", "Vortex"])
if not sh.path.isdir(workdirectory):
    sh.mkdir(workdirectory)
sh.chdir(workdirectory)

# Check what is in this directory and clean unused files and subdirectories
print("The current path is: {}".format(sh.pwd()))
print("The content of the current directory is:")
pprint.pprint(sh.dir())
sh.rmall("*")

# Create a simple script
script = r"""#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import print_function, division, unicode_literals, absolute_import

import os
import pprint

print("Hello world !")
my_path = os.getcwd()
print("The current path is {}".format(my_path))
print("The repository contains:")
pprint.pprint(os.listdir(my_path))
"""

# Write this script into a file using Vortex
script_name = "Hello_world.py"
script_container = toolbox.proxy.container(local=script_name, actualfmt="ascii")
script_container.write(script)
script_container.close()

# Check that it has trully been writen and change its rights
print("The content of the script is:")
pprint.pprint(sh.cat(script_name))
sh.xperm(script_name, force=True)
print("The content of the current directory is:")
pprint.pprint(sh.dir())

# Create a ResourceHandler corresponding to this script
script_rh = toolbox.executable(
    kind="script",
    language="python",
    local="script.py",
    remote= "/".join([workdirectory, script_name])
)[0]


# Run the script in a temporary directory
tmp_dir = "Test_Vortex"

with sh.cdcontext(tmp_dir, create=True):
    print("The current path is: {}".format(sh.pwd()))
    script_rh.get()
    print("The content of the current directory is:")
    pprint.pprint(sh.dir())
    algo = toolbox.algo(
        engine = "exec",
        interpreter = "python",
    )
    algo.run(script_rh)

# Tidy the work directory
pprint.pprint(sh.dir())
sh.rmall(tmp_dir + "/*")
sh.rmdir(tmp_dir)
sh.rmall("*")
