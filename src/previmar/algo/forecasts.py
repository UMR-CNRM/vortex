#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.algo.components import Parallel


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
