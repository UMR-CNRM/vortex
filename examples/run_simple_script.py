#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
This example runs a simple Hello world script, created on the fly.
It should run everywhere.

Ok 20180731 - GR
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import pprint

import common
import vortex
from vortex import toolbox

# Prevent IDEs from removing seemingly unused imports
assert any([common, ])


# Set up the Vortex environment
t = vortex.ticket()
sh = t.sh
e = t.env

# Change the working directory
working_directory = sh.path.join(e.HOME, "tmp", "vortex_examples_tmpdir")
sh.cd(working_directory, create=True)
print("The current path is: {}".format(sh.pwd()))

# Create a simple script
script = r"""#!/usr/bin/python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import pprint

print("Hello world !")
my_path = os.getcwd()
print("The current path is {}".format(my_path))
print("The directory contains:")
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
    kind     = "script",
    language = "python",
    local    = "script.py",
    remote   = sh.path.join(working_directory, script_name)
)[0]

# Run the script in a temporary directory
with sh.cdcontext("running_directory", create=True):
    print("The current path is: {}".format(sh.pwd()))
    script_rh.get()
    print("The content of the current directory is:")
    pprint.pprint(sh.dir())
    algo = toolbox.algo(
        engine      = "exec",
        interpreter = "python",
    )
    algo.run(script_rh)

# Tidy up: remove the working directory
pprint.pprint(sh.dir())
sh.rmall(working_directory)
