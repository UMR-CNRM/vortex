"""
General interest and NWP specific MPI launchers.
"""

import collections
import re
import math

from bronx.fancies import loggers
from bronx.syntax.iterators import interleave
import footprints

from vortex.algo import mpitools
from vortex.syntax.stdattrs import DelayedEnvValue
from vortex.tools.arm import ArmForgeTool
from ..tools.partitioning import setup_partitioning_in_namelist

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class MpiAuto(mpitools.MpiTool):
    """MpiTools that uses mpiauto as a proxy to several MPI implementations"""

    _footprint = dict(
        attr=dict(
            mpiname=dict(
                values=[
                    "mpiauto",
                ],
            ),
            mpiopts=dict(default=None),
            optprefix=dict(default="--"),
            optmap=dict(
                default=footprints.FPDict(
                    nn="nn",
                    nnp="nnp",
                    openmp="openmp",
                    np="np",
                    prefixcommand="prefix-command",
                    allowodddist="mpi-allow-odd-dist",
                )
            ),
            timeoutrestart=dict(
                info="The number of attempts made by mpiauto",
                optional=True,
                default=DelayedEnvValue("MPI_INIT_TIMEOUT_RESTART", 2),
                doc_visibility=footprints.doc.visibility.ADVANCED,
                doc_zorder=-90,
            ),
            sublauncher=dict(
                info="How to actualy launch the MPI program",
                values=["srun", "libspecific"],
                optional=True,
                doc_visibility=footprints.doc.visibility.ADVANCED,
                doc_zorder=-90,
            ),
            mpiwrapstd=dict(
                values=[
                    False,
                ],
            ),
            bindingmethod=dict(
                info="How to bind the MPI processes",
                values=["vortex", "arch", "launcherspecific"],
                optional=True,
                doc_visibility=footprints.doc.visibility.ADVANCED,
                doc_zorder=-90,
            ),
            mplbased=dict(
                info="Is the executable based on MPL?",
                type=bool,
                optional=True,
                default=False,
            ),
        )
    )

    _envelope_wrapper_tpl = "envelope_wrapper_mpiauto.tpl"
    _envelope_rank_var = "MPIAUTORANK"
    _needs_mpilib_specific_mpienv = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bindingmethod = "arch" if self.mplbased else "vortex"

    def _reshaped_mpiopts(self):
        """Raw list of mpi tool command line options."""
        options = super()._reshaped_mpiopts()
        options["init-timeout-restart"] = [(self.timeoutrestart,)]
        if self.sublauncher == "srun":
            options["use-slurm-mpi"] = [()]
        elif self.sublauncher == "libspecific":
            options["no-use-slurm-mpi"] = [()]
        if self.bindingmethod:
            for k in [
                "{:s}use-{:s}-bind".format(p, t)
                for p in ("", "no-")
                for t in ("arch", "slurm", "intelmpi", "openmpi")
            ]:
                options.pop(k, None)
            if self.bindingmethod == "arch":
                options["use-arch-bind"] = [()]
            elif (
                self.bindingmethod == "launcherspecific"
                and self.sublauncher == "srun"
            ):
                options["no-use-arch-bind"] = [()]
                options["use-slurm-bind"] = [()]
            elif self.bindingmethod == "launcherspecific":
                options["no-use-arch-bind"] = [()]
                for k in [
                    "use-{:s}-bind".format(t)
                    for t in ("slurm", "intelmpi", "openmpi")
                ]:
                    options[k] = [()]
            elif self.bindingmethod == "vortex":
                options["no-use-arch-bind"] = [()]
        return options

    def _envelope_fix_envelope_bit(self, e_bit, e_desc):
        """Set the envelope fake binary options."""
        e_bit.options = {
            k: v for k, v in e_desc.items() if k not in ("openmp",)
        }
        e_bit.options["prefixcommand"] = self._envelope_wrapper_name
        if self.binaries:
            e_bit.master = self.binaries[0].master

    def _set_binaries_hack(self, binaries):
        """Set the list of :class:`MpiBinaryDescription` objects associated with this instance."""
        if len(binaries) > 1 and self.bindingmethod not in (
            None,
            "arch",
            "vortex",
        ):
            logger.info(
                "The '{:s}' binding method is not working properly with multiple binaries.".format(
                    self.bindingmethod
                )
            )
            logger.warning("Resetting the binding method to 'vortex'.")
            self.bindingmethod = "vortex"

    def _set_binaries_envelope_hack(self, binaries):
        """Tweak the envelope after binaries were setup."""
        super()._set_binaries_envelope_hack(binaries)
        for e_bit in self.envelope:
            e_bit.master = binaries[0].master

    def _set_envelope(self, value):
        """Set the envelope description."""
        super()._set_envelope(value)
        if len(self._envelope) > 1 and self.bindingmethod not in (
            None,
            "arch",
            "vortex",
        ):
            logger.info(
                "The '{:s}' binding method is not working properly with complex envelopes.".format(
                    self.bindingmethod
                )
            )
            logger.warning("Resetting the binding method to 'vortex'.")
            self.bindingmethod = "vortex"

    envelope = property(mpitools.MpiTool._get_envelope, _set_envelope)

    def _hook_binary_mpiopts(self, binary, options):
        tuned = options.copy()
        # Regular MPI tasks count (the usual...)
        if "nnp" in options and "nn" in options:
            if options["nn"] * options["nnp"] == options["np"]:
                # Remove harmful options
                del tuned["np"]
                tuned.pop("allowodddist", None)
                # that's the strange MPI distribution...
            else:
                tuned["allowodddist"] = (
                    None  # With this, let mpiauto determine its own partitioning
                )
        else:
            msg = "The provided mpiopts are insufficient to build the command line: {!s}".format(
                options
            )
            raise mpitools.MpiException(msg)
        return tuned

    def _envelope_mkwrapper_todostack(self):
        ranksidx = 0
        todostack, ranks_bsize = super()._envelope_mkwrapper_todostack()
        for bin_obj in self.binaries:
            if bin_obj.options:
                for mpirank in range(ranksidx, ranksidx + bin_obj.nprocs):
                    prefix_c = bin_obj.options.get("prefixcommand", None)
                    if prefix_c:
                        todostack[mpirank] = (
                            prefix_c,
                            [
                                todostack[mpirank][0],
                            ]
                            + todostack[mpirank][1],
                            todostack[mpirank][2],
                        )
                ranksidx += bin_obj.nprocs
        return todostack, ranks_bsize

    def _envelope_mkcmdline_extra(self, cmdl):
        """If possible, add an openmp option when the arch binding method is used."""

        if self.bindingmethod != "vortex":
            openmps = {b.options.get("openmp", None) for b in self.binaries}
            if len(openmps) > 1:
                if self.bindingmethod is not None:
                    logger.warning(
                        "Non-uniform OpenMP threads number... Not specifying anything."
                    )
            else:
                openmp = openmps.pop() or 1
                cmdl.append(self.optprefix + self.optmap["openmp"])
                cmdl.append(str(openmp))

    def setup_environment(self, opts):
        """Last minute fixups."""
        super().setup_environment(opts)
        if self.bindingmethod in ("arch", "vortex"):
            # Make sure srun does nothing !
            self._logged_env_set("SLURM_CPU_BIND", "none")

    def setup(self, opts=None):
        """Ensure that the prefixcommand has the execution rights."""
        for bin_obj in self.binaries:
            prefix_c = bin_obj.options.get("prefixcommand", None)
            if prefix_c is not None:
                if self.system.path.exists(prefix_c):
                    self.system.xperm(prefix_c, force=True)
                else:
                    raise OSError("The prefixcommand do not exists.")
        super().setup(opts)


