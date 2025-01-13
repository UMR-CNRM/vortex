"""
Various Post-Processing AlgoComponents.
"""

import collections
import json
import re
import time

from bronx.datagrip.namelist import NamelistBlock
from bronx.fancies import loggers
from footprints.stdtypes import FPTuple
import footprints
from taylorism import Boss

from vortex.layout.monitor import (
    BasicInputMonitor,
    AutoMetaGang,
    MetaGang,
    EntrySt,
    GangSt,
)
from vortex.algo.components import (
    AlgoComponentDecoMixin,
    AlgoComponentError,
    algo_component_deco_mixin_autodoc,
)
from vortex.algo.components import (
    TaylorRun,
    BlindRun,
    ParaBlindRun,
    Parallel,
    Expresso,
)
from vortex.syntax.stdattrs import DelayedEnvValue, FmtInt
from vortex.tools.grib import EcGribDecoMixin
from vortex.tools.parallelism import (
    TaylorVortexWorker,
    VortexWorkerBlindRun,
    ParallelResultParser,
)
from vortex.tools.systems import ExecutionError

from ..tools.grib import GRIBFilter
from ..tools.drhook import DrHookDecoMixin

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class _FA2GribWorker(VortexWorkerBlindRun):
    """The taylorism worker that actually do the gribing (in parallel).

    This is called indirectly by taylorism when :class:`Fa2Grib` is used.
    """

    _footprint = dict(
        attr=dict(
            kind=dict(values=["fa2grib"]),
            # Progrid parameters
            fortnam=dict(),
            fortinput=dict(),
            compact=dict(),
            timeshift=dict(type=int),
            timeunit=dict(type=int),
            numod=dict(type=int),
            sciz=dict(type=int),
            scizoffset=dict(type=int, optional=True),
            # Input/Output data
            file_in=dict(),
            file_out=dict(),
            member=dict(
                type=FmtInt,
                optional=True,
            ),
        )
    )

    def vortex_task(self, **kwargs):
        logger.info("Starting the Fa2Grib processing for tag=%s", self.name)

        thisoutput = "GRIDOUTPUT"
        rdict = dict(rc=True)

        # First, check that the hooks were applied
        for thisinput in [
            x
            for x in self.context.sequence.inputs()
            if x.rh.container.localpath() == self.file_in
        ]:
            if thisinput.rh.delayhooks:
                thisinput.rh.apply_get_hooks()

        # Jump into a working directory
        cwd = self.system.pwd()
        tmpwd = self.system.path.join(cwd, self.file_out + ".process.d")
        self.system.mkdir(tmpwd)
        self.system.cd(tmpwd)

        # Build the local namelist block
        nb = NamelistBlock(name="NAML")
        nb.NBDOM = 1
        nb.CHOPER = self.compact
        nb.INUMOD = self.numod
        if self.scizoffset is not None:
            nb.ISCIZ = self.scizoffset + (
                self.member if self.member is not None else 0
            )
        else:
            if self.sciz:
                nb.ISCIZ = self.sciz
        if self.timeshift:
            nb.IHCTPI = self.timeshift
        if self.timeunit:
            nb.ITUNIT = self.timeunit
        nb["CLFSORT(1)"] = thisoutput
        nb["CDNOMF(1)"] = self.fortinput
        with open(self.fortnam, "w") as namfd:
            namfd.write(nb.dumps())

        # Finally set the actual init file
        self.system.softlink(
            self.system.path.join(cwd, self.file_in), self.fortinput
        )

        # Standard execution
        list_name = self.system.path.join(cwd, self.file_out + ".listing")
        try:
            self.local_spawn(list_name)
        except ExecutionError as e:
            rdict["rc"] = e

        # Freeze the current output
        if self.system.path.exists(thisoutput):
            self.system.move(
                thisoutput, self.system.path.join(cwd, self.file_out)
            )
        else:
            logger.warning("Missing some grib output: %s", self.file_out)
            rdict["rc"] = False

        # Final cleaning
        self.system.cd(cwd)
        self.system.remove(tmpwd)

        if self.system.path.exists(self.file_out):
            # Deal with promised resources
            expected = [
                x
                for x in self.context.sequence.outputs()
                if x.rh.provider.expected
                and x.rh.container.localpath() == self.file_out
            ]
            for thispromise in expected:
                thispromise.put(incache=True)

        logger.info("Fa2Grib processing is done for tag=%s", self.name)

        return rdict


class _GribFilterWorker(TaylorVortexWorker):
    """The taylorism worker that actually filter the gribfiles.

    This is called indirectly by taylorism when :class:`Fa2Grib` is used.
    """

    _footprint = dict(
        attr=dict(
            kind=dict(values=["gribfilter"]),
            # Filter settings
            filters=dict(
                type=FPTuple,
            ),
            concatenate=dict(
                type=bool,
            ),
            # Put files if they are expected
            put_promises=dict(
                type=bool,
                optional=True,
                default=True,
            ),
            # Input/Output data
            file_in=dict(),
            file_outfmt=dict(),
            file_outintent=dict(
                optional=True,
                default="in",
            ),
        )
    )

    def vortex_task(self, **kwargs):
        logger.info("Starting the GribFiltering for tag=%s", self.file_in)

        rdict = dict(rc=True)

        # Create the filtering object and add filters
        gfilter = GRIBFilter(concatenate=self.concatenate)
        if self.filters:
            gfilter.add_filters(*list(self.filters))

        # Process the input file
        newfiles = gfilter(self.file_in, self.file_outfmt, self.file_outintent)

        if newfiles:
            if self.put_promises:
                # Deal with promised resources
                allpromises = [
                    x
                    for x in self.context.sequence.outputs()
                    if x.rh.provider.expected
                ]
                for newfile in newfiles:
                    expected = [
                        x
                        for x in allpromises
                        if x.rh.container.localpath() == newfile
                    ]
                    for thispromise in expected:
                        thispromise.put(incache=True)
        else:
            logger.warning("No file has been generated.")
            rdict["rc"] = False

        logger.info("GribFiltering is done for tag=%s", self.name)

        return rdict


