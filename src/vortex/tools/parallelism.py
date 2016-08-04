# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

from collections import deque, defaultdict
import StringIO
import sys

import footprints
from footprints import loggers
import taylorism
import vortex

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
        kind = (),
    )

    def _vortex_shortcuts(self):
        """Setup a few shotcuts."""
        self.ticket  = vortex.sessions.current()
        self.context = self.ticket.context
        self.system  = self.context.system

    def _vortex_rc_wrapup(self, rc, psi_rc):
        """Complement the return code with the ParallelSilencer recording."""
        # Update the return values
        if not isinstance(rc, dict):
            rc = dict(msg=rc)
        rc.update(psi_rc)
        return rc

    def _task(self, **kwargs):
        """Should not be overriden anymore: see :meth:`vortex_task`."""
        self._vortex_shortcuts()
        with ParallelSilencer(self.context) as psi:
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
        attr = dict(
            progname = dict(
            ),
            progargs = dict(
                type = footprints.FPList,
                default = footprints.FPList(),
                optional = True,
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
        tmpio = open(stdoutfile, 'w')
        self.system.remove('core')
        self.system.softlink('/dev/null', 'core')
        self.local_spawn_hook()
        self.system.target().spawn_hook(self.system)
        logger.info("The fa2grib stdout/err will be saved to %s", stdoutfile)
        logger.info("Starting the following command: %s", " ".join([self.progname, ] +
                                                                   self.progargs))
        self.system.spawn([self.progname, ] + self.progargs, output=tmpio,
                          fatal=True)


class ParallelSilencer(object):
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

    def __init__(self, context):
        """

        :param vortex.layout.contexts.Context context: : The context we will record.
        """
        self._ctx = context
        # Variables were the records will be stored
        self._reset_records(handler=False)
        # Other temporary stuff
        self._reset_temporary()

    def _reset_records(self, handler=True):
        """Reset variables were the records are stored."""
        self._ctx_r = None
        self._log_r = deque()
        self._io_r = StringIO.StringIO()
        if handler:
            self._slurp_h = loggers.SlurpHandler(self._log_r)

    def _reset_temporary(self):
        """Reset other temporary stuff."""
        self._removed_h = defaultdict(list)
        (self._prev_stdo, self._prev_stde) = (None, None)

    def __enter__(self):
        """The beginning of a new context."""
        # Reset all
        self._reset_records()
        # Start the recording of the context (to be replayed in the main process)
        self._ctx_r = self._ctx.get_recorder()
        # Reset all the log handlers and slurp everything
        for a_logger in [loggers.getLogger(x) for x in loggers.roots]:
            a_logger.addHandler(self._slurp_h)
        for a_logger in [loggers.getLogger(x) for x in loggers.lognames]:
            for a_handler in [h for h in a_logger.handlers
                              if not isinstance(h, loggers.SlurpHandler)]:
                a_logger.removeHandler(a_handler)
                self._removed_h[a_logger].append(a_handler)
        # Do not speak on stdout/err
        self._prev_stdo = sys.stdout
        self._prev_stde = sys.stderr
        sys.stdout = self._io_r
        sys.stderr = self._io_r
        return self

    def __exit__(self, exctype, excvalue, exctb):
        """The end of a context."""
        self._stop_recording()

    def _stop_recording(self):
        """Stop recording and restore everything."""
        if self._prev_stdo is not None:
            # Stop recording the context
            self._ctx_r.unregister()
            # Restore the loggers
            for a_logger in [loggers.getLogger(x) for x in loggers.roots]:
                a_logger.removeHandler(self._slurp_h)
            for a_logger in [loggers.getLogger(x) for x in loggers.lognames]:
                for a_handler in self._removed_h[a_logger]:
                    a_logger.addHandler(a_handler)
            # Restore stdout/err
            sys.stdout = self._prev_stdo
            sys.stderr = self._prev_stde
            # Cleanup
            self._reset_temporary()

    def export_result(self):
        """Return everything that has been recorded.

        :return: A dictionary that can be processed with the :class:`ParallelResultParser` class.
        """
        self._stop_recording()
        self._io_r.seek(0)
        return dict(context_record=self._ctx_r,
                    log_record=self._log_r,
                    stdoe_record=self._io_r.readlines())


class ParallelResultParser(object):
    """Summarise the results of a parallel execution.

    Just pass to this object the `rc` of a `taylorism` worker based on
    :class:`TaylorVortexWorker`. It will:

        * update the context with the changes made by the worker ;
        * display the standard output/error if the worker
        * display the log messages issued by the worker
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
            raise(res)
        else:
            logger.info('Parallel processing results for %s', res['name'])
            # Update the context
            logger.info('... Updating the current context ...')
            res['report']['context_record'].replay_in(self.context)
            # Display the log records
            if res['report']['log_record']:
                logger.info('... Dump of the log entries created by the subprocess ...')
                while res['report']['log_record']:
                    lrecord = res['report']['log_record'].popleft()
                    a_logger = loggers.getLogger(lrecord.name)
                    a_logger.handle(lrecord)
            # Display the stdout
            if res['report']['stdoe_record']:
                logger.info('... Dump of the mixed standard/error output generated by the subprocess ...')
                for l in res['report']['stdoe_record']:
                    sys.stdout.write(l)
            logger.info("... That's all for all for %s ...", res['name'])

            return res['report'].get('rc', True)

    def __call__(self, res):
        return self.slurp(res)
