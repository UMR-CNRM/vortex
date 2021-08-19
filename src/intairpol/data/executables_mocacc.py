# -*- coding: utf-8 -*-

"""
Resources to deal with mocage accident executables.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.data.executables import BlackBox
from vortex.syntax.stdattrs import model
from gco.syntax.stdattrs import gvar


class MakeFm(BlackBox):
    """Program that computes FM from BDAP gribs."""

    # fmt: off
    _footprint = [
        gvar,
        model,
        dict(
            info = 'Program that computes FM from BDAP gribs.""",',
            attr = dict(
                kind = dict(
                    values = ["makefm"]
                ),
                gvar = dict(
                    default = "master_makefm"
                ),
                model = dict(
                    values = ['mocage', ]
                ),
            ),
        ),
    ]
    # fmt: on

    @property
    def realkind(self):
        return "makefm"
