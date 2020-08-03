# -*- coding: utf-8 -*-

"""Algo components for MOCAGE Accident."""


from __future__ import absolute_import, print_function, division, unicode_literals


from collections import defaultdict

import footprints as fp

from bronx.fancies import loggers
from bronx.stdtypes import date

from vortex.algo.components import Parallel, AlgoComponentError, AlgoComponent
from vortex.syntax.stdattrs import a_date, model


#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class MakeFm(Parallel):
    """Algo component for makefm.

    Convert nwp (numerical weather prediction) grib files, generally
    extracted from BDAP, to FA files to be used later as input of MOCAGE.

    It involves conversion of vertical levels and changes in horizontal geometry.
    """

    # fmt: off
    _footprint = [
        model,
        dict(
            info = "Create forcing for Mocage accident from gribs",
            attr = dict(
                kind = dict(
                    values = ["makefm"]
                ),
                model = dict(
                    values = ["mocage"]
                ),
            ),
        ),
    ]
    # fmt: on

    @property
    def realkind(self):
        return "makefm"

    @staticmethod
    def _res_to_str(res):
        """Str from float resolution."""
        return "{0:06.3f}".format(res)

    @staticmethod
    def _fix_nam_macro(rh, macro, value):
        """Set a given namelist macro and issue a log message."""
        rh.contents.setmacro(macro, value)
        logger.info(
            "Setup %s macro to %s in %s", macro, value, rh.container.actualpath()
        )

    @property
    def _sorted_inputs_resolution(self):
        """Build a dictionary to group by resolution.

        The result looks like that:

        {
            '00.500': {
                "gribs": ["grib05name1", "grib05name2", ...],
                "bdap_nwp_geom": <Geometry>,
                "mocage_geom": <Geometry>
                }
            '00.100': {
                "gribs": ["grib01name1", "grib01name2", ...],
                "bdap_nwp_geom": <Geometry>,
                "mocage_geom": <Geometry>
                }
        }

        .. note:
           Mocage Geometry and NWP gribs geometry have the same resolution,
           but generally differ on nlon, nlat, lonmin, latmin.
        """
        out = defaultdict(lambda: {"gribs": []})

        for sec in self.context.sequence.effective_inputs(role="BdapNwp"):
            res_str = self._res_to_str(sec.rh.resource.geometry.resolution)
            out[res_str]["gribs"].append(sec.rh.container.localpath())

        json_conf = self.context.sequence.effective_inputs(role="ExtraConf")[0].rh

        for nwp_geom in json_conf.contents.set_bdap_extracted_nwp_geometries():
            out[self._res_to_str(nwp_geom.resolution)]["bdap_nwp_geom"] = nwp_geom

        for moc_geom in json_conf.contents.set_mocage_geometries():
            out[self._res_to_str(moc_geom.resolution)]["mocage_geom"] = moc_geom

        return out

    @property
    def _nwp_valids_at(self):
        """Sorted list of nwp validities."""
        valids_at = set()
        for sec in self.context.sequence.effective_inputs(role="BdapNwp"):
            valids_at.add(sec.rh.resource.date + sec.rh.resource.term)

        return sorted(list(valids_at))

    def _create_makefm_nml(
        self, gribs, bdap_nwp_geom, mocage_geom, pressure_levels=[-9999]
    ):
        """Create a namelist to be used with makefm

        :param gribs: list of grib files to process
        :param bdap_nwp_geom: Geometry of input nwp gribs
        :param mocage_geom: Geometry of MOCAGE output FA files
        :param pressure_levels: list of pressure levels needed for each grib.
        """

        # namelist update
        namrh = self.context.sequence.effective_inputs(
            role="NamelistMakefm", kind="namelist"
        )

        namrh = namrh[0].rh

        self._fix_nam_macro(namrh, "GRIBS_SIZE", len(gribs))
        self._fix_nam_macro(namrh, "BDAP_LEVELS_SIZE", len(pressure_levels))

        self._fix_nam_macro(namrh, "GRIBS", gribs)

        self._fix_nam_macro(namrh, "BDAP_GRID_GRIDNAME", bdap_nwp_geom.area)
        self._fix_nam_macro(
            namrh,
            "BDAP_GRID_LATITUDEOFFIRSTPOINTINDEGREES",
            bdap_nwp_geom.latmin + (bdap_nwp_geom.nlat - 1) * bdap_nwp_geom.resolution,
        )
        self._fix_nam_macro(
            namrh, "BDAP_GRID_LONGITUDEOFFIRSTPOINTINDEGREES", bdap_nwp_geom.lonmin
        )
        self._fix_nam_macro(
            namrh, "BDAP_GRID_LATITUDEOFLASTPOINTINDEGREES", bdap_nwp_geom.latmin
        )
        self._fix_nam_macro(
            namrh,
            "BDAP_GRID_LONGITUDEOFLASTPOINTINDEGREES",
            bdap_nwp_geom.lonmin + (bdap_nwp_geom.nlon - 1) * bdap_nwp_geom.resolution,
        )
        self._fix_nam_macro(
            namrh, "BDAP_GRID_NUMBEROFPOINTSALONGAPARALLEL", bdap_nwp_geom.nlon
        )
        self._fix_nam_macro(
            namrh, "BDAP_GRID_NUMBEROFPOINTSALONGAMERIDIAN", bdap_nwp_geom.nlat
        )
        self._fix_nam_macro(namrh, "BDAP_LEVELS", pressure_levels)

        self._fix_nam_macro(namrh, "MOCAGE_GRID_GRIDNAME", mocage_geom.area)
        self._fix_nam_macro(
            namrh,
            "MOCAGE_GRID_LATITUDEOFFIRSTPOINTINDEGREES",
            mocage_geom.latmin + (mocage_geom.nlat - 1) * mocage_geom.resolution,
        )
        self._fix_nam_macro(
            namrh, "MOCAGE_GRID_LONGITUDEOFFIRSTPOINTINDEGREES", mocage_geom.lonmin
        )
        self._fix_nam_macro(
            namrh, "MOCAGE_GRID_LATITUDEOFLASTPOINTINDEGREES", mocage_geom.latmin
        )
        self._fix_nam_macro(
            namrh,
            "MOCAGE_GRID_LONGITUDEOFLASTPOINTINDEGREES",
            mocage_geom.lonmin + (mocage_geom.nlon - 1) * mocage_geom.resolution,
        )
        self._fix_nam_macro(
            namrh, "MOCAGE_GRID_NUMBEROFPOINTSALONGAPARALLEL", mocage_geom.nlon
        )
        self._fix_nam_macro(
            namrh, "MOCAGE_GRID_NUMBEROFPOINTSALONGAMERIDIAN", mocage_geom.nlat
        )

        namrh.save()

        sh = self.system
        sh.highlight("makefm.nml content")
        namrh.container.cat()

    def prepare(self, rh, opts):
        """Drhook should not try to initialise MPI."""
        super(MakeFm, self).prepare(rh, opts)
        self.export("drhook_not_mpi")

    def postfix(self, rh, opts):
        # We always call the superclass
        super(MakeFm, self).postfix(rh, opts)
        # Just to see what happened
        self.system.header("We are all done !")

    def execute(self, rh, opts):
        """Loop on the various resolutions."""
        for res_dict in self._sorted_inputs_resolution.values():
            self._create_makefm_nml(
                res_dict["gribs"], res_dict["bdap_nwp_geom"], res_dict["mocage_geom"]
            )
            super(MakeFm, self).execute(rh, opts)


