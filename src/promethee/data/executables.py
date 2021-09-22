# -*- coding: utf-8 -*-

"""
Promethee executable script.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.data.executables import Script

#: No automatic export
__all__ = []


class PrometheeScript(Script):
    """Python script, which could be executed with command line arguments.

    This kind of executable resource can be properly executed using
    a :class:`promethee.algo.scriptbased.PrometheeAlgo`.

    For instance : I have a Python3.7 script 'toto.py' which arguments are
    '-f, --foo', '-b,--bar'. I would usually execute that script with:

    >>> python3.7 toto.py --foo 42 --bar 51

    In Vortex, I would get my script and executing it this way:

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

    * :class:`vortex.data.executables.Script`

    Attrs:

    * kind (str): Executable kind. Must be 'promethee_script'.
    * language (str): Script language. Must be 'python'.

    """
    _footprint = dict(
        info = "Python script, that could be executed with command line args.",
        attr = dict(
            kind = dict(
                optional    = False,
                values      = ['promethee_script'],
            ),
            language = dict(
                optional    = True,
                values      = ["python"],
                default     = "python",
            ),
        ),
    )

    def command_line(self, **kwargs):
        """Out of *kwargs*, create a command line to pass on to the script.

        It returns:

        * str: Command line to pass on to the script

        """
        cmdline = " ".join(
            ["--{} {}".format(key, value) for key, value in kwargs.items()]
        )
        return cmdline