class MpiAutoDDT(MpiAuto):
    """
    MpiTools that uses mpiauto as a proxy to several MPI implementations
    with DDT support.
    """

    _footprint = dict(
        attr=dict(
            mpiname=dict(
                values=[
                    "mpiauto-ddt",
                ],
            ),
        )
    )

    _conf_suffix = "-ddt"

    def _reshaped_mpiopts(self):
        options = super()._reshaped_mpiopts()
        if "prefix-mpirun" in options:
            raise mpitools.MpiException(
                "It is not allowed to start DDT with another "
                + 'prefix_mpirun command defined: "{:s}"'.format(options)
            )
        armtool = ArmForgeTool(self.ticket)
        options["prefix-mpirun"] = [
            (
                " ".join(
                    armtool.ddt_prefix_cmd(
                        sources=self.sources,
                        workdir=self.system.path.dirname(
                            self.binaries[0].master
                        ),
                    )
                ),
            )
        ]
        return options


# Some IFS/Arpege specific things :


def arpifs_obsort_nprocab_binarydeco(cls):
    """Handle usual IFS/Arpege environment tweaking for OBSORT (nproca & nprocb).

    Note: This is a class decorator for class somehow based on MpiBinaryDescription
    """
    orig_setup_env = getattr(cls, "setup_environment")

    def setup_environment(self, opts):
        orig_setup_env(self, opts)
        self.env.NPROCA = int(self.env.NPROCA or self.nprocs)
        self.env.NPROCB = int(
            self.env.NPROCB or self.nprocs // self.env.NPROCA
        )
        logger.info(
            "MPI Setup NPROCA=%d and NPROCB=%d",
            self.env.NPROCA,
            self.env.NPROCB,
        )

    if hasattr(orig_setup_env, "__doc__"):
        setup_environment.__doc__ = orig_setup_env.__doc__

    setattr(cls, "setup_environment", setup_environment)
    return cls


