# -*- coding: utf-8 -*-

"""
TODO: Module documentation
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers

from vortex.data.flow import FlowResource

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class AlphaWeightFile(FlowResource):
    """Input file containing model weights used in Alpha.
    """
    _footprint = [
        dict(
            info = 'Input file containing model weights used in Alpha.',
            attr = dict(
                kind = dict(
                    values  = ['weightFile', ],
                ),
                model = dict(
                    values = ['alpha', ],
                ),
                nativefmt = dict(
                    values  = ['json']
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'weightFile'