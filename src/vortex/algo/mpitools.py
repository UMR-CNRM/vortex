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

import collections
import collections.abc
import importlib
import itertools
import locale
import re
import shlex

import footprints
from bronx.fancies import loggers
from bronx.syntax.parsing import xlist_strings
from vortex.config import from_config
from vortex.tools import env
from vortex.tools.arm import ArmForgeTool
from vortex.tools.systems import ExecutionError
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
    _collector = ("mpitool",)
    _footprint = dict(
        info="MpiTool class in charge of a particular MPI implementation",
        attr=dict(
            sysname=dict(
                info="The current OS name (e.g. Linux)",
            ),
            mpiname=dict(
                info="The MPI implementation one wishes to use",
            ),
            mpilauncher=dict(
                info="The MPI launcher command to be used", optional=True
            ),
            mpiopts=dict(
                info="Extra arguments for the MPI command",
                optional=True,
                default="",
            ),
            mpiwrapstd=dict(
                info="When using the Vortex' global wrapper redirect stderr/stdout",
                type=bool,
                optional=True,
                default=False,
                doc_visibility=footprints.doc.visibility.ADVANCED,
                doc_zorder=-90,
            ),
            mpibind_topology=dict(
                optional=True,
                default="numapacked",
                doc_visibility=footprints.doc.visibility.ADVANCED,
                doc_zorder=-90,
            ),
            optsep=dict(
                info="Separator between MPI options and the program name",
                optional=True,
                default="--",
            ),
            optprefix=dict(
                info="MPI options prefix", optional=True, default="--"
            ),
            optmap=dict(
                info=(
                    "Mapping between MpiBinaryDescription objects "
                    + "internal data and actual command line options"
                ),
                type=footprints.FPDict,
                optional=True,
                default=footprints.FPDict(nn="nn", nnp="nnp", openmp="openmp"),
            ),
            binsep=dict(
                info="Separator between multiple binary groups",
                optional=True,
                default="--",
            ),
            basics=dict(
                type=footprints.FPList,
                optional=True,
                default=footprints.FPList(
                    [
                        "system",
                        "env",
                        "target",
                        "context",
                        "ticket",
                    ]
                ),
            ),
            bindingmethod=dict(
                info="How to bind the MPI processes",
                values=[
                    "vortex",
                ],
                access="rwx",
                optional=True,
                doc_visibility=footprints.doc.visibility.ADVANCED,
                doc_zorder=-90,
            ),
        ),
    )

    _envelope_bit_kind = "basicenvelopebit"
    _envelope_wrapper_tpl = "envelope_wrapper_default.tpl"
    _wrapstd_wrapper_tpl = "wrapstd_wrapper_default.tpl"
    _envelope_wrapper_name = "./global_envelope_wrapper.py"
    _wrapstd_wrapper_name = "./global_wrapstd_wrapper.py"
    _envelope_rank_var = "MPIRANK"
    _supports_manual_ranks_mapping = False
    _needs_mpilib_specific_mpienv = True

    def __init__(self, *args, **kw):
        """After parent initialization, set master, options and basics to undefined."""
        logger.debug("Abstract mpi tool init %s", self.__class__)
        super().__init__(*args, **kw)
        self._launcher = self.mpilauncher or self.generic_mpiname
        self._binaries = []
        self._envelope = []
        self._sources = []
        self._mpilib_data_cache = None
        self._mpilib_identification_cache = None
        self._ranks_map_cache = None
        self._complex_ranks_map = None
        for k in self.basics:
            self.__dict__["_" + k] = None

    @property
    def realkind(self):
        return "mpitool"

    @property
    def generic_mpiname(self):
        return self.mpiname.split("-")[0]

    def __getattr__(self, key):
        """Have a look to basics values provided by some proxy."""
        if key in self.basics:
            return getattr(self, "_" + key)
        else:
            raise AttributeError(
                "Attribute [%s] is not a basic mpitool attribute" % key
            )

    def import_basics(self, obj, attrs=None):
        """Import some current values such as system, env, target and context from provided ``obj``."""
        if attrs is None:
            attrs = self.basics
        for k in [x for x in attrs if x in self.basics and hasattr(obj, x)]:
            setattr(self, "_" + k, getattr(obj, k))
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
        logger.warning(
            "Setting a new value [%s] to mpi launcher [%s].", value, self
        )
        self._launcher = value

    launcher = property(_get_launcher, _set_launcher)

    def _get_envelope(self):
        """Returns the envelope description."""
        return self._envelope

    def _valid_envelope(self, value):
        """Tweak the envelope description values."""
        pass

    def _set_envelope(self, value):
        """Set the envelope description."""
        if not (
            isinstance(value, collections.abc.Iterable)
            and all(
                [
                    isinstance(b, dict)
                    and all(
                        [
                            bk in ("nn", "nnp", "openmp", "np")
                            for bk in b.keys()
                        ]
                    )
                    for b in value
                ]
            )
        ):
            raise ValueError("This should be an Iterable of dictionaries.")
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
        # Detect possible groups of binaries
        groups = collections.defaultdict(list)
        for a_bin in self.binaries:
            if a_bin.group is not None:
                groups[a_bin.group].append(a_bin)
        new_envelope = list()
        for a_bin in self.binaries:
            if a_bin.group is None:
                # The usual (and easy) case
                new_envelope.append(
                    {
                        k: v
                        for k, v in a_bin.options.items()
                        if k in ("nn", "nnp", "openmp", "np")
                    }
                )
            elif a_bin.group in groups:
                # Deal with group of binaries
                group = groups.pop(a_bin.group)
                n_nodes = {g_bin.options.get("nn", None) for g_bin in group}
                if None in n_nodes:
                    raise ValueError(
                        "To build a proper envelope, "
                        + '"nn" needs to be specified in all binaries'
                    )
                done_nodes = 0
                for n_node in sorted(n_nodes):
                    new_desc = {}
                    new_desc["nn"] = n_node - done_nodes
                    new_desc["nnp"] = 0
                    for g_bin in [
                        g_bin
                        for g_bin in group
                        if g_bin.options["nn"] >= n_node
                    ]:
                        new_desc["nnp"] += g_bin.options["nnp"]
                    new_envelope.append(new_desc)
                    done_nodes = n_node
        self.envelope = new_envelope

    def _set_binaries_hack(self, binaries):
        """Perform any action right after the binaries have been setup."""
        pass

    def _set_binaries_envelope_hack(self, binaries):
        """Tweak the envelope after binaries were setup."""
        pass

    def _set_binaries(self, value):
        """Set the list of :class:`MpiBinaryDescription` objects associated with this instance."""
        if not (
            isinstance(value, collections.abc.Iterable)
            and all([isinstance(b, MpiBinary) for b in value])
        ):
            raise ValueError(
                "This should be an Iterable of MpiBinary instances."
            )
        has_bin_groups = not all([b.group is None for b in value])
        if not (self._supports_manual_ranks_mapping or not has_bin_groups):
            raise ValueError(
                "Binary groups are not supported by this MpiTool class"
            )
        has_bin_distribution = not all([b.distribution is None for b in value])
        if not (
            self._supports_manual_ranks_mapping or not has_bin_distribution
        ):
            raise ValueError(
                "Binary distribution option is not supported by this MpiTool class"
            )
        self._binaries = value
        if not self.envelope and self.bindingmethod == "vortex":
            self._set_envelope_from_binaries()
        elif not self.envelope and (has_bin_groups or has_bin_distribution):
            self._set_envelope_from_binaries()
        self._set_binaries_hack(self._binaries)
        if self.envelope:
            self._set_binaries_envelope_hack(self._binaries)
        self._mpilib_data_cache = None
        self._mpilib_identification_cache = None
        self._ranks_map_cache = None
        self._complex_ranks_map = None

    binaries = property(_get_binaries, _set_binaries)

    def _mpilib_data(self):
        """From the binaries, try to detect MPI library and mpirun paths."""
        if self._mpilib_data_cache is None:
            mpilib_guesses = (
                "libmpi.so",
                "libmpi_mt.so",
                "libmpi_dbg.so",
                "libmpi_dbg_mt.so",
            )
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
                    if shp.exists(shp.join(mpidir, "bin", "mpirun")):
                        mpitoolsdir = shp.join(mpidir, "bin")
                    if not mpitoolsdir and shp.exists(
                        shp.join(mpidir, "..", "bin", "mpirun")
                    ):
                        mpitoolsdir = shp.normpath(
                            shp.join(mpidir, "..", "bin")
                        )
                    if mpilib and mpitoolsdir:
                        mpilib_data.add(
                            (shp.realpath(mpilib), shp.realpath(mpitoolsdir))
                        )
            # All the binary must use the same library !
            if len(mpilib_data) == 0:
                logger.info("No MPI library was detected.")
                self._mpilib_data_cache = ()
            elif len(mpilib_data) > 1:
                logger.error("Multiple MPI library were detected.")
                self._mpilib_data_cache = ()
            else:
                self._mpilib_data_cache = mpilib_data.pop()
        return self._mpilib_data_cache if self._mpilib_data_cache else None

    def _mpilib_match_result(self, regex, rclines, which):
        for line in rclines:
            matched = regex.match(line)
            if matched:
                logger.info(
                    "MPI implementation detected: %s (%s)",
                    which,
                    " ".join(matched.groups()),
                )
                return [which] + [int(res) for res in matched.groups()]
        return False

    def _mpilib_identification(self):
        """Try to guess the name and version of the MPI library."""
        if self._mpilib_data() is None:
            return None
        if self._mpilib_identification_cache is None:
            mpi_lib, mpi_tools_dir = self._mpilib_data()
            ld_libs_extra = set()
            sh = self.system
            mpirun_path = sh.path.join(mpi_tools_dir, "mpirun")
            if sh.path.exists(mpirun_path):
                try:
                    libs = sh.ldd(mpirun_path)
                except ExecutionError:
                    # This may happen if the mpirun binary is statically linked
                    libs = dict()
                if any([libname is None for libname in libs.values()]):
                    libscache = dict()
                    for binary in self.binaries:
                        for lib, libpath in sh.ldd(binary.master).items():
                            if libpath:
                                libscache[lib] = sh.path.dirname(libpath)
                    for missing_lib in [
                        lib for lib, libname in libs.items() if libname is None
                    ]:
                        if missing_lib in libscache:
                            ld_libs_extra.add(libscache[missing_lib])
                with self.env.clone() as localenv:
                    for libpath in ld_libs_extra:
                        localenv.setgenericpath("LD_LIBRARY_PATH", libpath)
                    rc = sh.spawn(
                        [mpirun_path, "--version"], output=True, fatal=False
                    )
                if rc:
                    id_res = self._mpilib_match_result(
                        re.compile(
                            r"^.*Intel.*MPI.*Version\s+(\d+)\s+Update\s+(\d+)",
                            re.IGNORECASE,
                        ),
                        rc,
                        "intelmpi",
                    )
                    id_res = id_res or self._mpilib_match_result(
                        re.compile(
                            r"^.*Open\s*MPI.*\s+(\d+)\.(\d+)(?:\.(\d+))?",
                            re.IGNORECASE,
                        ),
                        rc,
                        "openmpi",
                    )
                    if id_res:
                        ld_libs_extra = tuple(sorted(ld_libs_extra))
                        self._mpilib_identification_cache = tuple(
                            [mpi_lib, mpi_tools_dir, ld_libs_extra] + id_res
                        )
            if self._mpilib_identification_cache is None:
                ld_libs_extra = tuple(sorted(ld_libs_extra))
                self._mpilib_identification_cache = (
                    mpi_lib,
                    mpi_tools_dir,
                    ld_libs_extra,
                    "unknown",
                )
        return self._mpilib_identification_cache

    def _get_sources(self):
        """Returns a list of directories that may contain source files."""
        return self._sources

    def _set_sources(self, value):
        """Set the list of of directories that may contain source files."""
        if not isinstance(value, collections.abc.Iterable):
            raise ValueError("This should be an Iterable.")
        self._sources = value

    sources = property(_get_sources, _set_sources)

    def _actual_mpiopts(self):
        """The mpiopts string."""
        return self.mpiopts

    def _reshaped_mpiopts(self):
        """Raw list of mpi tool command line options."""
        klast = None
        options = collections.defaultdict(list)
        for optdef in shlex.split(self._actual_mpiopts()):
            if optdef.startswith("-"):
                optdef = optdef.lstrip("-")
                options[optdef].append([])
                klast = optdef
            elif klast is not None:
                options[klast][-1].append(optdef)
            else:
                raise MpiException(
                    "Badly shaped mpi option around {!s}".format(optdef)
                )
        return options

    def _hook_binary_mpiopts(self, binary, options):
        """A nasty hook to modify binaries' mpiopts on the fly."""
        return options

    @property
    def _ranks_mapping(self):
        """When group are defined, associate each MPI rank with a "real" slot."""
        if self._ranks_map_cache is None:
            self._complex_ranks_map = False
            if not self.envelope:
                raise RuntimeError(
                    "Ranks mapping should always be used within an envelope."
                )
            # First deal with bingroups
            ranks_map = dict()
            has_bin_groups = not all([b.group is None for b in self.binaries])
            cursor = 0  # The MPI rank we are currently processing
            if has_bin_groups:
                if not self._supports_manual_ranks_mapping:
                    raise RuntimeError(
                        "This MpiTool class does not supports ranks mapping."
                    )
                self._complex_ranks_map = True
                cursor0 = 0  # The first available "real" slot
                group_cache = collections.defaultdict(list)
                for a_bin in self.binaries:
                    if a_bin.group is None:
                        # Easy, the usual case
                        reserved = list(range(cursor0, cursor0 + a_bin.nprocs))
                        cursor0 += a_bin.nprocs
                    else:
                        reserved = group_cache.get(a_bin, [])
                        if not reserved:
                            # It is the first time this group of binaries is seen
                            # Find out what are the binaries in this group
                            bin_buddies = [
                                bin_b
                                for bin_b in self.binaries
                                if bin_b.group == a_bin.group
                            ]
                            if all(
                                [
                                    "nn" in bin_b.options
                                    for bin_b in bin_buddies
                                ]
                            ):
                                # Each of the binary descriptions should define the number of nodes
                                max_nn = max(
                                    [
                                        bin_b.options["nn"]
                                        for bin_b in bin_buddies
                                    ]
                                )
                                for i_node in range(max_nn):
                                    for bin_b in bin_buddies:
                                        if bin_b.options["nn"] > i_node:
                                            group_cache[bin_b].extend(
                                                range(
                                                    cursor0,
                                                    cursor0
                                                    + bin_b.options["nnp"],
                                                )
                                            )
                                            cursor0 += bin_b.options["nnp"]
                            else:
                                # If the number of nodes is not defined, revert to the number of tasks.
                                # This will probably result in strange results !
                                for bin_b in bin_buddies:
                                    group_cache[bin_b].extend(
                                        range(cursor0, cursor0 + bin_b.nprocs)
                                    )
                                    cursor0 += bin_b.nprocs
                            reserved = group_cache[a_bin]
                    for rank in range(a_bin.nprocs):
                        ranks_map[rank + cursor] = reserved[rank]
                    cursor += a_bin.nprocs
            else:
                # Just do nothing...
                for a_bin in self.binaries:
                    for rank in range(a_bin.nprocs):
                        ranks_map[rank + cursor] = rank + cursor
                    cursor += a_bin.nprocs
            # Then deal with distribution
            do_bin_distribution = not all(
                [b.distribution in (None, "continuous") for b in self.binaries]
            )
            if self._complex_ranks_map or do_bin_distribution:
                if not self.envelope:
                    raise RuntimeError(
                        "Ranks mapping shoudl always be used within an envelope."
                    )
            if do_bin_distribution:
                if not self._supports_manual_ranks_mapping:
                    raise RuntimeError(
                        "This MpiTool class does not supports ranks mapping."
                    )
                self._complex_ranks_map = True
                if all(
                    [
                        "nn" in b.options and "nnp" in b.options
                        for b in self.envelope
                    ]
                ):
                    # Extract node information
                    node_cursor = 0
                    nodes_id = list()
                    for e_bit in self.envelope:
                        for _ in range(e_bit.options["nn"]):
                            nodes_id.extend(
                                [
                                    node_cursor,
                                ]
                                * e_bit.options["nnp"]
                            )
                            node_cursor += 1
                    # Re-order ranks given the distribution
                    cursor = 0
                    for a_bin in self.binaries:
                        if a_bin.distribution == "roundrobin":
                            # The current list of ranks
                            actual_ranks = [
                                ranks_map[i]
                                for i in range(cursor, cursor + a_bin.nprocs)
                            ]
                            # Find the node number associated with each rank
                            nodes_dict = collections.defaultdict(
                                collections.deque
                            )
                            for rank in actual_ranks:
                                nodes_dict[nodes_id[rank]].append(rank)
                            # Create a new list of ranks in a round-robin manner
                            actual_ranks = list()
                            iter_nodes = itertools.cycle(
                                sorted(nodes_dict.keys())
                            )
                            for _ in range(a_bin.nprocs):
                                av_ranks = None
                                while not av_ranks:
                                    av_ranks = nodes_dict[next(iter_nodes)]
                                actual_ranks.append(av_ranks.popleft())
                            # Inject the result back
                            for i in range(a_bin.nprocs):
                                ranks_map[cursor + i] = actual_ranks[i]
                        cursor += a_bin.nprocs
                else:
                    logger.warning(
                        "Cannot enforce binary distribution if the envelope"
                        + "does not contain nn/nnp information"
                    )
            # Cache the final result !
            self._ranks_map_cache = ranks_map
        return self._ranks_map_cache

    @property
    def _complex_ranks_mapping(self):
        """Is it a complex ranks mapping (e.g not the identity)."""
        if self._complex_ranks_map is None:
            # To initialise everything...
            self._ranks_mapping
        return self._complex_ranks_map

    def _wrapstd_mkwrapper(self):
        """Generate the wrapper script used when wrapstd=True."""
        if not self.mpiwrapstd:
            return None
        # Create the launchwrapper
        with importlib.resources.path(
            "vortex.algo.mpitools_templates",
            self._wrapstd_wrapper_tpl,
        ) as tplpath:
            wtpl = config.load_template(tplpath, encoding="utf-8")
        with open(self._wrapstd_wrapper_name, "w", encoding="utf-8") as fhw:
            fhw.write(
                wtpl.substitute(
                    python=self.system.executable,
                    mpirankvariable=self._envelope_rank_var,
                )
            )
        self.system.xperm(self._wrapstd_wrapper_name, force=True)
        return self._wrapstd_wrapper_name

    def _simple_mkcmdline(self, cmdl):
        """Builds the MPI command line when no envelope is used.

        :param list[str] cmdl: the command line as a list
        """
        effective = 0
        wrapstd = self._wrapstd_mkwrapper()
        for bin_obj in self.binaries:
            if bin_obj.master is None:
                raise MpiException("No master defined before launching MPI")
            # If there are no options, do not bother...
            if len(bin_obj.expanded_options()):
                if effective > 0 and self.binsep:
                    cmdl.append(self.binsep)
                e_options = self._hook_binary_mpiopts(
                    bin_obj, bin_obj.expanded_options()
                )
                for k in sorted(e_options.keys()):
                    if k in self.optmap:
                        cmdl.append(self.optprefix + str(self.optmap[k]))
                        if e_options[k] is not None:
                            cmdl.append(str(e_options[k]))
                if self.optsep:
                    cmdl.append(self.optsep)
                if wrapstd:
                    cmdl.append(wrapstd)
                cmdl.append(bin_obj.master)
                cmdl.extend(bin_obj.arguments)
                effective += 1

    def _envelope_fix_envelope_bit(self, e_bit, e_desc):
        """Set the envelope fake binary options."""
        e_bit.options = {
            k: v for k, v in e_desc.items() if k not in ("openmp", "np")
        }
        e_bit.master = self._envelope_wrapper_name

    def _envelope_mkwrapper_todostack(self):
        ranksidx = 0
        ranks_bsize = dict()
        todostack = dict()
        for bin_obj in self.binaries:
            if bin_obj.master is None:
                raise MpiException("No master defined before launching MPI")
            # If there are no options, do not bother...
            if bin_obj.options and bin_obj.nprocs != 0:
                if not bin_obj.nprocs:
                    raise ValueError(
                        "nranks must be provided when using envelopes"
                    )
                for mpirank in range(ranksidx, ranksidx + bin_obj.nprocs):
                    if bin_obj.allowbind:
                        ranks_bsize[mpirank] = bin_obj.options.get("openmp", 1)
                    else:
                        ranks_bsize[mpirank] = -1
                    todostack[mpirank] = (
                        bin_obj.master,
                        bin_obj.arguments,
                        bin_obj.options.get("openmp", None),
                    )
                ranksidx += bin_obj.nprocs
        return todostack, ranks_bsize

    def _envelope_mkwrapper_cpu_dispensers(self):
        # Dispensers map
        totalnodes = 0
        ranks_idx = 0
        dispensers_map = dict()
        for e_bit in self.envelope:
            if "nn" in e_bit.options and "nnp" in e_bit.options:
                for _ in range(e_bit.options["nn"]):
                    cpu_disp = self.system.cpus_ids_dispenser(
                        topology=self.mpibind_topology
                    )
                    if not cpu_disp:
                        raise MpiException(
                            "Unable to detect the CPU layout with topology: {:s}".format(
                                self.mpibind_topology,
                            )
                        )
                    for _ in range(e_bit.options["nnp"]):
                        dispensers_map[ranks_idx] = (cpu_disp, totalnodes)
                        ranks_idx += 1
                    totalnodes += 1
            else:
                logger.error(
                    "Cannot compute a proper binding without nn/nnp information"
                )
                raise MpiException("Vortex binding error.")
        return dispensers_map

    def _envelope_mkwrapper_bindingstack(self, ranks_bsize):
        binding_stack = dict()
        binding_node = dict()
        if self.bindingmethod:
            dispensers_map = self._envelope_mkwrapper_cpu_dispensers()
            # Actually generate the binding map
            ranks_idx = 0
            for e_bit in self.envelope:
                for _ in range(e_bit.options["nn"]):
                    for _ in range(e_bit.options["nnp"]):
                        cpu_disp, i_node = dispensers_map[
                            self._ranks_mapping[ranks_idx]
                        ]
                        if ranks_bsize.get(ranks_idx, 1) != -1:
                            try:
                                binding_stack[ranks_idx] = cpu_disp(
                                    ranks_bsize.get(ranks_idx, 1)
                                )
                            except (StopIteration, IndexError):
                                # When CPU dispensers are exhausted (it might happened if more tasks
                                # than available CPUs are requested).
                                dispensers_map = (
                                    self._envelope_mkwrapper_cpu_dispensers()
                                )
                                cpu_disp, i_node = dispensers_map[
                                    self._ranks_mapping[ranks_idx]
                                ]
                                binding_stack[ranks_idx] = cpu_disp(
                                    ranks_bsize.get(ranks_idx, 1)
                                )
                        else:
                            binding_stack[ranks_idx] = set(
                                self.system.cpus_info.cpus.keys()
                            )
                        binding_node[ranks_idx] = i_node
                        ranks_idx += 1
        return binding_stack, binding_node

    def _envelope_mkwrapper_tplsubs(self, todostack, bindingstack):
        return dict(
            python=self.system.executable,
            sitepath=self.system.path.join(self.ticket.glove.siteroot, "site"),
            mpirankvariable=self._envelope_rank_var,
            todolist=(
                "\n".join(
                    [
                        "  {:d}: ('{:s}', [{:s}], {:s}),".format(
                            mpi_r,
                            what[0],
                            ", ".join(["'{:s}'".format(a) for a in what[1]]),
                            str(what[2]),
                        )
                        for mpi_r, what in sorted(todostack.items())
                    ]
                )
            ),
            bindinglist=(
                "\n".join(
                    [
                        "  {:d}: [{:s}],".format(
                            mpi_r, ", ".join(["{:d}".format(a) for a in what])
                        )
                        for mpi_r, what in sorted(bindingstack.items())
                    ]
                )
            ),
        )

    def _envelope_mkwrapper(self, cmdl):
        """Generate the wrapper script used when an envelope is defined."""
        # Generate the dictionary that associate rank numbers and programs
        todostack, ranks_bsize = self._envelope_mkwrapper_todostack()
        # Generate the binding stuff
        bindingstack, bindingnode = self._envelope_mkwrapper_bindingstack(
            ranks_bsize
        )
        # Print binding details
        logger.debug(
            "Vortex Envelope Mechanism is used"
            + (" & vortex binding is on." if bindingstack else ".")
        )
        env_info_head = "{:5s} {:24s} {:4s}".format(
            "#rank", "binary_name", "#OMP"
        )
        env_info_fmt = "{:5d} {:24s} {:4s}"
        if bindingstack:
            env_info_head += " {:5s}   {:s}".format("#node", "bindings_list")
            env_info_fmt2 = " {:5d}   {:s}"
        binding_str = [env_info_head]
        for i_rank in sorted(todostack):
            entry_str = env_info_fmt.format(
                i_rank,
                self.system.path.basename(todostack[i_rank][0])[:24],
                str(todostack[i_rank][2]),
            )
            if bindingstack:
                entry_str += env_info_fmt2.format(
                    bindingnode[i_rank],
                    ",".join([str(c) for c in sorted(bindingstack[i_rank])]),
                )
            binding_str.append(entry_str)
        logger.debug(
            "Here are the envelope details:\n%s", "\n".join(binding_str)
        )
        # Create the launchwrapper
        with importlib.resources.path(
            "vortex.algo.mpitools_templates",
            self._envelope_wrapper_tpl,
        ) as tplpath:
            wtpl = config.load_template(tplpath, encoding="utf-8")
        with open(self._envelope_wrapper_name, "w", encoding="utf-8") as fhw:
            fhw.write(
                wtpl.substitute(
                    **self._envelope_mkwrapper_tplsubs(todostack, bindingstack)
                )
            )
        self.system.xperm(self._envelope_wrapper_name, force=True)
        return self._envelope_wrapper_name

    def _envelope_mkcmdline(self, cmdl):
        """Builds the MPI command line when an envelope is used.

        :param list[str] cmdl: the command line as a list
        """
        self._envelope_mkwrapper(cmdl)
        wrapstd = self._wrapstd_mkwrapper()
        for effective, e_bit in enumerate(self.envelope):
            if effective > 0 and self.binsep:
                cmdl.append(self.binsep)
            e_options = self._hook_binary_mpiopts(
                e_bit, e_bit.expanded_options()
            )
            for k in sorted(e_options.keys()):
                if k in self.optmap:
                    cmdl.append(self.optprefix + str(self.optmap[k]))
                    if e_options[k] is not None:
                        cmdl.append(str(e_options[k]))
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
        cmdl = [
            self.launcher,
        ]
        for k, instances in sorted(self._reshaped_mpiopts().items()):
            for instance in instances:
                cmdl.append(self.optprefix + str(k))
                for a_value in instance:
                    cmdl.append(str(a_value))
        if self.envelope:
            self._envelope_mkcmdline(cmdl)
        else:
            self._simple_mkcmdline(cmdl)
        return cmdl

    def clean(self, opts=None):
        """post-execution cleaning."""
        if self.mpiwrapstd:
            # Deal with standard output/error files
            for outf in sorted(self.system.glob("vwrap_stdeo.*")):
                rank = int(outf[12:])
                with open(
                    outf,
                    encoding=locale.getlocale()[1] or "ascii",
                    errors="replace",
                ) as sfh:
                    for i, l in enumerate(sfh):
                        if i == 0:
                            self.system.highlight(
                                "rank {:d}: stdout/err".format(rank)
                            )
                        print(l.rstrip("\n"))
                self.system.remove(outf)
        if self.envelope and self.system.path.exists(
            self._envelope_wrapper_name
        ):
            self.system.remove(self._envelope_wrapper_name)
        if self.mpiwrapstd:
            self.system.remove(self._wrapstd_wrapper_name)
        # Call the dedicated method en registered MPI binaries
        for bin_obj in self.binaries:
            bin_obj.clean(opts)

    def find_namelists(self, opts=None):
        """Find any namelists candidates in actual context inputs."""
        namcandidates = [
            x.rh
            for x in self.context.sequence.effective_inputs(
                kind=("namelist", "namelistfp")
            )
        ]
        if opts is not None and "loop" in opts:
            namcandidates = [
                x
                for x in namcandidates
                if (
                    hasattr(x.resource, "term")
                    and x.resource.term == opts["loop"]
                )
            ]
        else:
            logger.info("No loop option in current parallel execution.")
        self.system.highlight("Namelist candidates")
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
            changed = self.setup_namelist_delta(
                namc, namrh.container.actualpath()
            )
            # Call the dedicated method en registered MPI binaries
            for bin_obj in self.binaries:
                changed = (
                    bin_obj.setup_namelist_delta(
                        namc, namrh.container.actualpath()
                    )
                    or changed
                )
            if changed:
                if namc.dumps_needs_update:
                    logger.info(
                        "Rewritting the %s namelists file.",
                        namrh.container.actualpath(),
                    )
                    namc.rewrite(namrh.container)

    def _logged_env_set(self, k, v):
        """Set an environment variable *k* and emit a log message."""
        logger.info(
            'Setting the "%s" environment variable to "%s"', k.upper(), v
        )
        self.env[k] = v

    def _logged_env_del(self, k):
        """Delete the environment variable *k* and emit a log message."""
        logger.info('Deleting the "%s" environment variable', k.upper())
        del self.env[k]

    def _environment_substitution_dict(self):
        """Things that may be substituted in environment variables."""
        sdict = dict()
        mpilib_data = self._mpilib_data()
        if mpilib_data:
            sdict.update(mpilib=mpilib_data[0], mpibindir=mpilib_data[1])
        return sdict

    def setup_environment(self, opts):
        """MPI environment setup."""
        confdata = from_config(section="mpienv")
        envsub = self._environment_substitution_dict()
        for k, v in confdata.items():
            if k not in self.env:
                try:
                    v = str(v).format(**envsub)
                except KeyError:
                    logger.warning(
                        "Substitution failed for the environment "
                        + "variable %s. Ignoring it.",
                        k,
                    )
                else:
                    self._logged_env_set(k, v)
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

    _collector = ("mpibinary",)
    _abstract = True
    _footprint = dict(
        info="Holds information about a given MPI binary",
        attr=dict(
            kind=dict(
                info="A free form description of the binary's type",
                values=[
                    "basic",
                ],
            ),
            nodes=dict(
                info="The number of nodes for this MPI binary",
                type=int,
                optional=True,
                access="rwx",
            ),
            tasks=dict(
                info="The number of tasks per node for this MPI binary",
                type=int,
                optional=True,
                access="rwx",
            ),
            openmp=dict(
                info="The number of threads per task for this MPI binary",
                type=int,
                optional=True,
                access="rwx",
            ),
            ranks=dict(
                info="The number of MPI ranks to use (only when working in an envelope)",
                type=int,
                optional=True,
                access="rwx",
            ),
            allowbind=dict(
                info="Allow the MpiTool to bind this executable",
                type=bool,
                optional=True,
                default=True,
            ),
            basics=dict(
                type=footprints.FPList,
                optional=True,
                default=footprints.FPList(
                    ["system", "env", "target", "context"]
                ),
            ),
        ),
    )

    def __init__(self, *args, **kw):
        """After parent initialization, set master and options to undefined."""
        logger.debug("Abstract mpi tool init %s", self.__class__)
        super().__init__(*args, **kw)
        self._master = None
        self._arguments = ()
        self._options = None
        self._group = None

    def __getattr__(self, key):
        """Have a look to basics values provided by some proxy."""
        if key in self.basics:
            return getattr(self, "_" + key)
        else:
            raise AttributeError(
                "Attribute [%s] is not a basic mpitool attribute" % key
            )

    def import_basics(self, obj, attrs=None):
        """Import some current values such as system, env, target and context from provided ``obj``."""
        if attrs is None:
            attrs = self.basics
        for k in [x for x in attrs if x in self.basics and hasattr(obj, x)]:
            setattr(self, "_" + k, getattr(obj, k))

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
            self._options["np"] = self.ranks
            if self.nodes is not None or self.tasks is not None:
                raise ValueError("Incompatible options provided.")
        else:
            if self.nodes is not None:
                self._options["nn"] = self.nodes
            if self.tasks is not None:
                self._options["nnp"] = self.tasks
        if self.openmp is not None:
            self._options["openmp"] = self.openmp
        for k, v in value.items():
            self._options[k.lstrip("-").lower()] = v

    options = property(_get_options, _set_options)

    def expanded_options(self):
        """The MPI options actually used by the :class:`MpiTool` object to generate the command line."""
        options = self.options.copy()
        options.setdefault("np", self.nprocs)
        return options

    def _get_group(self):
        """The group the current binary belongs to (may be ``None``)."""
        return self._group

    def _set_group(self, value):
        """Set the binary's group."""
        self._group = value

    group = property(_get_group, _set_group)

    @property
    def nprocs(self):
        """Figure out what is the effective total number of tasks."""
        if "np" in self.options:
            nbproc = int(self.options["np"])
        elif "nnp" in self.options and "nn" in self.options:
            nbproc = int(self.options.get("nnp")) * int(self.options.get("nn"))
        else:
            raise MpiException("Impossible to compute nprocs.")
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
        if isinstance(args, str):
            self._arguments = args.split()
        elif isinstance(args, collections.abc.Iterable):
            self._arguments = [str(a) for a in args]
        else:
            raise ValueError("Improper *args* argument provided.")

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
        attr=dict(
            kind=dict(
                values=[
                    "basicenvelopebit",
                ],
            ),
        )
    )