def parallel_grib_filter(
    context,
    inputs,
    outputs,
    intents=(),
    cat=False,
    filters=FPTuple(),
    nthreads=8,
):
    """A simple method that calls the GRIBFilter class in parallel.

    :param vortex.layout.contexts.Context context: the current context
    :param list[str] inputs: the list of input file names
    :param list[str] outputs: the list of output file names
    :param list[str] intents: the list of intent (in|inout) for output files (in if omitted)
    :param bool cat: whether or not to concatenate the input files (False by default)
    :param tuple filters: a list of filters to apply (as a list of JSON dumps)
    :param int nthreads: the maximum number of tasks used concurently (8 by default)
    """
    if not cat and len(filters) == 0:
        raise AlgoComponentError(
            "cat must be true or filters must be provided"
        )
    if len(inputs) != len(outputs):
        raise AlgoComponentError(
            "inputs and outputs must have the same length"
        )
    if len(intents) != len(outputs):
        intents = FPTuple(
            [
                "in",
            ]
            * len(outputs)
        )
    boss = Boss(
        scheduler=footprints.proxy.scheduler(
            limit="threads", max_threads=nthreads
        )
    )
    common_i = dict(
        kind="gribfilter", filters=filters, concatenate=cat, put_promises=False
    )
    for ifile, ofile, intent in zip(inputs, outputs, intents):
        logger.info(
            "%s -> %s (intent: %s) added to the GRIBfilter task's list",
            ifile,
            ofile,
            intent,
        )
        boss.set_instructions(
            common_i,
            dict(
                name=[
                    ifile,
                ],
                file_in=[
                    ifile,
                ],
                file_outfmt=[
                    ofile,
                ],
                file_outintent=[
                    intent,
                ],
            ),
        )
    boss.make_them_work()
    boss.wait_till_finished()
    logger.info("All files are processed.")
    report = boss.get_report()
    prp = ParallelResultParser(context)
    for r in report["workers_report"]:
        if isinstance(prp(r), Exception):
            raise AlgoComponentError("An error occurred in GRIBfilter.")


class Fa2Grib(ParaBlindRun):
    """Standard FA conversion, e.g. with PROGRID as a binary resource."""

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=["fa2grib"],
            ),
            timeout=dict(
                type=int,
                optional=True,
                default=300,
            ),
            refreshtime=dict(
                type=int,
                optional=True,
                default=20,
            ),
            fatal=dict(
                type=bool,
                optional=True,
                default=True,
            ),
            fortnam=dict(
                optional=True,
                default="fort.4",
            ),
            fortinput=dict(
                optional=True,
                default="fort.11",
            ),
            compact=dict(
                optional=True,
                default=DelayedEnvValue("VORTEX_GRIB_COMPACT", "L"),
            ),
            timeshift=dict(
                type=int,
                optional=True,
                default=DelayedEnvValue("VORTEX_GRIB_SHIFT", 0),
            ),
            timeunit=dict(
                type=int,
                optional=True,
                default=DelayedEnvValue("VORTEX_GRIB_TUNIT", 1),
            ),
            numod=dict(
                type=int,
                optional=True,
                default=DelayedEnvValue("VORTEX_GRIB_NUMOD", 221),
            ),
            sciz=dict(
                type=int,
                optional=True,
                default=DelayedEnvValue("VORTEX_GRIB_SCIZ", 0),
            ),
            scizoffset=dict(
                type=int,
                optional=True,
            ),
        )
    )

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super().prepare(rh, opts)
        self.system.remove(self.fortinput)
        self.env.DR_HOOK_NOT_MPI = 1
        self.system.subtitle(
            "{:s} : directory listing (pre-run)".format(self.realkind)
        )
        self.system.dir(output=False, fatal=False)

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""

        self._default_pre_execute(rh, opts)

        common_i = self._default_common_instructions(rh, opts)
        # Update the common instructions
        common_i.update(
            dict(
                fortnam=self.fortnam,
                fortinput=self.fortinput,
                compact=self.compact,
                numod=self.numod,
                sciz=self.sciz,
                scizoffset=self.scizoffset,
                timeshift=self.timeshift,
                timeunit=self.timeunit,
            )
        )
        tmout = False

        # Monitor for the input files
        bm = BasicInputMonitor(
            self.context,
            caching_freq=self.refreshtime,
            role="Gridpoint",
            kind="gridpoint",
        )
        with bm:
            while not bm.all_done or len(bm.available) > 0:
                while bm.available:
                    s = bm.pop_available().section
                    file_in = s.rh.container.localpath()
                    # Find the name of the output file
                    if s.rh.provider.member is not None:
                        file_out = "GRIB{:s}_{!s}+{:s}".format(
                            s.rh.resource.geometry.area,
                            s.rh.provider.member,
                            s.rh.resource.term.fmthm,
                        )
                    else:
                        file_out = "GRIB{:s}+{:s}".format(
                            s.rh.resource.geometry.area,
                            s.rh.resource.term.fmthm,
                        )
                    logger.info(
                        "Adding input file %s to the job list", file_in
                    )
                    self._add_instructions(
                        common_i,
                        dict(
                            name=[
                                file_in,
                            ],
                            file_in=[
                                file_in,
                            ],
                            file_out=[
                                file_out,
                            ],
                            member=[
                                s.rh.provider.member,
                            ],
                        ),
                    )

                if not (bm.all_done or len(bm.available) > 0):
                    # Timeout ?
                    tmout = bm.is_timedout(self.timeout)
                    if tmout:
                        break
                    # Wait a little bit :-)
                    time.sleep(1)
                    bm.health_check(interval=30)

        self._default_post_execute(rh, opts)

        for failed_file in [
            e.section.rh.container.localpath() for e in bm.failed.values()
        ]:
            logger.error(
                "We were unable to fetch the following file: %s", failed_file
            )
            if self.fatal:
                self.delayed_exception_add(
                    IOError("Unable to fetch {:s}".format(failed_file)),
                    traceback=False,
                )

        if tmout:
            raise OSError("The waiting loop timed out")


