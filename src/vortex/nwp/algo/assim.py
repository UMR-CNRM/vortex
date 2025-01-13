"""
AlgoComponents dedicated to computations related to Data Assimilation systems.
"""

from bronx.fancies import loggers
from bronx.stdtypes.date import Date

from vortex.algo.components import BlindRun, Parallel
from vortex.syntax.stdattrs import a_date
from .ifsroot import IFSParallel
from ..tools import odb, drhook

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class MergeVarBC(Parallel):
    """Merge two VarBC files.

    The VarBC file resulting from the MergeVarBC contains all the items of the
    first VarBC file plus any new item that would be present in the second file.
    """

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=["mergevarbc"],
            ),
            varbcout=dict(
                optional=True,
                default="VARBC.cycle_out",
            ),
        )
    )

    def prepare(self, rh, opts):
        """Find any ODB candidate in input files."""

        sh = self.system

        sh.touch(self.varbcout)

        # Let ancesters doing real stuff
        super().prepare(rh, opts)


class Anamix(IFSParallel):
    """Merge the surface and atmospheric analyses into a single file"""

    _footprint = dict(
        info="Merge surface and atmospheric analyses",
        attr=dict(
            kind=dict(
                values=["anamix"],
            ),
            conf=dict(
                default=701,
            ),
            xpname=dict(
                default="CANS",
            ),
            timestep=dict(
                default=1,
            ),
        ),
    )


class SstAnalysis(IFSParallel):
    """SST (Sea Surface Temperature) Analysis"""

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=["sstana", "sst_ana", "sst_analysis", "c931"],
                remap=dict(autoremap="first"),
            ),
            conf=dict(
                default=931,
            ),
            xpname=dict(
                default="ANAL",
            ),
            timestep=dict(
                default="1.",
            ),
        )
    )


class SeaIceAnalysis(IFSParallel):
    """Sea Ice Analysis"""

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=["seaiceana", "seaice_ana", "seaice_analysis", "c932"],
                remap=dict(autoremap="first"),
            ),
            conf=dict(
                default=932,
            ),
            xpname=dict(
                default="ANAL",
            ),
            timestep=dict(
                default="1.",
            ),
            date=dict(
                type=Date,
            ),
        )
    )

    def find_namelists(self, opts=None):
        namrh_list = super().find_namelists(opts)
        if not namrh_list:
            logger.critical("No namelist was found.")
            raise ValueError("No namelist was found for seaice analysis")
        return namrh_list

    def prepare_namelist_delta(self, rh, namcontents, namlocal):
        super().prepare_namelist_delta(rh, namcontents, namlocal)
        self._set_nam_macro(namcontents, namlocal, "IDAT", int(self.date.ymd))
        return True


class Canari(IFSParallel, odb.OdbComponentDecoMixin):
    """Surface analysis."""

    _footprint = dict(
        info="Surface assimilation based on optimal interpolation",
        attr=dict(
            kind=dict(
                values=["canari"],
            ),
            binarysingle=dict(
                default="basicnwpobsort",
            ),
            conf=dict(
                default=701,
            ),
            xpname=dict(
                default="CANS",
            ),
        ),
    )

    def prepare(self, rh, opts):
        """Get a look at raw observations input files."""
        super().prepare(rh, opts)

        # Looking for input observations
        obsodb = [
            x
            for x in self.lookupodb()
            if x.rh.resource.part.startswith("surf")
        ]
        if not obsodb:
            raise ValueError("No surface obsdata for canari")
        self.odb_date_and_layout_from_sections(obsodb)

        # Find the unique input ODb database
        ssurf = obsodb.pop()
        if obsodb:
            logger.error("More than one surface obsdata provided")
            logger.error(
                "Using : %s / %s",
                ssurf.rh.resource.layout,
                ssurf.rh.resource.part,
            )
            for sobs in obsodb:
                logger.error(
                    "Skip : %s / %s",
                    sobs.rh.resource.layout,
                    sobs.rh.resource.part,
                )

        # Fix paths + generate a global IOASSING file
        cma_path = self.system.path.abspath(ssurf.rh.container.localpath())
        self.odb.fix_db_path(self.virtualdb, cma_path)
        self.odb.ioassign_gather(cma_path)

        # Some extra settings
        self.odb.create_poolmask(self.virtualdb, cma_path)
        self.odb.shuffle_setup(self.slots, mergedirect=True, ccmadirect=False)
        self.env.update(
            ODB_POOLMASKING=1,
            ODB_PACKING=-1,
            BASETIME=self.date.ymdh,
        )

        # Fix the input DB intent
        self.odb_rw_or_overwrite_method(ssurf)


