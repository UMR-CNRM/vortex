#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []


import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.layout.nodes import Task
from vortex.tools.actions import actiond as ad


class OpTask(Task):
    """Wrapper for setting up and performing a miscellaneous op task for a serial execution."""

    _tag_topcls = False

    def report_execution_error(self):
        reseau  = self.conf.rundate.hh
        logpath = self.env.LOG
        rundir  = self.env.getvar('RUNDIR') + '/opview/' + self.tag
        listing = rundir + '/NODE.001_01'
        model   = self.env.getvar('OP_VAPP').upper()
        conf    = self.env.getvar('OP_VCONF').lower()
        xpid    = self.env.getvar('OP_XPID').lower()
        member  = self.env.getvar('OP_MEMBER')
        if member:
            self.sh.header('Send a mail due to an execution error')
            ad.opmail(reseau=reseau, task=self.tag, member=member, id ='execution_error_member', log=logpath, rundir=rundir, listing=listing, model=model, conf=conf, xpid=xpid)
            raise
        else:
            self.sh.header('Send a mail due to an execution error')
            ad.opmail(reseau=reseau, task=self.tag, id ='execution_error', log=logpath, rundir=rundir, listing=listing, model=model, conf=conf, xpid=xpid)
            raise

    def defaults(self, extras):
        """Set defaults for toolbox defaults, with priority to actual conf."""
        extras.setdefault('namespace', self.conf.get('namespace', 'vortex.cache.fr'))
        extras.setdefault('gnamespace', self.conf.get('gnamespace', 'opgco.cache.fr'))
        super(OpTask, self).defaults(extras)

    def __exit__(self, exc_type, exc_value, traceback):
        """Cleanup promises on exit."""
        # Note: If an MTOOL like tool was to be used, this should be changed...
        self.ticket.context.clear_promises()
        super(OpTask, self).__exit__(exc_type, exc_value, traceback)


class OpTaskMPI(OpTask):
    """Wrapper for setting up and performing a miscellaneous op task for an MPI execution.

    This is now useless (kept for backward compatibility)
    """

    _tag_topcls = False