class _NWPIoServerMixin:
    _NWP_IOSERV_PATTERNS = ("io_serv.*.d",)

    def _nwp_ioserv_setup_namelist(
        self, namcontents, namlocal, total_iotasks, computed_iodist_value=None
    ):
        """Applying IO Server profile on local namelist ``namlocal`` with contents namcontents."""
        if "NAMIO_SERV" in namcontents:
            namio = namcontents["NAMIO_SERV"]
        else:
            namio = namcontents.newblock("NAMIO_SERV")

        namio.nproc_io = total_iotasks
        if computed_iodist_value is not None:
            namio.idistio = computed_iodist_value

        if "VORTEX_IOSERVER_METHOD" in self.env:
            namio.nio_serv_method = self.env.VORTEX_IOSERVER_METHOD

        if "VORTEX_IOSERVER_BUFMAX" in self.env:
            namio.nio_serv_buf_maxsize = self.env.VORTEX_IOSERVER_BUFMAX

        if "VORTEX_IOSERVER_MLSERVER" in self.env:
            namio.nmsg_level_server = self.env.VORTEX_IOSERVER_MLSERVER

        if "VORTEX_IOSERVER_MLCLIENT" in self.env:
            namio.nmsg_level_client = self.env.VORTEX_IOSERVER_MLCLIENT

        if "VORTEX_IOSERVER_PROCESS" in self.env:
            namio.nprocess_level = self.env.VORTEX_IOSERVER_PROCESS

        if "VORTEX_IOSERVER_PIOMODEL" in self.env:
            namio.pioprocr_MDL = self.env.VORTEX_IOSERVER_PIOMODEL

        self.system.highlight(
            "Parallel io server namelist for {:s}".format(namlocal)
        )
        print(namio.dumps())

        return True

    def _nwp_ioserv_iodirs(self):
        """Return an ordered list of directories matching the ``pattern`` attribute."""
        found = []
        for pattern in self._NWP_IOSERV_PATTERNS:
            found.extend(self.system.glob(pattern))
        return sorted(found)

    def _nwp_ioserv_clean(self):
        """Post-execution cleaning for io server."""

        # Old fashion way to make clear that some polling is needed.
        self.system.touch("io_poll.todo")

        # Get a look inside io server output directories according to its own pattern
        ioserv_filelist = set()
        ioserv_prefixes = set()
        iofile_re = re.compile(
            r"((ICMSH|PF|GRIBPF).*\+\d+(?::\d+)?(?:\.sfx)?)(?:\..+)?$"
        )
        self.system.highlight("Dealing with IO directories")
        iodirs = self._nwp_ioserv_iodirs()
        if iodirs:
            logger.info("List of IO directories: %s", ",".join(iodirs))
            f_summary = collections.defaultdict(lambda: [" "] * len(iodirs))
            for i, iodir in enumerate(iodirs):
                for iofile in self.system.listdir(iodir):
                    zf = iofile_re.match(iofile)
                    if zf:
                        f_summary[zf.group(1)][i] = "+"
                        ioserv_filelist.add((zf.group(1), zf.group(2)))
                        ioserv_prefixes.add(zf.group(2))
                    else:
                        f_summary[iofile][i] = "?"
            max_names_len = max([len(iofile) for iofile in f_summary.keys()])
            fmt_names = "{:" + str(max_names_len) + "s}"
            logger.info(
                "Data location accross the various IOserver directories:\n%s",
                "\n".join(
                    [
                        (fmt_names + " |{:s}|").format(iofile, "".join(where))
                        for iofile, where in sorted(f_summary.items())
                    ]
                ),
            )
        else:
            logger.info("No IO directories were found")

        if "GRIBPF" in ioserv_prefixes:
            # If GRIB are requested, do not bother with old FA PF files
            ioserv_prefixes.discard("PF")
            ioserv_filelist = {(f, p) for f, p in ioserv_filelist if p != "PF"}

        # Touch the output files
        for tgfile, _ in ioserv_filelist:
            self.system.touch(tgfile)

        # Touch the io_poll.todo.PREFIX
        for prefix in ioserv_prefixes:
            self.system.touch("io_poll.todo.{:s}".format(prefix))