class Screening(IFSParallel, odb.OdbComponentDecoMixin):
    """Observation screening."""

    _footprint = dict(
        info="Observations screening.",
        attr=dict(
            kind=dict(
                values=["screening", "screen", "thinning"],
                remap=dict(autoremap="first"),
            ),
            binarysingle=dict(
                default="basicnwpobsort",
            ),
            ioassign=dict(
                optional=False,
            ),
            conf=dict(
                default=2,
            ),
            xpname=dict(
                default="SCRE",
            ),
        ),
    )

    def prepare(self, rh, opts):
        """Get a look at raw observations input files."""
        super().prepare(rh, opts)

        # Looking for input observations
        allodb = self.lookupodb()
        self.odb_date_and_layout_from_sections(allodb)

        # Perform the pre-merging stuff (this will create the ECMA virtual DB)
        virtualdb_path = self.odb_merge_if_needed(allodb)
        # Prepare the CCMA DB
        ccma_path = self.odb_create_db(layout="CCMA")

        # Fix paths + generate a global IOASSING file
        self.odb.fix_db_path(self.virtualdb, virtualdb_path)
        self.odb.fix_db_path("CCMA", ccma_path)
        self.odb.ioassign_gather(virtualdb_path, ccma_path)

        # Some extra settings
        self.odb.create_poolmask(self.virtualdb, virtualdb_path)
        self.odb.shuffle_setup(self.slots, mergedirect=True, ccmadirect=True)

        # Look for extras ODB raw
        self.odb_handle_raw_dbs()

        # Fix the input databases intent
        self.odb_rw_or_overwrite_method(*allodb)

        # Look for channels namelists and set appropriate links
        self.setchannels()


class IFSODBCCMA(IFSParallel, odb.OdbComponentDecoMixin):
    """Specialised IFSODB for CCMA processing"""

    _abstract = True
    _footprint = dict(
        attr=dict(
            virtualdb=dict(
                default="ccma",
            ),
            binarysingle=dict(
                default="basicnwpobsort",
            ),
        )
    )

    def prepare(self, rh, opts):
        """Get a look at raw observations input files."""
        super().prepare(rh, opts)

        sh = self.system

        # Looking for input observations
        allodb = self.lookupodb()
        allccma = [x for x in allodb if x.rh.resource.layout.lower() == "ccma"]
        if allccma:
            if len(allccma) > 1:
                logger.error(
                    "Multiple CCMA databases detected: only the first one is taken into account"
                )
        else:
            raise ValueError("Missing CCMA input data for " + self.kind)

        # Set env and IOASSIGN
        ccma = allccma.pop()
        ccma_path = sh.path.abspath(ccma.rh.container.localpath())
        self.odb_date_and_layout_from_sections(
            [
                ccma,
            ]
        )
        self.odb.fix_db_path(ccma.rh.resource.layout, ccma_path)
        self.odb.ioassign_gather(ccma_path)

        # Fix the input database intent
        self.odb_rw_or_overwrite_method(ccma)

        # Look for channels namelists and set appropriate links
        self.setchannels()


class Minim(IFSODBCCMA):
    """Observation minimisation."""

    _footprint = dict(
        info="Minimisation in the assimilation process.",
        attr=dict(
            kind=dict(
                values=["minim", "min", "minimisation"],
                remap=dict(autoremap="first"),
            ),
            conf=dict(
                default=131,
            ),
            xpname=dict(
                default="MINI",
            ),
        ),
    )

    def prepare(self, rh, opts):
        """Find out if preconditioning eigenvectors are here."""
        super().prepare(rh, opts)

        # Check if a preconditioning EV map is here
        evmaprh = self.context.sequence.effective_inputs(
            role=("PreconEVMap", "PreconditionningEVMap"), kind="precevmap"
        )
        if evmaprh:
            if len(evmaprh) > 1:
                logger.warning(
                    "Several preconditioning EV maps provided. Using the first one."
                )
            nprec_ev = evmaprh[0].rh.contents.data["evlen"]
            # If there are preconditioning EV: update the namelist
            if nprec_ev > 0:
                for namrh in [
                    x.rh
                    for x in self.context.sequence.effective_inputs(
                        role="Namelist",
                        kind="namelist",
                    )
                ]:
                    namc = namrh.contents
                    try:
                        namc["NAMVAR"].NPCVECS = nprec_ev
                        namc.rewrite(namrh.container)
                    except Exception:
                        logger.critical(
                            "Could not fix NAMVAR in %s",
                            namrh.container.actualpath(),
                        )
                        raise
                logger.info(
                    "%d preconditioning EV will by used (NPCVECS=%d).",
                    nprec_ev,
                    nprec_ev,
                )
            else:
                logger.warning(
                    "A preconditioning EV map was found, "
                    + "but no preconditioning EV are available."
                )
        else:
            logger.info("No preconditioning EV were found.")

    def postfix(self, rh, opts):
        """Find out if any special resources have been produced."""
        sh = self.system

        # Look up for PREConditionning Eigen Vectors
        prec = sh.ls("MEMINI*")
        if prec:
            prec_info = dict(evlen=len(prec))
            prec_info["evnum"] = [int(x[6:]) for x in prec]
            sh.json_dump(prec_info, "precev_map.out", indent=4)

        super().postfix(rh, opts)


