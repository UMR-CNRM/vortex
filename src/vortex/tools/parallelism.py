"""
Abstract classes for :mod:`taylorism` workers to be used in conjunction with
AlgoComponents based on the :class:`~vortex.algo.components.TaylorRun` class.
"""

import io
import logging
import sys

from bronx.fancies import loggers
from bronx.stdtypes import date
import footprints
import taylorism
import vortex
from vortex.tools.systems import ExecutionError

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class TaylorVortexWorker(taylorism.Worker):
    """Vortex version of the :class:`taylorism.Worker` class.

    This class provides additional features:

        * Useful shortcuts (system, context, ...)
        * Setup a Context recorder to track changes in the Context (and replay them later)
        * Setup necessary hooks to record the logging messages and standard output. They
          are sent back to the main process where they are displayed using the
          :class:`ParallelResultParser` class.
    """

    _abstract = True
    _footprint = dict(
        attr=dict(
            kind=dict(),
            taskdebug=dict(
                info="Dump all stdout/stderr to a file (in real live !)",
                type=bool,
                default=False,
                optional=True,
            ),
        )
    )

    def _vortex_shortcuts(self):
        """Setup a few shortcuts."""
        self.ticket = vortex.sessions.current()
        self.context = self.ticket.context
        self.system = self.context.system

    def _vortex_rc_wrapup(self, rc, psi_rc):
        """Complement the return code with the ParallelSilencer recording."""
        # Update the return values
        if not isinstance(rc, dict):
            rc = dict(msg=rc)
        rc.update(psi_rc)
        return rc

    def _task(self, **kwargs):
        """Should not be overridden anymore: see :meth:`vortex_task`."""
        self._vortex_shortcuts()
        with ParallelSilencer(
            self.context, self.name, debug=self.taskdebug
        ) as psi:
            rc = self.vortex_task(**kwargs)
            psi_rc = psi.export_result()
        return self._vortex_rc_wrapup(rc, psi_rc)

    def vortex_task(self, **kwargs):
        """This method is to be implemented through inheritance: the real work happens here!"""
        raise NotImplementedError()


class VortexWorkerBlindRun(TaylorVortexWorker):
    """Include utility methods to run a basic program (i.e no MPI)."""

    _abstract = True
    _footprint = dict(
        attr=dict(
            progname=dict(),
            progargs=dict(
                type=footprints.FPList,
                default=footprints.FPList(),
                optional=True,
            ),
            progtaskset=dict(
                info="Topology/Method to set up the CPU affinity of the child task.",
                default=None,
                optional=True,
            ),
            progtaskset_bsize=dict(
                info="The number of threads used by one task",
                type=int,
                default=1,
                optional=True,
            ),
            progenvdelta=dict(
                info="Any alteration to environment variables",
                type=footprints.FPDict,
                default=footprints.FPDict({}),
                optional=True,
            ),
        )
    )

    def local_spawn_hook(self):
        """Last chance to say something before execution."""
        pass

    def local_spawn(self, stdoutfile):
        """Execute the command specified in the **progname** attributes.

        :param stdoutfile: Path to the file where the standard/error output will
                           be saved.
        """
        tmpio = open(stdoutfile, "wb")
        try:
            self.system.softlink("/dev/null", "core")
        except FileExistsError:
            pass
        self.local_spawn_hook()
        self.system.default_target.spawn_hook(self.system)
        logger.info("The program stdout/err will be saved to %s", stdoutfile)
        logger.info(
            "Starting the following command: %s (taskset=%s, id=%d)",
            " ".join(
                [
                    self.progname,
                ]
                + self.progargs
            ),
            str(self.progtaskset),
            self.scheduler_ticket,
        )
        with self.system.env.delta_context(**self.progenvdelta):
            self.system.spawn(
                [
                    self.progname,
                ]
                + self.progargs,
                output=tmpio,
                fatal=True,
                taskset=self.progtaskset,
                taskset_id=self.scheduler_ticket,
                taskset_bsize=self.progtaskset_bsize,
            )

    def delayed_error_local_spawn(self, stdoutfile, rcdict):
        """local_spawn wrapped in a try/except in order to trigger delayed exceptions."""
        try:
            self.local_spawn(stdoutfile)
        except ExecutionError as e:
            logger.error("The execution failed.")
            rcdict["rc"] = e
        return rcdict

    def find_namelists(self, opts=None):  # @UnusedVariable
        """Find any namelists candidates in actual context inputs."""
        namcandidates = [
            x.rh
            for x in self.context.sequence.effective_inputs(kind="namelist")
        ]
        self.system.subtitle("Namelist candidates")
        for nam in namcandidates:
            nam.quickview()

        return namcandidates


class TeeLikeStringIO(io.StringIO):
    """A StringIO variatn that can also write to several files."""

    def __init__(self):
        super().__init__()
        self._tees = set()

    def record_teefile(self, filename, mode="w", line_buffering=True):
        """Add **filename** to the set of extra logfiles."""
        self._tees.add(
            open(filename, mode=mode, buffering=int(line_buffering))
        )

    def discard_tees(self):
        """Dismiss all of the extra logfiles."""
        for teeio in self._tees:
            teeio.close()
        self._tees = set()

    def write(self, t):
        """Write in the present StringIO but also in the extra logfiles."""
        for teeio in self._tees:
            teeio.write(t)
        super().write(t)

    def filedump(self, filename, mode="w"):
        """Dump all of the captured data to **filename**."""
        with open(filename, mode=mode) as fhdump:
            self.seek(0)
            for line in self:
                fhdump.write(line)


