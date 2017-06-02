#!/usr/bin/env python
# -*- coding: utf-8 -*-
# pylint: disable=unused-argument

#: No automatic export
__all__ = []

import collections
import sys
import traceback
import shlex
import multiprocessing

from taylorism import Boss
from taylorism.schedulers import MaxThreadsScheduler
import footprints
logger = footprints.loggers.getLogger(__name__)

import vortex
from vortex.algo  import mpitools
from vortex.tools import date
from vortex.tools.parallelism import ParallelResultParser
from vortex.syntax.stdattrs import DelayedEnvValue


class AlgoComponentError(Exception):
    """Generic exception class for Algo Components."""
    pass


class DelayedAlgoComponentError(AlgoComponentError):
    """Triggered when exceptions occured during the execution but were delayed."""
    def __init__(self, excs):
        super(DelayedAlgoComponentError, self).__init__("One or several errors occurs during the run.")
        self._excs = excs

    def __str__(self):
        outstr = "One or several errors occur during the run. In order of appearance:\n"
        outstr += "\n".join(['{0:3d}. {1!s} (type: {2!s})'.format(i + 1, exc, type(exc))
                             for i, exc in enumerate(self._excs)])
        return outstr


class ParallelInconsistencyAlgoComponentError(Exception):
    """Generic exception class for Algo Components."""
    def __init__(self, target):
        msg = "The len of {:s} is inconsistent with the number or ResourceHandlers."
        super(ParallelInconsistencyAlgoComponentError, self).__init__(msg.format(target))


