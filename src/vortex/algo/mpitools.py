#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
This package handles MPI interface objects responsible of parallel executions.
MpiTool objects use the :mod:`footprints` mechanism.
"""

#: No automatic export
__all__ = []

import shlex

import footprints
from vortex.tools import env
from vortex.autolog import logdefault as logger


class MpiException(Exception):
    """Raise an exception in the parallel execution mode."""
    pass


class MpiTool(footprints.FootprintBase):
    """Root class for any :class:`MpiTool` subclasses."""

    _abstract  = True
    _collector = ('mpitool',)
    _footprint = dict(
        info = 'MPI toolkit',
        attr = dict(
            sysname = dict(),
            mpiopts = dict(
                optional = True,
                default  = ''
            ),
            nodes = dict(
                type     = int,
                optional = True,
                default  = 1,
                access   = 'rwx'
            ),
            tasks = dict(
                type     = int,
                optional = True,
                default  = 4,
                access   = 'rwx'
            ),
            openmp = dict(
                type     = int,
                optional = True,
                default  = 6,
                access   = 'rwx'
            ),
            optsep = dict(
                optional = True,
                default  = '--'
            ),
            optprefix = dict(
                optional = True,
                default  = '--'
            ),
            basics = dict(
                type     = footprints.FPList,
                optional = True,
                default  = footprints.FPList('system', 'env', 'target', 'context')
            )
        )
    )

    def __init__(self, *args, **kw):
        """After parent initialization, set master, options and basics undefined."""
        logger.debug('Abstract mpi tool init %s', self.__class__)
        super(MpiTool, self).__init__(*args, **kw)
        self._master = None
        self._options = None
        for k in self.basics:
            self.__dict__['_' + k] = None

    @property
    def realkind(self):
        return 'mpitool'

    def __getattr__(self, key):
        """Have a look to basics values provided by some proxy."""
        if key in self.basics:
            return getattr(self, '_' + key)
        else:
            raise AttributeError('Attribute [%s] is not a basic mpitool attribute' % key)

    def import_basics(self, obj, attrs=None):
        """Import some current values such as system, env, target and context from provided ``obj``."""
        if attrs is None:
            attrs = self.basics
        for k in [ x for x in attrs if x in self.basics and hasattr(obj, x) ]:
            setattr(self, '_' + k, getattr(obj, k))

    def _get_options(self):
        """Retrieve current set of mpitool command line options."""
        if self._options is None:
            self._set_options(None)
        return self._options

    def _set_options(self, value=None):
        """Raw list of mpi tool command line options."""
        self._options = dict()
        if value is None:
            value = dict()
        klast = None
        for optdef in shlex.split(self.mpiopts):
            if optdef.startswith('-'):
                optdef = optdef.lstrip('-')
                self._options[optdef] = None
                klast = optdef
            elif klast is not None:
                self._options[klast] = optdef
            else:
                raise MpiException('Badly shaped mpi option around %s', optdef)
        if self.nodes is not None:
            self._options['nn'] = self.nodes
        if self.tasks is not None:
            self._options['nnp'] = self.tasks
        if self.openmp is not None:
            self._options['openmp'] = self.openmp
        for k, v in value.items():
            self._options[k.lstrip('-').lower()] = v

    options = property(_get_options, _set_options)

    @property
    def nprocs(self):
        """Figure out what is the effective number of tasks."""
        if 'np' in self.options:
            nbproc = int(self.options['np'])
        else:
            nbproc = int(self.options.get('nnp', 1)) * int(self.options.get('nn', 1))
        return nbproc

    def _get_master(self):
        """Retrieve the master binary name that should be used."""
        return self._master

    def _set_master(self, master):
        """Keep a copy of local master pathname."""
        self._master = master

    master = property(_get_master, _set_master)

    def clean(self, opts=None):
        """Abstract method for post-execution cleaning."""
        pass

    def find_namelists(self, opts=None):
        """Find any namelists candidates in actual context inputs."""
        namcandidates = [ x.rh for x in self.context.sequence.effective_inputs(kind=('namelist', 'namelistfp')) ]
        if opts is not None and 'loop' in opts:
            namcandidates = [
                x for x in namcandidates
                if (hasattr(x.resource, 'term') and x.resource.term == opts['loop'])
            ]
        else:
            logger.info('No loop option in current parallel execution.')
        self.system.subtitle('Namelist candidates')
        for nam in namcandidates:
            nam.quickview()
        return namcandidates

    def setup_namelist_delta(self, namcontents, namlocal):
        """Abstract method for applying a delta: return False."""
        return False

    def setup_namelists(self, opts=None):
        """Braodcast some MPI information to input namelists."""
        for namrh in self.find_namelists(opts):
            namc = namrh.contents
            if self.setup_namelist_delta(namc, namrh.container.actualpath()):
                namc.rewrite(namrh.container)

    def setup_environment(self, opts):
        """Abstract mpi environment setup."""
        pass

    def setup(self, opts=None):
        """Specific MPI settings before running."""
        self.setup_namelists(opts)
        if self.target is not None:
            self.setup_environment(opts)


class MpiServerIO(MpiTool):
    """Standard MPI launcher interface."""

    _abstract = True
    _footprint = dict(
        attr = dict(
            io = dict(
                type = bool
            ),
        )
    )

    def __init__(self, *args, **kw):
        """After parent initialization, set launcher value."""
        logger.debug('Abstract mpi tool init %s', self.__class__)
        super(MpiServerIO, self).__init__(*args, **kw)
        thisenv = env.current()
        if self.tasks is None:
            self.tasks = thisenv.VORTEX_IOSERVER_TASKS
        if self.openmp is None:
            self.openmp = thisenv.VORTEX_IOSERVER_OPENMP

    def mkcmdline(self, args):
        """Builds the mpi command line."""
        if self.master is None:
            raise MpiException('No master defined before launching IO Server')
        cmdl = [ self.optsep ]
        for k, v in self.options.items():
            cmdl.append(self.optprefix + str(k))
            if v is not None:
                cmdl.append(str(v))
        cmdl.append(self.optsep)
        cmdl.append(self.master)
        cmdl.extend(args)
        return cmdl


class MpiSubmit(MpiTool):
    """Standard MPI launcher interface."""

    _abstract = True
    _footprint = dict(
        attr = dict(
            mpiname = dict(),
        ),
    )

    def __init__(self, *args, **kw):
        """After parent initialization, set launcher value."""
        logger.debug('Abstract mpi tool init %s', self.__class__)
        super(MpiSubmit, self).__init__(*args, **kw)
        thisenv = env.current()
        if 'vortex_mpi_launcher' in thisenv:
            self._launcher = thisenv.VORTEX_MPI_LAUNCHER
        else:
            self._launcher = self.mpiname

    def _get_launcher(self):
        """
        Returns the name of the mpi tool to be used, set from VORTEX_MPI_LAUNCHER environment variable
        or from the current attribute :attr:`mpiname` or explicit setting.
        """
        return self._launcher

    def _set_launcher(self, value):
        """Set current launcher mpi name. Should be some special trick, so issue a warning."""
        logger.warning('Setting a new value [%s] to mpi launcher [%s].' % value, self)
        self._launcher = value

    launcher = property(_get_launcher, _set_launcher)

    def mkcmdline(self, args):
        """Builds the mpi command line."""
        if self.master is None:
            raise MpiException('No master defined before launching MPI')
        cmdl = [ self.launcher ]
        for k, v in self.options.items():
            cmdl.append(self.optprefix + str(k))
            if v is not None:
                cmdl.append(str(v))
        if self.optprefix == '--':
            cmdl.append('--')
        cmdl.append(self.master)
        cmdl.extend(args)
        return cmdl

    def setup_namelist_delta(self, namcontents, namlocal):
        """Applying MPI profile on local namelist ``namlocal`` with contents namcontents."""
        namw = False
        if 'NBPROC' in namcontents.macros():
            logger.info('Setup NBPROC=%s in %s', self.nprocs, namlocal)
            namcontents.setmacro('NBPROC', self.nprocs)
            namcontents.setmacro('NCPROC', self.nprocs)
            namcontents.setmacro('NDPROC', 1)
            namw = True
        if 'NAMPAR1' in namcontents:
            np1 = namcontents['NAMPAR1']
            for nstr in [ x for x in ('NSTRIN', 'NSTROUT') if x in np1 ]:
                if np1[nstr] > self.nprocs:
                    logger.info('Setup %s=%s in NAMPAR1 %s', nstr, self.nprocs, namlocal)
                    np1[nstr] = self.nprocs
                    namw = True
        return namw

    def setup_environment(self, opts):
        """Fix some environmental or behavior according to target definition."""
        if self.target.config.has_section('mpienv'):
            for k, v in self.target.config.items('mpienv'):
                logger.debug('Setting MPI env %s = %s', k, v)
                self.env[k] = str(v)


class MpiRun(MpiSubmit):
    """Standard MPI launcher on most systems, e.g. `mpirun`."""

    _footprint = dict(
        attr = dict(
            sysname = dict(
                values  = ['Linux']
            ),
            mpiname = dict(
                values  = ['mpirun', 'mpiperso', 'default'],
                remap   = dict(
                    default = 'mpirun'
                ),
            ),
            optprefix = dict(
                default = '-'
            )
        )
    )

