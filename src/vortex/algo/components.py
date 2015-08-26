#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import shlex
import multiprocessing

import footprints
logger = footprints.loggers.getLogger(__name__)

import vortex
from vortex.algo  import mpitools
from vortex.tools import date


class AlgoComponent(footprints.FootprintBase):
    """Component in charge of running executable resources."""

    _abstract  = True
    _collector = ('component',)
    _footprint = dict(
        info = 'Abstract algo component',
        attr = dict(
            engine = dict(
                values   = [ 'algo' ]
            ),
            flyput = dict(
                optional = True,
                default  = False,
                access   = 'rwx',
            ),
            flypoll = dict(
                optional = True,
                default  = 'io_poll',
                access   = 'rwx',
            ),
            flyargs = dict(
                type     = footprints.FPTuple,
                optional = True,
                default  = footprints.FPTuple(),
            ),
            timeout = dict(
                type     = int,
                optional = True,
                default  = 120,
            ),
        )
    )

    def __init__(self, *args, **kw):
        """Before parent initialization, preset the internal FS log to an empty list."""
        logger.debug('Algo component init %s', self.__class__)
        self._fslog = list()
        self._promises = None
        self._expected = None
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
                x.rh for x in self.context.sequence.outputs()
                if x.rh.provider.expected
            ]
        return self._promises

    @property
    def expected_resources(self):
        """Return the list of really expected inputs."""
        if self._expected is None:
            self._expected = [
                x.rh for x in self.context.sequence.effective_inputs()
                if x.rh.is_expected()
            ]
        return self._expected

    def grab(self, rh, comment='resource', fatal=True, sleep=10, timeout=None):
        """Wait for a given resource and get it if expected."""
        local = rh.container.localpath()
        self.system.header('Wait for ' + comment + ' ... [' + local + ']')
        if timeout is None:
            timeout = self.timeout
        if rh.wait(timeout=timeout, sleep=sleep):
            if rh.is_expected():
                rh.get(incache=True, insitu=False, fatal=fatal)
        elif fatal:
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
        sh = self.system
        absx = sh.path.abspath(xfile)
        sh.xperm(absx, force=True)
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
            if any([ x.container.basename.startswith(arg) for x in self.promises ]):
                logger.info(
                    'Match some promise %s',
                    str([ x.container.basename for x in self.promises if x.container.basename.startswith(arg) ])
                )
                actual_args.append(arg)
            else:
                logger.info('Do not match any promise %s', str([ x.container.basename for x in self.promises ]))
        return actual_args

    def flyput_sleep(self):
        """Return a sleeping time in seconds between io_poll commands."""
        return getattr(self, 'io_poll_sleep', self.env.get('IO_POLL_SLEEP', 20))

    def flyput_job(self, io_poll_method, io_poll_args, event_complete, event_free):
        """Poll new data resources."""
        logger.info('Polling with method %s', str(io_poll_method))
        logger.info('Polling with args %s', str(io_poll_args))

        time_sleep = self.flyput_sleep()
        redo = True

        while redo and not event_complete.is_set():
            data = list()
            event_free.clear()
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
                    candidates = [ x for x in self.promises if x.container.basename == thisdata ]
                    if candidates:
                        logger.info('Polled data is promised <%s>', thisdata)
                        bingo = candidates.pop()
                        bingo.put(incache=True)
                    else:
                        logger.warning('Polled data not promised <%s>', thisdata)
            except Exception as trouble:
                logger.error('Polling trouble: %s', str(trouble))
                redo = False
            finally:
                event_free.set()
            if redo and not data:
                logger.info('Get asleep for %d seconds...', time_sleep)
                self.system.sleep(time_sleep)

        if redo:
            logger.info('Polling exit on complete event')
        else:
            logger.warning('Polling exit on abort')

    def flyput_begin(self):
        """Launch a co-process to handle promises."""

        nope = (None, None, None)
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

        p_io = multiprocessing.Process(
            name   = self.footprint_clsname(),
            target = self.flyput_job,
            args   = (io_poll_method, io_poll_args, event_stop, event_free),
        )

        # The co-process is started
        p_io.start()

        return (p_io, event_stop, event_free)

    def flyput_end(self, p_io, e_complete, e_free):
        """Wait for the co-process in charge of promises."""
        e_complete.set()
        logger.info('Waiting for polling process... <%s>', p_io.pid)
        t0 = date.now()
        e_free.wait(60)
        p_io.join(30)
        t1 = date.now()
        waiting = t1 - t0
        logger.info('Waiting for polling process took %f seconds', waiting.total_seconds())
        if p_io.is_alive():
            logger.warning('Force termination of polling process')
            p_io.terminate()
        logger.info('Polling still alive ? %s', str(p_io.is_alive()))
        return not p_io.is_alive()

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
        p_io, e_complete, e_free = self.flyput_begin()

        sh.subtitle('{0:s} : directory listing (pre-execution)'.format(self.realkind))
        sh.remove('core')
        sh.softlink('/dev/null', 'core')
        sh.dir(output=False)
        self.spawn_hook()
        self.target.spawn_hook(sh)
        sh.subtitle('{0:s} : start execution'.format(self.realkind))
        sh.spawn(args, output=False, fatal=opts.get('fatal', True))
        sh.subtitle('{0:s} : directory listing (post-execution)'.format(self.realkind))
        sh.dir(output=False)

        # On-the-fly coprocessing cleaning
        if p_io:
            self.flyput_end(p_io, e_complete, e_free)

    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        return dict()

    def spawn_command_line(self, rh):
        """Split the shell command line of the resource to be run."""
        opts = self.spawn_command_options()
        return shlex.split(rh.resource.command_line(**opts))

    def execute(self, rh, opts):
        """Abstract method."""
        pass

    def postfix(self, rh, opts):
        """Abstract method."""
        pass

    def dumplog(self, opts):
        """Dump to local file the internal log of the current algo component."""
        self.system.pickle_dump(self.fslog, 'log.' + self.fstag())

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

    def run(self, rh, **kw):
        """Sequence for execution : prepare / execute / postfix."""
        self._status = True

        # Before trying to do anything, check the executable
        if not self.valid_executable(rh):
            logger.warning('Resource %s is not a valid executable', rh.resource)
            return False

        # Get instance shorcuts to context and system objects
        self.ticket  = vortex.sessions.current()
        self.context = self.ticket.context
        self.system  = self.context.system
        self.target  = kw.pop('target', None)
        if self.target is None:
            self.target = self.system.target()

        # A cloned environment is now bound to OS
        self.env = self.context.env.clone()
        self.env.active(True)

        # The actual "run" recipe
        self.prepare(rh, kw)        #1
        self.fsstamp(kw)            #2
        self.execute(rh, kw)        #3
        self.fscheck(kw)            #4
        self.postfix(rh, kw)        #5
        self.dumplog(kw)            #6

        # Restore previous OS environement and free local references
        self.env.active(False)
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
        initrh = [
            x.rh for x in self.context.sequence.effective_inputs(role=initrole, kind=initkind)
            if inittest(x.rh)
        ]

        if not initrh:
            logger.warning(
                'Could not find logical role %s with kind %s - assuming already renamed',
                initrole, initkind
            )

        if len(initrh) > 1:
            logger.warning('More than one role %s with kind %s %s', initrole, initkind, initrh)

        if initname is not None:
            for l in [ x.container.localpath() for x in initrh ]:
                if not self.system.path.exists(initname):
                    self.system.symlink(l, initname)
                    break

        return initrh


