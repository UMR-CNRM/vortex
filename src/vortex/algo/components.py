#!/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re
import shlex

import footprints

import vortex
from vortex.autolog import logdefault as logger
from vortex.algo import mpitools

class AlgoComponent(footprints.FootprintBase):
    """Component in charge of running executable resources."""

    _abstract  = True
    _collector = ('component',)
    _footprint = dict(
        info = 'Abstract algo component',
        attr = dict(
            engine = dict(
                values = [ 'algo' ]
            )
        )
    )

    def __init__(self, *args, **kw):
        """Before parent initialization, preset the internal FS log to an empty list."""
        logger.debug('Algo component init %s', self)
        self.fslog = list()
        super(AlgoComponent, self).__init__(*args, **kw)

    @property
    def realkind(self):
        """Default kind is ``algo``."""
        return 'algo'

    def fstag(self):
        """Defines a tag specific to the current algo component."""
        return '.'.join((self.realkind, self.engine))

    def fsstamp(self, opts):
        """Ask the current context to put a stamp on file system."""
        self.context.fstrack_stamp(tag=self.fstag())

    def fscheck(self, opts):
        """Ask the current context to check changes on file system since last stamp."""
        self.fslog.append(self.context.fstrack_check(tag=self.fstag()))

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
        self.system.chmod(absx, 0755)
        return absx

    def spawn_hook(self):
        """Last chance to say something before execution."""
        pass

    def spawn(self, args):
        """
        Spawn in the current system the command as defined in raw ``args``.

        The followings environment variables could drive part of the execution:

          * VORTEX_DEBUG_ENV : dump current environment before spawn
        """
        if self.env.true('vortex_debug_env'):
            self.system.subtitle('{0:s} : dump environment (os bound: {1:s})'.format(
                self.realkind,
                str(self.env.osbound())
            ))
            self.env.osdump()

        self.system.subtitle('{0:s} : directory listing (pre-execution)'.format(self.realkind))
        self.system.dir(output=False)
        self.spawn_hook()
        self.system.subtitle('{0:s} : start execution'.format(self.realkind))
        self.system.spawn(args, output=False)
        self.system.subtitle('{0:s} : directory listing (post-execution)'.format(self.realkind))
        self.system.dir(output=False)

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

    def run(self, rh, **kw):
        """Sequence for execution : prepare / execute / postfix."""
        self._status = True
        if not self.valid_executable(rh):
            logger.warning('Resource %s is not a valid executable', rh.resource)
            return False
        self.context = vortex.sessions.ticket().context
        self.system  = self.context.system
        self.env     = self.context.env
        self.target  = kw.pop('target', None)
        if self.target is None:
            self.target = self.system.target()
        self.prepare(rh, kw)
        self.fsstamp(kw)
        self.execute(rh, kw)
        self.fscheck(kw)
        self.postfix(rh, kw)
        self.dumplog(kw)
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

class Expresso(AlgoComponent):
    """
    Run a script resource in the good environment. Mandatory arguments are:
     * interpreter (values = ksh, bash, perl, python)
     * engine ( values =  exec, launch )
    """

    _footprint = dict(
        attr = dict(
            interpreter = dict(
                values = [ 'ksh', 'bash', 'perl', 'python' ]
            ),
            engine = dict(
                values = [ 'exec', 'launch' ]
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
        self.spawn(args)


class BlindRun(AlgoComponent):
    """
    Run any executable resource in the current environment. Mandatory argument is:
     * engine ( values =  blind )
    """

    _footprint = dict(
        attr = dict(
            engine = dict(
                values = [ 'blind' ]
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
        self.spawn(args)


class Parallel(AlgoComponent):
    """
    Run a binary launched with MPI support.
    """

    _footprint = dict(
        attr = dict(
            engine = dict(
                values = [ 'parallel' ]
            ),
            mpitool = dict(
                optional = True,
                type = mpitools.MpiSubmit
            ),
            mpiname = dict(
                optional = True,
                alias = [ 'mpi' ],
            ),
            ioserver = dict(
                optional = True,
                type = mpitools.MpiServerIO
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
            mpiname = self.mpiname or self.env.VORTEX_MPI_NAME
            mpi = footprints.proxy.mpitool(
                mpiname = mpiname,
                sysname = self.system.sysname,
                nodes   = self.env.VORTEX_SUBMIT_NODES,
                tasks   = self.env.VORTEX_SUBMIT_TASKS,
                openmp  = self.env.VORTEX_SUBMIT_OPENMP,
            )

        if not mpi:
            logger.critical('Component %s could not find any mpitool', self.shortname())
            raise AttributeError, 'No valid mpitool attr could be found.'

        mpi.import_basics(self)
        mpi.options = opts.get('mpiopts', dict())
        mpi.master  = self.absexcutable(rh.container.localpath())

        self.system.subtitle('{0:s} : parallel engine'.format(self.realkind))
        print mpi

        io = self.ioserver
        if not io and self.env.VORTEX_IOSERVER_NODES:
            io = footprints.proxy.mpitool(
                io      = True,
                sysname = self.system.sysname,
                nodes   = self.env.VORTEX_IOSERVER_NODES,
                tasks   = self.env.VORTEX_IOSERVER_TASKS,
                openmp  = self.env.VORTEX_IOSERVER_OPENMP,
            )

        # Building full command line options, including executable options and optional io server
        args = list()
        if io:
            io.import_basics(self)
            io.options = { x.lstrip('io_'):opts[x] for x in opts.keys() if x.startswith('io_') }
            mpi.options['nn'] = mpi.options['nn'] - io.options['nn']
            io.master  = mpi.master
            args = io.mkcmdline(self.spawn_command_line(rh))

        args[:0] = mpi.mkcmdline(self.spawn_command_line(rh))
        logger.info('Run in parallel mode %s', args)

        # Specific parallel settings
        mpi.setup(opts)
        if io:
            io.setup(opts)

        # This is actual running command
        self.spawn(args)

        # Specific parallel cleaning
        if io:
            io.clean(opts)
        mpi.clean(opts)