class AbstractMocaccRoot(Parallel):
    """Abstract Algo component to be used whenever the Mocage Accident model is involved.

    .. note::
       Should be common with AbstractMocageRoot one day. At the moment, polling and namelist
       creation are different.
    """

    # fmt: off
    _abstract = True
    _footprint = [
        model,
        dict(
            info = 'Abstract Mocage AlgoComponent',
            attr = dict(
                kind = dict(
                ),
                basedate = a_date,
                model = dict(
                    values   = ['mocage', ]
                ),
                extrasetup = dict(
                    info     = "Some additive settings (environment variables)",
                    optional = True,
                    default  = None,
                ),
            )
        )
    ]
    # fmt: on

    @property
    def realkind(self):
        return "abstract_mocage"

    def _fix_nam_macro(self, rh, macro, value):
        """Set a given namelist macro and issue a log message."""
        rh.contents.setmacro(macro, value)
        logger.info(
            "Setup %s macro to %s in %s", macro, value, rh.container.actualpath()
        )

    def prepare(self, rh, opts):
        """Prepare the synchronisation with next tasks."""
        # to control synchronisation and promised files: use the script in iopoll method
        # The script executed via iopoll method returns the list of promised files ready
        if self.promises:
            self.flyput = True
        else:
            self.flyput = False
        if self.extrasetup:
            self.export(self.extrasetup)
        super(AbstractMocaccRoot, self).prepare(rh, opts)

    def _prepare_mocage_fc_namelist_YYYYMMDD(self, namrh, first, last):
        """Fix the YYYYn MMn and DDn namelist macros."""
        self._fix_nam_macro(namrh, "YYYY1", int(first.year))
        self._fix_nam_macro(namrh, "YYYY2", int(last.year))
        self._fix_nam_macro(namrh, "MM1", int(first.month))
        self._fix_nam_macro(namrh, "MM2", int(last.month))
        self._fix_nam_macro(namrh, "DD1", int(first.day))
        self._fix_nam_macro(namrh, "DD2", int(last.day))
        self._fix_nam_macro(namrh, "HH1", int(first.hour))
        self._fix_nam_macro(namrh, "HH2", int(last.hour))


