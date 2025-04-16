"""
AlgoComponents to work with Observational DataBases.
"""

from collections import defaultdict
import copy
import re
import time

from bronx.fancies import loggers
from bronx.stdtypes.date import utcnow
from bronx.stdtypes.dictionaries import Foo
from bronx.system.memory import convert_bytes_in_unit
import footprints
from taylorism import Boss

from vortex.tools.systems import ExecutionError

from vortex.algo.components import Parallel, ParaBlindRun
from vortex.tools.parallelism import VortexWorkerBlindRun

from ..syntax.stdattrs import arpifs_cycle

from ..data.obs import ObsMapContent, ObsMapItem, ObsRefContent, ObsRefItem
from ..tools import odb, drhook


#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class Raw2OdbExecutionError(ExecutionError):
    def __init__(self, odb_database):
        self.odb_database = odb_database
        super().__init__("Raw2odb execution failed.")

    def __str__(self):
        return "Error while running bator for ODB database < {:s} >".format(
            self.odb_database
        )


class Bateur(VortexWorkerBlindRun):
    """
    Worker for parallel BATOR run. It returns in its report a synthesis about
    actual run-time and consumed memory (versus predictions).
    """

    _footprint = [
        arpifs_cycle,
        dict(
            info="Bateur: launches a single bator execution in a parallel context",
            attr=dict(
                base=dict(
                    info="name of the odb database to process",
                ),
                workdir=dict(
                    info="working directory of the run",
                ),
                inputsize=dict(
                    info="input files total size in bytes",
                    type=int,
                    default=0,
                ),
            ),
        ),
    ]

    @property
    def memory_in_bytes(self):
        return self.memory * 1024 * 1024

    def vortex_task(self, **kwargs):
        odb_drv = odb.OdbDriver(self.cycle, self.system, self.system.env)
        self.system.cd("wkdir_" + self.base)

        dbpath = self.system.path.join(self.workdir, "ECMA." + self.base)
        listpath = self.system.path.join(self.workdir, "listing." + self.base)

        odb_drv.fix_db_path("ecma", dbpath)

        real_time = -time.time()
        start_time = utcnow().isoformat()
        rdict = dict(rc=True)
        try:
            self.local_spawn(listpath)
        except ExecutionError:
            rdict["rc"] = Raw2OdbExecutionError(self.base)
        real_time += time.time()

        if self.system.memory_info is not None:
            realMem = self.system.memory_info.children_maxRSS("B")
            memRatio = (
                (realMem / float(self.memory_in_bytes))
                if self.memory_in_bytes > 0
                else None
            )
        else:
            realMem = None
            memRatio = None

        rdict["synthesis"] = dict(
            base=self.base,
            inputsize=self.inputsize,
            mem_expected=self.memory_in_bytes,
            mem_real=realMem,
            mem_ratio=memRatio,
            time_expected=self.expected_time,
            time_start=start_time,
            time_real=real_time,
            time_ratio=(
                real_time / float(self.expected_time)
                if self.expected_time > 0
                else None
            ),
            sched_id=self.scheduler_ticket,
        )

        # Save a copy of io assign map in the new database
        if self.system.path.isdir(dbpath):
            self.system.cp(
                self.system.path.join(
                    self.workdir, "odb_db_template", "IOASSIGN"
                ),
                self.system.path.join(dbpath, "IOASSIGN"),
            )
        else:
            logger.warning("ODB database not created: " + self.base)

        return rdict


