#!/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re
import sys
import shlex

import vortex
from vortex.autolog import logdefault as logger
from vortex.syntax import BFootprint
from vortex.utilities.catalogs import ClassesCollector, build_catalog_functions
from vortex.tools import targets
from vortex.algo import mpitools

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

    @property
    def realkind(self):
        """Default kind is ``algo``."""
        return 'algo'

    def fstag(self):
        """Defines a tag specific to the current algo component."""
        return '.'.join((self.realkind, self.engine))

    def fsstamp(self, ctx, opts):
        """Ask the current context to put a stamp on file system."""
        ctx.fstrack_stamp(tag=self.fstag())

    def fscheck(self, ctx, opts):
        """Ask the current context to check changes on file system since last stamp."""
        self.fslog = ctx.fstrack_check(tag=self.fstag())

    def export(self, packenv):
        """Export environment variables in given pack."""
        if self.target.config.has_section(packenv):
            for k, v in self.target.config.items(packenv):
                logger.info('Setting %s env %s = %s', packenv.upper(), k, v)
                self.env[k] = v

    def prepare(self, rh, ctx, opts):
        """Set some defaults env values."""
        if opts.get('fortran', True):
            self.export('fortran')

    def absexcutable(self, xfile):
        """Retuns the absolute pathname of the ``xfile`` executable."""
        absx = self.system.path.abspath(xfile)
        self.system.chmod(absx, 0755)
        return absx

    def spawn(self, args):
        """
        Spawn in the current system the command as defined in raw ``args``.

        The followings environment variables could drive part of the execution:

          * VORTEX_DEBUG_ENV : dump current environment before spawn
        """
        if self.env.true('vortex_debug_env'):
            self.system.subtitle('{0:s} : dump environment (os bound: {1:s}'.format(
                self.realkind,
                str(self.env.osbound())
            ))
            self.env.osdump()

        self.system.subtitle('{0:s} : directory listing (pre-execution)'.format(self.realkind))
        self.system.dir(output=False)
        self.system.subtitle('{0:s} : start execution'.format(self.realkind))
        self.system.spawn(args, output=False)
        self.system.subtitle('{0:s} : directory listing (post-execution)'.format(self.realkind))
        self.system.dir(output=False)

    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        return dict()

    def spawn_command_line(self, rh, ctx):
        """Split the shell command line of the resource to be run."""
        opts = self.spawn_command_options()
        return shlex.split(rh.resource.command_line(**opts))

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
        ctx = vortex.sessions.ticket().context
        self.system = ctx.system
        self.env = ctx.env
        self.target = kw.setdefault('target', targets.default(hostname=self.system.hostname, sysname=self.system.sysname))
        del kw['target']
        self.prepare(rh, ctx, kw)
        self.fsstamp(ctx, kw)
        self.execute(rh, ctx, kw)
        self.fscheck(ctx, kw)
        self.postfix(rh, ctx, kw)
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
                print '{0}  {1:s}: {2:s}'.format(tab, subobj, obj)
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

    def execute(self, rh, ctx, opts):
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

    def execute(self, rh, ctx, opts):
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
            ),
            engine = dict(
                values = [ 'parallel' ]
            )
        )
    )

    def execute(self, rh, ctx, opts):
        """
        Run the specified resource handler through the `mitool` launcher,
        using the resource command_line method as args. A named argument `mpiopts`
        could be provided.
        """
        mpi = self.mpitool
        if not mpi:
            mpiname = self.mpiname
            if not mpiname:
                mpiname = self.env.VORTEX_MPI_NAME
            mpi = mpitools.load(sysname=self.system.sysname, mpiname=mpiname)

        if not mpi:
            logger.critical('Component %s could not find any mpitool', self.shortname())
            raise AttributeError, 'No valid mpitool attr could be found.'

        self.system.subtitle('{0:s} : parallel engine'.format(self.realkind))
        print mpi

        mpi.setoptions(self.system, self.env, opts.get('mpiopts', dict()))
        mpi.setmaster(self.absexcutable(rh.container.localpath()))

        args = mpi.commandline(self.system, self.env, self.spawn_command_line(rh, ctx))
        logger.info('Run in parallel mode %s', args)

        mpi.setup(ctx, self.target)
        self.spawn(args)
        mpi.clean(ctx, self.target)


class AlgoComponentsCatalog(ClassesCollector):
    """Class in charge of collecting :class:`AlgoComponent` items."""

    def __init__(self, **kw):
        logger.debug('Algorithmic Components catalog init %s', self)
        cat = dict(
            remod = re.compile(r'.*\.algo'),
            classes = [ AlgoComponent ],
            itementry = 'algo'
        )
        cat.update(kw)
        super(AlgoComponentsCatalog, self).__init__(**cat)

    @classmethod
    def tablekey(cls):
        return 'components'


build_catalog_functions(sys.modules.get(__name__), AlgoComponentsCatalog)

if __name__ == '__main__':
    e = Expresso(engine='exec', interpreter='bash')
    e.quickview(1, 0)

