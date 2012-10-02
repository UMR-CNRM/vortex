#!/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import re
from vortex.algo.mpitools import MpiRun

from vortex.tools import env


class NecMpiRun(MpiRun):
    """MPIRUN utility on NEC SX systems."""
    
    _footprint = dict(
        attr = dict(
            sysname = dict(
                values = [ 'SUPER-UX' ]
            ),
        )
    )

    def setup(self):
        """
        Prepares automatic export of variables through the MPIEXPORT mechanism.
        The list of variables could be extended or reduced through:
        
         * MPIRUN_FILTER
         * MPIRUN_DISCARD
        """
        
        e = env.current()

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
