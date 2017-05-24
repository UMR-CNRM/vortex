#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)
import re

from vortex.algo.components import Parallel
from vortex.data.executables import BlackBox
from vortex.tools.date import Date


class SurgesCouplingForecasts(Parallel):
    """"""
    _footprint = dict(
        attr = dict(
            binary = dict(
               values = ['hycomcoupling'],
            ),  
        )
    )

    def prepare(self, rh, opts):
        super(SurgesCouplingForecasts, self).prepare(rh, opts)
        sh = self.system
        # Jump into a working directory
        logger.info('Change on Execution Directory on EXEC_OASIS')
        cwd = sh.pwd()
        tmpwd='EXEC_OASIS'
        sh.cd(tmpwd)
    
    def postfix(self, rh, opts):
        sh = self.system
        # Jump into the previous working directory
        logger.info('Change on Previous Directory (rundir)')
        cwd = sh.pwd()
        tmpwd='../'
        sh.cd(tmpwd)