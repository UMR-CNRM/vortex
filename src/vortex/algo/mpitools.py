#!/bin/env python
# -*- coding:Utf-8 -*-

r"""
This package handles MPI interface objects responsible of parallel executions.
The associated modules defines the catalog factory based on the shared footprint mechanism.
"""

#: No automatic export
__all__ = []

import re, sys
from vortex.autolog import logdefault as logger
from vortex.syntax import BFootprint
from vortex.tools import env
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


    @property
    def realkind(self):
        return 'mpitool'

    def setup(self):
        """Abstract method."""
        pass

    def clean(self):
        """Abstract method."""
        pass

    def launcher(self):
        """
        Returns the name of the mpi tool to be used,
        coming either from VORTEX_MPI_LAUNCHER environment variable
        or the current attribute :attr:`mpiname`.
        """
        e = env.current()
        if 'vortex_mpi_launcher' in e:
            return e.vortex_mpi_launcher
        else:
            return self.mpiname

    def options(self, kopts):
        """Raw list of mpi tool command line options."""
        opts = self.mpiopts.split()
        for x in kopts:
            opts.extend(['-' + x, str(kopts[x])])
        return opts



class MpiRun(MpiTool):
    """Standard MPI launcher on most systems."""

    _footprint = dict(
        attr = dict(
            sysname = dict(
                values = [ 'Linux' ]
            ),
            mpiname = dict(
                values = [ 'mpirun', 'mpiperso', 'default' ],
                remap = dict( default = 'mpirun' )
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
