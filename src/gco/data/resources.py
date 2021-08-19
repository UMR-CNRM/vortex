# -*- coding: utf-8 -*-

"""
TODO: Module documentation.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.data.outflow import StaticResource
from gco.syntax.stdattrs import gvar

#: Automatic export of MiscGenv
__all__ = ['MiscGenv', ]


class MiscGenv(StaticResource):
    """
    Base classe for genv-only kind of resources.

    Extended footprint:

    * gvar (type :class:`gco.syntax.stdattrs.GenvKey`)
    * kind (values: ``miscgenv``)
    """

    _footprint = [
        gvar,
        dict(
            info = 'Miscellaneous genv constant',
            attr = dict(
                kind = dict(
                    values = ['miscgenv']
                )
            )
        )
    ]

    @property
    def realkind(self):
        """Default realkind is ``miscgenv``."""
        return 'miscgenv'