class StandaloneGRIBFilter(TaylorRun):
    _footprint = dict(
        attr=dict(
            kind=dict(
                values=["gribfilter"],
            ),
            timeout=dict(
                type=int,
                optional=True,
                default=300,
            ),
            refreshtime=dict(
                type=int,
                optional=True,
                default=20,
            ),
            concatenate=dict(
                type=bool,
                default=False,
                optional=True,
            ),
            fatal=dict(
                type=bool,
                optional=True,
                default=True,
            ),
        )
    )

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super().prepare(rh, opts)
        self.system.subtitle(
            "{:s} : directory listing (pre-run)".format(self.realkind)
        )
        self.system.dir(output=False, fatal=False)

    def execute(self, rh, opts):
        # We re-serialise data because footprints don't like dictionaries
        filters = [
            json.dumps(x.rh.contents.data)
            for x in self.context.sequence.effective_inputs(
                role="GRIBFilteringRequest", kind="filtering_request"
            )
        ]
        filters = FPTuple(filters)

        self._default_pre_execute(rh, opts)

        common_i = self._default_common_instructions(rh, opts)
        # Update the common instructions
        common_i.update(dict(concatenate=self.concatenate, filters=filters))
        tmout = False

        # Monitor for the input files
        bm = BasicInputMonitor(
            self.context,
            caching_freq=self.refreshtime,
            role="Gridpoint",
            kind="gridpoint",
        )
        with bm:
            while not bm.all_done or len(bm.available) > 0:
                while bm.available:
                    s = bm.pop_available().section
                    file_in = s.rh.container.localpath()
                    file_outfmt = re.sub(
                        r"^(.*?)((:?\.[^.]*)?)$",
                        r"\1_{filtername:s}\2",
                        file_in,
                    )

                    logger.info(
                        "Adding input file %s to the job list", file_in
                    )
                    self._add_instructions(
                        common_i,
                        dict(
                            name=[
                                file_in,
                            ],
                            file_in=[
                                file_in,
                            ],
                            file_outfmt=[
                                file_outfmt,
                            ],
                        ),
                    )

                if not (bm.all_done or len(bm.available) > 0):
                    # Timeout ?
                    tmout = bm.is_timedout(self.timeout)
                    if tmout:
                        break
                    # Wait a little bit :-)
                    time.sleep(1)
                    bm.health_check(interval=30)

        self._default_post_execute(rh, opts)

        for failed_file in [
            e.section.rh.container.localpath() for e in bm.failed.values()
        ]:
            logger.error(
                "We were unable to fetch the following file: %s", failed_file
            )
            if self.fatal:
                self.delayed_exception_add(
                    IOError("Unable to fetch {:s}".format(failed_file)),
                    traceback=False,
                )

        if tmout:
            raise OSError("The waiting loop timed out")


class AddField(BlindRun):
    """Miscellaneous manipulation on input FA resources."""

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=["addcst", "addconst", "addfield"],
                remap=dict(
                    addconst="addcst",
                ),
            ),
            fortnam=dict(
                optional=True,
                default="fort.4",
            ),
            fortinput=dict(
                optional=True,
                default="fort.11",
            ),
            fortoutput=dict(
                optional=True,
                default="fort.12",
            ),
        )
    )

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super().prepare(rh, opts)
        self.system.remove(self.fortinput)
        self.env.DR_HOOK_NOT_MPI = 1

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""

        # Is there any namelist provided ?
        namrh = [
            x.rh
            for x in self.context.sequence.effective_inputs(
                role=("Namelist"), kind="namelist"
            )
        ]
        if namrh:
            self.system.softlink(namrh[0].container.localpath(), self.fortnam)
        else:
            logger.warning("Do not find any namelist for %s", self.kind)

        # Look for some sources files
        srcrh = [
            x.rh
            for x in self.context.sequence.effective_inputs(
                role=("Gridpoint", "Sources"), kind="gridpoint"
            )
        ]
        srcrh.sort(key=lambda rh: rh.resource.term)

        for r in srcrh:
            self.system.title(
                "Loop on domain {:s} and term {:s}".format(
                    r.resource.geometry.area, r.resource.term.fmthm
                )
            )

            # Some cleaning
            self.system.remove(self.fortinput)
            self.system.remove(self.fortoutput)

            # Prepare double input
            self.system.link(r.container.localpath(), self.fortinput)
            self.system.cp(r.container.localpath(), self.fortoutput)

            # Standard execution
            opts["loop"] = r.resource.term
            super().execute(rh, opts)

            # Some cleaning
            self.system.rmall("DAPDIR", self.fortinput, self.fortoutput)

    def postfix(self, rh, opts):
        """Post add cleaning."""
        super().postfix(rh, opts)
        self.system.remove(self.fortnam)