class Expresso(AlgoComponent):
    """
    Run a script resource in the good environment. Mandatory arguments are:
     * interpreter (values = awk, ksh, bash, perl, python)
     * engine ( values =  exec, launch )
    """

    _footprint = dict(
        attr = dict(
            interpreter = dict(
                values = ['awk', 'ksh', 'bash', 'perl', 'python']
            ),
            engine = dict(
                values = ['exec', 'launch']
            )
        )
    )

    def execute(self, rh, opts):
        """
        Run the specified resource handler through the current interpreter,
        using the resource command_line method as args.
        """
        args = [ self.interpreter, rh.container.localpath() ]
        args.extend(self.spawn_command_line(rh))
        logger.debug('Run script %s', args)
        self.spawn(args, opts)


class BlindRun(AlgoComponent):
    """
    Run any executable resource in the current environment. Mandatory argument is:
     * engine ( values =  blind )
    """

    _footprint = dict(
        attr = dict(
            engine = dict(
                values = ['blind']
            )
        )
    )

    def execute(self, rh, opts):
        """
        Run the specified resource handler as an absolute executable,
        using the resource command_line method as args.
        """

        args = [ self.absexcutable(rh.container.localpath()) ]
        args.extend(self.spawn_command_line(rh))
        logger.debug('BlindRun executable resource %s', args)
        self.spawn(args, opts)