class Raw2ODBparallel(
    ParaBlindRun, odb.OdbComponentDecoMixin, drhook.DrHookDecoMixin
):
    """Convert raw observations files to ODB using taylorism."""

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=["raw2odb", "bufr2odb", "obsoul2odb"],
                remap=dict(
                    bufr2odb="raw2odb",
                    obsoul2odb="raw2odb",
                ),
            ),
            engine=dict(
                values=[
                    "blind",
                    "parallel",
                ]  # parallel -> for backward compatibility
            ),
            ioassign=dict(
                optional=False,
            ),
            lamflag=dict(
                info="Activate LAMFLAG (i.e work for Limited Area Model)",
                type=bool,
                optional=True,
                default=False,
            ),
            ontime=dict(
                info="Check observation's resources date vs own data attribute.",
                type=bool,
                optional=True,
                default=True,
            ),
            mapall=dict(
                info="All observation files must be accounted for in an obsmap file. ",
                type=bool,
                optional=True,
                default=False,
            ),
            maponly=dict(
                info=(
                    "Work only with observation files listed in the obsmap files. "
                    + "(if False, obsmap entries may be automatically generated)."
                ),
                type=bool,
                optional=True,
                default=False,
            ),
            member=dict(
                info=(
                    "The current member's number "
                    + "(may be omitted in deterministic configurations)."
                ),
                optional=True,
                type=int,
            ),
            dataid=dict(
                info=(
                    "The ODB databases created by Bator contain an identifier "
                    + "that is specified as a command-line argument. This "
                    + "switch tweaks the way the command-line argument is "
                    + "generated."
                ),
                values=["empty", "hh"],
                default="hh",
                optional=True,
            ),
            ntasks=dict(
                info=(
                    "The maximum number of allowed concurrent task for "
                    "parallel execution."
                ),
                default=1,
                optional=True,
            ),
            maxmemory=dict(
                info="The maximum amount of usable memory (in GiB)",
                type=int,
                optional=True,
            ),
            parallel_const=dict(
                info=(
                    "Constant that are used to predict execution time and "
                    + "memory consumption for a given ODB database."
                ),
                type=footprints.FPDict,
                optional=True,
            ),
        )
    )

    _donot_link_roles = [
        "Observations",
        "Obsmap",
        "IOPoll",
        "LFIScripts",
        "LFITOOLS",
        "Binary",
        "Bator",
        "Batodb",
    ]

    def __init__(self, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self.para_synthesis = dict()
        self.obspack = dict()
        self.obsmapout = list()
        self._effective_maxmem = None

    @property
    def effective_maxmem(self):
        """Return the maximum amount of usable memory (in MiB)."""
        if self._effective_maxmem is None:
            if self.maxmemory:
                self._effective_maxmem = (
                    self.maxmemory * 1024
                )  # maxmemory in GB
            else:
                sys_maxmem = self.system.memory_info.system_RAM("MiB")
                # System memory minus 20% or minus 4GB
                self._effective_maxmem = max(
                    sys_maxmem * 0.8, sys_maxmem - 4 * 1024
                )
        return self._effective_maxmem

    def input_obs(self):
        """Find out which are the usable observations."""
        obsall = [
            x
            for x in self.context.sequence.effective_inputs(
                kind="observations"
            )
        ]
        obsall.sort(key=lambda s: s.rh.resource.part)

        # Looking for valid raw observations
        sizemin = self.env.VORTEX_OBS_SIZEMIN or 80
        obsok = list()
        for secobs in obsall:
            rhobs = secobs.rh
            if rhobs.resource.nativefmt == "odb":
                logger.warning(
                    "Observations set [%s] is ODB ready", rhobs.resource.part
                )
                continue
            if rhobs.container.totalsize < sizemin:
                logger.warning(
                    "Observations set [%s] is far too small: %d",
                    rhobs.resource.part,
                    rhobs.container.totalsize,
                )
            else:
                logger.info(
                    "Observations set [%s] has size: %d",
                    rhobs.resource.part,
                    int(rhobs.container.totalsize),
                )
                obsok.append(Foo(rh=rhobs, refdata=list(), mapped=False))

        # Check the observations dates
        for obs in [obs for obs in obsok if obs.rh.resource.date != self.date]:
            logger.warning(
                "Observation [%s] %s [time mismatch: %s / %s]",
                "discarded" if self.ontime else "is questionable",
                obs.rh.resource.part,
                obs.rh.resource.date.isoformat(),
                self.date.isoformat(),
            )
        if self.ontime:
            obsok = [obs for obs in obsok if obs.rh.resource.date == self.date]

        return obsok

    def _retrieve_refdatainfo(self, obslist):
        """Look for refdata resources and link their content with the obslist."""
        refmap = dict()
        refall = list(self.context.sequence.effective_inputs(kind="refdata"))
        for rdata in refall:
            logger.info("Inspect refdata " + rdata.rh.container.localpath())
            self.system.subtitle(rdata.role)
            rdata.rh.container.cat()
            for item in rdata.rh.contents:
                refmap[(item.fmt.lower(), item.data, item.instr)] = (
                    rdata.rh,
                    item,
                )

        # Build actual refdata
        for obs in obslist:
            thispart = obs.rh.resource.part
            thisfmt = obs.rh.container.actualfmt.lower()
            logger.info(
                " ".join(
                    ("Building information for [", thisfmt, "/", thispart, "]")
                )
            )

            # Gather equivalent refdata lines
            if not self.system.path.exists("norefdata." + thispart) and (
                not self.env.VORTEX_OBSDB_NOREF
                or not re.search(
                    thispart, self.env.VORTEX_OBSDB_NOREF, re.IGNORECASE
                )
            ):
                for k, v in refmap.items():
                    x_fmt, x_data = k[:2]
                    if x_fmt == thisfmt and x_data == thispart:
                        rdata, item = v
                        obs.refdata.append(rdata.contents.formatted_data(item))
        return refmap, refall

    def _map_refdatainfo(self, refmap, refall, imap, thismap):
        """Associate obsmap entries with refdata entries."""
        thiskey = (imap.fmt.lower(), imap.data, imap.instr)
        if thiskey in refmap:
            rdata, item = refmap[thiskey]
            thismap.refdata.append(rdata.contents.formatted_data(item))
        else:
            logger.warning(
                "Creating automatic refdata entry for " + str(thiskey)
            )
            item = ObsRefItem(
                imap.data, imap.fmt, imap.instr, self.date.ymd, self.date.hh
            )
            if refall:
                thismap.refdata.append(
                    refall[0].rh.contents.formatted_data(item)
                )
            else:
                logger.error("No default for formatting data %s", item)
                thismap.refdata.append(ObsRefContent.formatted_data(item))

    @staticmethod
    def _new_obspack_item():
        """Create a now entry in obspack."""
        return Foo(
            mapping=list(), standalone=False, refdata=list(), obsfile=dict()
        )

    def prepare(self, rh, opts):
        """Get a look at raw observations input files."""

        sh = self.system
        cycle = rh.resource.cycle

        # First create the proper IO assign table for any of the resulting ECMA databases
        self.odb_create_db("ECMA", "odb_db_template")
        self.env.IOASSIGN = sh.path.abspath(
            sh.path.join("odb_db_template", "IOASSIGN")
        )

        # Looking for input observations
        obsok = self.input_obs()

        # Building refdata map for direct access to (fmt, data, instr) entries
        if cycle < "cy42_op1":
            # Refdata information is not needed anymore with cy42_op1
            refmap, refall = self._retrieve_refdatainfo(obsok)

        # Looking for obs maps
        mapitems = list()
        for omsec in self.context.sequence.effective_inputs(kind="obsmap"):
            logger.info(
                " ".join(
                    (
                        "Gathering information from map",
                        omsec.rh.container.localpath(),
                    )
                )
            )
            sh.subtitle(omsec.role)
            omsec.rh.container.cat()
            mapitems.extend(omsec.rh.contents)

        self.obspack = defaultdict(self._new_obspack_item)  # Reset the obspack
        for imap in mapitems:
            # Match observation files and obsmap entries + Various checks
            logger.info("Inspect " + str(imap))
            candidates = [
                obs
                for obs in obsok
                if (
                    obs.rh.resource.part == imap.data
                    and obs.rh.container.actualfmt.lower() == imap.fmt.lower()
                )
            ]
            if not candidates:
                errmsg = (
                    "No input obsfile could match [data:{:s}/fmt:{:s}]".format(
                        imap.data, imap.fmt
                    )
                )
                if self.mapall:
                    raise ValueError(errmsg)
                else:
                    logger.warning(errmsg)
                    continue
            candidates[-1].mapped = True
            # Build the obspack entry
            thismap = self.obspack[imap.odb]
            thismap.mapping.append(imap)
            thismap.obsfile[imap.fmt.upper() + "." + imap.data] = candidates[
                -1
            ]
            # Map refdata and obsmap entries
            if cycle < "cy42_op1":
                # Refdata information is not needed anymore with cy42_op1
                self._map_refdatainfo(refmap, refall, imap, thismap)

        # Deal with observations that are not described in the obsmap
        for notmap in [obs for obs in obsok if not obs.mapped]:
            thispart = notmap.rh.resource.part
            logger.info("Inspect not mapped obs " + thispart)
            if thispart not in self.obspack:
                thisfmt = notmap.rh.container.actualfmt.upper()
                thismsg = "standalone obs entry [data:{:s} / fmt:{:s}]".format(
                    thispart, thisfmt
                )
                if self.maponly:
                    logger.warning("Ignore " + thismsg)
                else:
                    logger.warning("Active " + thismsg)
                    thismap = self.obspack[thispart]
                    thismap.standalone = thisfmt
                    thismap.mapping.append(
                        ObsMapItem(thispart, thispart, thisfmt, thispart)
                    )
                    thismap.refdata = notmap.refdata
                    thismap.obsfile[thisfmt.upper() + "." + thispart] = notmap

        # Informations about timeslots
        logger.info("The timeslot definition is: %s", str(self.slots))
        if cycle < "cy42_op1":
            # ficdate is not needed anymore with cy42_op1...
            self.slots.as_file(self.date, "ficdate")
        else:
            # From cy42_op1 onward, we only need environment variables
            for var, value in self.slots.as_environment().items():
                logger.info("Setting env %s = %s", var, str(value))
                self.env[var] = value

        # Let ancestors handling most of the env setting
        super().prepare(rh, opts)
        self.env.update(
            BATOR_NBPOOL=self.npool,
            BATODB_NBPOOL=self.npool,
            BATOR_NBSLOT=self.slots.nslot,
            BATODB_NBSLOT=self.slots.nslot,
        )
        self.env.default(
            TIME_INIT_YYYYMMDD=self.date.ymd,
            TIME_INIT_HHMMSS=self.date.hm + "00",
        )
        if self.lamflag:
            for lamvar in ("BATOR_LAMFLAG", "BATODB_LAMFLAG"):
                logger.info("Setting env %s = %d", lamvar, 1)
                self.env[lamvar] = 1

        if self.member is not None:
            for nam in self.context.sequence.effective_inputs(
                kind=("namelist", "namelistfp")
            ):
                nam.rh.contents.setmacro("MEMBER", self.member)
                logger.info(
                    "Setup macro MEMBER=%s in %s",
                    self.member,
                    nam.rh.container.actualpath(),
                )
                if nam.rh.contents.dumps_needs_update:
                    nam.rh.save()

    def spawn_command_options(self):
        """Any data useful to build the command line."""
        opts_dict = super().spawn_command_options()
        opts_dict["dataid"] = self.dataid
        opts_dict["date"] = self.date
        return opts_dict

    def _default_pre_execute(self, rh, opts):
        """Change default initialisation to use LongerFirstScheduler"""
        # Start the task scheduler
        self._boss = Boss(
            verbose=self.verbose,
            scheduler=footprints.proxy.scheduler(
                limit="threads+memory",
                max_threads=self.ntasks,
                max_memory=self.effective_maxmem,
            ),
        )
        self._boss.make_them_work()

    def execute(self, rh, opts):
        """
        For each base, a directory is created such that each worker works in his
        directory. Symlinks are created into these working directories.
        """

        sh = self.system
        cycle = rh.resource.cycle

        batnam = [
            x.rh
            for x in self.context.sequence.effective_inputs(
                role="NamelistBatodb"
            )
        ]
        # Give a glance to the actual namelist
        if batnam:
            sh.subtitle("Namelist Raw2ODB")
            batnam[0].container.cat()

        self.obsmapout = list()  # Reset the obsmapout
        scheduler_instructions = defaultdict(list)

        workdir = sh.pwd()

        for odbset, thispack in self.obspack.items():
            odbname = self.virtualdb.upper() + "." + odbset
            sh.title("Cocooning ODB set: " + odbname)
            with sh.cdcontext("wkdir_" + odbset, create=True):
                for inpt in [
                    s
                    for s in self.context.sequence.inputs()
                    if s.stage == "get"
                ]:
                    if inpt.role not in self._donot_link_roles:
                        logger.info(
                            "creating softlink: %s -> %s",
                            inpt.rh.container.localpath(),
                            sh.path.join(
                                workdir, inpt.rh.container.localpath()
                            ),
                        )
                        sh.softlink(
                            sh.path.join(
                                workdir, inpt.rh.container.localpath()
                            ),
                            inpt.rh.container.localpath(),
                        )

                if cycle < "cy42_op1":
                    # Special stuff for cy < 42
                    logger.info("creating softlink for ficdate.")
                    sh.softlink(sh.path.join(workdir, "ficdate"), "ficdate")

                odb_input_size = 0
                for obsname, obsinfo in thispack.obsfile.items():
                    logger.info(
                        "creating softlink: %s -> %s",
                        obsname,
                        sh.path.join(
                            workdir, obsinfo.rh.container.localpath()
                        ),
                    )
                    sh.softlink(
                        sh.path.join(
                            workdir, obsinfo.rh.container.localpath()
                        ),
                        obsname,
                    )
                    if thispack.standalone and cycle < "cy42_op1":
                        logger.info(
                            "creating softlink: %s -> %s",
                            thispack.standalone,
                            sh.path.join(
                                workdir, obsinfo.rh.container.localpath()
                            ),
                        )
                        sh.softlink(
                            sh.path.join(
                                workdir, obsinfo.rh.container.localpath()
                            ),
                            thispack.standalone,
                        )

                    odb_input_size += obsinfo.rh.container.totalsize

                # Fill the actual refdata according to information gathered in prepare stage
                if cycle < "cy42_op1":
                    if thispack.refdata:
                        with open("refdata", "w") as fd:
                            for rdentry in thispack.refdata:
                                fd.write(str(rdentry + "\n"))
                        sh.subtitle("Local refdata for: {:s}".format(odbname))
                        sh.cat("refdata", output=False)
                # Drive bator with a batormap file (from cy42_op1 onward)
                else:
                    with open("batormap", "w") as fd:
                        for mapentry in sorted(thispack.mapping):
                            fd.write(
                                str(
                                    ObsMapContent.formatted_data(mapentry)
                                    + "\n"
                                )
                            )
                    sh.subtitle("Local batormap for: {:s}".format(odbname))
                    sh.cat("batormap", output=False)

                self.obsmapout.extend(thispack.mapping)

                # Compute the expected memory and time
                if isinstance(self.parallel_const, dict):
                    pconst = self.parallel_const.get(
                        odbset,
                        self.parallel_const.get("default", (999999.0, 1.0)),
                    )
                    offsets = self.parallel_const.get(
                        "offset", (0.0, 0.0)
                    )  # In MiB for the memory
                else:
                    pconst = (999999.0, 1.0)
                    offsets = (0.0, 0.0)
                bTime = (odb_input_size * pconst[1] / 1048576) + offsets[1]
                bMemory = odb_input_size * pconst[0] + (
                    offsets[0] * 1024 * 1024
                )
                bMemory = bMemory / 1024.0 / 1024.0
                if bMemory > self.effective_maxmem:
                    logger.info(
                        "For %s, the computed memory needs exceed the node limit.",
                        odbset,
                    )
                    logger.info(
                        "Memory requirement reseted to %d (originally %d.)",
                        int(self.effective_maxmem),
                        int(bMemory),
                    )
                    bMemory = self.effective_maxmem
                scheduler_instructions["name"].append(
                    "ODB_database_{:s}".format(odbset)
                )
                scheduler_instructions["base"].append(odbset)
                scheduler_instructions["memory"].append(bMemory)
                scheduler_instructions["expected_time"].append(bTime)
                scheduler_instructions["inputsize"].append(odb_input_size)

        sh.title("Launching Bator using taylorism...")
        self._default_pre_execute(rh, opts)
        common_i = self._default_common_instructions(rh, opts)
        # Update the common instructions
        common_i.update(
            dict(
                workdir=workdir,
                cycle=cycle,
            )
        )

        self._add_instructions(common_i, scheduler_instructions)

        post_opts = copy.copy(opts)
        post_opts["synthesis"] = self.para_synthesis
        self._default_post_execute(rh, post_opts)

    def _default_rc_action(self, rh, opts, report, rc):
        super()._default_rc_action(rh, opts, report, rc)
        my_report = report["report"].get("synthesis", None)
        if my_report:
            opts["synthesis"][my_report.pop("base")] = my_report

    def postfix(self, rh, opts):
        """Post conversion cleaning."""
        sh = self.system

        # Remove empty ECMA databases from the output obsmap
        self.obsmapout = [
            x
            for x in self.obsmapout
            if (
                sh.path.isdir("ECMA." + x.odb)
                and sh.path.isdir("ECMA." + x.odb + "/1")
            )
        ]

        # At least one non-empty database is needed...
        self.algoassert(
            self.obsmapout, "At least one non-empty ODB database is expected"
        )

        # Generate the output bator_map
        with open("batodb_map.out", "w") as fd:
            for x in sorted(self.obsmapout):
                fd.write(str(ObsMapContent.formatted_data(x) + "\n"))

        # Generate a global refdata (if cycle allows it and if possible)
        if rh.resource.cycle < "cy42_op1":
            rdrh_dict = {
                y.rh.resource.part: y.rh
                for y in self.context.sequence.effective_inputs(kind="refdata")
                if y.rh.resource.part != "all"
            }
            with open("refdata_global", "w") as rdg:
                for x in sorted(self.obsmapout):
                    if (
                        x.data in rdrh_dict
                        and sh.path.getsize(
                            rdrh_dict[x.data].container.localpath()
                        )
                        > 0
                    ):
                        with open(
                            rdrh_dict[x.data].container.localpath()
                        ) as rdl:
                            rdg.write(rdl.readline())
                    elif (
                        sh.path.exists("refdata." + x.data)
                        and sh.path.getsize("refdata." + x.data) > 0
                    ):
                        with open("refdata." + x.data) as rdl:
                            rdg.write(rdl.readline())
                    else:
                        logger.info(
                            "Unable to create a global refdata entry for data="
                            + x.data
                        )

        sh.json_dump(self.para_synthesis, "parallel_exec_synthesis.json")

        # Print the parallel execution summary
        sh.subtitle("Here is the parallel execution synthesis: memory aspects")
        header = "Database  InputSize(MiB) PredMem(GiB) RealMem(GiB) Real/Pred Ratio"
        rfmt = "{:8s} {:>15.0f} {:>12.1f} {:>12.1f} {:>15.2f}"
        print(header)
        for row in sorted(self.para_synthesis.keys()):
            srep = self.para_synthesis[row]
            print(
                rfmt.format(
                    row,
                    convert_bytes_in_unit(srep["inputsize"], "MiB"),
                    convert_bytes_in_unit(srep["mem_expected"], "GiB"),
                    (
                        99.99
                        if srep["mem_real"] is None
                        else convert_bytes_in_unit(srep["mem_real"], "GiB")
                    ),
                    (
                        99.99
                        if srep["mem_ratio"] is None
                        else srep["mem_ratio"]
                    ),
                )
            )

        sh.subtitle(
            "Here is the parallel execution synthesis: elapsed time aspects"
        )
        header = (
            "Database  InputSize(MiB) PredTime(s) RealTime(s) Real/Pred Ratio"
        )
        rfmt = "{:8s} {:>15.0f} {:>11.1f} {:>11.1f} {:>15.2f}"
        print(header)
        for row in sorted(self.para_synthesis.keys()):
            srep = self.para_synthesis[row]
            print(
                rfmt.format(
                    row,
                    convert_bytes_in_unit(srep["inputsize"], "MiB"),
                    srep["time_expected"],
                    srep["time_real"],
                    (
                        99.99
                        if srep["time_ratio"] is None
                        else srep["time_ratio"]
                    ),
                )
            )

        sh.subtitle("Here is the parallel execution synthesis: timeline")
        header = "Database                           StartTime(UTC) PredMem(GiB) RealTime(s) ExecSlot"
        rfmt = "{:8s} {:>40s} {:>11.1f} {:>12.1f} {:>8s}"
        print(header)
        for row, srep in sorted(
            self.para_synthesis.items(), key=lambda x: x[1]["time_start"]
        ):
            print(
                rfmt.format(
                    row,
                    srep["time_start"],
                    convert_bytes_in_unit(srep["mem_expected"], "GiB"),
                    srep["time_real"],
                    str(srep["sched_id"]),
                )
            )

        print(
            "\nThe memory limit was set to: {:.1f} GiB".format(
                self.effective_maxmem / 1024.0
            )
        )

        super().postfix(rh, opts)


class OdbAverage(Parallel, odb.OdbComponentDecoMixin, drhook.DrHookDecoMixin):
    """TODO the father of this component is very much welcome."""

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=["average"],
            ),
            binarysingle=dict(
                default="basicobsort",
            ),
            ioassign=dict(),
            outdb=dict(
                optional=True,
                default="ccma",
                value=["ecma", "ccma"],
            ),
            maskname=dict(
                optional=True,
                default="mask4x4.txt",
            ),
        )
    )

    def _mpitool_attributes(self, opts):
        conf_dict = super()._mpitool_attributes(opts)
        conf_dict.update({"mplbased": True})
        return conf_dict

    def prepare(self, rh, opts):
        """Find any ODB candidate in input files."""

        sh = self.system

        # Looking for input observations
        obsall = [
            x
            for x in self.lookupodb()
            if x.rh.resource.layout.lower() == "ecma"
        ]
        # One database at a time
        if len(obsall) != 1:
            raise ValueError("One and only one ECMA input should be here")
        self.bingo = ecma = obsall[0]

        # First create a fake CCMA
        self.layout_new = self.outdb.upper()
        ccma_path = self.odb_create_db(self.layout_new)
        self.odb.fix_db_path(self.layout_new, ccma_path)

        self.layout_in = ecma.rh.resource.layout.upper()
        ecma_path = sh.path.abspath(ecma.rh.container.localpath())
        self.odb.fix_db_path(self.layout_in, ecma_path)

        self.odb.ioassign_gather(ecma_path, ccma_path)

        ecma_pool = sh.path.join(ecma_path, "1")
        if not sh.path.isdir(ecma_pool):
            logger.error("The input ECMA base is empty")
            self.abort("No ECMA input")
            return

        self.odb.create_poolmask(self.layout_new, ccma_path)

        # Some extra settings
        self.env.update(
            TO_ODB_CANARI=0,
            TO_ODB_REDUC=self.env.TO_ODB_REDUC or 1,
            TO_ODB_SETACTIVE=1,
        )

        # Let ancesters handling most of the env setting
        super().prepare(rh, opts)

    def spawn_command_options(self):
        """Prepare command line options to binary."""
        return dict(
            dbin=self.layout_in,
            dbout=self.layout_new,
            npool=self.npool,
            nslot=self.slots.nslot,
            date=self.date,
            masksize=4,
        )

    def execute(self, rh, opts):
        """To mask input."""

        sh = self.system

        mask = [
            x.rh
            for x in self.context.sequence.effective_inputs(kind="atmsmask")
        ]
        if not mask:
            raise ValueError("Could not find any MASK input")

        # Have a look to mask file
        if mask[0].container.localpath() != self.maskname:
            sh.softlink(mask[0].container.localpath(), self.maskname)

        sh.subtitle("Mask")
        mask[0].container.cat()

        # Standard execution
        super().execute(rh, opts)

    def postfix(self, rh, opts):
        """Post shuffle / average cleaning."""
        sh = self.system

        with sh.cdcontext(self.layout_new):
            for ccma in sh.glob("{:s}.*".format(self.layout_new)):
                slurp = sh.cat(ccma, outsplit=False).replace(
                    self.layout_new, self.layout_in
                )
                with open(
                    ccma.replace(self.layout_new, self.layout_in), "w"
                ) as fd:
                    fd.write(str(slurp))
                sh.rm(ccma)

        sh.mv(
            self.layout_new, self.layout_in + "." + self.bingo.rh.resource.part
        )

        super().postfix(rh, opts)