class DegradedDiagPEError(AlgoComponentError):
    """Exception raised when some of the members are missing in the calculations."""

    def __init__(self, ginfo, missings):
        super().__init__()
        self._ginfo = ginfo
        self._missings = missings

    def __str__(self):
        outstr = (
            "Missing input data for geometry={0.area:s}, term={1!s}:\n".format(
                self._ginfo["geometry"], self._ginfo["term"]
            )
        )
        for k, missing in self._missings.items():
            for member in missing:
                outstr += "{:s}: member #{!s}\n".format(k, member)
        return outstr


class DiagPE(BlindRun, DrHookDecoMixin, EcGribDecoMixin):
    """Execution of diagnostics on grib input (ensemble forecasts specific)."""

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=["diagpe"],
            ),
            method=dict(
                info="The method used to compute the diagnosis",
                values=["neighbour"],
            ),
            numod=dict(
                type=int,
                info="The GRIB model number",
                optional=True,
                default=DelayedEnvValue("VORTEX_GRIB_NUMOD", 118),
            ),
            timeout=dict(
                type=int,
                optional=True,
                default=900,
            ),
            refreshtime=dict(
                type=int,
                optional=True,
                default=20,
            ),
            missinglimit=dict(
                type=int,
                optional=True,
                default=0,
            ),
            waitlimit=dict(
                type=int,
                optional=True,
                default=900,
            ),
            fatal=dict(
                type=bool,
                optional=True,
                default=True,
            ),
            gribfilter_tasks=dict(
                type=int,
                optional=True,
                default=8,
            ),
        ),
    )

    _method2output_map = dict(neighbour="GRIB_PE_VOISIN")

    def spawn_hook(self):
        """Usually a good habit to dump the fort.4 namelist."""
        super().spawn_hook()
        if self.system.path.exists("fort.4"):
            self.system.subtitle(
                "{:s} : dump namelist <fort.4>".format(self.realkind)
            )
            self.system.cat("fort.4", output=False)

    def _actual_execute(
        self, gmembers, ifilters, filters, basedate, finalterm, rh, opts, gang
    ):
        mygeometry = gang.info["geometry"]
        myterm = gang.info["term"]

        self.system.title(
            "Start processing for geometry={:s}, term={!s}.".format(
                mygeometry.area, myterm
            )
        )

        # Find out what is the common set of members
        members = set(
            gmembers
        )  # gmembers is mutable: we need a copy of it (hence the explicit set())
        missing_members = dict()
        for subgang in gang.memberslist:
            smembers = {
                s.section.rh.provider.member
                for s in subgang.memberslist
                if s.state == EntrySt.available
            }
            ufomembers = {
                s.section.rh.provider.member
                for s in subgang.memberslist
                if s.state == EntrySt.ufo
            }
            missing_members[subgang.nickname] = (
                gmembers - smembers - ufomembers
            )
            members &= smembers
        # Record an error
        if members != gmembers:
            newexc = DegradedDiagPEError(gang.info, missing_members)
            logger.error("Some of the data are missing for this geometry/term")
            if self.fatal:
                self.delayed_exception_add(newexc, traceback=False)
            else:
                logger.info(
                    "Fatal is false consequently no exception is recorded. It would look like this:"
                )
                print(newexc)
        members = sorted(members)

        # This is hopeless :-(
        if gang.state == GangSt.failed:
            return

        # If needed, concatenate or filter the "superset" files
        supersets = list()
        for subgang in gang.memberslist:
            supersets.extend(
                [
                    (
                        s.section.rh.container.localpath(),
                        re.sub(
                            r"^[a-zA-Z]+_(.*)$",
                            r"\1",
                            s.section.rh.container.localpath(),
                        ),
                    )
                    for s in subgang.memberslist
                    if s.section.role == "GridpointSuperset"
                ]
            )
        supersets_todo = [
            (s, t) for s, t in supersets if not self.system.path.exists(t)
        ]
        if supersets_todo:
            if len(ifilters):
                parallel_grib_filter(
                    self.context,
                    [s for s, t in supersets_todo],
                    [t for s, t in supersets_todo],
                    filters=ifilters,
                    nthreads=self.gribfilter_tasks,
                )
            else:
                parallel_grib_filter(
                    self.context,
                    [s for s, t in supersets_todo],
                    [t for s, t in supersets_todo],
                    cat=True,
                    nthreads=self.gribfilter_tasks,
                )

        # Tweak the namelist
        namsec = self.setlink(
            initrole="Namelist", initkind="namelist", initname="fort.4"
        )
        for nam in [x.rh for x in namsec if "NAM_PARAM" in x.rh.contents]:
            logger.info(
                "Substitute the date (%s) to AAAAMMJJHH namelist entry",
                basedate.ymdh,
            )
            nam.contents["NAM_PARAM"]["AAAAMMJJHH"] = basedate.ymdh
            logger.info(
                "Substitute the number of members (%d) to NBRUN namelist entry",
                len(members),
            )
            nam.contents["NAM_PARAM"]["NBRUN"] = len(members)
            logger.info(
                "Substitute the the number of terms to NECH(0) namelist entry"
            )
            nam.contents["NAM_PARAM"]["NECH(0)"] = 1
            logger.info(
                "Substitute the ressource term to NECH(1) namelist entry"
            )
            # NB: term should be expressed in minutes
            nam.contents["NAM_PARAM"]["NECH(1)"] = int(myterm)
            nam.contents["NAM_PARAM"]["ECHFINALE"] = finalterm.hour
            # Now, update the model number for the GRIB files
            logger.info(
                "Substitute the model number (%d) to namelist entry",
                self.numod,
            )
            nam.contents["NAM_PARAM"]["NMODELE"] = self.numod
            # Add the NAM_PARAMPE block
            if "NAM_NMEMBRES" in nam.contents:
                # Cleaning is needed...
                del nam.contents["NAM_NMEMBRES"]
            newblock = nam.contents.newblock("NAM_NMEMBRES")
            for i, member in enumerate(members):
                newblock["NMEMBRES({:d})".format(i + 1)] = int(member)
            # We are done with the namelist
            nam.save()

        # Standard execution
        opts["loop"] = myterm
        super().execute(rh, opts)

        actualname = r"{:s}_{:s}\+{:s}".format(
            self._method2output_map[self.method], mygeometry.area, myterm.fmthm
        )
        # Find out the output file and filter it
        filtered_out = list()
        if len(filters):
            for candidate in [
                f
                for f in self.system.glob(
                    self._method2output_map[self.method] + "*"
                )
                if re.match(actualname, f)
            ]:
                logger.info("Starting GRIB filtering on %s.", candidate)
                filtered_out.extend(
                    filters(candidate, candidate + "_{filtername:s}")
                )

        # The diagnostic output may be promised
        expected = [
            x
            for x in self.promises
            if (
                re.match(actualname, x.rh.container.localpath())
                or x.rh.container.localpath() in filtered_out
            )
        ]
        for thispromise in expected:
            thispromise.put(incache=True)

    def execute(self, rh, opts):
        """Loop on the various grib files provided."""

        # Intialise a GRIBFilter for output files (at least try to)
        gfilter = GRIBFilter(concatenate=False)
        # We re-serialise data because footprints don't like dictionaries
        ofilters = [
            x.rh.contents.data
            for x in self.context.sequence.effective_inputs(
                role="GRIBFilteringRequest", kind="filtering_request"
            )
        ]
        gfilter.add_filters(ofilters)

        # Do we need to filter input files ?
        # We re-serialise data because footprints don't like dictionaries
        ifilters = [
            json.dumps(x.rh.contents.data)
            for x in self.context.sequence.effective_inputs(
                role="GRIBInputFilteringRequest"
            )
        ]

        # Monitor for the input files
        bm = BasicInputMonitor(
            self.context,
            caching_freq=self.refreshtime,
            role=(re.compile(r"^Gridpoint"), "Sources"),
            kind="gridpoint",
        )
        # Check that the date is consistent among inputs
        basedates = set()
        members = set()
        for rhI in [s.section.rh for s in bm.memberslist]:
            basedates.add(rhI.resource.date)
            members.add(rhI.provider.member)
        if len(basedates) > 1:
            raise AlgoComponentError(
                "The date must be consistent among the input resources"
            )
        basedate = basedates.pop()
        # Setup BasicGangs
        basicmeta = AutoMetaGang()
        basicmeta.autofill(
            bm,
            ("term", "safeblock", "geometry"),
            allowmissing=self.missinglimit,
            waitlimit=self.waitlimit,
        )
        # Find out what are the terms, domains and blocks
        geometries = set()
        terms = collections.defaultdict(set)
        blocks = collections.defaultdict(set)
        reverse = dict()
        for m in basicmeta.memberslist:
            (geo, term, block) = (
                m.info["geometry"],
                m.info["term"],
                m.info["safeblock"],
            )
            geometries.add(geo)
            terms[geo].add(term)
            blocks[geo].add(block)
            reverse[(geo, term, block)] = m
        for geometry in geometries:
            terms[geometry] = sorted(terms[geometry])
        # Setup the MetaGang that fits our needs
        complexmeta = MetaGang()
        complexgangs = collections.defaultdict(collections.deque)
        for geometry in geometries:
            nterms = len(terms[geometry])
            for i_term, term in enumerate(terms[geometry]):
                elementary_meta = MetaGang()
                elementary_meta.info = dict(geometry=geometry, term=term)
                cterms = [
                    terms[geometry][i]
                    for i in range(i_term, min(i_term + 2, nterms))
                ]
                for inside_term in cterms:
                    for inside_block in blocks[geometry]:
                        try:
                            elementary_meta.add_member(
                                reverse[(geometry, inside_term, inside_block)]
                            )
                        except KeyError:
                            raise KeyError(
                                "Something is wrong in the inputs: check again !"
                            )
                complexmeta.add_member(elementary_meta)
                complexgangs[geometry].append(elementary_meta)

        # Now, starts monitoring everything
        with bm:
            current_gang = dict()
            for geometry in geometries:
                try:
                    current_gang[geometry] = complexgangs[geometry].popleft()
                except IndexError:
                    current_gang[geometry] = None

            while any([g is not None for g in current_gang.values()]):
                for geometry, a_gang in [
                    (g, current_gang[g])
                    for g in geometries
                    if (
                        current_gang[g] is not None
                        and current_gang[g].state is not GangSt.ufo
                    )
                ]:
                    self._actual_execute(
                        members,
                        ifilters,
                        gfilter,
                        basedate,
                        terms[geometry][-1],
                        rh,
                        opts,
                        a_gang,
                    )

                    # Next one
                    try:
                        current_gang[geometry] = complexgangs[
                            geometry
                        ].popleft()
                    except IndexError:
                        current_gang[geometry] = None

                if not (
                    bm.all_done
                    or any(
                        gang is not None and gang.state is not GangSt.ufo
                        for gang in current_gang.values()
                    )
                ):
                    # Timeout ?
                    bm.is_timedout(self.timeout, IOError)
                    # Wait a little bit :-)
                    time.sleep(1)
                    bm.health_check(interval=30)


