"""
TODO: module documentation.
"""

import contextlib

from bronx.fancies import loggers
from vortex.algo.components import DelayedAlgoComponentError
from vortex.layout.nodes import Task
from vortex.tools.actions import actiond as ad

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class OpTask(Task):
    """Wrapper for setting up and performing a miscellaneous op task for a serial execution."""

    _tag_topcls = False

    def report_execution_error(self, exc, **kw_infos):  # @UnusedVariable
        """Report any execution error."""
        listing = self.env.getvar('RUNDIR') + '/opview/' + self.tag + '/NODE.001_01'
        self.sh.header('Send a mail due to an execution error')
        ad.opmail(task=self.tag, id='execution_error', listing=listing)

    def defaults(self, extras):
        """Set defaults for toolbox defaults, with priority to actual conf."""
        extras.setdefault('namespace', self.conf.get('namespace', 'vortex.cache.fr'))
        extras.setdefault('gnamespace', self.conf.get('gnamespace', 'opgco.cache.fr'))
        super().defaults(extras)

    @contextlib.contextmanager
    def isolate(self):
        """In Op Jobs always clear un-honored promises."""
        with super().isolate():
            try:
                yield
            finally:
                # Note: If an MTOOL like tool was to be used, this should be changed...
                self.ticket.context.clear_promises()


class MissingObsMixin:
    """This mixin can be added to any bator-like task.

    It provides functions to alter the component_runner behaviour when the
    processing of one or several ODB fails
    """

    def missing_obs_filter_error(self, exc):
        """Mask Bator failures (but prints something)."""
        if isinstance(exc, DelayedAlgoComponentError):
            logger.warning('Exception caught: %s', str(exc))
            return True, dict()
        else:
            return False, dict()

    def missing_obs_report(self, exc, **kw_infos):
        """Report (e-mail) any Bator failure."""
        listing = self.env.getvar('RUNDIR') + '/opview/' + self.tag + '/NODE.001_01'
        outstr = ("Les bases ODB suivantes ont rencontré des problèmes lors de " +
                  "l'exécution de la tâche {:s}\n".format(self.tag))
        for i, iexc in enumerate(exc._excs):
            outstr += "\n-{:2d}: {:s}".format(i + 1, iexc.odb_database.upper())

        ad.opmail(task=self.tag, id='execution_nonfatal_error', msg=outstr, listing=listing)


class OpTaskMPI(OpTask):
    """Wrapper for setting up and performing a miscellaneous op task for an MPI execution.

    This is now useless (kept for backward compatibility)
    """

    _tag_topcls = False