class OdbCompress(Parallel, odb.OdbComponentDecoMixin, drhook.DrHookDecoMixin):
    """Take a screening ODB ECMA database and create the compressed CCMA database."""

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=["odbcompress"],
            ),
            ioassign=dict(),
        )
    )

    def _mpitool_attributes(self, opts):
        conf_dict = super()._mpitool_attributes(opts)
        conf_dict.update({"mplbased": True})
        return conf_dict

    def prepare(self, rh, opts):
        """Find any ODB candidate in input files and fox ODB env accordingly."""

        obsall = [
            x
            for x in self.lookupodb()
            if x.rh.resource.layout.lower() == "ecma"
        ]
        if len(obsall) > 1:
            obsvirtual = [o for o in obsall if o.rh.resource.part == "virtual"]
            if len(obsvirtual) != 1:
                raise ValueError(
                    "One and only one virtual database must be provided"
                )
            ecma = obsvirtual[0]
        elif len(obsall) == 1:
            ecma = obsall[0]
        else:
            raise ValueError("No ECMA database provided")

        # First create a fake CCMA
        self.layout_new = "ccma"
        ccma_path = self.odb_create_db(self.layout_new)
        self.odb.fix_db_path(self.layout_new, ccma_path)

        self.layout_in = ecma.rh.resource.layout.upper()
        ecma_path = self.system.path.abspath(ecma.rh.container.localpath())
        self.odb.fix_db_path(self.layout_in, ecma_path)

        self.odb.ioassign_gather(ecma_path, ccma_path)

        self.odb.create_poolmask(self.layout_new, ccma_path)

        self.odb_rw_or_overwrite_method(*obsall)

        # Let ancesters handling most of the env setting
        super().prepare(rh, opts)

    def spawn_command_options(self):
        """Prepare command line options to binary."""
        return dict(
            dbin=self.layout_in,
            dbout=self.layout_new,
            npool=self.npool,
            nslot=self.slots.nslot,
            date=self.date,
        )