@algo_component_deco_mixin_autodoc
class _DiagPIDecoMixin(AlgoComponentDecoMixin):
    """Class variables and methods usefull for DiagPI."""

    _MIXIN_EXTRA_FOOTPRINTS = [
        footprints.Footprint(
            attr=dict(
                kind=dict(
                    values=["diagpi", "diaglabo"],
                ),
                numod=dict(
                    info="The GRIB model number",
                    type=int,
                    optional=True,
                    default=DelayedEnvValue("VORTEX_GRIB_NUMOD", 62),
                ),
                gribcat=dict(type=bool, optional=True, default=False),
                gribfilter_tasks=dict(
                    type=int,
                    optional=True,
                    default=8,
                ),
            ),
        )
    ]

    def _prepare_pihook(self, rh, opts):
        """Set some variables according to target definition."""

        # Check for input files to concatenate
        if self.gribcat:
            srcsec = self.context.sequence.effective_inputs(
                role=("Gridpoint", "Sources", "Preview", "Previous"),
                kind="gridpoint",
            )
            cat_list_in = [sec for sec in srcsec if not sec.rh.is_expected()]
            outsec = self.context.sequence.effective_inputs(
                role="GridpointOutputPrepare"
            )
            cat_list_out = [sec for sec in outsec if not sec.rh.is_expected()]
            self._automatic_cat(cat_list_in, cat_list_out)

        # prepare for delayed filtering
        self._delayed_filtering = []

    def _postfix_pihook(self, rh, opts):
        """Filter outputs."""
        if self._delayed_filtering:
            self._batch_filter(self._delayed_filtering)

    def _spawn_pihook(self):
        """Usually a good habit to dump the fort.4 namelist."""
        if self.system.path.exists("fort.4"):
            self.system.subtitle(
                "{:s} : dump namelist <fort.4>".format(self.realkind)
            )
            self.system.cat("fort.4", output=False)

    _MIXIN_PREPARE_HOOKS = (_prepare_pihook,)
    _MIXIN_POSTFIX_HOOKS = (_postfix_pihook,)
    _MIXIN_SPAWN_HOOKS = (_spawn_pihook,)

    def _automatic_cat(self, list_in, list_out):
        """Concatenate the *list_in* and *list_out* input files."""
        if self.gribcat:
            inputs = []
            outputs = []
            intents = []
            for seclist, intent in zip((list_in, list_out), ("in", "inout")):
                for isec in seclist:
                    tmpin = isec.rh.container.localpath() + ".tmpcat"
                    self.system.move(
                        isec.rh.container.localpath(), tmpin, fmt="grib"
                    )
                    inputs.append(tmpin)
                    outputs.append(isec.rh.container.localpath())
                    intents.append(intent)
            parallel_grib_filter(
                self.context,
                inputs,
                outputs,
                intents,
                cat=True,
                nthreads=self.gribfilter_tasks,
            )
            for ifile in inputs:
                self.system.rm(ifile, fmt="grib")

    def _batch_filter(self, candidates):
        """If no promises are made, the GRIB are filtered at once at the end."""
        # We re-serialise data because footprints don't like dictionaries
        filters = [
            json.dumps(x.rh.contents.data)
            for x in self.context.sequence.effective_inputs(
                role="GRIBFilteringRequest", kind="filtering_request"
            )
        ]
        parallel_grib_filter(
            self.context,
            candidates,
            [f + "_{filtername:s}" for f in candidates],
            filters=FPTuple(filters),
            nthreads=self.gribfilter_tasks,
        )

    def _execute_picommons(self, rh, opts):
        """Loop on the various grib files provided."""

        # Intialise a GRIBFilter (at least try to)
        gfilter = GRIBFilter(concatenate=False)
        gfilter.add_filters(self.context)

        srcsec = self.context.sequence.effective_inputs(
            role=("Gridpoint", "Sources"), kind="gridpoint"
        )
        srcsec.sort(key=lambda s: s.rh.resource.term)

        outsec = self.context.sequence.effective_inputs(
            role="GridpointOutputPrepare"
        )
        if outsec:
            outsec.sort(key=lambda s: s.rh.resource.term)

        for sec in srcsec:
            r = sec.rh
            self.system.title(
                "Loop on domain {:s} and term {:s}".format(
                    r.resource.geometry.area, r.resource.term.fmthm
                )
            )
            # Tweak the namelist
            namsec = self.setlink(
                initrole="Namelist", initkind="namelist", initname="fort.4"
            )
            for nam in [x.rh for x in namsec if "NAM_PARAM" in x.rh.contents]:
                logger.info(
                    "Substitute the date (%s) to AAAAMMJJHH namelist entry",
                    r.resource.date.ymdh,
                )
                nam.contents["NAM_PARAM"]["AAAAMMJJHH"] = r.resource.date.ymdh
                logger.info(
                    "Substitute the the number of terms to NECH(0) namelist entry"
                )
                nam.contents["NAM_PARAM"]["NECH(0)"] = 1
                logger.info(
                    "Substitute the ressource term to NECH(1) namelist entry"
                )
                # NB: term should be expressed in minutes
                nam.contents["NAM_PARAM"]["NECH(1)"] = int(r.resource.term)
                # Add the member number in a dedicated namelist block
                if r.provider.member is not None:
                    mblock = nam.contents.newblock("NAM_PARAMPE")
                    mblock["NMEMBER"] = int(r.provider.member)
                # Now, update the model number for the GRIB files
                if "NAM_DIAG" in nam.contents:
                    nmod = self.numod
                    logger.info(
                        "Substitute the model number (%d) to namelist entry",
                        nmod,
                    )
                    for namk in ("CONV", "BR", "HIV", "ECHOT", "ICA", "PSN"):
                        if (
                            namk in nam.contents["NAM_DIAG"]
                            and nam.contents["NAM_DIAG"][namk] != 0
                        ):
                            nam.contents["NAM_DIAG"][namk] = nmod
                # We are done with the namelist
                nam.save()

            cat_list_in = []
            cat_list_out = []

            # Expect the input grib file to be here
            if sec.rh.is_expected():
                cat_list_in.append(sec)
            self.grab(sec, comment="diagpi source")
            if outsec:
                out = outsec.pop(0)
                assert out.rh.resource.term == sec.rh.resource.term
                if out.rh.is_expected():
                    cat_list_out.append(out)
                self.grab(out, comment="diagpi output")

            # Also link in previous grib files in order to compute some winter diagnostics
            srcpsec = [
                x
                for x in self.context.sequence.effective_inputs(
                    role=("Preview", "Previous"), kind="gridpoint"
                )
                if x.rh.resource.term < r.resource.term
            ]
            for pr in srcpsec:
                if pr.rh.is_expected():
                    cat_list_in.append(pr)
                self.grab(
                    pr, comment="diagpi additional source for winter diag"
                )

            self._automatic_cat(cat_list_in, cat_list_out)

            # Standard execution
            opts["loop"] = r.resource.term
            super(self.mixin_execute_companion(), self).execute(rh, opts)

            actualname = r"GRIB[-_A-Z]+{:s}\+{:s}(?:_member\d+)?$".format(
                r.resource.geometry.area, r.resource.term.fmthm
            )
            # Find out the output file and filter it
            filtered_out = list()
            if len(gfilter):
                for candidate in [
                    f
                    for f in self.system.glob("GRIB*")
                    if re.match(actualname, f)
                ]:
                    if len(self.promises):
                        logger.info(
                            "Starting GRIB filtering on %s.", candidate
                        )
                        filtered_out.extend(
                            gfilter(candidate, candidate + "_{filtername:s}")
                        )
                    else:
                        self._delayed_filtering.append(candidate)

            # The diagnostic output may be promised
            expected = [
                x
                for x in self.promises
                if (
                    re.match(actualname, x.rh.container.localpath())
                    or x.rh.container.localpath() in filtered_out
                )
            ]
            for thispromise in expected:
                thispromise.put(incache=True)

    _MIXIN_EXECUTE_OVERWRITE = _execute_picommons


