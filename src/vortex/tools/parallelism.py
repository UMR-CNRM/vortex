# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

from collections import deque
import StringIO
import sys

import footprints
from footprints import loggers
logger = loggers.getLogger(__name__)
import taylorism

import vortex


class TaylorVortexWorker(taylorism.Worker):
    """Vortex version of the :class:`taylorism.Worker` class.

    This class provides additional features:
    * Useful shortcuts (system, context, ...)
    * Setup a Context recorder to track changes in the Context (and replay them later)
    * The necessary hooks to record the logging messages and standard output. They
      are sent back to the main process where they are displayed using the
      :class:`ParellelResultParser` class.
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

    def _vortex_setuphooks(self):
        """Records the log messages and of the standard output and suppress them."""
        # Start the recording of the context (to be replayed in the main process)
        self._ctx_recorder = self.context.get_recorder()
        # Reset all the log handlers and slurp everything
        self._log_record = deque()
        slurp_handler = loggers.SlurpHandler(self._log_record)
        for a_logger in [loggers.getLogger(x) for x in loggers.roots]:
            a_logger.addHandler(slurp_handler)
        for a_logger in [loggers.getLogger(x) for x in loggers.lognames]:
            for a_handler in [h for h in a_logger.handlers
                              if not isinstance(h, loggers.SlurpHandler)]:
                a_logger.removeHandler(a_handler)
        # Do not speak on stderr
        self._sys_stdoe = StringIO.StringIO()
        sys.stdout = self._sys_stdoe
        sys.stderr = self._sys_stdoe

    def _vortex_rc_wrapup(self, rc):
        """
        Stop the recording of the log messages and of the standard output;
        finally send them back to the main process.
        """
        # Stop recording
        self._ctx_recorder.unregister()
        # Update the return values
        if not isinstance(rc, dict):
            rc = dict(msg=rc)
        rc['context_record'] = self._ctx_recorder
        rc['log_record'] = self._log_record
        self._sys_stdoe.seek(0)
        rc['stdoe_record'] = self._sys_stdoe.readlines()
        return rc

    def _task(self, **kwargs):
        """Should not be overriden anymore: see :meth:`vortex_task`."""
        self._vortex_shortcuts()
        self._vortex_setuphooks()

        rc = self.vortex_task(**kwargs)

        return self._vortex_rc_wrapup(rc)

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


class ParallelResultParser(object):
    """Summarise the results of a parallel execution."""

    def __init__(self, context):
        """

        :param context: The context where the results will be replayed.
        """
        self.context = context

    def slurp(self, res):
        """Summarise the results of a parallel execution.

        :param res: A result record
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
