#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import footprints

from vortex.algo.components import Parallel

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


class SurgesCouplingForecasts(Parallel):
    """"""
    _footprint = dict(
        attr = dict(
            binary = dict(
                values = ['hycomcoupling'],
            ),
        )
    )

    def execute(self, rh, opts):
        """Jump into the correct working directory."""
        tmpwd = 'EXEC_OASIS'
        logger.info('Temporarily change the working dir to ./%s', tmpwd)
        with self.system.cdcontext(tmpwd):
            super(SurgesCouplingForecasts, self).execute(rh, opts)


class SurgesCouplingInterp(SurgesCouplingForecasts):
    """Algo for interpolation case, not documented yet"""
    _footprint = dict(
        attr = dict(
            binary = dict(
                values = ['hycominterp'],
            ),
        )
    )
