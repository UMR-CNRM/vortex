#!/bin/env python
# -*- coding:Utf-8 -*-

"""
This package handles MPI interface objects responsible of parallel executions.
The associated modules defines the catalog factory based on the shared footprint mechanism.
"""

#: No automatic export
__all__ = []

import re, sys, shlex

import footprints

from vortex.autolog import logdefault as logger
from vortex.utilities.catalogs import ClassesCollector, build_catalog_functions


class MpiException(Exception):
    """Raise an exception in the parallel execution mode."""
    pass

class MpiTool(footprints.BFootprint):
    """Root class for any :class:`MpiTool` subclasses."""

    _footprint = dict(
        info = 'MPI toolkit',
        attr = dict(
            sysname = dict(),
            mpiname = dict(),
            mpiopts = dict(
                optional = True,
                default = 'v'
            ),
            optprefix = dict(
                optional = True,
                default = '-'
            )
        )
    )

    def __init__(self, *args, **kw):
        """After parent initialization, set the master undefined."""
        logger.debug('Abstract mpi tool init %s', self.__class__)
        super(MpiTool, self).__init__(*args, **kw)
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

    def setoptions(self, system, e, opts=None):
        """Raw list of mpi tool command line options."""
        self._options = dict()
        klast = None
        for optdef in shlex.split(self.mpiopts):
            if optdef.startswith('-'):
                optdef = optdef.lstrip('-')
                self._options[optdef] = None
                klast = optdef
            elif klast != None:
                self._options[klast] = optdef
            else:
                raise MpiException('Badly shaped mpi option around %s', optdef)
        if opts:
            for k, v in opts.items():
                self._options[k.lstrip('-')] = v
        if 'nn' not in self._options:
            self._options['nn'] = e.SWAPP_SUBMIT_NODES
        if 'nnp' not in self._options:
            self._options['nnp'] = e.SWAPP_SUBMIT_TASKS
        return self._options

    def setmaster(self, master):
        """Keep a copy of local master pathname."""
        self._master = master

    def commandline(self, system, e, args):
        """Builds the mpi command line."""
        cmdl = [ self.launcher(system, e) ]
        for k, v in self._options.items():
            cmdl.append(self.optprefix + str(k))
            if v != None:
                cmdl.append(str(v))
        if self._master == None:
            raise MpiException('No master defined before launching MPI')
        if self.optprefix == '--':
            cmdl.append('--')
        cmdl.append(self._master)
        cmdl.extend(args)
        return cmdl

    def setup_namelists(self, ctx, target=None, opts=None):
        """Braodcast number of MPI tasks to namelists."""

        # Figure out what is the effective number of tasks
        if 'np' in self._options:
            nbproc = int(self._options['np'])
        else:
            nbproc = int(self._options.get('nnp', 1)) * int(self._options.get('nn', 1))

        # Define the actual list of active namelist
        namcandidates = [ x.rh for x in ctx.sequence.effective_inputs(kind=('namelist', 'namelistfp')) ]
        if opts != None and 'loop' in opts:
            namcandidates = [ x for x in namcandidates if (hasattr(x.resource, 'term') and x.resource.term == opts['loop']) ]
        else:
            logger.warning('No loop option.')
        logger.warning('Namelist candidates %s', namcandidates)
        for namrh in namcandidates:
            namc = namrh.contents
            namw = False
            if 'NBPROC' in namc.macros():
                logger.info('Setup NBPROC=%s in %s', nbproc, namrh.container.localpath())
                namc.setmacro('NBPROC', nbproc)
                namc.setmacro('NCPROC', nbproc)
                namc.setmacro('NDPROC', 1)
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

    def setup_environment(self, ctx, target, opts):
        """Fix some environmental or behavior according to target definition."""
        if target.config.has_section('mpienv'):
            for k, v in target.config.items('mpienv'):
                logger.info('Setting MPI env %s = %s', k, v)
                ctx.env[k] = str(v)

    def setup(self, ctx, target=None, opts=None):
        """Specific MPI settings before running."""
        self.setup_namelists(ctx, target, opts)
        if target:
            self.setup_environment(ctx, target, opts)

    def clean(self, ctx, target=None, opts=None):
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
        """
        Define defaults regular expresion for module search, list of tracked classes
        and the item entry name in pickled footprint resolution.
        """
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
        """The entry point for global catalogs table. -- Here: mpitools."""
        return 'mpitools'


build_catalog_functions(sys.modules.get(__name__), MpiToolsCatalog)