class MpiBinary(MpiBinaryDescription):
    _footprint = dict(
        attr=dict(
            distribution=dict(
                info="Describes how the various nodes are distributed accross nodes",
                values=["continuous", "roundrobin"],
                optional=True,
            ),
        )
    )


class MpiBinaryBasic(MpiBinary):
    """Set NPROC and NBPROC in namelists given the MPI distribution."""

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=[
                    "basicsingle",
                ],
            ),
        )
    )

    def setup_namelist_delta(self, namcontents, namlocal):
        """Applying MPI profile on local namelist ``namlocal`` with contents namcontents."""
        namw = False
        # List of macros actualy used in the namelist
        nam_macros = set()
        for nam_block in namcontents.values():
            nam_macros.update(nam_block.macros())
        # Look for relevant once
        nprocs_macros = ("NPROC", "NBPROC", "NTASKS")
        if any([n in nam_macros for n in nprocs_macros]):
            for n in nprocs_macros:
                logger.info(
                    "Setup macro %s=%s in %s", n, self.nprocs, namlocal
                )
                namcontents.setmacro(n, self.nprocs)
            namw = True
        return namw


class MpiBinaryIOServer(MpiBinary):
    """Standard binary description for IO Server binaries."""

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=[
                    "ioserv",
                ],
            ),
        )
    )

    def __init__(self, *args, **kw):
        """After parent initialization, set launcher value."""
        logger.debug("Abstract mpi tool init %s", self.__class__)
        super().__init__(*args, **kw)
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
        """The number of IO nodes may be 0: account for that."""
        if self.nprocs == 0:
            return dict()
        else:
            return super().expanded_options()


