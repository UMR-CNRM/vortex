#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
This package handles MPI interface objects responsible of parallel executions.
:class:`MpiTool` and :class:`MpiBinaryDescription` objects use the
:mod:`footprints` mechanism.

A :class:`MpiTool` object is directly related to a concrete MPI implementation: it
builds the proper command line, update the namelists with relevant MPI parameters
(for instance, the total number of tasks), update the environment to fit the MPI
implementation needs, ... It heavily relies on :class:`MpiBinaryDescription`
objects that describe the settings and behaviours associated with each of the
binaries that will be launched.

Here is a typical use of MpiTools:

.. code-block:: python

    # We will assume that bin0, bin1 are valid executable's Resource Handlers

    from footprints import proxy as fpx
    import vortex

    t = vortex.ticket()

    # Create the mpitool object for a given MPI implementation
    mpitool = fpx.mpitool(sysname=t.system().sysname,
                          mpiname='mpirun',  # To use Open-MPI's mpirun
                          )
    # NB: mpiname='...' may be omitted. In such a case, the VORTEX_MPI_NAME
    #     environment variable is used

    # Create the MPI binaires descriptions
    dbin0 = fpx.mpibinary(kind='basic', nodes=2, tasks=4, openmp=10)
    dbin0.master = bin0.container.localpath()
    dbin1 = fpx.mpibinary(kind='basic', nodes=1, tasks=8, openmp=5)
    dbin1.master = bin1.container.localpath()

    # Note: the number of nodes, tasks, ... can be overwritten at any time using:
    #       dbinX.options = dict(nn=M, nnp=N, openmp=P)

    # Associate the MPI binaires descriptions to the mpitool object
    mpitool.binaries = [dbin0, dbin1]

    bargs = ['-test bin0'    # Command line arguments for bin0
             '-test bin1' ]  # Command line arguments for bin1
    # Build the MPI command line :
    args = mpitool.mkcmdline(bargs)

    # Setup various usefull things (env, system, ...)
    mpitool.import_basics(an_algo_component_object)

    # Specific parallel settings (the namelists and environment may be modified here)
    mpitool.setup(dict())  # The dictionary may contain additional options

    # ...
    # Here you may run the command contained in *args*
    # ...

    # Specific parallel cleaning
    mpitool.clean(opts)

Actually, in real scripts, all of this is carried out by the
:class:`vortex.algo.components.Parallel` class which saves a lot of hassle.

Note: Namelists and environment changes are orchestrated as follows:
    * Changes (if any) are apply be the :class:`MpiTool` object
    * Changes (if any) are apply by each of the :class:`MpiBinaryDescription` objects
      attached to the MpiTool object