class _AbstractMpiNWP(mpitools.MpiBinaryBasic, _NWPIoServerMixin):
    """The kind of binaries used in IFS/Arpege."""

    _abstract = True

    def __init__(self, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self._incore_iotasks = None
        self._effective_incore_iotasks = None
        self._incore_iotasks_fixer = None
        self._incore_iodist = None

    @property
    def incore_iotasks(self):
        """The number of tasks dedicated to the IO server."""
        return self._incore_iotasks

    @incore_iotasks.setter
    def incore_iotasks(self, value):
        """The number of tasks dedicated to the IO server."""
        if isinstance(value, str) and value.endswith("%"):
            value = math.ceil(self.nprocs * float(value[:-1]) / 100)
        self._incore_iotasks = int(value)
        self._effective_incore_iotasks = None

    @property
    def incore_iotasks_fixer(self):
        """Tweak the number of iotasks in order to respect a given constraints."""
        return self._incore_iotasks_fixer

    @incore_iotasks_fixer.setter
    def incore_iotasks_fixer(self, value):
        """Tweak the number of iotasks in order to respect a given constraints."""
        if not isinstance(value, str):
            raise ValueError("A string is expected")
        if value.startswith("nproc_multiple_of_"):
            self._incore_iotasks_fixer = (
                "nproc_multiple_of",
                [int(i) for i in value[18:].split(",")],
            )
        else:
            raise ValueError('The "{:s}" value is incorrect'.format(value))

    @property
    def effective_incore_iotasks(self):
        """Apply fixers to incore_iotasks and return this value.

        e.g. "nproc_multiple_of_15,16,17" ensure that the number of processes
        dedicated to computations (i.e. total number of process - IO processes)
        is a multiple of 15, 16 or 17.
        """
        if self.incore_iotasks is not None:
            if self._effective_incore_iotasks is None:
                if self.incore_iotasks_fixer is not None:
                    if self.incore_iotasks_fixer[0] == "nproc_multiple_of":
                        # Allow for 5% less, or add some tasks
                        for candidate in interleave(
                            range(self.incore_iotasks, self.nprocs + 1),
                            range(
                                self.incore_iotasks - 1,
                                int(math.ceil(0.95 * self.incore_iotasks)) - 1,
                                -1,
                            ),
                        ):
                            if any(
                                [
                                    (self.nprocs - candidate) % multiple == 0
                                    for multiple in self.incore_iotasks_fixer[
                                        1
                                    ]
                                ]
                            ):
                                self._effective_incore_iotasks = candidate
                                break
                    else:
                        raise RuntimeError("Unsupported fixer")
                    if self._effective_incore_iotasks != self.incore_iotasks:
                        logger.info(
                            "The number of IO tasks was updated form %d to %d "
                            + 'because of the "%s" fixer',
                            self.incore_iotasks,
                            self._effective_incore_iotasks,
                            self.incore_iotasks_fixer[0],
                        )
                else:
                    self._effective_incore_iotasks = self.incore_iotasks
            return self._effective_incore_iotasks
        else:
            return None

    @property
    def incore_iodist(self):
        """How to distribute IO server tasks within model tasks."""
        return self._incore_iodist

    @incore_iodist.setter
    def incore_iodist(self, value):
        """How to distribute IO server tasks within model tasks."""
        allowed = (
            "begining",
            "end",
            "scattered",
        )
        if not (isinstance(value, str) and value in allowed):
            raise ValueError(
                "'{!s}' is not an allowed value ('{:s}')".format(
                    value, ", ".join(allowed)
                )
            )
        self._incore_iodist = value

    def _set_nam_macro(self, namcontents, namlocal, macro, value):
        """Set a namelist macro and log it!"""
        namcontents.setmacro(macro, value)
        logger.info("Setup macro %s=%s in %s", macro, str(value), namlocal)

    def setup_namelist_delta(self, namcontents, namlocal):
        """Applying MPI profile on local namelist ``namlocal`` with contents namcontents."""
        namw = False
        # List of macros actually used in the namelist
        nam_macros = set()
        for nam_block in namcontents.values():
            nam_macros.update(nam_block.macros())
        # The actual number of tasks involved in computations
        effective_nprocs = self.nprocs
        if self.effective_incore_iotasks is not None:
            effective_nprocs -= self.effective_incore_iotasks
        # Set up the effective_nprocs related macros
        nprocs_macros = ("NPROC", "NBPROC", "NTASKS")
        if any([n in nam_macros for n in nprocs_macros]):
            for n in nprocs_macros:
                self._set_nam_macro(namcontents, namlocal, n, effective_nprocs)
            namw = True
            if any([n in nam_macros for n in ("NCPROC", "NDPROC")]):
                self._set_nam_macro(
                    namcontents,
                    namlocal,
                    "NCPROC",
                    int(self.env.VORTEX_NPRGPNS or effective_nprocs),
                )
                self._set_nam_macro(
                    namcontents,
                    namlocal,
                    "NDPROC",
                    int(self.env.VORTEX_NPRGPEW or 1),
                )
                namw = True
        if "NAMPAR1" in namcontents:
            np1 = namcontents["NAMPAR1"]
            for nstr in [x for x in ("NSTRIN", "NSTROUT") if x in np1]:
                if (
                    isinstance(np1[nstr], (int, float))
                    and np1[nstr] > effective_nprocs
                ):
                    logger.info(
                        "Setup %s=%s in NAMPAR1 %s",
                        nstr,
                        effective_nprocs,
                        namlocal,
                    )
                    np1[nstr] = effective_nprocs
                    namw = True
        # Deal with partitioning macros
        namw_p = setup_partitioning_in_namelist(
            namcontents,
            effective_nprocs,
            self.options.get("openmp", 1),
            namlocal,
        )
        namw = namw or namw_p
        # Incore IO tasks
        if self.effective_incore_iotasks is not None:
            c_iodist = None
            if self.incore_iodist is not None:
                if self.incore_iodist == "begining":
                    c_iodist = -1
                elif self.incore_iodist == "end":
                    c_iodist = 0
                elif self.incore_iodist == "scattered":
                    # Ensure that there is at least one task on the first node
                    c_iodist = min(
                        self.nprocs // self.effective_incore_iotasks,
                        self.options.get("nnp", self.nprocs),
                    )
                else:
                    raise RuntimeError(
                        "incore_iodist '{!s}' is not supported: check your code".format(
                            self.incore_iodist
                        )
                    )
            namw_io = self._nwp_ioserv_setup_namelist(
                namcontents,
                namlocal,
                self.effective_incore_iotasks,
                computed_iodist_value=c_iodist,
            )
            namw = namw or namw_io
        return namw

    def clean(self, opts=None):
        """Finalise the IO server run."""
        super().clean(opts=opts)
        if self.incore_iotasks:
            self._nwp_ioserv_clean()


class MpiNWP(_AbstractMpiNWP):
    """The kind of binaries used in IFS/Arpege."""

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=[
                    "basicnwp",
                ]
            ),
        ),
    )


