# -*- coding: utf-8 -*-

"""
Various Resources for executables used in demo jobs.
"""

from __future__ import print_function, absolute_import, division, unicode_literals


from vortex.data.executables import Script
from gco.syntax.stdattrs import gvar


class StdpostScript(Script):
    """An executable that computes some post-processing on a file."""

    _footprint = [
        gvar,
        dict(
            info = 'Executable that computes some post processing',
            attr = dict(
                kind = dict(
                    values   = ['demo_ppscript', ],
                    optional = False,
                ),
                gvar=dict(
                    default='[model]_demo_ppscript',
                ),
                language = dict(
                    default = 'bash',
                    values = ['bash'],
                    optional = True,
                )
            )
        )
    ]

    @property
    def realkind(self):
        return 'demo_ppscript'

    def command_line(self, **opts):
        """Returns optional attribute :attr:`rawopts`."""
        extra_args = []
        if 'todo' in opts:
            extra_args.append(opts['todo'])  # The name of the file to work on
        return ' '.join([super(StdpostScript, self).command_line(**opts), ] + extra_args)