class MpiRun(MpiTool):
    """Standard MPI launcher on most systems: `mpirun`."""

    _footprint = dict(
        attr=dict(
            sysname=dict(values=["Linux", "Darwin", "UnitTestLinux"]),
            mpiname=dict(
                values=["mpirun", "mpiperso", "default"],
                remap=dict(default="mpirun"),
            ),
            optsep=dict(
                default="",
            ),
            optprefix=dict(
                default="-",
            ),
            optmap=dict(default=footprints.FPDict(np="np", nnp="npernode")),
            binsep=dict(
                default=":",
            ),
        )
    )


class SRun(MpiTool):
    """SLURM's srun launcher."""

    _footprint = dict(
        attr=dict(
            sysname=dict(values=["Linux", "UnitTestLinux"]),
            mpiname=dict(
                values=[
                    "srun",
                ],
            ),
            optsep=dict(
                default="",
            ),
            optprefix=dict(
                default="--",
            ),
            optmap=dict(
                default=footprints.FPDict(
                    nn="nodes", nnp="ntasks-per-node", np="ntasks"
                )
            ),
            slurmversion=dict(type=int, optional=True),
            mpiwrapstd=dict(
                default=True,
            ),
            bindingmethod=dict(
                info="How to bind the MPI processes",
                values=[
                    "native",
                    "vortex",
                ],
                access="rwx",
                optional=True,
                doc_visibility=footprints.doc.visibility.ADVANCED,
                doc_zorder=-90,
            ),
        )
    )

    _envelope_nodelist_name = "./global_envelope_nodelist"
    _envelope_rank_var = "SLURM_PROCID"
    _supports_manual_ranks_mapping = True

    @property
    def _actual_slurmversion(self):
        """Return the slurm major version number."""
        slurmversion = self.slurmversion or from_config(
            section="mpitool", key="slurmversion"
        )
        if not slurmversion:
            raise ValueError("No slurm version specified")
        return slurmversion

    def _set_binaries_hack(self, binaries):
        """Set the list of :class:`MpiBinaryDescription` objects associated with this instance."""
        if (
            not self.envelope
            and len(
                [binary for binary in binaries if binary.expanded_options()]
            )
            > 1
        ):
            self._set_envelope_from_binaries()

    def _valid_envelope(self, value):
        """Tweak the envelope ddescription values."""
        for e in value:
            if not ("nn" in e and "nnp" in e):
                raise MpiException(
                    "Srun needs a nn/nnp specification to build the envelope."
                )

    def _set_envelope(self, value):
        """Set the envelope description."""
        super()._set_envelope(value)
        if len(self._envelope) > 1 and self.bindingmethod not in (
            None,
            "vortex",
        ):
            logger.warning("Resetting the binding method to 'Vortex'.")
            self.bindingmethod = "vortex"

    envelope = property(MpiTool._get_envelope, _set_envelope)

    def _set_binaries_envelope_hack(self, binaries):
        """Tweak the envelope after binaries were setup."""
        if self.bindingmethod not in (None, "vortex"):
            openmps = {b.options.get("openmp", None) for b in binaries}
            if len(openmps) > 1:
                logger.warning(
                    "Resetting the binding method to 'Vortex' because "
                    + "the number of threads is not uniform."
                )
                self.bindingmethod = "vortex"

    @property
    def _cpubind_opt(self):
        return self.optprefix + (
            "cpu_bind" if self._actual_slurmversion < 18 else "cpu-bind"
        )

    def _build_cpumask(self, cmdl, what, bsize):
        """Add a --cpu-bind option if needed."""
        cmdl.append(self._cpubind_opt)
        if self.bindingmethod == "native":
            assert len(what) == 1, "Only one item is allowed."
            if what[0].allowbind:
                ids = self.system.cpus_ids_per_blocks(
                    blocksize=bsize,
                    topology=self.mpibind_topology,
                    hexmask=True,
                )
                if not ids:
                    raise MpiException(
                        "Unable to detect the CPU layout with topology: {:s}".format(
                            self.mpibind_topology,
                        )
                    )
                masklist = [
                    m
                    for _, m in zip(
                        range(what[0].options["nnp"]), itertools.cycle(ids)
                    )
                ]
                cmdl.append("mask_cpu:" + ",".join(masklist))
            else:
                cmdl.append("none")
        else:
            cmdl.append("none")

    def _simple_mkcmdline(self, cmdl):
        """Builds the MPI command line when no envelope is used.

        :param list[str] cmdl: the command line as a list
        """
        target_bins = [
            binary
            for binary in self.binaries
            if len(binary.expanded_options())
        ]
        self._build_cpumask(
            cmdl, target_bins, target_bins[0].options.get("openmp", 1)
        )
        super()._simple_mkcmdline(cmdl)

    def _envelope_mkcmdline(self, cmdl):
        """Builds the MPI command line when an envelope is used.

        :param list[str] cmdl: the command line as a list
        """
        # Simple case, only one envelope description
        openmps = {b.options.get("openmp", 1) for b in self.binaries}
        if (
            len(self.envelope) == 1
            and not self._complex_ranks_mapping
            and len(openmps) == 1
        ):
            self._build_cpumask(cmdl, self.envelope, openmps.pop())
            super()._envelope_mkcmdline(cmdl)
        # Multiple entries... use the nodelist stuff :-(
        else:
            # Find all the available nodes and ranks
            base_nodelist = []
            totalnodes = 0
            totaltasks = 0
            availnodes = itertools.cycle(
                xlist_strings(
                    self.env.SLURM_NODELIST
                    if self._actual_slurmversion < 18
                    else self.env.SLURM_JOB_NODELIST
                )
            )
            for e_bit in self.envelope:
                totaltasks += e_bit.nprocs
                for _ in range(e_bit.options["nn"]):
                    availnode = next(availnodes)
                    logger.debug("Node #%5d is: %s", totalnodes, availnode)
                    base_nodelist.extend(
                        [
                            availnode,
                        ]
                        * e_bit.options["nnp"]
                    )
                    totalnodes += 1
            # Re-order the nodelist based on the binary groups
            nodelist = list()
            for i_rank in range(len(base_nodelist)):
                if i_rank < len(self._ranks_mapping):
                    nodelist.append(base_nodelist[self._ranks_mapping[i_rank]])
                else:
                    nodelist.append(base_nodelist[i_rank])
            # Write it to the nodefile
            with open(self._envelope_nodelist_name, "w") as fhnl:
                fhnl.write("\n".join(nodelist))
            # Generate wrappers
            self._envelope_mkwrapper(cmdl)
            wrapstd = self._wrapstd_mkwrapper()
            # Update the command line
            cmdl.append(self.optprefix + "nodelist")
            cmdl.append(self._envelope_nodelist_name)
            cmdl.append(self.optprefix + "ntasks")
            cmdl.append(str(totaltasks))
            cmdl.append(self.optprefix + "distribution")
            cmdl.append("arbitrary")
            cmdl.append(self._cpubind_opt)
            cmdl.append("none")
            if wrapstd:
                cmdl.append(wrapstd)
            cmdl.append(e_bit.master)

    def clean(self, opts=None):
        """post-execution cleaning."""
        super().clean(opts)
        if self.envelope and len(self.envelope) > 1:
            self.system.remove(self._envelope_nodelist_name)

    def _environment_substitution_dict(self):  # @UnusedVariable
        """Things that may be substituted in environment variables."""
        sdict = super()._environment_substitution_dict()
        shp = self.system.path
        # Detect the path to the srun command
        actlauncher = self.launcher
        if not shp.exists(self.launcher):
            actlauncher = self.system.which(actlauncher)
            if not actlauncher:
                logger.error("The SRun launcher could not be found.")
                return sdict
        sdict["srunpath"] = actlauncher
        # Detect the path to the PMI library
        pmilib = shp.normpath(
            shp.join(shp.dirname(actlauncher), "..", "lib64", "libpmi.so")
        )
        if not shp.exists(pmilib):
            pmilib = shp.normpath(
                shp.join(shp.dirname(actlauncher), "..", "lib", "libpmi.so")
            )
            if not shp.exists(pmilib):
                logger.error("Could not find a PMI library")
                return sdict
        sdict["pmilib"] = pmilib
        return sdict

    def setup_environment(self, opts):
        """Tweak the environment with some srun specific settings."""
        super().setup_environment(opts)
        if (
            self._complex_ranks_mapping
            and self._mpilib_identification()
            and self._mpilib_identification()[3] == "intelmpi"
        ):
            logger.info(
                "(Sadly) with IntelMPI, I_MPI_SLURM_EXT=0 is needed when a complex arbitrary"
                + "ranks distribution is used. Exporting it !"
            )
            self.env["I_MPI_SLURM_EXT"] = 0
        if len(self.binaries) == 1 and not self.envelope:
            omp = self.binaries[0].options.get("openmp", None)
            if omp is not None:
                self._logged_env_set("OMP_NUM_THREADS", omp)
        if self.bindingmethod == "native" and "OMP_PROC_BIND" not in self.env:
            self._logged_env_set("OMP_PROC_BIND", "true")
        # cleaning unwanted environment stuff
        unwanted = set()
        for k in self.env:
            if k.startswith("SLURM_"):
                k = k[6:]
                if (
                    k in ("NTASKS", "NPROCS")
                    or re.match("N?TASKS_PER_", k)
                    or re.match("N?CPUS_PER_", k)
                ):
                    unwanted.add(k)
        for k in unwanted:
            self.env.delvar("SLURM_{:s}".format(k))


