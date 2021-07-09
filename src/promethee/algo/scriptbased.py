#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Promethee custom Algo Component
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from footprints import FPDict
from vortex.algo.components import Expresso

#: No automatic export
__all__ = []


class PrometheeAlgo(Expresso):
    """PrometheeAlgo : This algo component is used for executing Python scripts
    with args, like a common Python script execution in command line.

    For instance : I have a Python3.7 script 'toto.py' which arguments are
    '-f, --foo', '-b,--bar'. I would usually execute that script with :
    >>> python3.7 toto.py --foo 42 --bar 51

    In Vortex, I would get my script as a promethee.data.executable.PrometheeScript,
    and executing it this way :
    >>> tb_script = toolbox.executable(
    ...     kind        = "promethee_script",
    ...     language    = "python",
    ...     remote      = "path_to_my_script.py",
    ...     local       = "toto.py",
    ... )[0]
    >>> tb_algo = toolbox.algo(
    ...     kind        = "promethee_algo",
    ...     interpreter = "python3.7",
    ...     cmdline     = {"foo":42, "bar":51},   
    ... )
    >>> tb_algo.run(tb_script)

    This Algo Component is primarily designed for a Promethee usage, but it should
    fit any Python script execution.

    Inheritance:
        vortex.algo.components.Expresso

    Attrs:
        kind          (str) : Algo kind. Must be 'promethee_algo'.
        interpreter   (str) : Interpreter to use for executing scripts.
        engine        (str) : Optionnal engine, default is 'exec'.
        extendpypath (list) : The list of things to be prepended in the python's path.
            The added paths must lead to python packages used by the script to execute.
            Default is [].
        timeout       (int) : Default timeout (in sec.) used when waiting for
            an expected resource. Default is 180.
        cmdline      (dict) : Optionnal command line arguments to pass on to
            the script to execute.

    """
    _footprint = dict(
        info = "Algo Component for executing Python scripts with args.",
        attr = dict(
            kind = dict(
                values      = ["promethee_algo"],
            ),
            interpreter = dict(
                info        = "The interpreter needed to run the script.",
            ),
            engine = dict(
                optional    = True,
                values      = ["exec", "launch",],
                default     = "exec",
            ),
            cmdline=dict(
                info        = "The command line arguments to pass on to the script.",
                type        = FPDict,
                default     = FPDict({"nproc" : 32}),
                optional    = True,
            ),
        )
    )

    def spawn_command_options(self):
        """
        Method called by the script resource to spawn the command line arguments.
        """
        return self.cmdline