class OdbMatchup(Parallel, odb.OdbComponentDecoMixin, drhook.DrHookDecoMixin):
    """Report some information from post-minim CCMA to post-screening ECMA base."""

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=["matchup"],
            ),
            fcmalayout=dict(
                optional=True,
                value=["ecma", "ccma", "CCMA", "ECMA"],
                remap=dict(CCMA="ccma", ECMA="ecma"),
            ),
        )
    )

    def _mpitool_attributes(self, opts):
        conf_dict = super()._mpitool_attributes(opts)
        conf_dict.update({"mplbased": True})
        return conf_dict

    def prepare(self, rh, opts):
        """Find ODB candidates in input files."""

        sh = self.system

        # Looking for input observations
        obsscr_virtual = [
            x
            for x in self.lookupodb()
            if x.rh.resource.stage.startswith("screen")
            and x.rh.resource.part == "virtual"
        ]
        obsscr_parts = [
            x
            for x in self.lookupodb()
            if x.rh.resource.stage.startswith("screen")
            and x.rh.resource.part != "virtual"
        ]
        obscompressed = [
            x
            for x in self.lookupodb()
            if x.rh.resource.stage.startswith("min")
            or x.rh.resource.stage.startswith("traj")
        ]

        # One database at a time
        if not obsscr_virtual:
            raise ValueError("Could not find any ODB screening input")
        if not obscompressed:
            raise ValueError("Could not find any ODB minim input")

        # Set actual layout and path
        ecma = obsscr_virtual.pop(0)
        ccma = obscompressed.pop(0)
        self.layout_screening = ecma.rh.resource.layout
        self.layout_compressed = ccma.rh.resource.layout
        self.layout_fcma = (
            self.layout_compressed
            if self.fcmalayout is None
            else self.fcmalayout
        )
        ecma_path = sh.path.abspath(ecma.rh.container.localpath())
        ccma_path = sh.path.abspath(ccma.rh.container.localpath())

        self.odb.fix_db_path(self.layout_screening, ecma_path)
        self.odb.fix_db_path(self.layout_compressed, ccma_path)
        self.odb.ioassign_gather(ccma_path, ecma_path)

        # Ok, but why ???
        sh.cp(
            sh.path.join(ecma_path, "ECMA.dd"),
            sh.path.join(ccma_path, "ECMA.dd"),
        )

        # Let ancesters handling most of the env setting
        super().prepare(rh, opts)

        # Fix the input database intent
        self.odb_rw_or_overwrite_method(ecma)
        self.odb_rw_or_overwrite_method(*obsscr_parts)

    def spawn_command_options(self):
        """Prepare command line options to binary."""
        return dict(
            dbin=self.layout_compressed,
            dbout=self.layout_screening,
            npool=self.npool,
            nslot=self.slots.nslot,
            date=self.date,
            fcma=self.layout_fcma,
        )


