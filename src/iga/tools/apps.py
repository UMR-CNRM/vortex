#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from bronx.fancies import loggers

from vortex.layout.nodes import Task
from vortex.tools.actions import actiond as ad

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class OpTask(Task):
    """Wrapper for setting up and performing a miscellaneous op task for a serial execution."""

    _tag_topcls = False

    def report_execution_error(self):
        """Report any execution error."""
        listing   = self.env.getvar('RUNDIR') + '/opview/' + self.tag + '/NODE.001_01'
        self.sh.header('Send a mail due to an execution error')
        ad.opmail(task=self.tag, id ='execution_error', listing=listing)
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