class DiagPI(BlindRun, _DiagPIDecoMixin, EcGribDecoMixin):
    """Execution of diagnostics on grib input (deterministic forecasts specific)."""

    pass


class DiagPIMPI(Parallel, _DiagPIDecoMixin, EcGribDecoMixin):
    """Execution of diagnostics on grib input (deterministic forecasts specific)."""

    pass


class Fa2GaussGrib(BlindRun, DrHookDecoMixin):
    """Standard FA conversion, e.g. with GOBPTOUT as a binary resource."""

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=["fa2gaussgrib"],
            ),
            fortinput=dict(
                optional=True,
                default="PFFPOS_FIELDS",
            ),
            numod=dict(
                type=int,
                optional=True,
                default=DelayedEnvValue("VORTEX_GRIB_NUMOD", 212),
            ),
            verbose=dict(
                type=bool,
                optional=True,
                default=False,
            ),
        )
    )

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""

        thisoutput = "GRID_" + self.fortinput[7:14] + "1"

        gpsec = self.context.sequence.effective_inputs(
            role=("Historic", "ModelState")
        )
        gpsec.sort(key=lambda s: s.rh.resource.term)

        for sec in gpsec:
            r = sec.rh

            self.system.title(
                "Loop on files: {:s}".format(r.container.localpath())
            )

            # Some preventive cleaning
            self.system.remove(thisoutput)
            self.system.remove("fort.4")

            # Build the local namelist block
            nb = NamelistBlock(name="NAML")
            nb.NBDOM = 1
            nb.INUMOD = self.numod

            nb["LLBAVE"] = self.verbose
            nb["CDNOMF(1)"] = self.fortinput
            with open("fort.4", "w") as namfd:
                namfd.write(nb.dumps())

            self.system.header(
                "{:s} : local namelist {:s} dump".format(
                    self.realkind, "fort.4"
                )
            )
            self.system.cat("fort.4", output=False)

            # Expect the input FP file source to be there...
            self.grab(sec, comment="fullpos source")

            # Finally set the actual init file
            self.system.softlink(r.container.localpath(), self.fortinput)

            # Standard execution
            super().execute(rh, opts)

            # Freeze the current output
            if self.system.path.exists(thisoutput):
                self.system.move(
                    thisoutput,
                    "GGRID" + r.container.localpath()[6:],
                    fmt="grib",
                )
            else:
                logger.warning("Missing some grib output for %s", thisoutput)

            # Some cleaning
            self.system.rmall(self.fortinput)