class SRunDDT(SRun):
    """SLURM's srun launcher with ARM's DDT."""

    _footprint = dict(
        attr=dict(
            mpiname=dict(
                values=[
                    "srun-ddt",
                ],
            ),
        )
    )

    _conf_suffix = "-ddt"

    def mkcmdline(self):
        """Add the DDT prefix command to the command line"""
        cmdl = super().mkcmdline()
        armtool = ArmForgeTool(self.ticket)
        for extra_c in reversed(
            armtool.ddt_prefix_cmd(
                sources=self.sources,
                workdir=self.system.path.dirname(self.binaries[0].master),
            )
        ):
            cmdl.insert(0, extra_c)
        return cmdl


class OmpiMpiRun(MpiTool):
    """OpenMPI's mpirun launcher."""

    _footprint = dict(
        attr=dict(
            sysname=dict(values=["Linux", "UnitTestLinux"]),
            mpiname=dict(
                values=[
                    "openmpi",
                ],
            ),
            optsep=dict(
                default="",
            ),
            optprefix=dict(
                default="-",
            ),
            optmap=dict(
                default=footprints.FPDict(np="np", nnp="npernode", xopenmp="x")
            ),
            binsep=dict(
                default=":",
            ),
            mpiwrapstd=dict(
                default=True,
            ),
            bindingmethod=dict(
                info="How to bind the MPI processes",
                values=[
                    "native",
                    "vortex",
                ],
                optional=True,
                doc_visibility=footprints.doc.visibility.ADVANCED,
                doc_zorder=-90,
            ),
            preexistingenv=dict(
                optional=True,
                type=bool,
                default=False,
            ),
        )
    )

    _envelope_rankfile_name = "./global_envelope_rankfile"
    _envelope_rank_var = "OMPI_COMM_WORLD_RANK"
    _supports_manual_ranks_mapping = True

    def _get_launcher(self):
        """Returns the name of the mpi tool to be used."""
        if self.mpilauncher:
            return self.mpilauncher
        else:
            mpi_data = self._mpilib_data()
            if mpi_data:
                return self.system.path.join(mpi_data[1], "mpirun")
            else:
                return self._launcher

    launcher = property(_get_launcher, MpiTool._set_launcher)

    def _set_binaries_hack(self, binaries):
        if not self.envelope and self.bindingmethod == "native":
            self._set_envelope_from_binaries()

    def _valid_envelope(self, value):
        """Tweak the envelope description values."""
        for e in value:
            if not ("nn" in e and "nnp" in e):
                raise MpiException(
                    "OpenMPI/mpirun needs a nn/nnp specification "
                    + "to build the envelope."
                )

    def _hook_binary_mpiopts(self, binary, options):
        openmp = options.pop("openmp", None)
        if openmp is not None:
            options["xopenmp"] = "OMP_NUM_THREADS={:d}".format(openmp)
        return options

    def _simple_mkcmdline(self, cmdl):
        """Builds the MPI command line when no envelope is used.

        :param list[str] cmdl: the command line as a list
        """
        if self.bindingmethod is not None:
            raise RuntimeError(
                "If bindingmethod is set, an enveloppe should allways be used."
            )
        super()._simple_mkcmdline(cmdl)

    def _create_rankfile(self, rankslist, nodeslist, slotslist):
        rf_strings = []

        def _dump_slot_string(slot_strings, s_start, s_end):
            if s_start == s_end:
                slot_strings.append("{:d}".format(s_start))
            else:
                slot_strings.append("{:d}-{:d}".format(s_start, s_end))

        for rank, node, slot in zip(rankslist, nodeslist, slotslist):
            slot_strings = list()
            if slot:
                slot = sorted(slot)
                s_end = s_start = slot[0]
                for s in slot[1:]:
                    if s_end + 1 == s:
                        s_end = s
                    else:
                        _dump_slot_string(slot_strings, s_start, s_end)
                        s_end = s_start = s
                _dump_slot_string(slot_strings, s_start, s_end)
            rf_strings.append(
                "rank {:d}={:s} slot={:s}".format(
                    rank, node, ",".join(slot_strings)
                )
            )
        logger.info("self.preexistingenv = {}".format(self.preexistingenv))
        if self.preexistingenv and self.system.path.exists(
            self._envelope_rankfile_name
        ):
            logger.info("envelope file found in the directory")
        else:
            if self.preexistingenv:
                logger.info(
                    "preexistingenv set to true, but no envelope file found"
                )
                logger.info("Using vortex computed one")
            logger.debug(
                "Here is the rankfile content:\n%s", "\n".join(rf_strings)
            )
            with open(self._envelope_rankfile_name, mode="w") as tmp_rf:
                tmp_rf.write("\n".join(rf_strings))
        return self._envelope_rankfile_name

    def _envelope_nodelist(self):
        """Create the relative nodelist based on the envelope"""
        base_nodelist = []
        totalnodes = 0
        for e_bit in self.envelope:
            for i_node in range(e_bit.options["nn"]):
                logger.debug("Node #%5d is: +n%d", i_node, totalnodes)
                base_nodelist.extend(
                    [
                        "+n{:d}".format(totalnodes),
                    ]
                    * e_bit.options["nnp"]
                )
                totalnodes += 1
        return base_nodelist

    def _envelope_mkcmdline(self, cmdl):
        """Builds the MPI command line when an envelope is used.

        :param list[str] args: the command line as a list
        """
        cmdl.append(self.optprefix + "oversubscribe")
        if self.bindingmethod in (None, "native"):
            # Generate the dictionary that associate rank numbers and programs
            todostack, ranks_bsize = self._envelope_mkwrapper_todostack()
            # Generate the binding stuff
            bindingstack, _ = self._envelope_mkwrapper_bindingstack(
                ranks_bsize
            )
            # Generate a relative nodelist
            base_nodelist = self._envelope_nodelist()
            # Generate the rankfile
            ranks = sorted(todostack)
            nodes = [base_nodelist[self._ranks_mapping[r]] for r in ranks]
            if bindingstack:
                slots = [bindingstack[r] for r in ranks]
            else:
                slots = [
                    sorted(self.system.cpus_info.cpus.keys()),
                ] * len(ranks)
            rfile = self._create_rankfile(ranks, nodes, slots)
            # Add the rankfile on the command line
            cmdl.append(self.optprefix + "rankfile")
            cmdl.append(rfile)
            # Add the "usual" call to binaries and setup OMP_NUM_THREADS values
            wrapstd = self._wrapstd_mkwrapper()
            for i_bin, a_bin in enumerate(self.binaries):
                if i_bin > 0:
                    cmdl.append(self.binsep)
                openmp = a_bin.options.get("openmp", None)
                if openmp:
                    cmdl.append(self.optprefix + "x")
                    cmdl.append("OMP_NUM_THREADS={!s}".format(openmp))
                cmdl.append(self.optprefix + "np")
                cmdl.append(str(a_bin.nprocs))
                if wrapstd:
                    cmdl.append(wrapstd)
                cmdl.append(a_bin.master)
                cmdl.extend(a_bin.arguments)
        else:
            # Generate a host file but let vortex deal with the rest...
            base_nodelist = self._envelope_nodelist()
            ranks = list(range(len(base_nodelist)))
            rfile = self._create_rankfile(
                ranks,
                [base_nodelist[self._ranks_mapping[r]] for r in ranks],
                [
                    sorted(self.system.cpus_info.cpus.keys()),
                ]
                * len(base_nodelist),
            )
            # Generate wrappers
            self._envelope_mkwrapper(cmdl)
            wrapstd = self._wrapstd_mkwrapper()
            # Update the command line
            cmdl.append(self.optprefix + "rankfile")
            cmdl.append(rfile)
            cmdl.append(self.optprefix + "np")
            cmdl.append(str(len(base_nodelist)))
            if wrapstd:
                cmdl.append(wrapstd)
            cmdl.append(self.envelope[0].master)

    def clean(self, opts=None):
        """post-execution cleaning."""
        super().clean(opts)
        if self.envelope:
            self.system.remove(self._envelope_rankfile_name)

    def setup_environment(self, opts):
        """Tweak the environment with some srun specific settings."""
        super().setup_environment(opts)
        if self.bindingmethod == "native" and "OMP_PROC_BIND" not in self.env:
            self._logged_env_set("OMP_PROC_BIND", "true")
        for libpath in self._mpilib_identification()[2]:
            logger.info('Adding "%s" to LD_LIBRARY_PATH', libpath)
            self.env.setgenericpath("LD_LIBRARY_PATH", libpath)


class OmpiMpiRunDDT(OmpiMpiRun):
    """SLURM's srun launcher with ARM's DDT."""

    _footprint = dict(
        attr=dict(
            mpiname=dict(
                values=[
                    "openmpi-ddt",
                ],
            ),
        )
    )

    _conf_suffix = "-ddt"

    def mkcmdline(self):
        """Add the DDT prefix command to the command line"""
        cmdl = super(OmpiMpiRun, self).mkcmdline()
        armtool = ArmForgeTool(self.ticket)
        for extra_c in reversed(
            armtool.ddt_prefix_cmd(
                sources=self.sources,
                workdir=self.system.path.dirname(self.binaries[0].master),
            )
        ):
            cmdl.insert(0, extra_c)
        return cmdl
