#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
This example runs a simple Hello world script, created on the fly.
It should run everywhere.

Ok 20210621 - LFM
Ok 20200724 - PL python3 compatibility
Ok 20180731 - GR
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import sys

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
print("Working directory: {}".format(sh.pwd()))

# Create a script on the fly for the demo to be self-contained
script = ('#!{!s}'.format(sys.executable) + r"""
# -*- coding: utf-8 -*-

from __future__ import absolute_import, division, print_function, unicode_literals

import os
import pprint
import sys

print("Hello world !")
my_path = os.getcwd()
print("Current path: {}".format(my_path))
print("Directory content:")
pprint.pprint(os.listdir(my_path))
print("\nCommand line arguments:", sys.argv[1:])
""").encode('utf-8')

# Write this script into an executable file using Vortex
script_name = "Hello_world.py"
script_container = toolbox.proxy.container(local=script_name, actualfmt="ascii")
script_container.write(script)
script_container.close()

# Check that the script has truly been written and change its rights
print("\nScript {}:".format(script_name))
print('\t| ' + '\n\t| '.join(sh.cat(script_name)))
sh.xperm(script_name, force=True)
print("\nDirectory content:")
sh.dir(output=False)
print()

# Create a ResourceHandler corresponding to this script
script_rh = toolbox.executable(
    language = "python",
    local    = "script.py",
    remote   = sh.path.join(working_directory, script_name),
    rawopts  = '-v -fast',
)[0]

# Run the script in a temporary directory
with sh.cdcontext("running_directory", create=True):
    print("Current path: {}".format(sh.pwd()))
    script_rh.get()
    print("Current directory content:")
    sh.dir(output=False)
    print()
    algo = toolbox.algo(
        engine      = "exec",
        interpreter = "python",
    )
    algo.run(script_rh)

# Tidy up: remove the working directory
sh.rmall(working_directory)
