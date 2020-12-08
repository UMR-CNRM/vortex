#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TODO: Module documentation
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers
from footprints import FPDict
from vortex.algo.components import Expresso

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class PrometheeAlgo(Expresso):

    _footprint = dict(
        attr = dict(
            kind = dict(
                values      = ['promethee_algo'],
            ),
            interpreter = dict(
                optional    = True,
                values      = ['python3.7',]
            ),
            engine = dict(
                optional    = True,
                default     = "exec"
            ),
            cmdline=dict(
                type        = FPDict,
                default     = FPDict({"nproc" : 32}),
                optional    = True,
            ),
        )
    )

    def spawn_command_options(self):
        return self.cmdline