class Trajectory(IFSODBCCMA):
    """Observation trajectory."""

    _footprint = dict(
        info="Trajectory in the assimilation process.",
        attr=dict(
            kind=dict(
                values=["traj", "trajectory"],
                remap=dict(autoremap="first"),
            ),
            conf=dict(
                default=2,
            ),
            xpname=dict(
                default="TRAJ",
            ),
        ),
    )


class PseudoTrajectory(BlindRun, drhook.DrHookDecoMixin):
    """Copy a few fields from the Guess file into the Analysis file"""

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=["pseudotraj", "traj", "trajectory"],
                remap=dict(autoremap="first"),
            ),
        )
    )


class SstGrb2Ascii(BlindRun):
    """Transform sst grib files from the BDAP into ascii files"""

    _footprint = dict(
        info="Binary to change the format of sst BDAP files.",
        attr=dict(
            kind=dict(
                values=["lect_bdap"],
            ),
            date=a_date,
            nlat=dict(
                default=0,
            ),
            nlon=dict(
                default=0,
            ),
        ),
    )

    def prepare(self, rh, opts):
        """Add namelist delta, prepare the environment and build the arguments needed."""
        super().prepare(rh, opts)
        for namrh in [
            x.rh
            for x in self.context.sequence.effective_inputs(
                role="Namelist",
                kind="namelist",
            )
        ]:
            namc = namrh.contents
            try:
                namc.newblock("NAMFILE")
                namc["NAMFILE"].NBFICH = 1
                namc["NAMFILE"]["CCNFICH(1)"] = "GRIB_SST"
                namc.rewrite(namrh.container)
            except Exception:
                logger.critical(
                    "Could not fix NAMFILE in %s", namrh.container.actualpath()
                )
                raise

    def spawn_command_options(self):
        """Build the dictionnary to provide arguments to the binary."""
        return dict(
            year=self.date.year,
            month=self.date.month,
            day=self.date.day,
            hour=self.date.hour,
            lon=self.nlon,
            lat=self.nlat,
        )


class IceNetCDF2Ascii(BlindRun):
    """Transform ice NetCDF files from the BDPE into ascii files"""

    _footprint = dict(
        info="Binary to change the format of ice BDPE files.",
        attr=dict(
            kind=dict(
                values=["ice_nc2ascii"],
            ),
            output_file=dict(optional=True, default="ice_concent"),
            param=dict(
                optional=True,
                default="ice_conc",
            ),
        ),
    )

    def prepare(self, rh, opts):
        super().prepare(rh, opts)
        # Look for the input files
        list_netcdf = self.context.sequence.effective_inputs(
            role="NetCDFfiles", kind="observations"
        )
        hn_file = ""
        hs_file = ""
        for sect in list_netcdf:
            part = sect.rh.resource.part
            filename = sect.rh.container.filename
            if part == "ice_hn":
                if hn_file == "":
                    hn_file = filename
                    logger.info(
                        "The input file for the North hemisphere is: %s.",
                        hn_file,
                    )
                else:
                    logger.warning(
                        "There was already one file for the North hemisphere. "
                        "The following one, %s, is not used.",
                        filename,
                    )
            elif part == "ice_hs":
                if hs_file == "":
                    hs_file = filename
                    logger.info(
                        "The input file for the South hemisphere is: %s.",
                        hs_file,
                    )
                else:
                    logger.warning(
                        "There was already one file for the South hemisphere. "
                        "The following one, %s, is not used.",
                        filename,
                    )
            else:
                logger.warning("The following file is not used: %s.", filename)
        self.input_file_hn = hn_file
        self.input_file_hs = hs_file

    def spawn_command_options(self):
        """Build the dictionnary to provide arguments to the binary."""
        return dict(
            file_in_hn=self.input_file_hn,
            file_in_hs=self.input_file_hs,
            param=self.param,
            file_out=self.output_file,
        )