class MocaccForecast(AbstractMocaccRoot):
    """Algo component for mocage binary with mocage accident suites"""

    # fmt: off
    _footprint = dict(
        info = "Mocage accident forecast",
        attr = dict(
            kind = dict(
                values   = ["mocacc_forecast"]
            ),
            transinv = dict(
                type     = bool,
                info     = "activate inverse transport"
            ),
            llctbto = dict(
                type     = bool,
                info     = "with ctbto outputs (inverse transport only)"
            ),
            flyargs = dict(
                default  = fp.FPTuple(('HM',)),
            ),
            flypoll = dict(
                default  = 'iopoll_mocacc',
            ),
            iopoll_witness = dict(
                info     = "File storing validity of last fully written files (produced by MOCAGE)",
                optional = True,
                default  = "ECHHMNC",
            ),
            iopoll_donefile = dict(
                info     = "File storing files that have already been post-processed",
                optional = True,
                default  = "iopoll.already_done",
            ),
            iopoll_regex = dict(
                info     = "regex to find MOCAGE outputs file and their validity",
                optional = True,
                default  = r"HM.*\+(\d+).nc$"
            )
        ),
    )
    # fmt: on

    @property
    def realkind(self):
        return "mocacc_forecast"

    def prepare(self, rh, opts):
        """Prepare the synchronisation with next tasks."""
        # to control synchronisation and promised files : use the script in iopoll method
        # The script executed via iopoll method returns the list of promised files ready
        super(MocaccForecast, self).prepare(rh, opts)
        if self.promises:
            self.io_poll_kwargs = dict(
                witness=self.iopoll_witness,
                donefile=self.iopoll_donefile,
                regex=self.iopoll_regex,
            )

    def _get_single_rh(self, role, **kwargs):
        """Look for a single input of **role** and return its contents."""
        sec = self.context.sequence.effective_inputs(role=role, **kwargs)
        if len(sec) != 1:
            raise ValueError(
                "One and only one input with role={:s} is expected.".format(role)
            )
        return sec[0].rh

    @property
    def _fm_inputs(self):
        """Return the raw list of FMCoupling input sections."""
        return self.context.sequence.effective_inputs(role="FMCoupling")

    @property
    def _sorted_input_fms_by_geom(self):
        """
        Build a dictionary that contains a list of forcing files of for each
        geometry.
        """
        out = defaultdict(list)

        for sec in self._fm_inputs:
            out[sec.rh.resource.geometry].append(sec.rh.container.localpath())
        return out

    @property
    def _sorted_inputs_validities(self):
        """Build a sorted list of validities."""
        return sorted(
            set(
                [sec.rh.resource.date + sec.rh.resource.term for sec in self._fm_inputs]
            ), reverse=self.transinv
        )

    @property
    def _sorted_inputs_geometries(self):
        """Build a sorted list of forcing files geometries.
        """
        return sorted(
            set([sec.rh.resource.geometry for sec in self._fm_inputs]),
            key=lambda x: x.resolution,
            reverse=True,
        )

    def _prepare_mocage_fc_namelist(self, nbpolls):
        """Look for a forecast namelist + input files and update the namelist."""

        sh = self.system

        # Forecast namelist
        namrh = self._get_single_rh("NamelistForecast", kind="namelist")
        # Configuration file
        ct_extra_conf = self._get_single_rh("ExtraConf").contents

        polls = ["POLLUT{0:02d}".format(i + 1) for i in range(0, nbpolls)]
        # geometries sorted by resolution
        geoms = self._sorted_inputs_geometries

        sh.highlight("Forecast namelist:")

        # List of (geom, associated list of fm validities)
        fms_validities = self._sorted_inputs_validities
        starts_at = date.Date(self.basedate)
        ends_at = fms_validities[-1]

        inputs_period_in_hours = (fms_validities[1] - fms_validities[0]).length // 3600

        self._prepare_mocage_fc_namelist_YYYYMMDD(namrh, starts_at, ends_at)

        self._fix_nam_macro(namrh, "NDOM", len(geoms))
        self._fix_nam_macro(namrh, "DOMLST", [geom.area for geom in geoms])

        self._fix_nam_macro(namrh, "NHCY", inputs_period_in_hours)
        self._fix_nam_macro(namrh, "TRANSINV", self.transinv)
        self._fix_nam_macro(namrh, "LLCTBTO", self.llctbto)

        self._fix_nam_macro(namrh, "SRC_PROFILE", ct_extra_conf.source_vertical_profile)

        self._fix_nam_macro(namrh, "POLLSLST", polls)

        i = 0
        for geom in geoms:
            i += 1
            nb = namrh.contents.newblock("PARAM_G{0}".format(i))
            nb["NTRA{0}".format(i)] = nbpolls
            nb["NSLS{0}".format(i)] = 0
            nb["NEMI{0}".format(i)] = nbpolls
            nb["NDEP{0}".format(i)] = nbpolls
            nb["LONM{0}".format(i)] = geom.nlon
            nb["LATM{0}".format(i)] = geom.nlat
            nb["LONF{0}".format(i)] = geom.nlon
            nb["LATF{0}".format(i)] = geom.nlat

        namrh.save()

        sh.highlight("MOCAGE.nml content")
        namrh.container.cat()

        sh.cp(namrh.container.actualpath(), "namelist.list")

    def _init_empty_hm(self, nbpolls):
        """Create initial state HM files filled with zeros.

        :param nbpolls: number of pollutants to had in empty HM file

        .. note:
            In MOCAGE, the lowest value is 1.0e-30

        .. warning:
            Only work when FM (forcing files) and HM (output) have the
            same number of vertical levels (number of levels is taken
            from FM files).
        """

        MOCAGE_ZERO = 1.0e-30

        from common.util import usepygram
        if not usepygram.epygram_checker.is_available():
            raise AlgoComponentError("Epygram needs to be available")

        import numpy as np

        fms = self._sorted_input_fms_by_geom

        self.system.highlight("init_hm_empty")

        with usepygram.epy_env_prepare(self.ticket):
            validity = usepygram.epygram.base.FieldValidity(
                date_time=self.basedate,
                basis=self.basedate,
                term=date.Period(0),
                cumulativeduration=date.Period(0),
            )

            for grid in fms:
                empty_hm = "HM{0}+{1}".format(grid.area, self.basedate.ymdh)

                fm_r = usepygram.epygram.formats.resource(
                    filename=fms[grid][0], openmode="r"
                )
                hm_r = usepygram.epygram.formats.resource(
                    filename=empty_hm, openmode="w", fmt="FA", cdiden="ACCIDENT"
                )

                # Do not use surface field (SURFPRESSION for exemple),
                # to avoid wrong geometry
                field = fm_r.readfield("S001VENT_ZONAL")
                field.setdata(np.full_like(field.getdata(), MOCAGE_ZERO))

                hm_r.validity = validity
                nb_levels = len(fm_r.geometry.vcoordinate.levels)

                for poll in range(1, nbpolls + 1):
                    for level in range(1, nb_levels + 1):
                        fid = "L{0:03d}POLLUT{1:02d}".format(level, poll)
                        field.fid = {"FA": fid}
                        hm_r.writefield(field)

                fm_r.close()
                hm_r.close()

                self.system.highlight("{0} succesfully created".format(empty_hm))

    def _create_table_mocage_chem(self, cfg_content):
        """Create table_mocage_chem.txt from complete MOCAGE.CFG."""
        table_str = ""
        for numpoll in range(0, cfg_content.nbpolls):
            identstat = cfg_content[9 + numpoll * 21].strip()
            pollname = cfg_content[11 + numpoll * 21].strip()
            table_str += "{0:02d}, POLLUT{0:02d}, {0:02d}.210, {0:02d}.211, ".format(
                numpoll + 1
            )
            table_str += "{0:02d}.212, {0:02d}.213, 0 , 0.0, ".format(numpoll + 1)
            table_str += "true, 1, 0, 0, true, false, 222.0, 0.0, 0.0, 0.0, "
            table_str += "'{0}', '{1}'\n".format(identstat, pollname)

        self.system.highlight("table_mocage_chem.txt content")

        c = fp.proxy.container(filename="table_mocage_chem.txt", mode="w+")
        c.write(table_str)
        c.cat()

    def execute(self, rh, opts):
        """Standard execution."""
        cfg_content = self._get_single_rh("PointSourceConfig").contents

        # table_mocage_chem.txt (from MOCAGE.CFG without keywords)
        self._create_table_mocage_chem(cfg_content)

        #  Are empty initial state required ?
        if not self.context.sequence.effective_inputs(role="HMRestart"):
            self._init_empty_hm(cfg_content.nbpolls)

        # namelist update
        self._prepare_mocage_fc_namelist(cfg_content.nbpolls)

        super(MocaccForecast, self).execute(rh, opts)