class Reverser(BlindRun, DrHookDecoMixin):
    """Compute the initial state for Ctpini."""

    _footprint = dict(
        info="Compute initial state for Ctpini.",
        attr=dict(
            kind=dict(
                values=["reverser"],
            ),
            param_iter=dict(
                type=int,
            ),
            condlim=dict(
                type=int,
            ),
            ano_type=dict(
                type=int,
            ),
        ),
    )

    def prepare(self, rh, opts):
        # Get info about the directives files directory
        directives = self.context.sequence.effective_inputs(
            role="Directives", kind="ctpini_directives_file"
        )
        if len(directives) < 1:
            logger.error("No directive file found. Stop")
            raise ValueError("No directive file found.")
        if len(directives) > 1:
            logger.warning(
                "Multiple directive files found. This is strange..."
            )
        # Substitute values in the simili namelist
        param = self.context.sequence.effective_inputs(role="Param")
        if len(param) < 1:
            logger.error("No parameter file found. Stop")
            raise ValueError("No parameter file found.")
        elif len(param) > 1:
            logger.warning(
                "Multiple files for parameter, the first %s is taken",
                param[0].rh.container.filename,
            )
        param = param[0].rh
        paramct = param.contents
        dictkeyvalue = dict()
        dictkeyvalue[r"param_iter"] = str(self.param_iter)
        dictkeyvalue[r"condlim"] = str(self.condlim)
        dictkeyvalue[r"ano_type"] = str(self.ano_type)
        paramct.setitems(dictkeyvalue)
        param.save()
        logger.info("Here is the parameter file (after substitution):")
        param.container.cat()
        # Call the parent's prepare
        super().prepare(rh, opts)


