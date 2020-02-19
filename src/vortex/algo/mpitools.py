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

import io
import itertools
import locale
import shlex
import six
import sys

import footprints
from bronx.compat.moves import collections_abc
from bronx.fancies import loggers
from bronx.syntax.parsing import xlist_strings
from vortex.tools import env
from vortex.util import config

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class MpiException(Exception):
    """Raise an exception in the parallel execution mode."""
    pass


class MpiTool(footprints.FootprintBase):
    """Root class for any :class:`MpiTool` subclass."""

    _abstract = True
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
            mpilauncher = dict(
                info     = 'The MPI launcher command to be used',
                optional = True
            ),
            mpiopts = dict(
                info     = 'Extra arguments for the MPI command',
                optional = True,
                default  = ''
            ),
            mpiwrapstd = dict(
                info            = "When using the Vortex' global wrapper redirect stderr/stdout",
                type            = bool,
                optional        = True,
                default         = False,
                doc_visibility  = footprints.doc.visibility.ADVANCED,
                doc_zorder      = -90,
            ),
            mpibind_topology = dict(
                optional        = True,
                doc_visibility  = footprints.doc.visibility.ADVANCED,
                doc_zorder      = -90,
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
                default  = footprints.FPList(['system', 'env', 'target', 'context', 'ticket', ])
            ),
            bindingmethod = dict(
                info            = 'How to bind the MPI processes',
                values          = ['vortex', ],
                access          = 'rwx',
                optional        = True,
                doc_visibility  = footprints.doc.visibility.ADVANCED,
                doc_zorder      = -90,
            ),
        )
    )

    _envelope_bit_kind = 'basicenvelopebit'
    _envelope_wrapper_tpl = '@mpitools/envelope_wrapper_default.tpl'
    _wrapstd_wrapper_tpl = '@mpitools/wrapstd_wrapper_default.tpl'
    _envelope_wrapper_name = './global_envelope_wrapper.py'
    _wrapstd_wrapper_name = './global_wrapstd_wrapper.py'
    _envelope_rank_var = 'MPIRANK'
    _default_mpibind_topology = 'numapacked'

    def __init__(self, *args, **kw):
        """After parent initialization, set master, options and basics to undefined."""
        logger.debug('Abstract mpi tool init %s', self.__class__)
        super(MpiTool, self).__init__(*args, **kw)
        self._launcher = self.mpilauncher or self.mpiname
        self._binaries = []
        self._envelope = []
        self._sources = []
        self._mpilib_data_cache = None
        for k in self.basics:
            self.__dict__['_' + k] = None

    @property
    def realkind(self):
        return 'mpitool'

    @property
    def _actual_mpibind_topology(self):
        """The topology to be used with the Vortex' binding method."""
        if self.mpibind_topology is None:
            return self._default_mpibind_topology
        else:
            return self.mpibind_topology

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

    def _get_envelope(self):
        """Returns the envelope description."""
        return self._envelope

    def _valid_envelope(self, value):
        """Tweak the envelope ddescription values."""
        pass

    def _set_envelope(self, value):
        """Set the envelope description."""
        if not (isinstance(value, collections_abc.Iterable) and
                all([isinstance(b, dict) and all([bk in ('nn', 'nnp', 'openmp') for bk in b.keys()])
                     for b in value])):
            raise ValueError('This should be an Iterable of dictionaries.')
        self._valid_envelope(value)
        self._envelope = list()
        for e in value:
            e_bit = footprints.proxy.mpibinary(kind=self._envelope_bit_kind)
            self._envelope_fix_envelope_bit(e_bit, e)
            self._envelope.append(e_bit)

    envelope = property(_get_envelope, _set_envelope)

    def _get_binaries(self):
        """Returns the list of :class:`MpiBinaryDescription` objects associated with this instance."""
        return self._binaries

    def _set_envelope_from_binaries(self):
        """Create an envelope from existing binaries."""
        self.envelope = [v.options.copy() for v in self.binaries]

    def _set_binaries_envelope_hack(self, binaries):
        """Tweak the envelope after binaries were setup."""
        pass

    def _set_binaries(self, value):
        """Set the list of :class:`MpiBinaryDescription` objects associated with this instance."""
        if not (isinstance(value, collections_abc.Iterable) and
                all([isinstance(b, MpiBinaryDescription) for b in value])):
            raise ValueError('This should be an Iterable of MpiBinaryDescription instances.')
        self._binaries = value
        if not self.envelope and self.bindingmethod == 'vortex':
            self._set_envelope_from_binaries()
        if self.envelope:
            self._set_binaries_envelope_hack(self._binaries)
        self._mpilib_data_cache = None

    binaries = property(_get_binaries, _set_binaries)

    def _mpilib_data(self):
        """From the binaries, try to detect MPI library and mpirun path."""
        if self._mpilib_data_cache is None:
            mpilib_guesses = ('libmpi.so', 'libmpi_mt.so',
                              'libmpi_dbg.so', 'libmpi_dbg_mt.so')
            shp = self.system.path
            mpilib_data = set()
            for binary in self.binaries:
                # For each binary call ldd...
                mpilib = None
                try:
                    binlibs = self.system.ldd(binary.master)
                except (RuntimeError, ValueError):
                    # May fail if the 'master' is not a binary
                    continue
                for mpilib_guess in mpilib_guesses:
                    for l, lp in binlibs.items():
                        if l.startswith(mpilib_guess):
                            mpilib = lp
                            break
                    if mpilib:
                        break
                if mpilib:
                    mpilib = shp.normpath(mpilib)
                    mpitoolsdir = None
                    mpidir = shp.dirname(shp.dirname(mpilib))
                    if shp.exists(shp.join(mpidir, 'bin', 'mpirun')):
                        mpitoolsdir = shp.join(mpidir, 'bin')
                    if not mpitoolsdir and shp.exists(shp.join(mpidir, '..', 'bin', 'mpirun')):
                        mpitoolsdir = shp.normpath(shp.join(mpidir, '..', 'bin'))
                    if mpilib and mpitoolsdir:
                        mpilib_data.add((shp.realpath(mpilib),
                                         shp.realpath(mpitoolsdir)))
            # All the binary must use the same library !
            if len(mpilib_data) == 0:
                logger.info('No MPI library was detected.')
                self._mpilib_data_cache = ()
            elif len(mpilib_data) > 1:
                logger.error('Multiple MPI library were detected.')
                self._mpilib_data_cache = ()
            else:
                self._mpilib_data_cache = mpilib_data.pop()
        return self._mpilib_data_cache if self._mpilib_data_cache else None

    def _get_sources(self):
        """Returns a list of directories that may contain source files."""
        return self._sources

    def _set_sources(self, value):
        """Set the list of of directories taht may contain source files."""
        if not isinstance(value, collections_abc.Iterable):
            raise ValueError('This should be an Iterable.')
        self._sources = value

    sources = property(_get_sources, _set_sources)

    def _actual_mpiopts(self):
        """The mpiopts string."""
        return self.mpiopts

    def _reshaped_mpiopts(self):
        """Raw list of mpi tool command line options."""
        klast = None
        options = dict()
        for optdef in shlex.split(self._actual_mpiopts()):
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

    def _wrapstd_mkwrapper(self):
        """Generate the wrapper script used when wrapstd=True."""
        if not self.mpiwrapstd:
            return None
        # Create the launchwrapper
        wtpl = config.load_template(self.ticket,
                                    self._wrapstd_wrapper_tpl,
                                    encoding='utf-8')
        with io.open(self._wrapstd_wrapper_name, 'w', encoding='utf-8') as fhw:
            fhw.write(
                wtpl.substitute(
                    python=sys.executable,
                    mpirankvariable=self._envelope_rank_var,
                )
            )
        self.system.xperm(self._wrapstd_wrapper_name, force=True)
        return self._wrapstd_wrapper_name

    def _simple_mkcmdline(self, cmdl):
        """Builds the MPI command line when no envelope is used.

        :param list[str] args: the command line as a list
        """
        effective = 0
        wrapstd = self._wrapstd_mkwrapper()
        for bin_obj in self.binaries:
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
                if wrapstd:
                    cmdl.append(wrapstd)
                cmdl.append(bin_obj.master)
                cmdl.extend(bin_obj.arguments)
                effective += 1

    def _envelope_fix_envelope_bit(self, e_bit, e_desc):
        """Set the envelope fake binary options."""
        e_bit.options = {k: v for k, v in e_desc.items()
                         if k not in ('openmp')}
        e_bit.master = self._envelope_wrapper_name

    def _envelope_mkwrapper(self, cmdl):
        """Generate the wrapper script used when an envelope is defined."""
        # Generate the dictionary that associate rank numbers and programs
        ranksidx = 0
        ranks_bsize = dict()
        todostack = dict()
        for bin_obj in self.binaries:
            if bin_obj.master is None:
                raise MpiException('No master defined before launching MPI')
            # If there are no options, do not bother...
            if bin_obj.options:
                if not bin_obj.nprocs:
                    raise ValueError('nranks must be provided when using envelopes')
                for mpirank in range(ranksidx, ranksidx + bin_obj.nprocs):
                    ranks_bsize[mpirank] = bin_obj.options.get('openmp', 1)
                    todostack[mpirank] = (bin_obj.master, bin_obj.arguments,
                                          bin_obj.options.get('openmp', None))
                ranksidx += bin_obj.nprocs
        # Generate the binding stuff
        if self.bindingmethod == 'vortex':
            ranksidx = 0
            bindingstack = dict()
            for e_bit in self.envelope:
                if 'nn' in e_bit.options and 'nnp' in e_bit.options:
                    for _ in range(e_bit.options['nn']):
                        cpudisp = self.system.cpus_ids_dispenser(topology=self._actual_mpibind_topology)
                        if not cpudisp:
                            raise MpiException('Unable to detect the CPU layout with topology: {:s}'
                                               .format(self._actual_vortexbind_topology,))
                        for _ in range(e_bit.options['nnp']):
                            bindingstack[ranksidx] = cpudisp(ranks_bsize.get(ranksidx, 1))
                            ranksidx += 1
                else:
                    logger.error("Cannot compute a proper binding without nn/nnp information")
                    raise MpiException("Vortex binding error.")
        else:
            bindingstack = dict()

        # Create the launchwrapper
        wtpl = config.load_template(self.ticket,
                                    self._envelope_wrapper_tpl,
                                    encoding='utf-8')
        with io.open(self._envelope_wrapper_name, 'w', encoding='utf-8') as fhw:
            fhw.write(
                wtpl.substitute(
                    python=sys.executable,
                    sitepath=self.system.path.join(self.ticket.glove.siteroot, 'site'),
                    mpirankvariable=self._envelope_rank_var,
                    todolist=("\n".join(["  {:d}: ('{:s}', [{:s}], {:s}),".format(
                                         mpi_r,
                                         what[0],
                                         ', '.join(["'{:s}'".format(a) for a in what[1]]),
                                         str(what[2]))
                                         for mpi_r, what in sorted(todostack.items())])),
                    bindinglist=("\n".join(["  {:d}: [{:s}],".format(
                                            mpi_r,
                                            ', '.join(['{:d}'.format(a) for a in what]))
                                            for mpi_r, what in sorted(bindingstack.items())])),
                )
            )
        self.system.xperm(self._envelope_wrapper_name, force=True)
        return self._envelope_wrapper_name

    def _envelope_mkcmdline(self, cmdl):
        """Builds the MPI command line when an envelope is used.

        :param list[str] args: the command line as a list
        """
        self._envelope_mkwrapper(cmdl)
        wrapstd = self._wrapstd_mkwrapper()
        for effective, e_bit in enumerate(self.envelope):
            if effective > 0 and self.binsep:
                cmdl.append(self.binsep)
            e_options = self._hook_binary_mpiopts(e_bit.expanded_options())
            for k in sorted(e_options.keys()):
                if k in self.optmap:
                    cmdl.append(self.optprefix + six.text_type(self.optmap[k]))
                    if e_options[k] is not None:
                        cmdl.append(six.text_type(e_options[k]))
            self._envelope_mkcmdline_extra(cmdl)
            if self.optsep:
                cmdl.append(self.optsep)
            if wrapstd:
                cmdl.append(wrapstd)
            cmdl.append(e_bit.master)

    def _envelope_mkcmdline_extra(self, cmdl):
        """Possibly add extra options when building the envelope."""
        pass

    def mkcmdline(self):
        """Builds the MPI command line."""
        cmdl = [self.launcher, ]
        for k, v in sorted(self._reshaped_mpiopts().items()):
            cmdl.append(self.optprefix + six.text_type(k))
            if v is not None:
                cmdl.append(six.text_type(v))
        if self.envelope:
            self._envelope_mkcmdline(cmdl)
        else:
            self._simple_mkcmdline(cmdl)
        return cmdl

    def clean(self, opts=None):
        """post-execution cleaning."""
        if self.mpiwrapstd:
            # Deal with standard output/error files
            for outf in sorted(self.system.glob('vwrap_stdeo.*')):
                rank = int(outf[12:])
                with io.open(outf, 'r',
                             encoding=locale.getdefaultlocale()[1] or 'ascii',
                             errors='replace') as sfh:
                    for (i, l) in enumerate(sfh):
                        if i == 0:
                            self.system.subtitle('rank {:d}: stdout/err'.format(rank))
                        print(l.rstrip('\n'))
                self.system.remove(outf)
        if self.envelope:
            self.system.remove(self._envelope_wrapper_name)
        if self.mpiwrapstd:
            self.system.remove(self._wrapstd_wrapper_name)
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

    def _logged_env_set(self, k, v):
        """Set an environement variable *k* and emit a log message."""
        logger.info('Setting the "%s" environement variable to "%s"', k.upper(), v)
        self.env[k] = v

    def _logged_env_del(self, k):
        """Delete the environement variable *k* and emit a log message."""
        logger.info('Deleting the "%s" environement variable', k.upper())
        del self.env[k]

    def _environment_substitution_dict(self, opts, conflabel):  # @UnusedVariable
        """Things that may be substituted in environment variables."""
        sdict = dict()
        mpilib_data = self._mpilib_data()
        if mpilib_data:
            sdict.update(mpilib=mpilib_data[0], mpibindir=mpilib_data[1])
        return sdict

    def setup_environment(self, opts, conflabel):
        """MPI environment setup."""
        confdata = self.target.items('mpienv')
        confdata.update(self.target.items('mpienv:{:s}'.format(self.mpiname)))
        if conflabel:
            confdata.update(self.target.items('mpienv-{!s}'.format(conflabel)))
        envsub = self._environment_substitution_dict(opts, conflabel)
        for k, v in confdata.items():
            if k not in self.env:
                try:
                    v = six.text_type(v).format(** envsub)
                except KeyError:
                    logger.warning("Substitution failed for the environement " +
                                   "variable %s. Ignoring it.", k)
                else:
                    self._logged_env_set(k, v)
        # Call the dedicated method en registered MPI binaries
        for bin_obj in self.binaries:
            bin_obj.setup_environment(opts)

    def setup(self, opts=None, conflabel=None):
        """Specific MPI settings to be applied before run."""
        self.setup_namelists(opts)
        if self.target is not None:
            self.setup_environment(opts, conflabel)