class OdbReshuffle(
    Parallel, odb.OdbComponentDecoMixin, drhook.DrHookDecoMixin
):
    """Take a bunch of ECMA databases and create new ones with an updated number of pools."""

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=["reshuffle"],
            ),
        )
    )

    _OUT_DIRECTORY = "reshuffled"
    _BARE_OUT_LAYOUT = "ccma"

    def _mpitool_attributes(self, opts):
        conf_dict = super()._mpitool_attributes(opts)
        conf_dict.update({"mplbased": True})
        return conf_dict

    def prepare(self, rh, opts):
        """Find ODB candidates in input files."""

        # Looking for input observations
        obs_in_virtual = [
            x for x in self.lookupodb() if x.rh.resource.part == "virtual"
        ]
        if obs_in_virtual:
            raise ValueError("Do not input a Virtual database")
        self.obs_in_parts = [
            x for x in self.lookupodb() if x.rh.resource.part != "virtual"
        ]

        # Find the input layout
        in_layout = {x.rh.resource.layout for x in self.obs_in_parts}
        if len(in_layout) != 1:
            raise ValueError(
                "Incoherent layout in input databases or no input databases"
            )
        self.layout_in = in_layout.pop()

        # Some extra settings
        self.env.update(TO_ODB_FULL=1)

        # prepare the ouputs' directory
        self.system.mkdir(self._OUT_DIRECTORY)

        super().prepare(rh, opts)

    def execute(self, rh, opts):
        """Loop on available databases."""
        sh = self.system
        for a_db in self.obs_in_parts:
            sh.subtitle(
                "Dealing with {:s}".format(a_db.rh.container.localpath())
            )

            ecma_path = sh.path.abspath(a_db.rh.container.localpath())
            ccma_path = sh.path.abspath(
                sh.path.join(
                    self._OUT_DIRECTORY,
                    ".".join([self.layout_in.upper(), a_db.rh.resource.part]),
                )
            )
            self.odb_create_db(self._BARE_OUT_LAYOUT, dbpath=ccma_path)
            self.odb.fix_db_path(self.layout_in, ecma_path)
            self.odb.fix_db_path(self._BARE_OUT_LAYOUT, ccma_path)
            self.odb.ioassign_gather(ccma_path, ecma_path)

            # Apparently te binary tries to write in the input databse,
            # no idea why but...
            self.odb_rw_or_overwrite_method(a_db)

            super().execute(rh, opts)

            # CCMA -> ECMA
            self.odb.change_layout(
                self._BARE_OUT_LAYOUT, self.layout_in, ccma_path
            )

    def postfix(self, rh, opts):
        """Create a virtual database for output data."""
        self.system.subtitle("Creating the virtual database")
        virtual_db = self.odb_merge_if_needed(
            self.obs_in_parts, subdir=self._OUT_DIRECTORY
        )
        logger.info(
            "The output virtual DB was created: %s",
            self.system.path.join(self._OUT_DIRECTORY, virtual_db),
        )

    def spawn_command_options(self):
        """Prepare command line options to binary."""
        return dict(
            dbin=self.layout_in,
            dbout=self._BARE_OUT_LAYOUT,
            npool=self.npool,
        )