@arpifs_obsort_nprocab_binarydeco
class MpiNWPObsort(_AbstractMpiNWP):
    """The kind of binaries used in IFS/Arpege when the ODB OBSSORT code needs to be run."""

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=[
                    "basicnwpobsort",
                ]
            ),
        ),
    )


@arpifs_obsort_nprocab_binarydeco
class MpiObsort(mpitools.MpiBinaryBasic):
    """The kind of binaries used when the ODB OBSSORT code needs to be run."""

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=[
                    "basicobsort",
                ]
            ),
        ),
    )


class MpiNWPIO(mpitools.MpiBinaryIOServer, _NWPIoServerMixin):
    """Standard IFS/Arpege NWP IO server."""

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=[
                    "nwpioserv",
                ]
            ),
            iolocation=dict(
                values=[-1, 0], default=0, optional=True, type=int
            ),
        )
    )

    def setup_namelist_delta(self, namcontents, namlocal):
        """Setup the IO Server."""
        self._nwp_ioserv_setup_namelist(
            namcontents,
            namlocal,
            self.nprocs,
            computed_iodist_value=(-1 if self.iolocation == 0 else None),
        )

    def clean(self, opts=None):
        """Finalise the IO server run."""
        super().clean(opts=opts)
        self._nwp_ioserv_clean()