class AlgoComponent(footprints.FootprintBase):
    """Component in charge of any kind of processing."""

    _abstract  = True
    _collector = ('component',)
    _footprint = dict(
        info = 'Abstract algo component',
        attr = dict(
            engine = dict(
                info     = 'The way the executable should be run.',
                values   = [ 'algo' ]
            ),
            flyput = dict(
                info            = 'Activate a background job in charge off on the fly processing.',
                optional        = True,
                default         = False,
                access          = 'rwx',
                doc_visibility  = footprints.doc.visibility.GURU,
                doc_zorder      = -99,
            ),
            flypoll = dict(
                info            = 'The system method called by the flyput background job.',
                optional        = True,
                default         = 'io_poll',
                access          = 'rwx',
                doc_visibility  = footprints.doc.visibility.GURU,
                doc_zorder      = -99,
            ),
            flyargs = dict(
                info            = 'Arguments for the *flypoll* method.',
                type            = footprints.FPTuple,
                optional        = True,
                default         = footprints.FPTuple(),
                doc_visibility  = footprints.doc.visibility.GURU,
                doc_zorder      = -99,
            ),
            timeout = dict(
                info            = 'Default timeout (in sec.) used  when waiting for an expected resource.',
                type            = int,
                optional        = True,
                default         = 180,
                doc_zorder      = -50,
            ),
            server_run = dict(
                info            = 'Run the executable as a server.',
                type            = bool,
                optional        = True,
                values          = [False],
                default         = False,
                doc_visibility  = footprints.doc.visibility.ADVANCED,
            ),
            serversync_method = dict(
                info                    = 'The method that is used to synchronise with the server.',
                optional        = True,
                doc_visibility  = footprints.doc.visibility.GURU,
            ),
            serversync_medium = dict(
                info            = 'The medium that is used to synchronise with the server.',
                optional        = True,
                doc_visibility  = footprints.doc.visibility.GURU,
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Algo component init %s', self.__class__)
        self._fslog = list()
        self._promises = None
        self._expected = None
        self._delayed_excs = list()
        self._server_synctool = None
        self._server_process = None
        super(AlgoComponent, self).__init__(*args, **kw)

    @property
    def realkind(self):
        """Default kind is ``algo``."""
        return 'algo'

    @property
    def fslog(self):
        """Changes on the filesystem during the execution."""
        return self._fslog

    def fstag(self):
        """Defines a tag specific to the current algo component."""
        return '-'.join((self.realkind, self.engine))

    def fsstamp(self, opts):
        """Ask the current context to put a stamp on file system."""
        self.context.fstrack_stamp(tag=self.fstag())

    def fscheck(self, opts):
        """Ask the current context to check changes on file system since last stamp."""
        self._fslog.append(self.context.fstrack_check(tag=self.fstag()))

    @property
    def promises(self):
        """Build and return list of actual promises of the current component."""
        if self._promises is None:
            self._promises = [
                x for x in self.context.sequence.outputs()
                if x.rh.provider.expected
            ]
        return self._promises

    @property
    def expected_resources(self):
        """Return the list of really expected inputs."""
        if self._expected is None:
            self._expected = [
                x for x in self.context.sequence.effective_inputs()
                if x.rh.is_expected()
            ]
        return self._expected

    def delayed_exception_add(self, exc, traceback=True):
        """Store the exception so that it will be handled at the end of the run."""
        logger.error("An exception is delayed")
        if traceback:
            (exc_type, exc_value, exc_traceback) = sys.exc_info()
            print 'Exception type: ' + str(exc_type)
            print 'Exception info: ' + str(exc_value)
            print 'Traceback:'
            print "\n".join(traceback.format_tb(exc_traceback))
        self._delayed_excs.append(exc)

    def grab(self, sec, comment='resource', sleep=10, timeout=None):
        """Wait for a given resource and get it if expected."""
        local = sec.rh.container.localpath()
        self.system.header('Wait for ' + comment + ' ... [' + local + ']')
        if timeout is None:
            timeout = self.timeout
        if sec.rh.wait(timeout=timeout, sleep=sleep):
            if sec.rh.is_expected():
                sec.get(incache=True)
        elif sec.fatal:
            logger.critical('Missing expected resource <%s>', local)
            raise ValueError('Could not get ' + local)
        else:
            logger.error('Missing expected resource <%s>', local)

    def export(self, packenv):
        """Export environment variables in given pack."""
        if self.target.config.has_section(packenv):
            for k, v in self.target.config.items(packenv):
                if k not in self.env:
                    logger.info('Setting %s env %s = %s', packenv.upper(), k, v)
                    self.env[k] = v

    def prepare(self, rh, opts):
        """Set some defaults env values."""
        if opts.get('fortran', True):
            self.export('fortran')

    def absexcutable(self, xfile):
        """Retuns the absolute pathname of the ``xfile`` executable."""
        absx = self.system.path.abspath(xfile)
        return absx

    def flyput_method(self):
        """Check out what could be a valid io_poll command."""
        return getattr(self, 'io_poll_method', getattr(self.system, self.flypoll, None))

    def flyput_args(self):
        """Return actual io_poll prefixes."""
        return getattr(self, 'io_poll_args', tuple(self.flyargs))

    def flyput_check(self):
        """Check default args for io_poll command."""
        actual_args = list()
        for arg in self.flyput_args():
            logger.info('Check arg <%s>', arg)
            if any([ x.rh.container.basename.startswith(arg) for x in self.promises ]):
                logger.info(
                    'Match some promise %s',
                    str([ x.rh.container.basename for x in self.promises if x.rh.container.basename.startswith(arg) ])
                )
                actual_args.append(arg)
            else:
                logger.info('Do not match any promise %s', str([ x.rh.container.basename for x in self.promises ]))
        return actual_args

    def flyput_sleep(self):
        """Return a sleeping time in seconds between io_poll commands."""
        return getattr(self, 'io_poll_sleep', self.env.get('IO_POLL_SLEEP', 20))

    def flyput_job(self, io_poll_method, io_poll_args, event_complete, event_free,
                   queue_context):
        """Poll new data resources."""
        logger.info('Polling with method %s', str(io_poll_method))
        logger.info('Polling with args %s', str(io_poll_args))

        time_sleep = self.flyput_sleep()
        redo = True

        # Start recording the chnges in the current context
        ctxrec = self.context.get_recorder()

        while redo and not event_complete.is_set():
            event_free.clear()
            data = list()
            try:
                for arg in io_poll_args:
                    logger.info('Polling check arg %s', arg)
                    rc = io_poll_method(arg)
                    try:
                        data.extend(rc.result)
                    except AttributeError:
                        data.extend(rc)
                data = [ x for x in data if x ]
                logger.info('Polling retrieved data %s', str(data))
                for thisdata in data:
                    candidates = [ x for x in self.promises if x.rh.container.basename == thisdata ]
                    if candidates:
                        logger.info('Polled data is promised <%s>', thisdata)
                        bingo = candidates.pop()
                        bingo.put(incache=True)
                    else:
                        logger.warning('Polled data not promised <%s>', thisdata)
            except StandardError as trouble:
                logger.error('Polling trouble: %s', str(trouble))
                redo = False
            finally:
                event_free.set()
            if redo and not data and not event_complete.is_set():
                logger.info('Get asleep for %d seconds...', time_sleep)
                self.system.sleep(time_sleep)

        # Stop recording and send back the results
        ctxrec.unregister()
        logger.info('Sending the Context recorder to the master process.')
        queue_context.put(ctxrec)
        queue_context.close()

        if redo:
            logger.info('Polling exit on complete event')
        else:
            logger.warning('Polling exit on abort')

    def flyput_begin(self):
        """Launch a co-process to handle promises."""

        nope = (None, None, None, None)
        if not self.flyput:
            return nope

        sh = self.system
        sh.subtitle('On the fly - Begin')

        if not self.promises:
            logger.info('No promise, no co-process')
            return nope

        # Find out a polling method
        io_poll_method = self.flyput_method()
        if not io_poll_method:
            logger.error('No method or shell function defined for polling data')
            return nope

        # Be sure that some default args could match local promises names
        io_poll_args = self.flyput_check()
        if not io_poll_args:
            logger.error('Could not check default arguments for polling data')
            return nope

        # Define events for a nice termination
        event_stop = multiprocessing.Event()
        event_free = multiprocessing.Event()
        queue_ctx = multiprocessing.Queue()

        p_io = multiprocessing.Process(
            name   = self.footprint_clsname(),
            target = self.flyput_job,
            args   = (io_poll_method, io_poll_args, event_stop, event_free, queue_ctx),
        )

        # The co-process is started
        p_io.start()

        return (p_io, event_stop, event_free, queue_ctx)

    def flyput_end(self, p_io, e_complete, e_free, queue_ctx):
        """Wait for the co-process in charge of promises."""
        e_complete.set()
        logger.info('Waiting for polling process... <%s>', p_io.pid)
        t0 = date.now()
        e_free.wait(60)
        # Get the Queue and update the context
        time_sleep = self.flyput_sleep()
        try:
            # allow 5 sec to put data into queue (it should be more than enough)
            ctxrec = queue_ctx.get(block=True, timeout=time_sleep + 5)
        except multiprocessing.queues.Empty:
            logger.warning("Impossible to get the Context recorder")
            ctxrec = None
        finally:
            queue_ctx.close()
        if ctxrec is not None:
            ctxrec.replay_in(self.context)
        p_io.join(30)
        t1 = date.now()
        waiting = t1 - t0
        logger.info('Waiting for polling process took %f seconds', waiting.total_seconds())
        if p_io.is_alive():
            logger.warning('Force termination of polling process')
            p_io.terminate()
        logger.info('Polling still alive ? %s', str(p_io.is_alive()))
        return not p_io.is_alive()

    def server_begin(self, rh, opts):
        """Start a subprocess and run the server in it."""
        self._server_event = multiprocessing.Event()
        self._server_process = multiprocessing.Process(
            name   = self.footprint_clsname(),
            target = self.server_job,
            args   = (rh, opts)
        )
        self._server_process.start()

    def server_job(self, rh, opts):
        """Actually run the server and catch all Exceptions.

        If the server crashes, is killed or whatever, the Exception is displayed
        and the appropriate Event is set.
        """
        self.system.signal_intercept_on()
        try:
            self.execute_single(rh, opts)
        except:
            (exc_type, exc_value, exc_traceback) = sys.exc_info()
            print 'Exception type: ' + str(exc_type)
            print 'Exception info: ' + str(exc_value)
            print 'Traceback:'
            print "\n".join(traceback.format_tb(exc_traceback))
            # Alert the main process of the error
            self._server_event.set()

    def server_alive(self):
        """Is the server still running ?"""
        return (self._server_process is not None and
                self._server_process.is_alive())

    def server_end(self):
        """End the server.

        A first attempt is made to terminate it nicely. If it doesn't work,
        a SIGTERM is sent.
        """
        rc = False
        # This test should always suceed...
        if (self._server_synctool is not None and
                self._server_process is not None):
            # Is the process still running ?
            if self._server_process.is_alive():
                # Try to stop it nicely
                if self._server_synctool.trigger_stop():
                    t0 = date.now()
                    self._server_process.join(30)
                    waiting = date.now() - t0
                    logger.info('Waiting for the server to stop took %f seconds',
                                waiting.total_seconds())
                rc = not self._server_event.is_set()
                # Be less nice if needed...
                if self._server_process.is_alive():
                    logger.warning('Force termination of the server process')
                    self._server_process.terminate()
                    self.system.sleep(1)  # Allow some time for the process to terminate
            else:
                rc = not self._server_event.is_set()
            logger.info('Server still alive ? %s', str(self._server_process.is_alive()))
            # We are done with the server
            self._server_synctool = None
            self._server_process = None
            del self._server_event
            # Check the rc
            if not rc:
                raise AlgoComponentError('The server process ended badly.')
        return rc

    def spawn_hook(self):
        """Last chance to say something before execution."""
        pass

    def spawn(self, args, opts):
        """
        Spawn in the current system the command as defined in raw ``args``.

        The followings environment variables could drive part of the execution:

          * VORTEX_DEBUG_ENV : dump current environment before spawn
        """
        sh = self.system

        if self.env.true('vortex_debug_env'):
            sh.subtitle('{0:s} : dump environment (os bound: {1:s})'.format(
                self.realkind,
                str(self.env.osbound())
            ))
            self.env.osdump()

        # On-the-fly coprocessing initialisation
        p_io, e_complete, e_free, q_ctx = self.flyput_begin()

        sh.subtitle('{0:s} : directory listing (pre-execution)'.format(self.realkind))
        sh.remove('core')
        sh.softlink('/dev/null', 'core')
        sh.dir(output=False, fatal=False)
        self.spawn_hook()
        self.target.spawn_hook(sh)
        sh.subtitle('{0:s} : start execution'.format(self.realkind))
        sh.spawn(args, output=False, fatal=opts.get('fatal', True))

        # On-the-fly coprocessing cleaning
        if p_io:
            self.flyput_end(p_io, e_complete, e_free, q_ctx)

    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        return dict()

    def spawn_command_line(self, rh):
        """Split the shell command line of the resource to be run."""
        opts = self.spawn_command_options()
        return shlex.split(rh.resource.command_line(**opts))

    def execute_single(self, rh, opts):
        """Abstract method.

        When server_run is True, this method is used to start the server.
        Otherwise, this method is called by each :meth:`execute` call.
        """
        pass

    def execute(self, rh, opts):
        """Abstract method."""
        if self.server_run:
            # First time here ?
            if self._server_synctool is None:
                if self.serversync_method is None:
                    raise ValueError('The serversync_method must be provided.')
                self._server_synctool = footprints.proxy.serversynctool(
                    method = self.serversync_method,
                    medium = self.serversync_medium,
                )
                self._server_synctool.set_servercheck_callback(self.server_alive)
                self.server_begin(rh, opts)
                # Wait for the first request
                self._server_synctool.trigger_wait()
            # Acknowledge that we are ready and wait for the next request
            self._server_synctool.trigger_run()
        else:
            self.execute_single(rh, opts)

    def execute_finalise(self, opts):
        """Abstract method.

        This method is called inconditionaly when :meth:`execute` exits (even
        if an Exception was raised).
        """
        if self.server_run:
            self.server_end()

    def postfix(self, rh, opts):
        """Some basic informations."""
        self.system.subtitle('{0:s} : directory listing (post-run)'.format(self.realkind))
        self.system.dir(output=False, fatal=False)

    def dumplog(self, opts):
        """Dump to local file the internal log of the current algo component."""
        self.system.pickle_dump(self.fslog, 'log.' + self.fstag())

    def delayed_exceptions(self, opts):
        """Gather all the delayed exceptions and raises one if necessary."""
        if len(self._delayed_excs) > 0:
            excstmp = self._delayed_excs
            self._delayed_excs = list()
            raise DelayedAlgoComponentError(excstmp)

    def valid_executable(self, rh):
        """
        Return a boolean value according to the effective executable nature
        of the resource handler provided.
        """
        return True

    def abortfabrik(self, step, msg):
        """A shortcut to avoid next steps of the run."""
        def fastexit(self, *args, **kw):
            logger.warning('Run <%s> skipped because abort occured [%s]', step, msg)
        return fastexit

    def abort(self, msg='Not documented'):
        """A shortcut to avoid next steps of the run."""
        for step in ('prepare', 'execute', 'postfix'):
            setattr(self, step, self.abortfabrik(step, msg))

    def run(self, rh=None, **kw):
        """Sequence for execution : prepare / execute / postfix."""
        self._status = True

        # Get instance shorcuts to context and system objects
        self.ticket  = vortex.sessions.current()
        self.context = self.ticket.context
        self.system  = self.context.system
        self.target  = kw.pop('target', None)
        if self.target is None:
            self.target = self.system.target()

        # Before trying to do anything, check the executable
        if not self.valid_executable(rh):
            logger.warning('Resource %s is not a valid executable', rh.resource)
            return False

        # A cloned environment will be bound to the OS
        self.env = self.context.env.clone()
        with self.env:

            # The actual "run" recipe
            self.prepare(rh, kw)            #1
            self.fsstamp(kw)                #2
            try:
                self.execute(rh, kw)        #3
            finally:
                self.execute_finalise(kw)   #3.1
            self.fscheck(kw)                #4
            self.postfix(rh, kw)            #5
            self.dumplog(kw)                #6
            self.delayed_exceptions(kw)     #7

        # Free local references
        self.env = None
        self.system = None

        return self._status

    def quickview(self, nb=0, indent=0):
        """Standard glance to objects."""
        tab = '  ' * indent
        print '{0}{1:02d}. {2:s}'.format(tab, nb, repr(self))
        for subobj in ( 'kind', 'engine', 'interpreter'):
            obj = getattr(self, subobj, None)
            if obj:
                print '{0}  {1:s}: {2:s}'.format(tab, subobj, str(obj))
        print

    def setlink(self, initrole=None, initkind=None, initname=None, inittest=lambda x: True):
        """Set a symbolic link for actual resource playing defined role."""
        initsec = [
            x for x in self.context.sequence.effective_inputs(role=initrole, kind=initkind)
            if inittest(x.rh)
        ]

        if not initsec:
            logger.warning(
                'Could not find logical role %s with kind %s - assuming already renamed',
                initrole, initkind
            )

        if len(initsec) > 1:
            logger.warning('More than one role %s with kind %s',
                           initrole, initkind)

        if initname is not None:
            for l in [ x.rh.container.localpath() for x in initsec ]:
                if not self.system.path.exists(initname):
                    self.system.symlink(l, initname)
                    break

        return initsec


class ExecutableAlgoComponent(AlgoComponent):
    """Component in charge of running executable resources."""

    _abstract  = True

    def valid_executable(self, rh):
        """
        Return a boolean value according to the effective executable nature
        of the resource handler provided.
        """
        return rh is not None


class xExecutableAlgoComponent(ExecutableAlgoComponent):
    """Component in charge of running executable resources."""

    _abstract  = True

    def valid_executable(self, rh):
        """
        Return a boolean value according to the effective executable nature
        of the resource handler provided.
        """
        rc = super(xExecutableAlgoComponent, self).valid_executable(rh)
        if rc:
            # Ensure that the input file is executable
            xrh = rh if isinstance(rh, (list, tuple)) else [rh, ]
            for arh in xrh:
                self.system.xperm(arh.container.localpath(), force=True)
        return rc


class TaylorRun(AlgoComponent):
    """
    Run any taylorism Worker in the current environment.

    This abstract class includes helpers to use the taylorism package in order
    to introduce an external parallelisation. It is designed to work well with a
    taylorism Worker class that inherits from
    :class:`vortex.tools.parallelism.TaylorVortexWorker`.
    """

    _abstract = True
    _footprint = dict(
        info = 'Abstract algo component based on the taylorism package.',
        attr = dict(
            kind = dict(),
            verbose = dict(
                info        = 'Run in verbose mode',
                type        = bool,
                default     = False,
                optional    = True,
                doc_zorder  = -50,
            ),
            ntasks = dict(
                info        = 'The maximum number of parallel tasks',
                type        = int,
                default     = DelayedEnvValue('VORTEX_SUBMIT_TASKS', 1),
                optional    = True
            ),
        )
    )

    def __init__(self, *kargs, **kwargs):
        super(TaylorRun, self).__init__(*kargs, **kwargs)
        self._boss = None

    def _default_common_instructions(self, rh, opts):
        '''Create a common instruction dictionary that will be used by the workers.'''
        return dict(kind=self.kind, )

    def _default_pre_execute(self, rh, opts):
        '''Various initialisations. In particular it creates the task scheduler (Boss).'''
        # Start the task scheduler
        self._boss = Boss(verbose=self.verbose,
                          scheduler=MaxThreadsScheduler(max_threads=self.ntasks))
        self._boss.make_them_work()

    def _add_instructions(self, common_i, individual_i):
        '''Give a new set of instructions to the Boss.'''
        self._boss.set_instructions(common_i, individual_i)

    def _default_post_execute(self, rh, opts):
        '''Summarise the results of the various tasks that were run.'''
        logger.info("All the input files were dealt with: now waiting for the parallel processing to finish")
        self._boss.wait_till_finished()
        logger.info("The parallel processing has finished. here are the results:")
        report = self._boss.get_report()
        prp = ParallelResultParser(self.context)
        for r in report['workers_report']:
            rc = prp(r)
            if isinstance(rc, Exception):
                self.delayed_exception_add(rc, traceback=False)
                rc = False
            self._default_rc_action(rh, opts, r, rc)

    def _default_rc_action(self, rh, opts, report, rc):
        '''How should we process the return code ?'''
        if not rc:
            logger.warning("Apparently something went sideways with this task (rc=%s).",
                           str(rc))

    def execute(self, rh, opts):
        """
        This should be adapted to your needs...

        A usual sequence is::

            self._default_pre_execute(rh, opts)
            common_i = _default_common_instructions(rh, opts)
            # Update the common instructions
            common_i.update(dict(someattribute='Toto', ))

            # Your own code here

            # Give some instructions to the boss
            self._add_instructions(common_i, dict(someattribute=['Toto', ],))

            # Your own code here

            self._default_post_execute(rh, opts)

        """
        raise NotImplementedError


class Expresso(ExecutableAlgoComponent):
    """Run a script resource in the good environment."""

    _footprint = dict(
        info = 'AlgoComponent that simply runs a script',
        attr = dict(
            interpreter = dict(
                info   = 'The interpreter needed to run the script.',
                values = ['awk', 'ksh', 'bash', 'perl', 'python']
            ),
            engine = dict(
                values = ['exec', 'launch']
            )
        )
    )

    def _interpreter_args_fix(self, rh, opts):
        absexec = self.absexcutable(rh.container.localpath())
        if self.interpreter == 'awk':
            return ['-f', absexec]
        else:
            return [absexec, ]

    def execute_single(self, rh, opts):
        """
        Run the specified resource handler through the current interpreter,
        using the resource command_line method as args.
        """
        args = [self.interpreter, ]
        args.extend(self._interpreter_args_fix(rh, opts))
        args.extend(self.spawn_command_line(rh))
        logger.debug('Run script %s', args)
        self.spawn(args, opts)


class ParaExpresso(TaylorRun):
    """
    Run any script in the current environment.

    This abstract class includes helpers to use the taylorism package in order
    to introduce an external parallelisation. It is designed to work well with a
    taylorism Worker class that inherits from
    :class:`vortex.tools.parallelism.VortexWorkerBlindRun`.
    """

    _abstract = True
    _footprint = dict(
        info = 'AlgoComponent that simply runs a script using the taylorism package.',
        attr = dict(
            interpreter = dict(
                info   = 'The interpreter needed to run the script.',
                values = ['awk', 'ksh', 'bash', 'perl', 'python']
            ),
            engine = dict(
                values = ['exec', 'launch']
            ),
        )
    )

    def valid_executable(self, rh):
        """
        Return a boolean value according to the effective executable nature
        of the resource handler provided.
        """
        return rh is not None

    def _default_common_instructions(self, rh, opts):
        '''Create a common instruction dictionary that will be used by the workers.'''
        ddict = super(ParaExpresso, self)._default_common_instructions(rh, opts)
        ddict['progname'] = self.interpreter
        ddict['progargs'] = footprints.FPList([self.absexcutable(rh.container.localpath()), ] +
                                              self.spawn_command_line(rh))
        return ddict


class BlindRun(xExecutableAlgoComponent):
    """
    Run any executable resource in the current environment. Mandatory argument is:
     * engine ( values =  blind )
    """

    _footprint = dict(
        info = 'AlgoComponent that simply runs a serial binary',
        attr = dict(
            engine = dict(
                values = ['blind']
            )
        )
    )

    def execute_single(self, rh, opts):
        """
        Run the specified resource handler as an absolute executable,
        using the resource command_line method as args.
        """

        args = [self.absexcutable(rh.container.localpath())]
        args.extend(self.spawn_command_line(rh))
        logger.debug('BlindRun executable resource %s', args)
        self.spawn(args, opts)


class ParaBlindRun(TaylorRun):
    """
    Run any executable resource (without MPI) in the current environment.

    This abstract class includes helpers to use the taylorism package in order
    to introduce an external parallelisation. It is designed to work well with a
    taylorism Worker class that inherits from
    :class:`vortex.tools.parallelism.VortexWorkerBlindRun`.
    """

    _abstract = True
    _footprint = dict(
        info = 'Abstract AlgoComponent that runs a serial binary using the taylorism package.',
        attr = dict(
            engine = dict(
                values = ['blind']
            ),
            taskset = dict(
                info = "Topology/Method to set up the CPU affinity of the child task.",
                default = None,
                optional = True,
                values = ['raw', 'socketpacked', 'socketpacked_gomp']
            ),
            taskset_bsize = dict(
                info        = 'The number of threads used by one task',
                type        = int,
                default     = 1,
                optional    = True
            ),
        )
    )

    def valid_executable(self, rh):
        """
        Return a boolean value according to the effective executable nature
        of the resource handler provided.
        """
        rc = rh is not None
        if rc:
            # Ensure that the input file is executable
            xrh = rh if isinstance(rh, (list, tuple)) else [rh, ]
            for arh in xrh:
                self.system.xperm(arh.container.localpath(), force=True)
        return rc

    def _default_common_instructions(self, rh, opts):
        '''Create a common instruction dictionary that will be used by the workers.'''
        ddict = super(ParaBlindRun, self)._default_common_instructions(rh, opts)
        ddict['progname'] = self.absexcutable(rh.container.localpath())
        ddict['progargs'] = footprints.FPList(self.spawn_command_line(rh))
        ddict['progtaskset'] = self.taskset
        ddict['progtaskset_bsize'] = self.taskset_bsize
        return ddict


class Parallel(xExecutableAlgoComponent):
    """
    Run a binary launched with MPI support.
    """

    _footprint = dict(
        info = 'AlgoComponent that simply runs an MPI binary',
        attr = dict(
            engine = dict(
                values   = ['parallel']
            ),
            mpitool = dict(
                info            = 'The object used to launch the parallel program',
                optional        = True,
                type            = mpitools.MpiTool,
                doc_visibility  = footprints.doc.visibility.GURU,
            ),
            mpiname = dict(
                info            = ('The mpiname of a class in the mpitool collector ' +
                                   '(used only if *mpitool* is not provided)'),
                optional        = True,
                alias           = ['mpi'],
                doc_visibility  = footprints.doc.visibility.GURU,
            ),
            binaries = dict(
                info            = 'List of MpiBinaryDescription objects',
                optional        = True,
                type            = footprints.FPList,
                doc_visibility  = footprints.doc.visibility.GURU,
            ),
            binarysingle = dict(
                info            = 'If *binaries* is missing, the default binary role for single binaries',
                optional        = True,
                default         = 'basicsingle',
                doc_visibility  = footprints.doc.visibility.GURU,
            ),
            binarymutli = dict(
                info            = 'If *binaries* is missing, the default binary role for multiple binaries',
                type            = footprints.FPList,
                optional        = True,
                default         = footprints.FPList(['basic', ]),
                doc_visibility  = footprints.doc.visibility.GURU,
            ),
            ioserver = dict(
                info            = 'The object used to launch the IOserver part of the binary.',
                type            = mpitools.MpiBinaryIOServer,
                optional        = True,
                default         = None,
                doc_visibility  = footprints.doc.visibility.GURU,
            ),
            ioname = dict(
                info            = ('The binary_kind of a class in the mpibinary collector ' +
                                   '(used only if *ioserver* is not provided)'),
                optional        = True,
                default         = 'ioserv',
                doc_visibility  = footprints.doc.visibility.GURU,
            ),
            iolocation = dict(
                info            = 'Location of the IO server within the binary list',
                type            = int,
                default         = -1,
                optional        = True
            )
        )
    )

    def prepare(self, rh, opts):
        """Add some defaults env values for mpitool itself."""
        super(Parallel, self).prepare(rh, opts)
        if opts.get('mpitool', True):
            self.export('mpitool')

    def spawn_command_line(self, rh):
        """Split the shell command line of the resource to be run."""
        return [super(Parallel, self).spawn_command_line(r) for r in rh]

    def _bootstrap_mpitool(self, rh, opts):
        """Initialise the mpitool object and finds out the command line."""

        # Rh is a list binaries...
        if not isinstance(rh, collections.Iterable):
            rh = [rh, ]

        # Find the MPI launcher
        mpi = self.mpitool
        if not mpi:
            mpi_extras = dict()
            if self.env.VORTEX_MPI_OPTS is not None:
                mpi_extras['mpiopts'] = self.env.VORTEX_MPI_OPTS
            mpi = footprints.proxy.mpitool(
                sysname = self.system.sysname,
                mpiname = self.mpiname or self.env.VORTEX_MPI_NAME,
                ** mpi_extras
            )
        if not mpi:
            logger.critical('Component %s could not find any mpitool', self.footprint_clsname())
            raise AttributeError('No valid mpitool attr could be found.')

        # Some MPI presets
        mpi_desc = dict()
        for mpi_k in ('tasks', 'openmp'):
            mpi_kenv = 'VORTEX_SUBMIT_' + mpi_k.upper()
            if mpi_kenv in self.env:
                mpi_desc[mpi_k] = self.env.get(mpi_kenv)

        # The usual case: no indications, 1 binary + a potential ioserver
        if len(rh) == 1 and not self.binaries:

            # The main program
            master = footprints.proxy.mpibinary(
                kind = self.binarysingle,
                nodes   = self.env.get('VORTEX_SUBMIT_NODES', 1),
                ** mpi_desc)
            master.options = opts.get('mpiopts', dict())
            master.master  = self.absexcutable(rh[0].container.localpath())
            bins = [master, ]

            # A potential IO server
            io = self.ioserver
            if not io and int(self.env.get('VORTEX_IOSERVER_NODES', -1)) >= 0:
                io = footprints.proxy.mpibinary(
                    kind = self.ioname,
                    tasks   = self.env.VORTEX_IOSERVER_TASKS  or master.tasks,
                    openmp  = self.env.VORTEX_IOSERVER_OPENMP or master.openmp)
                io.options = {x[3:]: opts[x]
                              for x in opts.keys() if x.startswith('io_')}
                io.master = master.master
            if io:
                rh.append(rh[0])
                master.options['nn'] = master.options['nn'] - io.options['nn']
                if self.iolocation >= 0:
                    bins.insert(self.iolocation, io)
                else:
                    bins.append(io)

        # Multiple binaries are to be launched: no IO server support here.
        elif len(rh) > 1 and not self.binaries:

            # Binary roles
            if len(self.binarymutli) == 1:
                bnames = self.binarymutli * len(rh)
            else:
                if len(self.binarymutli) != len(rh):
                    raise ParallelInconsistencyAlgoComponentError("self.binarymulti")
                bnames = self.binarymutli

            # Check mpiopts shape
            u_mpiopts = opts.get('mpiopts', dict())
            for k, v in u_mpiopts.iteritems():
                if not isinstance(v, collections.Iterable):
                    raise ValueError('In such a case, mpiopts must be Iterable')
                if len(v) != len(rh):
                    raise ParallelInconsistencyAlgoComponentError('mpiopts[{:s}]'.format(k))

            # Create MpiBinaryDescription objects
            bins = list()
            for i, r in enumerate(rh):
                bins.append(footprints.proxy.mpibinary(kind = bnames[i],
                                                       nodes   = self.env.get('VORTEX_SUBMIT_NODES', 1),
                                                       ** mpi_desc))
                # Reshape mpiopts
                bins[i].options = {k: v[i] for k, v in u_mpiopts.iteritems()}
                bins[i].master  = self.absexcutable(r.container.localpath())

        # Nothing to do: binary descriptions are provided by the user
        else:
            if len(self.binaries) != len(rh):
                    raise ParallelInconsistencyAlgoComponentError("self.binaries")
            bins = self.binaries
            for i, r in enumerate(rh):
                bins[i].master = self.absexcutable(r.container.localpath())

        # The binaries description
        mpi.binaries = bins

        # Find out the command line
        bargs = self.spawn_command_line(rh)
        args = mpi.mkcmdline(bargs)
        for r, a in zip(rh, bargs):
            logger.info('Run %s in parallel mode. Args: %s', r.container.localpath(), ' '.join(a))
        logger.info('Full MPI commandline: %s', ' '.join(args))

        return mpi, args

    def execute_single(self, rh, opts):
        """Run the specified resource handler through the `mitool` launcher

        An argument named `mpiopts` could be provided as a dictionary: it may
        contains indications on the number of nodes, tasks, ...
        """

        self.system.subtitle('{0:s} : parallel engine'.format(self.realkind))

        # Return a mpitool object and the mpicommand line
        mpi, args = self._bootstrap_mpitool(rh, opts)

        # Setup various usefull things (env, system, ...)
        mpi.import_basics(self)

        # Specific parallel settings
        mpi.setup(opts)

        # This is actual running command
        self.spawn(args, opts)

        # Specific parallel cleaning
        mpi.clean(opts)
