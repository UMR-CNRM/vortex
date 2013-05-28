#!/bin/env python
# -*- coding:Utf-8 -*-

"""
This package handles MPI interface objects responsible of parallel executions.
The associated modules defines the catalog factory based on the shared footprint mechanism.
"""

#: No automatic export
__all__ = []

import re, sys, shlex
from vortex.autolog import logdefault as logger
from vortex.syntax import BFootprint
from vortex.utilities.catalogs import ClassesCollector, cataloginterface


class MpiTool(BFootprint):
    """Root class for any :class:`MpiTool` subclasses."""

    _footprint = dict(
        info = 'MPI toolkit',
        attr = dict(
            sysname = dict(),
            mpiname = dict(),
            mpiopts = dict(
                optional = True,
                default = '-v'
            )
        )
    )
    
    def __init__(self, *args, **kw):
        logger.debug('Abstract mpi tool init %s', self.__class__)
        super(MpiTool, self).__init__(*args, **kw)
        self.setoptions()
        self.setmaster(None)

    @property
    def realkind(self):
        return 'mpitool'

    def launcher(self, system, e):
        """
        Returns the name of the mpi tool to be used,
        coming either from VORTEX_MPI_LAUNCHER environment variable
        or the current attribute :attr:`mpiname`.
        """
        if 'vortex_mpi_launcher' in e:
            return e.vortex_mpi_launcher
        else:
            return self.mpiname

    def setoptions(self, opts=None):
        """Raw list of mpi tool command line options."""
        self._options = dict()
        klast = None
        for optdef in shlex.split(self.mpiopts):
            if optdef.startswith('-'):
                self._options[optdef] = None
                klast = optdef
            elif klast != None:
                self._options[klast] = optdef
            else:
                raise Exception('Badly shaped mpi option around %s', optdef)
        if opts:
            for k, v in opts.items():
                if not k.startswith('-'):
                    k = '-' + k
                self._options[k] = v
        return self._options

    def setmaster(self, master):
        """Keep a copy of local master pathname."""
        self._master = master

    def commandline(self, system, e, args):
        """Builds the mpi command line."""
        cmdl = [ self.launcher(system, e) ]
        for k, v in self._options.items():
            cmdl.append(str(k))
            if v != None:
                cmdl.append(str(v))
        if self._master == None:
            raise Exception('No master defined before launching MPI')
        cmdl.append(self._master)
        cmdl.extend(args)
        return cmdl

    def setup_namelists(self, ctx, target=None):
        """Braodcast number of MPI tasks to namelists."""
        if '-np' in self._options:
            nbproc = int(self._options['-np'])
        else:
            nbproc = int(self._options.get('-nnp', 1)) * int(self._options.get('-nn', 1))
        for namrh in [ x.rh for x in ctx.sequence.effective_inputs(kind='namelist') ]:
            namc = namrh.contents
            namw = False
            if 'NBPROC' in namc.macros():
                logger.info('Setup NBPROC=%s in %s', nbproc, namrh.container.localpath())
                namc.setmacro('NBPROC', nbproc)
                namw = True
            if 'NAMPAR1' in namc:
                np1 = namc['NAMPAR1']
                for nstr in [ x for x in ('NSTRIN', 'NSTROUT') if x in np1 ]:
                    if np1[nstr] > nbproc:
                        logger.info('Setup %s=%s in NAMPAR1 %s', nstr, nbproc, namrh.container.localpath())
                        np1[nstr] = nbproc
                        namw = True
            if namw:
                namc.rewrite(namrh.container)

    def setup_environment(self, ctx, target):
        """Fix some environmental or behavior according to target definition."""
        if target.config.has_section('mpienv'):
            for k, v in target.config.items('mpienv'):
                logger.info('Setting MPI env %s = %s', k, v)
                ctx.env[k] = str(v)

    def setup(self, ctx, target=None):
        """Specific MPI settings before running."""
        self.setup_namelists(ctx, target)
        if target:
            self.setup_environment(ctx, target)

    def clean(self, ctx, target=None):
        """Abstract method fot the time being."""
        pass


class MpiRun(MpiTool):
    """Standard MPI launcher on most systems."""

    _footprint = dict(
        attr = dict(
            sysname = dict(
                values = [ 'Linux' ]
            ),
            mpiname = dict(
                values = [ 'mpirun', 'mpiperso', 'default' ],
                remap = dict(default='mpirun')
            )
        )
    )


class MpiToolsCatalog(ClassesCollector):
    """Class in charge of collecting :class:`MpiTool` items."""

    def __init__(self, **kw):
        logger.debug('Mpi tools catalog init %s', self)
        cat = dict(
            remod = re.compile(r'.*\.mpitools'),
            classes = [ MpiTool ],
            itementry = 'mpitool'
        )
        cat.update(kw)
        super(MpiToolsCatalog, self).__init__(**cat)

    @classmethod
    def tablekey(cls):
        return 'mpitools'


cataloginterface(sys.modules.get(__name__), MpiToolsCatalog)