class DegradedEnsembleDiagError(AlgoComponentError):
    """Exception raised when some of the members are missing."""

    pass


class FailedEnsembleDiagError(DegradedEnsembleDiagError):
    """Exception raised when too many members are missing."""

    pass


class PyEnsembleDiag(Expresso):
    """Execution of diagnostics on grib input (ensemble forecasts specific)."""

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=["py_diag_ens"],
            ),
            timeout=dict(
                type=int,
                optional=True,
                default=1200,
            ),
            refreshtime=dict(
                type=int,
                optional=True,
                default=20,
            ),
            missinglimit=dict(
                type=int,
                optional=True,
                default=0,
            ),
            waitlimit=dict(
                type=int,
                optional=True,
                default=900,
            ),
        ),
    )

    def __init__(self, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self._cl_args = dict()

    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        return self._cl_args

    def _actual_execute(self, rh, opts, input_rhs, **infos):
        """Actually run the script for a specific bunch of input files (**inpu_rhs**)."""
        output_fname = (
            "ensdiag_{safeblock:s}_{geometry.tag:s}_{term.fmthm}.grib".format(
                **infos
            )
        )
        self._cl_args = dict(flowconf="flowconf.json", output=output_fname)

        # Create the JSON file that will be ingested by the script
        self.system.json_dump(
            dict(
                date=input_rhs[0].resource.date.ymdhm,
                term=infos["term"].fmthm,
                geometry=infos["geometry"].tag,
                area=infos["geometry"].area,
                block=infos["safeblock"],
                grib_files=[r.container.localpath() for r in input_rhs],
            ),
            self._cl_args["flowconf"],
        )

        # Actualy run the post-processing script
        super().execute(rh, opts)

        # The diagnostic output may be promised
        for thispromise in [
            x
            for x in self.promises
            if output_fname == x.rh.container.localpath()
        ]:
            thispromise.put(incache=True)

    @staticmethod
    def _gang_txt_id(gang):
        """A string that identifies the input data currently being processed."""
        return (
            "term={term.fmthm:s}, "
            + "geometry={geometry.tag:s} "
            + "and block={safeblock:s}"
        ).format(**gang.info)

    def _handle_gang_rescue(self, gang):
        """If some of the entries are missing, create a delayed exception."""
        if gang.state in (GangSt.pcollectable, GangSt.failed):
            txt_id = self._gang_txt_id(gang)
            self.system.subtitle("WARNING: Missing data for " + txt_id)
            for st in (EntrySt.ufo, EntrySt.failed, EntrySt.expected):
                if gang.members[st]:
                    print(
                        "Here is the list of Resource Handler with status < {:s} >:".format(
                            st
                        )
                    )
                    for i, e in enumerate(gang.members[st]):
                        e.section.rh.quickview(nb=i + 1, indent=1)
            self.delayed_exception_add(
                FailedEnsembleDiagError(
                    "Too many inputs are missing for " + txt_id
                )
                if gang.state == GangSt.failed
                else DegradedEnsembleDiagError(
                    "Some of the inputs are missing for " + txt_id
                ),
                traceback=False,
            )

    def execute(self, rh, opts):
        """Loop on the various grib files provided."""

        # Monitor for the input files
        bm = BasicInputMonitor(
            self.context, caching_freq=self.refreshtime, role="Gridpoint"
        )

        # Check that the date is consistent among inputs
        basedates = set()
        members = set()
        for rhI in [s.section.rh for s in bm.memberslist]:
            basedates.add(rhI.resource.date)
            members.add(rhI.provider.member)
        if len(basedates) > 1:
            raise AlgoComponentError(
                "The date must be consistent among the input resources"
            )

        # Setup BasicGangs
        basicmeta = AutoMetaGang()
        basicmeta.autofill(
            bm,
            ("term", "safeblock", "geometry"),
            allowmissing=self.missinglimit,
            waitlimit=self.waitlimit,
        )

        # Now, starts monitoring everything
        with bm:
            while basicmeta.has_ufo() or basicmeta.has_pcollectable():
                for thegang in basicmeta.consume_pcolectable():
                    txt_id = self._gang_txt_id(thegang)
                    self.system.title("Dealing with " + txt_id)

                    available = thegang.members[EntrySt.available]
                    self._handle_gang_rescue(thegang)

                    self._actual_execute(
                        rh,
                        opts,
                        [e.section.rh for e in available],
                        **thegang.info,
                    )

                    self.system.highlight("Done with " + txt_id)

                if (
                    not bm.all_done
                    and basicmeta.has_ufo()
                    and not basicmeta.has_pcollectable()
                ):
                    # Timeout ?
                    tmout = bm.is_timedout(self.timeout)
                    if tmout:
                        break
                    # Wait a little bit :-)
                    time.sleep(1)
                    bm.health_check(interval=30)

        # Warn for failed gangs
        if basicmeta.members[GangSt.failed]:
            self.system.title(
                "One or several (term, geometry, block) group(s) could not be processed"
            )
            for thegang in basicmeta.members[GangSt.failed]:
                self._handle_gang_rescue(thegang)