class FlagsCompute(
    Parallel, odb.OdbComponentDecoMixin, drhook.DrHookDecoMixin
):
    """Compute observations flags."""

    _footprint = dict(
        info="Computation of observations flags.",
        attr=dict(
            kind=dict(
                values=["flagscomp"],
            ),
        ),
    )

    def execute(self, rh, opts):
        """Spawn the binary for each of the input databases."""
        # Look for the input databases
        input_databases = self.context.sequence.effective_inputs(
            role="ECMA",
            kind="observations",
        )
        # Check that there is at least one database
        if len(input_databases) < 1:
            raise AttributeError("No database in input. Stop.")

        for input_database in input_databases:
            ecma = input_database.rh
            ecma_filename = ecma.container.filename
            # Environment variable to set DB path
            self.odb.fix_db_path(ecma.resource.layout, ecma.container.abspath)
            self.env.setvar("ODB_ECMA", ecma_filename)
            logger.info("Variable %s set to %s.", "ODB_ECMA", ecma_filename)
            # Path to the IOASSIGN file
            self.env.IOASSIGN = self.system.path.join(
                ecma.container.abspath, "IOASSIGN"
            )
            # Let ancesters handling most of the env setting
            super().execute(rh, opts)
            # Rename the output file according to the name of the part of the observations treated
            self.system.mv("BDM_CQ", "_".join(["BDM_CQ", ecma.resource.part]))
