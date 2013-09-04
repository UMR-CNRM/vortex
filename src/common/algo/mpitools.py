#!/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import re
from vortex.autolog import logdefault as logger
from vortex.algo.mpitools import MpiRun


class NecMpiRun(MpiRun):
    """MPIRUN utility on NEC SX systems."""
    
    _footprint = dict(
        attr = dict(
            sysname = dict(
                values = [ 'SUPER-UX' ]
            ),
        )
    )

    def setup(self, ctx, target=None, opts=None):
        """
        Prepares automatic export of variables through the MPIEXPORT mechanism.
        The list of variables could be extended or reduced through:

         * MPIRUN_FILTER
         * MPIRUN_DISCARD
        """

        super(NecMpiRun, self).setup(ctx, target)

        e = ctx.env

        if not e.false('mpirun_export'):
            if 'mpiexport' in e:
                mpix = set(e.mpiexport.split(','))
            else:
                mpix = set()

            if not e.false('mpirun_filter'):
                mpifilter = re.sub(',', '|', e.mpirun_filter)
                mpix.update(filter(lambda x: re.match(mpifilter, x), e.keys()))

            if not e.false('mpirun_discard'):
                mpidiscard = re.sub(',', '|', e.mpirun_discard)
                mpix = set(filter(lambda x: not re.match(mpidiscard, x), mpix))

            e.mpiexport = ','.join(mpix)
            logger.info('MPI export environment %s', e.mpiexport)


class MpiAuto(MpiRun):
    """Standard MPI launcher on most systems."""

    _footprint = dict(
        attr = dict(
            mpiname = dict(
                values = [ 'mpiauto' ],
            ),
            mpiopts = dict(
                default = '--wrap --verbose',
            ),
            optprefix = dict(
                default = '--'
            )
        )
    )