class ConfigurableMpiTool(MpiTool):

    _abstract = True
    _footprint = dict(
        attr = dict(
            mpiopts = dict(
                default = None
            ),
        )
    )

    _conf_suffix = ''

    @property
    def mpitool_conf(self):
        """Return the mpiauto configuration."""
        if self.target.config.has_section(self.mpiname):
            return dict(self.target.config.items(self.mpiname))
        else:
            return dict()

    def _actual_mpiopts(self):
        """Possibly read the mpiopts in the config file."""
        if self.mpiopts is None:
            return self.mpitool_conf.get('mpiopts' + self._conf_suffix, '')
        else:
            return self.mpiopts

    def _actual_mpiextraenv(self):
        """Possibly read the mpi extra environment variables in the config file."""
        new_envvar = dict()
        for kv in self.mpitool_conf.get('mpiextraenv' + self._conf_suffix, '').split(','):
            if kv:
                skv = kv.split('%', 1)
                if len(skv) == 2:
                    new_envvar[skv[0]] = skv[1]
        return new_envvar

    def _actual_mpidelenv(self):
        """Possibly read the mpi extra environment variables in the config file."""
        return [v
                for v in self.mpitool_conf.get('mpidelenv' + self._conf_suffix, '').split(',')
                if v]

    @property
    def _actual_mpibind_topology(self):
        """The topology to be used with the Vortex' binding method."""
        if self.mpibind_topology is None:
            return self.mpitool_conf.get('mpibind_topology' + self._conf_suffix,
                                         self._default_mpibind_topology)
        else:
            return self.mpibind_topology

    def setup_environment(self, opts, conflabel):
        """Last minute fixups."""
        super(ConfigurableMpiTool, self).setup_environment(opts, conflabel)
        for k, v in self._actual_mpiextraenv().items():
            self._logged_env_set(k, v)
        for k in self._actual_mpidelenv():
            self._logged_env_del(k)


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
            ranks = dict(
                info     = "The number of MPI ranks to use (only when working in an envelop)",
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
        self._arguments = ()
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
        if self.ranks is not None:
            self._options['np'] = self.ranks
            if self.nodes is not None or self.tasks is not None:
                raise ValueError('Incompatible options provided.')
        else:
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
        """The MPI options actually used by the :class:`MpiTool` object to generate the command line."""
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

    def _get_arguments(self):
        """Retrieve the master's arguments list."""
        return self._arguments

    def _set_arguments(self, args):
        """Keep a copy of the master binary pathname."""
        if isinstance(args, six.string_types):
            self._arguments = args.split()
        elif isinstance(args, collections_abc.Iterable):
            self._arguments = [six.text_type(a) for a in args]
        else:
            raise ValueError('Improper *args* argument provided.')

    arguments = property(_get_arguments, _set_arguments)

    def clean(self, opts=None):
        """Abstract method for post-execution cleaning."""
        pass

    def setup_namelist_delta(self, namcontents, namlocal):
        """Abstract method for applying a delta: return False."""
        return False

    def setup_environment(self, opts):
        """Abstract MPI environment setup."""
        pass


class MpiEnvelopeBit(MpiBinaryDescription):
    """Set NPROC and NBPROC in namelists given the MPI distribution."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['basicenvelopebit', ],
            ),
        )
    )


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
        nprocs_macros = ('NPROC', 'NBPROC', 'NTASKS')
        if any([n in namcontents.macros() for n in nprocs_macros]):
            for n in nprocs_macros:
                logger.info('Setup macro %s=%s in %s', n, self.nprocs, namlocal)
                namcontents.setmacro(n, self.nprocs)
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
        if self.ranks is None:
            self.ranks = thisenv.VORTEX_IOSERVER_RANKS
        if self.nodes is None:
            self.nodes = thisenv.VORTEX_IOSERVER_NODES
        if self.tasks is None:
            self.tasks = thisenv.VORTEX_IOSERVER_TASKS
        if self.openmp is None:
            self.openmp = thisenv.VORTEX_IOSERVER_OPENMP

    def expanded_options(self):
        """The number of IO nodes may be 0: accoutn for that."""
        if self.nprocs == 0:
            return dict()
        else:
            return super(MpiBinaryIOServer, self).expanded_options()


class MpiRun(MpiTool):
    """Standard MPI launcher on most systems: `mpirun`."""

    _footprint = dict(
        attr = dict(
            sysname = dict(
                values  = ['Linux', 'Darwin', 'UnitTestLinux']
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


class SRun(ConfigurableMpiTool):
    """SLURM's srun launcher."""

    _footprint = dict(
        attr = dict(
            sysname = dict(
                values  = ['Linux', 'UnitTestLinux']
            ),
            mpiname = dict(
                values  = ['srun', ],
            ),
            optsep = dict(
                default = '',
            ),
            optprefix = dict(
                default = '--',
            ),
            optmap = dict(
                default  = footprints.FPDict(nn='nodes', nnp='ntasks-per-node',
                                             openmp='cpus-per-task', np='ntasks')
            ),
            slurmversion = dict(
                type = int,
                optional = True
            ),
            mpiwrapstd = dict(
                default         = True,
            ),
            bindingmethod = dict(
                info            = 'How to bind the MPI processes',
                values          = ['native', 'vortex', ],
                access          = 'rwx',
                optional        = True,
                doc_visibility  = footprints.doc.visibility.ADVANCED,
                doc_zorder      = -90,
            ),
        )
    )

    _envelope_nodelist_name = './global_envelope_nodelist'
    _envelope_rank_var = 'SLURM_PROCID'

    @property
    def _actual_slurmversion(self):
        """Return the slurm major version number."""
        return (self.slurmversion or
                int(self.mpitool_conf.get('slurmversion', 0)) or
                18)

    def _set_binaries(self, value):
        """Set the list of :class:`MpiBinaryDescription` objects associated with this instance."""
        super(SRun, self)._set_binaries(value)
        if not self.envelope and len(self._binaries) > 1:
            self._set_envelope_from_binaries()

    binaries = property(MpiTool._get_binaries, _set_binaries)

    def _valid_envelope(self, value):
        """Tweak the envelope ddescription values."""
        for e in value:
            if not ('nn' in e and 'nnp' in e):
                raise MpiException("Srun needs a nn/nnp specification to build the envelope.")

    def _set_envelope(self, value):
        """Set the envelope description."""
        super(SRun, self)._set_envelope(value)
        if len(self._envelope) > 1 and self.bindingmethod not in (None, 'vortex'):
            logger.warning("Resetting the binding method to 'Vortex'.")
            self.bindingmethod = 'vortex'

    envelope = property(MpiTool._get_envelope, _set_envelope)

    def _set_binaries_envelope_hack(self, binaries):
        """Tweak the envelope after binaries were setup."""
        if self.bindingmethod not in (None, 'vortex'):
            openmps = set([b.options.get('openmp', None) for b in binaries])
            if len(openmps) > 1:
                logger.warning("Resetting the binding method to 'Vortex' because " +
                               "the number of threads is not uniform.")
                self.bindingmethod = 'vortex'

    @property
    def _cpubind_opt(self):
        return self.optprefix + ('cpu_bind' if self._actual_slurmversion < 18
                                 else 'cpu-bind')

    def _build_cpumask(self, cmdl, what, bsize):
        """Add a --cpu-bind option if needed."""
        if self.bindingmethod == 'native':
            assert len(what) == 1, "Only one item is allowed."
            ids = self.system.cpus_ids_per_blocks(blocksize=bsize,
                                                  topology=self._actual_mpibind_topology,
                                                  hexmask=True)
            if not ids:
                raise MpiException('Unable to detect the CPU layout with topology: {:s}'
                                   .format(self._actual_vortexbind_topology,))
            masklist = [m for _, m in zip(range(what[0].options['nnp']),
                                          itertools.cycle(ids))]
            cmdl.append(self._cpubind_opt)
            cmdl.append('mask_cpu:' + ','.join(masklist))
        else:
            cmdl.append(self._cpubind_opt)
            cmdl.append('none')

    def _simple_mkcmdline(self, cmdl):
        """Builds the MPI command line when no envelope is used.

        :param list[str] args: the command line as a list
        """
        self._build_cpumask(cmdl, self.binaries,
                            self.binaries[0].options.get('openmp', 1))
        super(SRun, self)._simple_mkcmdline(cmdl)

    def _envelope_mkcmdline(self, cmdl):
        """Builds the MPI command line when an envelope is used.

        :param list[str] args: the command line as a list
        """
        # Simple case, only one envelope description
        if len(self.envelope) == 1:
            self._build_cpumask(cmdl, self.envelope,
                                self.binaries[0].options.get('openmp', 1))
            super(SRun, self)._envelope_mkcmdline(cmdl)
        # Multiple entries... use de nodelist stuff :-(
        else:
            nodelist = []
            totaltasks = 0
            availnodes = itertools.cycle(xlist_strings(self.env.SLURM_NODELIST
                                                       if self._actual_slurmversion < 18
                                                       else self.env.SLURM_JOB_NODELIST))
            for e_bit in self.envelope:
                totaltasks += e_bit.nprocs
                for _ in range(e_bit.options['nn']):
                    availnode = next(availnodes)
                    nodelist.extend([availnode, ] * e_bit.options['nnp'])
            with io.open(self._envelope_nodelist_name, 'w') as fhnl:
                fhnl.write("\n".join(nodelist))
            self._envelope_mkwrapper(cmdl)
            wrapstd = self._wrapstd_mkwrapper()
            cmdl.append(self.optprefix + 'nodelist')
            cmdl.append(self._envelope_nodelist_name)
            cmdl.append(self.optprefix + 'ntasks')
            cmdl.append(str(totaltasks))
            cmdl.append(self.optprefix + 'distribution')
            cmdl.append('arbitrary')
            cmdl.append(self._cpubind_opt)
            cmdl.append('none')
            if wrapstd:
                cmdl.append(wrapstd)
            cmdl.append(e_bit.master)

    def clean(self, opts=None):
        """post-execution cleaning."""
        super(SRun, self).clean(opts)
        if self.envelope and len(self.envelope) > 1:
            self.system.remove(self._envelope_nodelist_name)

    def _environment_substitution_dict(self, opts, conflabel):  # @UnusedVariable
        """Things that may be substituted in environment variables."""
        sdict = super(SRun, self)._environment_substitution_dict(opts, conflabel)
        shp = self.system.path
        # Detect the path to the srun commande
        actlauncher = self.launcher
        if not shp.exists(self.launcher):
            actlauncher = self.system.which(actlauncher)
            if not actlauncher:
                logger.error('The SRun launcher could not be found.')
                return sdict
        sdict['srunpath'] = actlauncher
        # Detect the path to the PMI library
        pmilib = shp.normpath(shp.join(shp.dirname(actlauncher),
                                       '..', 'lib64', 'libpmi.so'))
        if not shp.exists(pmilib):
            pmilib = shp.normpath(shp.join(shp.dirname(actlauncher),
                                           '..', 'lib', 'libpmi.so'))
            if not shp.exists(pmilib):
                logger.error('Could not find a PMI library')
                return sdict
        sdict['pmilib'] = pmilib
        return sdict

    def setup_environment(self, opts, conflabel):
        if len(self.binaries) == 1 and not self.envelope:
            omp = self.binaries[0].options.get('openmp', None)
            if omp is not None:
                self._logged_env_set('OMP_NUM_THREADS', omp)
        if self.bindingmethod == 'native' and 'OMP_PROC_BIND' not in self.env:
            self._logged_env_set('OMP_PROC_BIND', 'true')
        super(SRun, self).setup_environment(opts, conflabel)