class Parallel(AlgoComponent):
    """
    Run a binary launched with MPI support.
    """

    _footprint = dict(
        attr = dict(
            engine = dict(
                values   = ['parallel']
            ),
            mpitool = dict(
                optional = True,
                type     = mpitools.MpiSubmit
            ),
            mpiname = dict(
                optional = True,
                alias    = ['mpi'],
            ),
            ioserver = dict(
                type     = mpitools.MpiServerIO,
                optional = True,
                default  = None,
            ),
        )
    )

    def prepare(self, rh, opts):
        """Add some defaults env values for mpitool itself."""
        super(Parallel, self).prepare(rh, opts)
        if opts.get('mpitool', True):
            self.export('mpitool')

    def execute(self, rh, opts):
        """
        Run the specified resource handler through the `mitool` launcher,
        using the resource command_line method as args.
        A argument named `mpiopts` could be provided as a dictionary.
        """
        mpi = self.mpitool
        if not mpi:
            mpi_desc = dict(
                sysname = self.system.sysname,
                mpiname = self.mpiname or self.env.VORTEX_MPI_NAME,
                nodes   = self.env.get('VORTEX_SUBMIT_NODES', 1),
            )
            for mpi_k in ('tasks', 'openmp'):
                mpi_kenv = 'VORTEX_SUBMIT_' + mpi_k.upper()
                if mpi_kenv in self.env:
                    mpi_desc[mpi_k] = self.env.get(mpi_kenv)
            mpi = footprints.proxy.mpitool(**mpi_desc)

        if not mpi:
            logger.critical('Component %s could not find any mpitool', self.footprint_clsname())
            raise AttributeError('No valid mpitool attr could be found.')

        mpi.import_basics(self)
        mpi.options = opts.get('mpiopts', dict())
        mpi.master  = self.absexcutable(rh.container.localpath())

        self.system.subtitle('{0:s} : parallel engine'.format(self.realkind))
        print mpi

        io = self.ioserver
        if not io and int(self.env.get('VORTEX_IOSERVER_NODES', 0)) > 0:
            io = footprints.proxy.mpitool(
                io      = True,
                sysname = self.system.sysname,
                nodes   = self.env.VORTEX_IOSERVER_NODES,
                tasks   = self.env.VORTEX_IOSERVER_TASKS  or mpi.tasks,
                openmp  = self.env.VORTEX_IOSERVER_OPENMP or mpi.openmp,
            )

        # Building full command line options, including executable options and optional io server
        args = list()
        if io:
            io.import_basics(self)
            io.options = {x[3:]: opts[x]
                          for x in opts.keys() if x.startswith('io_')}
            mpi.options['nn'] = mpi.options['nn'] - io.options['nn']
            io.master = mpi.master
            args = io.mkcmdline(self.spawn_command_line(rh))

        args[:0] = mpi.mkcmdline(self.spawn_command_line(rh))
        logger.info('Run in parallel mode %s', args)

        # Specific parallel settings
        mpi.setup(opts)
        if io:
            io.setup(opts)

        # This is actual running command
        self.spawn(args, opts)

        # Specific parallel cleaning
        if io:
            io.clean(opts)
        mpi.clean(opts)
