#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Promethee executables
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.data.executables import Script

#: No automatic export
__all__ = []


class PrometheeScript(Script):
    _footprint = dict(
        attr=dict(
            kind=dict(
                optional=False,
                values=['promethee_script'],
            ),
        ),
    )

    def command_line(self, **kwargs):
        cmdline = ' '.join(
            ["--{} {}".format(k, v) for k, v in kwargs.items()]
        )
        print(cmdline)
        return cmdline