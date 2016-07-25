#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []


import footprints
logger = footprints.loggers.getLogger(__name__)

from opinel.interrupt import SignalInterruptError

from vortex.layout.nodes import Task
from vortex.tools.actions import actiond as ad
from vortex.tools.systems import ExecutionError
from vortex.algo.components import DelayedAlgoComponentError

from . import op


class OpTask(Task):
    """Wrapper for setting up and performing a miscellaneous op task for a serial execution."""

    _tag_topcls = False

    def component_runner(self, tbalgo, tbx=(None, ), **kwargs):
        """Run the binaries listed in tbx using the tbalgo algo component."""
        for binary in tbx:
            try:
                tbalgo.run(binary, **kwargs)
            except (DelayedAlgoComponentError, ExecutionError,
                    SignalInterruptError):
                self.report_execution_error()
                raise

    def report_execution_error(self):
        reseau = self.conf.rundate.hh
        logpath = self.env.LOG
        rundir  = self.env.getvar('RUNDIR') + '/opview/' + self.tag
        listing = rundir + '/NODE.001_01'
        model   = self.env.getvar('OP_VAPP').upper()
        conf    = self.env.getvar('OP_VCONF').upper()
        self.sh.header('Send a mail due to an execution error')
        ad.opmail(reseau=reseau, task=self.tag, id ='execution_error', log=logpath, rundir=rundir, listing=listing, model=model, conf=conf)
        raise

    def register_cycle(self, cycle):
        """Register a given GCO cycle."""
        self.header('GCO cycle ' + cycle)
        op.register(self.ticket, cycle)

    def defaults(self, extras):
        """Set defaults for toolbox defaults, with priority to actual conf."""
        extras.setdefault('namespace', self.conf.get('namespace', 'vortex.cache.fr'))
        extras.setdefault('gnamespace', self.conf.get('gnamespace', 'opgco.cache.fr'))
        super(OpTask, self).defaults(extras)


class OpTaskMPI(OpTask):
    """Wrapper for setting up and performing a miscellaneous op task for an MPI execution."""

    _tag_topcls = False

    def component_runner(self, tbalgo, tbx, **kwargs):
        """Run the binaries listed in tbx using the tbalgo algo component."""
        mpiopts = dict(nn = int(self.conf.nnodes),
                       nnp = int(self.conf.ntasks), openmp = int(self.conf.openmp))
        for binary in tbx:
            try:
                tbalgo.run(binary, mpiopts = mpiopts, **kwargs)
            except (DelayedAlgoComponentError, ExecutionError,
                    SignalInterruptError):
                self.report_execution_error()
                raise