class ParallelSilencer:
    """Record everything and suppress all outputs (stdout, loggers, ...).

    The record is kept within the object: the *export_result* method returns
    the record as a dictionary that can be processed using the
    :class:`ParallelResultParser` class.

    :note: This object is designed to be used as a Context manager.

    :example:
        .. code-block:: python

            with ParallelSilencer(context) as psi:
                # do a lot of stuff here
                psi_record = psi.export_result()
            # do whatever you need with the psi_record
    """

    def __init__(self, context, taskname, debug=False):
        """

        :param vortex.layout.contexts.Context context: : The context we will record.
        """
        self._ctx = context
        self._taskdebug = debug
        self._debugfile = "{:s}_{:s}_stdeo.txt".format(
            taskname, date.now().ymdhms
        )
        self._ctx_r = None
        self._io_r = io.StringIO()
        # Other temporary stuff
        self._reset_temporary()

    def _reset_records(self):
        """Reset variables were the records are stored."""
        self._io_r = TeeLikeStringIO()
        if self._taskdebug:
            self._io_r.record_teefile(self._debugfile)
        self._stream_h = logging.StreamHandler(self._io_r)
        self._stream_h.setLevel(logging.DEBUG)
        self._stream_h.setFormatter(loggers.default_console.formatter)

    def _reset_temporary(self):
        """Reset other temporary stuff."""
        self._removed_h = dict()
        (self._prev_stdo, self._prev_stde) = (None, None)

    def __enter__(self):
        """The beginning of a new context."""
        # Reset all
        self._reset_records()
        # Start the recording of the context (to be replayed in the main process)
        self._ctx_r = self._ctx.get_recorder()
        # Reset all the log handlers and slurp everything
        r_logger = logging.getLogger()
        self._removed_h[r_logger] = list(r_logger.handlers)
        r_logger.addHandler(self._stream_h)
        for a_handler in self._removed_h[r_logger]:
            r_logger.removeHandler(a_handler)
        for a_logger in [
            logging.getLogger(x) for x in loggers.lognames | loggers.roots
        ]:
            self._removed_h[a_logger] = list(a_logger.handlers)
            for a_handler in self._removed_h[a_logger]:
                a_logger.removeHandler(a_handler)
        # Do not speak on stdout/err
        self._prev_stdo = sys.stdout
        self._prev_stde = sys.stderr
        sys.stdout = self._io_r
        sys.stderr = self._io_r
        return self

    def __exit__(self, exctype, excvalue, exctb):  # @UnusedVariable
        """The end of a context."""
        self._stop_recording()
        if (
            exctype is not None
            and not self._taskdebug
            and self._io_r is not None
        ):
            # Emergency dump of the outputs (even with debug=False) !
            self._io_r.filedump(self._debugfile)

    def _stop_recording(self):
        """Stop recording and restore everything."""
        if self._prev_stdo is not None:
            # Stop recording the context
            self._ctx_r.unregister()
            # Restore the loggers
            r_logger = logging.getLogger()
            for a_handler in self._removed_h[r_logger]:
                r_logger.addHandler(a_handler)
            r_logger.removeHandler(self._stream_h)
            for a_logger in [
                logging.getLogger(x) for x in loggers.roots | loggers.lognames
            ]:
                for a_handler in self._removed_h.get(a_logger, ()):
                    a_logger.addHandler(a_handler)
            # flush
            self._stream_h.flush()
            # Restore stdout/err
            sys.stdout = self._prev_stdo
            sys.stderr = self._prev_stde
            # Remove all tees
            self._io_r.discard_tees()
            # Cleanup
            self._reset_temporary()

    def export_result(self):
        """Return everything that has been recorded.

        :return: A dictionary that can be processed with the :class:`ParallelResultParser` class.
        """
        self._stop_recording()
        self._io_r.seek(0)
        return dict(
            context_record=self._ctx_r, stdoe_record=self._io_r.readlines()
        )


class ParallelResultParser:
    """Summarise the results of a parallel execution.

    Just pass to this object the `rc` of a `taylorism` worker based on
    :class:`TaylorVortexWorker`. It will:

        * update the context with the changes made by the worker ;
        * display the standard output/error of the worker
    """

    def __init__(self, context):
        """

        :param vortex.layout.contexts.Context context: The context where the results will be replayed.
        """
        self.context = context

    def slurp(self, res):
        """Summarise the results of a parallel execution.

        :param dict res: A result record
        """
        if isinstance(res, Exception):
            raise res
        else:
            sys.stdout.flush()
            logger.info("Parallel processing results for %s", res["name"])
            # Update the context
            logger.info("... Updating the current context ...")
            res["report"]["context_record"].replay_in(self.context)
            # Display the stdout
            if res["report"]["stdoe_record"]:
                logger.info(
                    "... Dump of the mixed standard/error output generated by the subprocess ..."
                )
                for l in res["report"]["stdoe_record"]:
                    sys.stdout.write(l)
            logger.info("... That's all for all for %s ...", res["name"])

            return res["report"].get("rc", True)

    def __call__(self, res):
        return self.slurp(res)
