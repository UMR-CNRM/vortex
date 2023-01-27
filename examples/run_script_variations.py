#!/usr/bin/env python3

"""
This example shows how to customize both the command line arguments passed to a
script, and the interpreter to use. It extends the example run_simple_script.py
(read it first) and should also run everywhere (python3.8 may be changed to any
other version if it is not available).

Ok 20200804 - PL
"""

import pprint

import common
import vortex
from footprints import FPDict
from footprints.util import mktuple
from vortex import toolbox
from vortex.algo.components import Expresso
from vortex.data.executables import Script

# Prevent IDEs from removing seemingly unused imports
assert any([common, ])

# keep stdout (partially) in sync with the logger's output for clarity
import sys
sys.stderr = sys.stdout


class UserDefinedAlgo(Expresso):
    """Add to Expresso the capability to

        - handle command line arguments
        - choose our own interpreter
    """
    _footprint = dict(
        attr=dict(
            kind=dict(
                values   = ['user_defined_algo'],
            ),
            cmdline=dict(
                type     = FPDict,
                default  = FPDict({'quick': 42, 'urgency': 'asap'}),
                optional = True,
            ),
            interpreter=dict(
                info     = 'The interpreter needed to run the script.',
                values   = ['python3.8']
            ),
        )
    )

    def spawn_command_options(self):
        print('In UserDefinedAlgo::spawn_command_options - self.cmdline is',
              pprint.pformat(self.cmdline)
              )
        return self.cmdline


class UserDefinedScript(Script):
    """Class GnuScript enforces a GNU syntax: --opt value1 value2.
       We define here our own variant: -opt=value1,value2.
    """
    _footprint = dict(
        attr=dict(
            kind=dict(
                optional = False,
                values   = ['user_defined_script'],
            ),
        ),
    )

    def command_line(self, **opts):
        """Build the command line arguments from the dictionary
           transmitted by the AlgoComponent.
        """
        args = ' '.join(
            ['-' + k + '=' + ','.join([str(x) for x in mktuple(v)])
             for k, v in opts.items()]
        )
        return "-method=UserDefinedScript " + args


# Set up the Vortex environment
t = vortex.ticket()
sh = t.sh
e = t.env
print("VORTEX runs with python", sys.version_info)

# Change the top-level working directory
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
print("\nCommand line arguments:", sys.argv[1:])
print("\nVersion of the interpeter:", sys.version_info)
""").encode('utf-8')

# Write this script into an executable file using Vortex
script_name = "Hello_world.py"
script_container = toolbox.proxy.container(local=script_name, actualfmt="ascii")
script_container.write(script)
script_container.close()
sh.xperm(script_name, force=True)

# Run in a temporary directory
with sh.cdcontext("running_directory", create=True):
    # Use our user defined Algo Component
    algo = toolbox.algo(
        kind        = 'user_defined_algo',
        engine      = "exec",
        interpreter = "python3.8",
        cmdline     = dict(has_arguments='yes_transmitted'),
    )
    assert isinstance(algo, UserDefinedAlgo)

    # Create a ResourceHandler to get the script
    script_rh = toolbox.executable(
        language = "python",
        local    = "script.py",
        remote   = sh.path.join(working_directory, script_name),
        kind     = "gnuscript",
    )[0]
    script_rh.get()
    assert isinstance(script_rh.resource, vortex.data.executables.GnuScript)

    # run 1
    algo.cmdline['jungling_material'] = 'apples'
    algo.run(script_rh)

    # run2 with other arguments
    del algo.cmdline['jungling_material']
    algo.cmdline['thinking_methods'] = ('squeeze_brain', 'ask_a_friend')
    algo.run(script_rh)

    # Same thing with our specific way of formatting arguments
    script_rh = toolbox.executable(
        language = "python",
        local    = "script.py",
        remote   = sh.path.join(working_directory, script_name),
        kind     = "user_defined_script",
    )[0]
    script_rh.get()
    assert isinstance(script_rh.resource, UserDefinedScript)

    # same cmdline as run2 above
    algo.run(script_rh)

# Tidy up
sh.rmall(working_directory)