"""

from __future__ import absolute_import, division, print_function, unicode_literals

import collections
import shlex

import six

import footprints
from bronx.fancies import loggers
from vortex.tools import env

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class MpiException(Exception):
    """Raise an exception in the parallel execution mode."""
    pass


class MpiTool(footprints.FootprintBase):
    """Root class for any :class:`MpiTool` subclass."""

    _abstract  = True
    _collector = ('mpitool', )
    _footprint = dict(
        info = 'MpiTool class in charge of a particular MPI implementation',
        attr = dict(
            sysname = dict(
                info     = 'The current OS name (e.g. Linux)',
            ),
            mpiname = dict(
                info     = 'The MPI implementation one wishes to use',
            ),
            mpiopts = dict(
                info     = 'Extra arguments for the MPI command',
                optional = True,
                default  = ''
            ),
            optsep = dict(
                info     = 'Separator between MPI options and the program name',
                optional = True,
                default  = '--'
            ),
            optprefix = dict(
                info     = 'MPI options prefix',
                optional = True,
                default  = '--'
            ),
            optmap = dict(
                info     = ('Mapping between MpiBinaryDescription objects ' +
                            'internal data and actual command line options'),
                type     = footprints.FPDict,
                optional = True,
                default  = footprints.FPDict(nn='nn', nnp='nnp', openmp='openmp')
            ),
            binsep = dict(
                info     = 'Separator between multiple binary groups',
                optional = True,
                default  = '--'
            ),
            basics = dict(
                type     = footprints.FPList,
                optional = True,
                default  = footprints.FPList(['system', 'env', 'target', 'context'])
            ),
        )
    )

    def __init__(self, *args, **kw):
        """After parent initialization, set master, options and basics to undefined."""
        logger.debug('Abstract mpi tool init %s', self.__class__)
        super(MpiTool, self).__init__(*args, **kw)
        thisenv = env.current()
        self._launcher = thisenv.VORTEX_MPI_LAUNCHER or self.mpiname
        self._binaries = []
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
        for k in [x for x in attrs if x in self.basics and hasattr(obj, x)]:
            setattr(self, '_' + k, getattr(obj, k))
        for bin_obj in self.binaries:
            bin_obj.import_basics(obj, attrs=None)

    def _get_launcher(self):
        """
        Returns the name of the mpi tool to be used, set from VORTEX_MPI_LAUNCHER
        environment variable, current attribute :attr:`mpiname` or explicit setting.
        """
        return self._launcher

    def _set_launcher(self, value):
        """Set current launcher mpi name. Should be some special trick, so issue a warning."""
        logger.warning('Setting a new value [%s] to mpi launcher [%s].' % (value, self))
        self._launcher = value

    launcher = property(_get_launcher, _set_launcher)

    def _get_binaries(self):
        """Returns the list of :class:`MpiBinaryDescription` objects associated with this instance."""
        return self._binaries

    def _set_binaries(self, value):
        """Set the list of :class:`MpiBinaryDescription` objects associated with this instance."""
        if not (isinstance(value, collections.Iterable) and
                all([isinstance(b, MpiBinaryDescription) for b in value])):
            raise ValueError('This should be an Iterable of MpiBinaryDescription instances.')
        self._binaries = value

    binaries = property(_get_binaries, _set_binaries)

    def _reshaped_mpiopts(self):
        """Raw list of mpi tool command line options."""
        klast = None
        options = dict()
        for optdef in shlex.split(self.mpiopts):
            if optdef.startswith('-'):
                optdef = optdef.lstrip('-')
                options[optdef] = None
                klast = optdef
            elif klast is not None:
                options[klast] = optdef
            else:
                raise MpiException('Badly shaped mpi option around %s', optdef)
        return options

    def _hook_binary_mpiopts(self, options):
        """A nasty hook to modify binaries' mpiopts on the fly."""
        return options

    def mkcmdline(self, args):
        """Builds the MPI command line.

        :param list[str] args: Command line arguments for each of the binaries.
        """
        cmdl = [self.launcher, ]
        for k, v in sorted(self._reshaped_mpiopts().items()):
            cmdl.append(self.optprefix + six.text_type(k))
            if v is not None:
                cmdl.append(six.text_type(v))
        effective = 0
        for i, bin_obj in enumerate(self.binaries):
            if bin_obj.master is None:
                raise MpiException('No master defined before launching MPI')
            # If there are no options, do not bother...
            if len(bin_obj.expanded_options()):
                if effective > 0 and self.binsep:
                    cmdl.append(self.binsep)
                e_options = self._hook_binary_mpiopts(bin_obj.expanded_options())
                for k in sorted(e_options.keys()):
                    if k in self.optmap:
                        cmdl.append(self.optprefix + six.text_type(self.optmap[k]))
                        if e_options[k] is not None:
                            cmdl.append(six.text_type(e_options[k]))
                if self.optsep:
                    cmdl.append(self.optsep)
                cmdl.append(bin_obj.master)
                cmdl.extend(args[i])
                effective += 1
        return cmdl

    def clean(self, opts=None):
        """post-execution cleaning."""
        # Call the dedicated method en registered MPI binaries
        for bin_obj in self.binaries:
            bin_obj.clean(opts)

    def find_namelists(self, opts=None):
        """Find any namelists candidates in actual context inputs."""
        namcandidates = [x.rh for x in
                         self.context.sequence.effective_inputs(kind=('namelist', 'namelistfp'))]
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
        """MPI information to be written in namelists."""
        for namrh in self.find_namelists(opts):
            namc = namrh.contents
            changed = self.setup_namelist_delta(namc, namrh.container.actualpath())
            # Call the dedicated method en registered MPI binaries
            for bin_obj in self.binaries:
                changed = bin_obj.setup_namelist_delta(namc, namrh.container.actualpath()) or changed
            if changed:
                namc.rewrite(namrh.container)

    def setup_environment(self, opts):
        """MPI environment setup."""
        if self.target.config.has_section('mpienv'):
            for k, v in self.target.config.items('mpienv'):
                if k not in self.env:
                    logger.debug('Setting MPI env %s = %s', k, v)
                    self.env[k] = six.text_type(v)
        # Call the dedicated method en registered MPI binaries
        for bin_obj in self.binaries:
            bin_obj.setup_environment(opts)

    def setup(self, opts=None):
        """Specific MPI settings to be applied before run."""
        self.setup_namelists(opts)
        if self.target is not None:
            self.setup_environment(opts)


