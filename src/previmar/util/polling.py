#!/usr/bin/env python
# -*- coding: utf-8 -*-

import io
import re

import footprints
import traceback, pdb


#: Export nothing
__all__ = []

logger = footprints.loggers.getLogger(__name__)

from vortex.tools.lfi import IO_Poll, LFI_Status


class PollingMarine(IO_Poll):
    """
    """
    _footprint = dict(
        info = 'Default io_poll marine system interface',
        attr = dict(
            kind = dict(
                values  = ['iopollmarine', 'io_poll_marine'],
            ),
            interpreter = dict(
                values  = ['bash', 'sh'],
                default = 'sh',
                optional = True,
            ),
            cmd = dict(
                default = 'iopoll_marine',
            ),
            nproc_io = dict(
                default = 1,
                optional = True,
            ), 
        )
    )


    def iopoll_marine(self, prefix):
        """Do the actual job of polling files prefixed by ``prefix``."""
        logger.info("BIENVENUE POPOL MARINE")
        cmd = ['--prefix', prefix]
  
        if self.nproc_io is None:
            raise IOError('The nproc_io option should be provided.')
        else:
            cmd.extend(['--nproc_io', str(self.nproc_io)])

        # Catch the processed file
        rawout = self._spawn(cmd)
   
        # Cumulative results
        st = LFI_Status()
        st.result = rawout
        for polledfile in st.result:
            self._polled.add(polledfile)
        st.rc &= self.sh.rclast
        return st



        #logger.info("COUCOU POPOL mARINE")
        #print traceback.print_stack()
        #logger.info("prefix %s", prefix)
        #logger.info("nproc_io %s", nproc_io)
     ##   logger.info(" pdb.set_trace() %s", pdb.set_trace())
      ##  logger.info("nproc_io %s", no)
        #logger.info("interpreter %s", self.interpreter)
        #logger.info("path %s", self.path)
        #logger.info("nproc_io %s", nproc_io)