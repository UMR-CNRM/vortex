#!/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re, sys
from vortex.autolog import logdefault as logger
from vortex import sessions
from vortex.syntax import BFootprint
from vortex.utilities.catalogs import ClassesCollector, cataloginterface

from vortex.utilities.decorators import printargs

import mpitools

class AlgoComponent(BFootprint):
    """
    Component in charge of running executable resources.
    """

    _footprint = dict(
        info = 'Abstract algo component',
        attr = dict(
            engine = dict(
                values = [ 'algo' ]
            )
        )
    )

    @classmethod
    def realkind(cls):
        """Default kind is ``algo``."""
        return 'algo'

    def fstag(self):
        """Defines a tag specific to the current algo component."""
        return '.'.join((self.realkind(), self.engine))

    def fsstamp(self, ctx, opts):
        """Ask the current context to put a stamp on file system."""
        ctx.fstrack_stamp(tag=self.fstag())

    def fscheck(self, ctx, opts):
        """Ask the current context to check changes on file system since last stamp."""
        self.fslog = ctx.fstrack_check(tag=self.fstag())

    def prepare(self, rh, ctx, opts):
        """Abstract method."""
        pass

    def absexcutable(self, xfile):
        """Retuns the absolute pathname of the ``xfile`` executable."""
        absx = self.system.path.abspath(xfile)
        self.system.chmod(absx, 0755)
        return absx

    @printargs
    def spawn(self, args):
        """
        Spawn in the current system the command as defined in raw ``args``.

        The followings environment variables could drive part of the execution:

          * VORTEX_DEBUG_ENV : dump current environment before spawn
        """
        e = self.env
        realkind = self.realkind()
        if e.true('vortex_debug_env'):
            self.system.subtitle('{0:s} : dump environment'.format(realkind))
            e.osdump()
            self.system.subtitle()
        self.system.subtitle('{0:s} : directory listing (pre-execution)'.format(realkind))
        self.system.dir()
        self.system.spawn(args)
        self.system.subtitle('{0:s} : directory listing (post-execution)'.format(realkind))
        self.system.dir()

    def spawn_command_line(self, rh, ctx):
        return rh.resource.command_line().split()

    def execute(self, rh, ctx, opts):
        """Abstract method."""
        pass

    def postfix(self, rh, ctx, opts):
        """Abstract method."""
        pass

    def valid_executable(self, rh):
        return True

    def run(self, rh, **kw):
        """Sequence for execution : prepare / execute / postfix."""
        self._status = True
        if not self.valid_executable(rh):
            logger.warning('Resource %s is not a valid executable', rh.resource)
            return False
        ctx = sessions.ticket().context
        self.system = ctx.system
        self.env = ctx.env
        self.prepare(rh, ctx, kw)
        self.fsstamp(ctx, kw)
        self.execute(rh, ctx, kw)
        self.fscheck(ctx, kw)
        self.postfix(rh, ctx, kw)
        self.env = None
        return self._status

class Expresso(AlgoComponent):
    """
    Run a script resource in the good environment. Mandatory arguments are:
     * interpreter (values = bash, perl, python)
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

    def execute(self, rh, ctx, kw):
        """
        Run the specified resource handler through the current interpreter,
        using the resource command_line method as args.
        """
        args = [ self.interpreter, rh.container.localpath() ]
        args.extend(self.spawn_command_line(rh, ctx))
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

    def execute(self, rh, ctx, kw):
        """
        Run the specified resource handler as an absolute executable,
        using the resource command_line method as args.
        """

        args = [ self.absexcutable(rh.container.localpath()) ]
        args.extend(self.spawn_command_line(rh, ctx))
        logger.debug('BlindRun executable resource %s', args)
        self.spawn(args)


class Parallel(AlgoComponent):
    """
    Run a binary launched with MPI support.
    """

    _footprint = dict(
        attr = dict(
            mpitool = dict(
                optional = True,
                type = mpitools.MpiTool
            ),
            mpiname = dict(
                optional = True,
                alias = [ 'mpi' ],
                default = 'mpirun'
            ),
            engine = dict(
                values = [ 'parallel' ]
            )
        )
    )

    def execute(self, rh, ctx, kw):
        """
        Run the specified resource handler through the `mitool` launcher,
        using the resource command_line method as args. A named argument `mpiopts`
        could be provided.
        """
        mpi = self.mpitool
        if not mpi:
            # TODO Eclipse parser is not smart enough to know about this "load" 
            mpi = mpitools.load(sysname=self.system.sysname, mpiname=self.mpiname)

        if not mpi:
            raise AttributeError, 'No valid mpitool attr could be found.'

        mpiopts = mpi.options(kw.get('mpiopts', dict()))
        args = [ mpi.launcher() ]
        args.extend(mpiopts)
        args.append(self.absexcutable(rh.container.localpath()))

        args.extend(self.spawn_command_line(rh, ctx))
        logger.debug('Run in parallel mode %s', args)
        mpi.setup()
        self.spawn(args)
        mpi.clean()


class AlgoComponentsCatalog(ClassesCollector):
    """Class in charge of collecting :class:`AlgoComponent` items."""

    def __init__(self, **kw):
        logger.debug('Algorithmic Components catalog init %s', self)
        cat = dict(
            remod = re.compile(r'.*\.algo'),
            classes = [ AlgoComponent ],
            itementry = AlgoComponent.realkind()
        )
        cat.update(kw)
        super(AlgoComponentsCatalog, self).__init__(**cat)

    @classmethod
    def tablekey(cls):
        return 'components'


cataloginterface(sys.modules.get(__name__), AlgoComponentsCatalog)

