#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers

from vortex.data.executables import Script

import iga.util.bpnames as bp
from gco.syntax.stdattrs import gvar

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)

class Script_Python(Script):

    _footprint = [
        gvar,
        dict(
            attr = dict(
                kind = dict(
                    values = ['prod','manager','traitement','amendements']
                ),
                gvar = dict(
                    default = 'ALPHA_EXE_[kind]',
                ),
                vconf = dict(
                    values = ['france_jj1','france_j2j3']
                ),
            )
        )
    ]

    def command_line(self, **kw):
	    return kw['command_line']

class Script_Shell(Script):

    """ This script launch alpha prod and amandements """

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
                    values = ['france_jj1','france_j2j3']
                ),

            )
        )
    ]

    def command_line(self, **kw):
        return kw['command_line']

