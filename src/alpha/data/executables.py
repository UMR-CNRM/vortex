#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TODO: Module documentation
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers

from vortex.data.executables import Script

from gco.syntax.stdattrs import gvar

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class AlphaPythonScript(Script):
    """TODO: Class documentation."""

    _footprint = [
        gvar,
        dict(
            attr = dict(
                kind = dict(
                    values = ['prod', 'manager', 'traitement', 'amendements']
                ),
                language = dict(
                    default = 'python',
                ),
                gvar = dict(
                    default = 'ALPHA_EXE_[kind]',
                ),
                vconf = dict(
                    values = ['france_jj1', 'france_j2j3']
                ),
            )
        )
    ]

    def command_line(self, **kw):
        return kw['command_line']


class AlphaShellScript(Script):
    """This script launch alpha prod and amandements."""

    _footprint = [
        gvar,
        dict(
            attr = dict(
                kind = dict(
                    values = ['launch']
                ),
                gvar = dict(
                    default = 'ALPHA_SRC_[kind]',
                ),
                vconf = dict(
                    values = ['france_jj1', 'france_j2j3']
                ),

            )
        )
    ]

    def command_line(self, **kw):
        return kw['command_line']