"""
AlgoComponents dedicated to NWP direct forecasts.
"""

import math
import re
from collections import defaultdict

from bronx.fancies import loggers
from bronx.stdtypes.date import Time, Month, Period
import footprints

from vortex.algo.components import AlgoComponentError, Parallel
from vortex.layout.dataflow import intent
from vortex.syntax.stdattrs import model
from vortex.util.structs import ShellEncoder
from .ifsroot import IFSParallel
from ..tools.drhook import DrHookDecoMixin
from ..syntax.stdattrs import outputid_deco

from typing import Any, Callable, Iterable
from vortex.data.handlers import Handler
from vortex.layout.dataflow import Section


#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class Forecast(IFSParallel):
    """Forecast for IFS-like Models."""

    _footprint = [
        outputid_deco,
        dict(
            info="Run a forecast with Arpege/IFS.",
            attr=dict(
                kind=dict(
                    values=["forecast", "fc"], remap=dict(forecast="fc")
                ),
                hist_terms=dict(
                    info="The list of terms when historical file production is requested.",
                    type=footprints.FPList,
                    optional=True,
                ),
                surfhist_terms=dict(
                    info="The list of terms when surface file production is requested.",
                    type=footprints.FPList,
                    optional=True,
                ),
                pos_terms=dict(
                    info="The list of terms when post-processed data is requested.",
                    type=footprints.FPList,
                    optional=True,
                ),
                s_norm_terms=dict(
                    info="The list of terms when spectal norms should be computed.",
                    type=footprints.FPList,
                    optional=True,
                ),
                flyargs=dict(
                    default=("ICMSH", "PF"),
                ),
                xpname=dict(default="FCST"),
                ddhpack=dict(
                    info="After run, gather the DDH output file in directories.",
                    type=bool,
                    optional=True,
                    default=False,
                    doc_zorder=-5,
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "forecast"

    def _outputs_configurator(self, bin_rh):
        return footprints.proxy.ifsoutputs_configurator(
            model=self.model,
            cycle=bin_rh.resource.cycle,
            fcterm_unit=self.fcunit,
        )

    def prepare(self, rh, opts):
        """Default pre-link for the initial condition file"""
        super().prepare(rh, opts)

        ininc = self.naming_convention("ic", rh)
        analysis = self.setlink(
            initrole=("InitialCondition", "Analysis"), initname=ininc()
        )

        if analysis:
            analysis = analysis.pop()
            thismonth = analysis.rh.resource.date.month

            # Possibly fix the model clim
            if self.do_climfile_fixer(rh, convkind="modelclim"):
                self.climfile_fixer(
                    rh,
                    convkind="modelclim",
                    month=thismonth,
                    inputrole=("GlobalClim", "InitialClim"),
                    inputkind="clim_model",
                )

            # Possibly fix post-processing clim files
            self.all_localclim_fixer(rh, thismonth)

            # File linking for IAU increments
            #
            # In the case of a forecast with IAU, the IFS executable
            # expects to find input increment files (both analysis and
            # background counterpart) names suffixed according to the
            # order by which they are to be applied.  In practice
            # input files are not renamed but links with correct names
            # are created pointing to them instead.  Both analysed and
            # background states are required: to inject analysis
            # increments over multiple timesteps, the IAU algorithm
            # must be able to compute a difference between analysis
            # and background states.
            #
            # TODO: Clarify where both regexp keys are coming from
            guesses = self.context.sequence.effective_inputs(
                role=re.compile(r"IAU_(Background|Guess)", flags=re.IGNORECASE)
            )
            analyses = self.context.sequence.effective_inputs(
                role=re.compile(r"IAU_(Analysis|Ic)", flags=re.IGNORECASE)
            )

            def key(s: Section):
                # Increment files are sorted according to date, then
                # effective term.
                return (
                    s.rh.resource.date,
                    s.rh.resource.date + s.rh.resource.term,
                )

            self._create_ordered_links(
                bin_handler=rh,
                sections=analyses,
                sort_key=key,
                nameconv_kind="iau_analysis",
            )
            self._create_ordered_links(
                bin_handler=rh,
                sections=guesses,
                sort_key=key,
                nameconv_kind="iau_background",
            )

        # Promises should be nicely managed by a co-proccess
        if self.promises:
            prefixes_set = set()
            for pr_res in [pr.rh.resource for pr in self.promises]:
                if pr_res.realkind == "historic":
                    prefixes_set.add("ICMSH")
                if pr_res.realkind == "gridpoint":
                    prefixes_set.add(
                        "{:s}PF".format(
                            "GRIB" if pr_res.nativefmt == "grib" else ""
                        )
                    )
            self.io_poll_args = tuple(prefixes_set)
            self.flyput = len(self.io_poll_args) > 0

    def _create_ordered_links(
        self,
        bin_handler: Handler,
        sections: Iterable[Section],
        sort_key: Callable[[Section], Any],
        nameconv_kind: str,
    ):
        """Create links to local files, with ordered names

        For an iterable of sections objects, this function creates
        symlinks to the corresponding local files (described by the
        assocatied "container" object".

        Link names are suffixed by a number string based on their
        order after sorting sections by the sort key. Example:
        ICIAUFCSTBK01,
        ICIAUFCSTBK02,
        ICIAUFCSTBK03...
        """
        for i, sec in enumerate(sorted(sections, key=sort_key)):
            nameconv = self.naming_convention(
                nameconv_kind,
                bin_handler,
                actualfmt=sec.rh.container.actualfmt,
            )
            target = nameconv(number=(i + 1))
            link_name = sec.rh.container.localpath()
            if self.system.path.exists(target):
                logger.warning(
                    "%s should be linked to %s but %s already exists.",
                    link_name,
                    target,
                    target,
                )
                continue
            logger.info("Linking %s to %s.", link_name, target)
            self.grab(sec, comment=nameconv_kind)
            self.system.softlink(link_name, target)

    def find_namelists(self, opts=None):
        """Find any namelists candidates in actual context inputs."""
        return [
            x.rh
            for x in self.context.sequence.effective_inputs(
                role="Namelist", kind="namelist"
            )
        ]

    def prepare_namelist_delta(self, rh, namcontents, namlocal):
        nam_updated = super().prepare_namelist_delta(rh, namcontents, namlocal)
        if namlocal == "fort.4":
            o_conf = self._outputs_configurator(rh)
            o_conf.modelstate = self.hist_terms
            o_conf.surf_modelstate = self.surfhist_terms
            o_conf.post_processing = self.pos_terms
            o_conf.spectral_diag = self.s_norm_terms
            nam_updated_bis = o_conf(namcontents, namlocal)
            nam_updated = nam_updated or nam_updated_bis
        return nam_updated

    def postfix(self, rh, opts):
        """Find out if any special resources have been produced."""

        sh = self.system

        # Look up for the gridpoint files
        gp_out = sh.ls("PF{}*".format(self.xpname))
        gp_map = defaultdict(list)
        if gp_out:
            re_pf = re.compile(
                r"^PF{}(\w+)\+(\d+(?::\d+)?)$".format(self.xpname)
            )
            for fname in gp_out:
                match_pf = re_pf.match(fname)
                if match_pf:
                    gp_map[match_pf.group(1).lower()].append(
                        Time(match_pf.group(2))
                    )
            for k, v in gp_map.items():
                v.sort()
                logger.info(
                    "Gridpoint files found: domain=%s, terms=%s",
                    k,
                    ",".join([str(t) for t in v]),
                )
        if len(gp_map) == 0:
            logger.info("No gridpoint file was found.")
        sh.json_dump(gp_map, "gridpoint_map.out", indent=4, cls=ShellEncoder)

        # Gather DDH in folders
        if self.ddhpack:
            ddhmap = dict(DL="dlimited", GL="global", ZO="zonal")
            for prefix, ddhkind in ddhmap.items():
                flist = sh.glob("DHF{}{}+*".format(prefix, self.xpname))
                if flist:
                    dest = "ddhpack_{}".format(ddhkind)
                    logger.info("Creating a DDH pack: %s", dest)
                    sh.mkdir(dest)
                    for lfa in flist:
                        sh.mv(lfa, dest, fmt="lfa")

        super().postfix(rh, opts)


class LAMForecast(Forecast):
    """Forecast for IFS-like Limited Area Models."""

    _footprint = dict(
        info="Run a forecast with an Arpege/IFS like Limited Area Model.",
        attr=dict(
            kind=dict(
                values=["lamfc", "lamforecast"],
                remap=dict(lamforecast="lamfc"),
            ),
        ),
    )

    synctool = "atcp.alad"
    synctpl = "sync-fetch.tpl"

    def spawn_command_options(self):
        """Dictionary provided for command line factory."""
        return dict(
            name=(self.xpname + "xxxx")[:4].upper(),
            timescheme=self.timescheme,
            timestep=self.timestep,
            fcterm=self.fcterm,
            fcunit=self.fcunit,
            model="aladin",
        )

    def prepare(self, rh, opts):
        """Default pre-link for boundary conditions files."""
        super().prepare(rh, opts)

        sh = self.system

        # Check boundaries conditions
        cplrh = [
            x.rh
            for x in self.context.sequence.effective_inputs(
                role="BoundaryConditions", kind="boundary"
            )
        ]
        cplrh.sort(key=lambda rh: rh.resource.date + rh.resource.term)

        # Ordered pre-linking of boundaring and building ot the synchronization tools
        firstsync = None
        sh.header("Check boundaries...")
        if any([x.is_expected() for x in cplrh]):
            logger.info("Some boundaries conditions are still expected")
            self.mksync = True
        else:
            logger.info("All boundaries conditions available")
            self.mksync = False

        for i, bound in enumerate(cplrh):
            thisbound = bound.container.localpath()
            lbcnc = self.naming_convention(
                "lbc", rh, actualfmt=bound.container.actualfmt
            )
            sh.softlink(thisbound, lbcnc(number=i))
            if self.mksync:
                bound.mkgetpr(
                    pr_getter=self.synctool + ".{:03d}".format(i),
                )
                if firstsync is None:
                    firstsync = self.synctool + ".{:03d}".format(i)

        # Set up the first synchronization step
        if firstsync is not None:
            sh.symlink(firstsync, self.synctool)

    def postfix(self, rh, opts):
        """Post forecast information and cleaning."""
        sh = self.system

        if self.mksync:
            synclog = self.synctool + ".log"
            if sh.path.exists(synclog):
                sh.subtitle(synclog)
                sh.cat(synclog, output=False)

        super().postfix(rh, opts)


class DFIForecast(LAMForecast):
    """OBSOLETE CODE: do not use."""

    _footprint = dict(
        info="Run a forecast with an Arpege/IFS like Limited Area Model (with DFIs).",
        attr=dict(
            kind=dict(
                values=["fcdfi"],
            ),
        ),
    )

    def prepare(self, rh, opts):
        """Pre-link boundary conditions as special DFI files."""
        super().prepare(rh, opts)
        ininc = self.naming_convention("ic", rh)
        lbcnc = self.naming_convention("lbc", rh, actualfmt="fa")
        for pseudoterm in (999, 0, 1):
            self.system.softlink(ininc(), lbcnc(number=pseudoterm))


class FullPos(IFSParallel):
    """Fullpos for geometries transforms in IFS-like Models.

    OBSOLETE a/c cy46 (use the 903 configuration / fullpos server instead).
    """

    _abstract = True
    _footprint = dict(
        attr=dict(
            xpname=dict(default="FPOS"),
            flyput=dict(
                default=False,
                values=[False],
            ),
            server_run=dict(
                values=[True, False],
            ),
            serversync_method=dict(
                default="simple_socket",
            ),
            serversync_medium=dict(
                default="cnt3_wait",
            ),
        )
    )

    @property
    def realkind(self):
        return "fullpos"


class FullPosGeo(FullPos):
    """Fullpos for geometries transforms in IFS-like Models.

    OBSOLETE a/c cy46 (use the 903 configuration / fullpos server instead).
    """

    _footprint = dict(
        info="Run a fullpos to interpolate to a new geometry",
        attr=dict(
            kind=dict(
                values=["l2h", "h2l"],
            ),
        ),
    )

    _RUNSTORE = "RUNOUT"

    def _compute_target_name(self, r):
        return "PF" + re.sub(
            "^(?:ICMSH)(.*?)(?:INIT)(.*)$", r"\1\2", r.container.localpath()
        ).format(self.xpname)

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""

        sh = self.system

        initrh = [
            x.rh
            for x in self.context.sequence.effective_inputs(
                role=("Analysis", "Guess", "InitialCondition"),
                kind=(
                    "analysis",
                    "historic",
                    "ic",
                    re.compile("(stp|ana)min"),
                    re.compile("pert"),
                ),
            )
        ]

        # is there one (deterministic forecast) or many (ensemble forecast) fullpos to perform ?
        isMany = len(initrh) > 1
        do_fix_input_clim = self.do_climfile_fixer(rh, convkind="modelclim")
        do_fix_output_clim = self.do_climfile_fixer(
            rh, convkind="targetclim", area="000"
        )
        ininc = self.naming_convention("ic", rh)
        infile = ininc()

        for num, r in enumerate(initrh):
            str_subtitle = "Fullpos execution on {}".format(
                r.container.localpath()
            )
            sh.subtitle(str_subtitle)

            # Set the actual init file
            if sh.path.exists(infile):
                if isMany:
                    logger.critical(
                        "Cannot process multiple Historic files if %s exists.",
                        infile,
                    )
            else:
                sh.cp(
                    r.container.localpath(),
                    infile,
                    fmt=r.container.actualfmt,
                    intent=intent.IN,
                )

            # Fix links for climatology files
            actualmonth = Month(r.resource.date + r.resource.term)
            startingclim = r.resource.geometry

            if do_fix_input_clim:
                self.climfile_fixer(
                    rh,
                    convkind="modelclim",
                    month=actualmonth,
                    geo=startingclim,
                    inputrole=(re.compile("^Clim"), re.compile("Clim$")),
                    inputkind="clim_model",
                )

            if do_fix_output_clim:
                self.climfile_fixer(
                    rh,
                    convkind="targetclim",
                    month=actualmonth,
                    notgeo=startingclim,
                    inputrole=(re.compile("^Clim"), re.compile("Clim$")),
                    inputkind="clim_model",
                    area="000",
                )

            # Standard execution
            super().execute(rh, opts)

            # Find the output filename
            output_file = [x for x in sh.glob("PF{:s}*+*".format(self.xpname))]
            if len(output_file) != 1:
                raise AlgoComponentError("No or multiple output files found.")
            output_file = output_file[0]

            # prepares the next execution
            if isMany:
                # Set a local storage place
                sh.mkdir(self._RUNSTORE)
                # Freeze the current output
                sh.move(
                    output_file,
                    sh.path.join(self._RUNSTORE, "pfout_{:d}".format(num)),
                    fmt=r.container.actualfmt,
                )
                sh.remove(infile, fmt=r.container.actualfmt)
                # Cleaning/Log management
                if not self.server_run:
                    # The only one listing
                    sh.cat("NODE.001_01", output="NODE.all")
                    # Some cleaning
                    sh.rmall("ncf927", "dirlst")
            else:
                # Link the output files to new style names
                sh.cp(
                    output_file,
                    self._compute_target_name(r),
                    fmt=r.container.actualfmt,
                    intent="in",
                )
                # Link the listing to NODE.all
                sh.cp("NODE.001_01", "NODE.all", intent="in")

    def postfix(self, rh, opts):
        """Post processing cleaning."""
        sh = self.system

        initrh = [
            x.rh
            for x in self.context.sequence.effective_inputs(
                role=("Analysis", "Guess", "InitialCondition"),
                kind=(
                    "analysis",
                    "historic",
                    "ic",
                    re.compile("(stp|ana)min"),
                    re.compile("pert"),
                ),
            )
        ]
        if len(initrh) > 1:
            for num, r in enumerate(initrh):
                sh.move(
                    "{:s}/pfout_{:d}".format(self._RUNSTORE, num),
                    self._compute_target_name(r),
                    fmt=r.container.actualfmt,
                )

        super().postfix(rh, opts)


class FullPosBDAP(FullPos):
    """Post-processing for IFS-like Models.

    OBSOLETE a/c cy46 (use the 903 configuration / fullpos server instead).
    """

    _footprint = dict(
        info="Run a fullpos to post-process raw model outputs",
        attr=dict(
            kind=dict(values=["fullpos", "fp"], remap=dict(fp="fullpos")),
            fcterm=dict(
                values=[
                    0,
                ],
            ),
            outputid=dict(
                info="The identifier for the encoding of post-processed fields.",
                optional=True,
            ),
            server_run=dict(
                values=[
                    False,
                ],
            ),
        ),
    )

    def prepare(self, rh, opts):
        """Some additional checks."""
        if self.system.path.exists("xxt00000000"):
            raise AlgoComponentError(
                "There should be no file named xxt00000000 in the working directory"
            )
        super().prepare(rh, opts)

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""

        sh = self.system

        namrh = [
            x.rh
            for x in self.context.sequence.effective_inputs(kind="namelistfp")
        ]

        namxx = [
            x.rh
            for x in self.context.sequence.effective_inputs(
                role="FullPosSelection",
                kind="namselect",
            )
        ]

        initsec = [
            x
            for x in self.context.sequence.effective_inputs(
                role=("InitialCondition", "ModelState"),
                kind="historic",
            )
        ]
        initsec.sort(key=lambda sec: sec.rh.resource.term)

        do_fix_input_clim = self.do_climfile_fixer(rh, convkind="modelclim")

        ininc = self.naming_convention("ic", rh)
        infile = ininc()

        for sec in initsec:
            r = sec.rh
            sh.subtitle("Loop on {:s}".format(r.resource.term.fmthm))

            thisdate = r.resource.date + r.resource.term
            thismonth = thisdate.month
            logger.info("Fullpos <month:%s>" % thismonth)

            if do_fix_input_clim:
                self.climfile_fixer(
                    rh,
                    convkind="modelclim",
                    month=thismonth,
                    geo=r.resource.geometry,
                    inputrole=(re.compile("^Clim"), re.compile("Clim$")),
                    inputkind="clim_model",
                )

            thesenames = self.all_localclim_fixer(rh, thismonth)

            # Set a local storage place
            runstore = "RUNOUT" + r.resource.term.fmtraw
            sh.mkdir(runstore)

            # Define an input namelist
            try:
                namfp = [
                    x for x in namrh if x.resource.term == r.resource.term
                ].pop()
                namfplocal = namfp.container.localpath()
                if self.outputid is not None:
                    self._set_nam_macro(
                        namfp.contents, namfplocal, "OUTPUTID", self.outputid
                    )
                namfp.contents.rewrite(namfp.container)
                sh.remove("fort.4")
                sh.symlink(namfplocal, "fort.4")
            except Exception:
                logger.critical(
                    "Could not get a fullpos namelist for term %s",
                    r.resource.term,
                )
                raise

            # Define an selection namelist
            if namxx:
                namxt = [
                    x for x in namxx if x.resource.term == r.resource.term
                ]
                if namxt:
                    sh.remove("xxt00000000")
                    sh.symlink(
                        namxt.pop().container.localpath(), "xxt00000000"
                    )
                else:
                    logger.critical(
                        "Could not get a selection namelist for term %s",
                        r.resource.term,
                    )
                    raise AlgoComponentError()
            else:
                logger.info("No selection namelist are provided.")

            # Finally set the actual init file
            sh.remove(infile)
            self.grab(
                sec,
                comment="Fullpos source (term={:s})".format(
                    r.resource.term.fmthm
                ),
            )
            sh.softlink(r.container.localpath(), infile)

            # Standard execution
            super().execute(rh, opts)

            # Freeze the current output
            for posfile in [
                x
                for x in (
                    sh.glob("PF{:s}*+*".format(self.xpname))
                    + sh.glob("GRIBPF{:s}*+*".format(self.xpname))
                )
            ]:
                rootpos = re.sub("0+$", "", posfile)
                fmtpos = "grib" if posfile.startswith("GRIB") else "lfi"
                targetfile = sh.path.join(
                    runstore, rootpos + r.resource.term.fmthm
                )
                targetbase = sh.path.basename(targetfile)

                # Deal with potential promises
                expected = [
                    x
                    for x in self.promises
                    if x.rh.container.localpath() == targetbase
                ]
                if expected:
                    logger.info(
                        "Start dealing with promises for: %s.",
                        ", ".join(
                            [x.rh.container.localpath() for x in expected]
                        ),
                    )
                    if posfile != targetbase:
                        sh.move(posfile, targetbase, fmt=fmtpos)
                        posfile = targetbase
                for thispromise in expected:
                    thispromise.put(incache=True)

                sh.move(posfile, targetfile, fmt=fmtpos)

            for logfile in sh.glob("NODE.*", "std*"):
                sh.move(logfile, sh.path.join(runstore, logfile))

            # Some cleaning
            sh.rmall("PX{:s}*".format(self.xpname), fmt="lfi")
            sh.rmall("ncf927", "dirlst")
            for clim in thesenames:
                sh.rm(clim)

    def postfix(self, rh, opts):
        """Post processing cleaning."""
        sh = self.system

        for fpfile in [
            x
            for x in (
                sh.glob("RUNOUT*/PF{:s}*".format(self.xpname))
                + sh.glob("RUNOUT*/GRIBPF{:s}*+*".format(self.xpname))
            )
            if sh.path.isfile(x)
        ]:
            sh.move(
                fpfile,
                sh.path.basename(fpfile),
                fmt="grib" if "GRIBPF" in fpfile else "lfi",
            )
        sh.cat("RUNOUT*/NODE.001_01", output="NODE.all")

        super().postfix(rh, opts)


class OfflineSurfex(Parallel, DrHookDecoMixin):
    """Run a forecast with the SURFEX's offline binary."""

    _footprint = [
        model,
        dict(
            info="Run a forecast with the SURFEX's offline binary.",
            attr=dict(
                kind=dict(
                    values=[
                        "offline_forecast",
                    ],
                ),
                model=dict(
                    values=[
                        "surfex",
                    ],
                ),
                model_tstep=dict(
                    info="The timestep of the model",
                    type=Period,
                ),
                diag_tstep=dict(
                    info="The timestep for writing diagnostics outputs",
                    type=Period,
                ),
                fcterm=dict(
                    info="The forecast's term",
                    type=Period,
                ),
                forcing_read_interval=dict(
                    info="Read the forcing file every...",
                    type=Period,
                    default=Period("PT12H"),
                    optional=True,
                ),
            ),
        ),
    ]

    def valid_executable(self, rh):
        """Check the executable's resource."""
        bmodel = getattr(rh.resource, "model", None)
        rc = bmodel == "surfex" and rh.resource.realkind == "offline"
        if not rc:
            logger.error("Inapropriate binary provided")
        return rc and super().valid_executable(rh)

    @staticmethod
    def _fix_nam_macro(sec, macro, value):
        """Set a given namelist macro and issue a log message."""
        sec.rh.contents.setmacro(macro, value)
        logger.info("Setup %s macro to %s.", macro, str(value))

    def prepare(self, rh, opts):
        """Setup the appropriate namelist macros."""
        self.system.subtitle("Offline SURFEX Settings.")
        # Find the run/final date
        ic = self.context.sequence.effective_inputs(
            role=("InitialConditions", "ModelState", "Analysis")
        )
        if ic:
            if len(ic) > 1:
                logger.warning(
                    "Multiple initial conditions, using only the first one..."
                )
            rundate = ic[0].rh.resource.date
            if hasattr(ic[0].rh.resource, "term"):
                rundate += ic[0].rh.resource.term
            finaldate = rundate + self.fcterm
            finaldate = [
                finaldate.year,
                finaldate.month,
                finaldate.day,
                finaldate.hour * 3600
                + finaldate.minute * 60
                + finaldate.second,
            ]
            logger.info("The final date is : %s", str(finaldate))
            nbreads = int(
                math.ceil(
                    (finaldate - rundate).length
                    / self.forcing_read_interval.length
                )
            )
        else:
            logger.warning(
                "No initial conditions were found. Hope you know what you are doing..."
            )
            finaldate = None
        # Ok, let's find the namelist
        namsecs = self.context.sequence.effective_inputs(
            role=("Namelist", "Namelistsurf")
        )
        for namsec in namsecs:
            logger.info("Processing: %s", namsec.rh.container.localpath())
            self._fix_nam_macro(namsec, "TSTEP", self.model_tstep.length)
            self._fix_nam_macro(
                namsec, "TSTEP_OUTPUTS", self.diag_tstep.length
            )
            if finaldate:
                self._fix_nam_macro(namsec, "FINAL_STOP", finaldate)
                self._fix_nam_macro(namsec, "NB_READS", nbreads)
            if namsec.rh.contents.dumps_needs_update:
                namsec.rh.save()
            logger.info("Namelist dump: \n%s", namsec.rh.container.read())