class PostMocacc(AlgoComponent):
    """
    Post-processing of Mocage accident.

    Netcdf files produced by Forecast are converted into grib with :
    - interpolation from model levels to height and pressure levels
    - aggregation of pollutants
    - temporal integration

    This post-processing is done with an external python module.

    For a few terms, a tarfile include all already created gribs (+ a fews other files).
    When created, this promised tarfile is cached, to allow hook on it in operations (BDPE routing).
    """

    # fmt: off
    _footprint = [
        model,
        dict(
            info = "Post-processing of mocage accident",
            attr = dict(
                kind = dict(
                    values   = ["post_mocacc"]
                ),
                engine = dict(
                    values   = ["custom"]
                ),
                model = dict(
                    values   = ["mocage"]
                ),
                extern_module = dict(
                    info     = "External module to be used"
                ),
                extern_func = dict(
                    info     = "Function within external module to call"
                ),
                hpc_done = dict(
                    info     = "File indicating end of simulation. Added to tar",
                    optional = True,
                    default  = "hpc.done",
                ),
                restart_json = dict(
                    info     = "File listing available validities for a restart from this run.Added to tar",
                    optional = True,
                    default  = "restart.json",
                )
            ),
        ),
    ]
    # fmt: on

    @property
    def realkind(self):
        return "postmocacc"

    def _create_restart_json(self):
        """Create a json file with available validitities for a restart."""
        seq = self.context.sequence
        rh_extra_conf = self.context.sequence.effective_inputs(role="ExtraConf")[0].rh
        validities = {
            "ihm_origin": "unknown",
            "id": rh_extra_conf.provider.scenario,
            "validity_times": rh_extra_conf.contents.validities_restart_iso,
        }

        if seq.effective_inputs(role="AlerteJson"):
            alerte_json = seq.effective_inputs(role="AlerteJson")[0].rh
            validities["ihm_origin"] = alerte_json.contents["ihm_origin"]

        self.system.json_dump(validities, self.restart_json)

    def execute(self, rh, opts):
        """Standard execution."""
        sh = self.system
        seq = self.context.sequence

        import importlib

        mymodule = importlib.import_module(self.extern_module)
        myfunc = getattr(mymodule, self.extern_func)

        # What are the routing terms and associated promised sections ?
        routed_outputs = {
            s.rh.resource.term: s
            for s in self.promises
            if s.role == "PromiseRoutingMocaccOutputs"
        }

        logger.info(
            [
                promised_sec.rh.container.localpath()
                for (_, promised_sec) in routed_outputs.items()
            ]
        )
        if routed_outputs:
            last_routed_output = sorted(routed_outputs.keys())[-1]

        # netcdf files from forecast
        ncrh = self.context.sequence.effective_inputs(role="NetcdfForecast")
        transinv = True if ncrh[-1].rh.resource.term < ncrh[0].rh.resource.term else False

        # overwrite ncrh by the ascending sort of the ncrh list
        # or descinding if inverse transport
        ncrh.sort(key=lambda s: s.rh.resource.term, reverse=transinv)

        latest_by_geom = dict()

        # store netcdf paths expected from forecast by term, when netcdf has been processed, its path is
        # removed
        todo_netcdf_by_term = defaultdict(set)

        for sec in ncrh:
            todo_netcdf_by_term[sec.rh.resource.term].add(sec.rh.container.localpath())

        # store grib paths produced from input netcdfs
        done_grib_by_term = defaultdict(set)

        # loop waiting for netcdfs produced during forecast
        # these netcdfs are converted into grib1
        # from model levels to height and pressure levels
        for sec in ncrh:
            r = sec.rh

            # wait for the next netcdf file to be translated in grib1 format
            self.grab(sec, comment="Grib1 format from netcdf forecasts")

            sh.title(
                "Loop on domain {0:s} and term {1:s}".format(
                    r.resource.geometry.area, r.resource.term.fmthm
                )
            )

            # wont work with concurrency or parallelism as previous resource is expected
            # for the same geometry, for temporal integration
            if r.resource.geometry in latest_by_geom and not transinv:
                logger.info(
                    "Time integration using {0!s} as initial state".format(
                        latest_by_geom[r.resource.geometry]
                    )
                )
                gribname = myfunc(
                    r.container.filename, [latest_by_geom[r.resource.geometry]]
                )
            else:
                logger.info("No initial state for time integration")
                gribname = myfunc(r.container.filename, [])

            latest_by_geom[r.resource.geometry] = r.container.localpath()
            todo_netcdf_by_term[r.resource.term].discard(r.container.localpath())
            done_grib_by_term[r.resource.term].add(gribname)

            # If needed terms have already been done, for all geometries
            # prepare tar for routing
            # wont work with concurrency or parallelism...
            if (
                r.resource.term in routed_outputs
                and not todo_netcdf_by_term[r.resource.term]
            ):

                promised_sec = routed_outputs[r.resource.term]
                tarname = promised_sec.rh.container.localpath()
                gribs = []

                for (term, gribs_by_term) in done_grib_by_term.items():
                    if term <= r.resource.term and not transinv:
                        gribs += gribs_by_term
                    elif term >= r.resource.term and transinv:
                        gribs += gribs_by_term

                # Alerte.json may be missing
                files_to_add = (
                    [
                        sec.rh.container.localpath()
                        for sec in seq.effective_inputs(role="PointSourceConfig")
                    ]
                    + [
                        sec.rh.container.localpath()
                        for sec in seq.effective_inputs(role="AlerteJson")
                    ]
                    + gribs
                )

                # only for the last term :
                # - add file indicating end of simulation to tar
                # - add restart.json
                if r.resource.term == last_routed_output:
                    sh.touch(self.hpc_done)
                    self._create_restart_json()
                    files_to_add.append(self.hpc_done)
                    files_to_add.append(self.restart_json)

                sh.title("tar in {0}".format(tarname))
                sh.tar(tarname, *files_to_add)

                # To allow flying routing via hook on promise
                promised_sec.put(incache=True)