class MpiBinaryDescription(footprints.FootprintBase):
    """Root class for any :class:`MpiBinaryDescription` subclass."""

    _collector = ('mpibinary',)
    _footprint = dict(
        info = 'Holds information about a given MPI binary',
        attr = dict(
            kind = dict(
                info     = "A free form description of the binary's type",
                values   = ['basic', ],
            ),
            nodes = dict(
                info     = "The number of nodes for this MPI binary",
                type     = int,
                optional = True,
                access   = 'rwx'
            ),
            tasks = dict(
                info     = "The number of tasks per node for this MPI binary",
                type     = int,
                optional = True,
                access   = 'rwx'
            ),
            openmp = dict(
                info     = "The number of threads per task for this MPI binary",
                type     = int,
                optional = True,
                access   = 'rwx'
            ),
            basics = dict(
                type     = footprints.FPList,
                optional = True,
                default  = footprints.FPList(['system', 'env', 'target', 'context'])
            )
        )
    )

    def __init__(self, *args, **kw):
        """After parent initialization, set master and options to undefined."""
        logger.debug('Abstract mpi tool init %s', self.__class__)
        super(MpiBinaryDescription, self).__init__(*args, **kw)
        self._master = None
        self._options = None

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
        for k in [x for x in attrs if x in self.basics and hasattr(obj, x)]:
            setattr(self, '_' + k, getattr(obj, k))

    def _get_options(self):
        """Retrieve the current set of MPI options."""
        if self._options is None:
            self._set_options(None)
        return self._options

    def _set_options(self, value=None):
        """Input a raw list of MPI options."""
        self._options = dict()
        if value is None:
            value = dict()
        if self.nodes is not None:
            self._options['nn'] = self.nodes
        if self.tasks is not None:
            self._options['nnp'] = self.tasks
        if self.openmp is not None:
            self._options['openmp'] = self.openmp
        for k, v in value.items():
            self._options[k.lstrip('-').lower()] = v

    options = property(_get_options, _set_options)

    def expanded_options(self):
        """The MPI options actualy used by the :class:`MpiTool` object to generate the command line."""
        options = self.options.copy()
        options.setdefault('np', self.nprocs)
        return options

    @property
    def nprocs(self):
        """Figure out what is the effective total number of tasks."""
        if 'np' in self.options:
            nbproc = int(self.options['np'])
        elif 'nnp' in self.options and 'nn' in self.options:
            nbproc = int(self.options.get('nnp')) * int(self.options.get('nn'))
        else:
            raise MpiException('Impossible to compute nprocs.')
        return nbproc

    def _get_master(self):
        """Retrieve the master binary name that should be used."""
        return self._master

    def _set_master(self, master):
        """Keep a copy of the master binary pathname."""
        self._master = master

    master = property(_get_master, _set_master)

    def clean(self, opts=None):
        """Abstract method for post-execution cleaning."""
        pass

    def setup_namelist_delta(self, namcontents, namlocal):
        """Abstract method for applying a delta: return False."""
        return False

    def setup_environment(self, opts):
        """Abstract MPI environment setup."""
        pass


class MpiBinaryBasic(MpiBinaryDescription):
    """Set NPROC and NBPROC in namelists given the MPI distribution."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['basicsingle', ],
            ),
        )
    )

    def setup_namelist_delta(self, namcontents, namlocal):
        """Applying MPI profile on local namelist ``namlocal`` with contents namcontents."""
        namw = False
        if 'NBPROC' in namcontents.macros() or 'NPROC' in namcontents.macros():
            logger.info('Setup NBPROC=%s in %s', self.nprocs, namlocal)
            namcontents.setmacro('NPROC', self.nprocs)
            namcontents.setmacro('NBPROC', self.nprocs)
            namw = True
        return namw


class MpiBinaryIOServer(MpiBinaryDescription):
    """Standard binary description for IO Server binaries."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['ioserv', ],
            ),
        )
    )

    def __init__(self, *args, **kw):
        """After parent initialization, set launcher value."""
        logger.debug('Abstract mpi tool init %s', self.__class__)
        super(MpiBinaryIOServer, self).__init__(*args, **kw)
        thisenv = env.current()
        if self.nodes is None:
            self.nodes = thisenv.VORTEX_IOSERVER_NODES
        if self.tasks is None:
            self.tasks = thisenv.VORTEX_IOSERVER_TASKS
        if self.openmp is None:
            self.openmp = thisenv.VORTEX_IOSERVER_OPENMP

    def expanded_options(self):
        """The number of IO nodes may be 0: accoutn for that."""
        if self.options['nn'] == 0:
            return dict()
        else:
            return super(MpiBinaryIOServer, self).expanded_options()


class MpiRun(MpiTool):
    """Standard MPI launcher on most systems: `mpirun`."""

    _footprint = dict(
        attr = dict(
            sysname = dict(
                values  = ['Linux', 'Darwin']
            ),
            mpiname = dict(
                values  = ['mpirun', 'mpiperso', 'default'],
                remap   = dict(
                    default = 'mpirun'
                ),
            ),
            optsep = dict(
                default = '',
            ),
            optprefix = dict(
                default = '-',
            ),
            optmap = dict(
                default  = footprints.FPDict(np='np', nnp='npernode')
            ),
            binsep = dict(
                default = ':',
            )
        )
    )
