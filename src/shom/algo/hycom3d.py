"""
Created on Thu Apr  4 17:32:49 2019 by sraynaud
"""

from collections import defaultdict

import bronx.stdtypes.date as vdate
from bronx.fancies import loggers
from footprints.stdtypes import FPList, FPDict
import footprints
from vortex.syntax.stdattrs import date
from vortex.data import geometries
from vortex.algo.components import AlgoComponentDecoMixin, AlgoComponentError
from vortex.algo.components import Expresso, BlindRun, Parallel, ParaBlindRun
from vortex.tools.parallelism import VortexWorkerBlindRun

from ..util.env import config_to_env_vars, stripout_conda_env


__all__ = []

logger = loggers.getLogger(__name__)


# %% Utility classes (mixins for common behaviours)

class Hycom3dSpecsFileDecoMixin(AlgoComponentDecoMixin):
    """Provide utility methods for dealing with specs file."""

    def _get_specs_data(self, fname):
        """Return specs data from json."""
        return self.system.json_load(fname)

    def _get_specs_and_link(self, fname):
        """Return specs data and link files."""
        specs = self._get_specs_data(fname)
        for path in specs.get("links", []):
            local_path = self.system.path.basename(path)
            if not self.system.path.exists(local_path):
                self.system.symlink(path, local_path)
        return specs


# %% Compilation

class Hycom3dCompilator(Expresso):
    """TODO Class Documentation."""

    _footprint = dict(
        info="Compile inicon",
        attr=dict(
            kind=dict(
                values=["hycom3d_compilator"],
            ),
            env_config=dict(
                info="Environment variables and options for compilation",
                optional=True,
                type=FPDict,
                default=FPDict(),
            ),
        ),
    )

    def prepare(self, rh, kw):
        super().prepare(rh, kw)
        # Note LFM: A clone of the environment is already created in
        #           AlgoComponent.run. There is no need to clone it again.
        stripout_conda_env(self.ticket, self.env)
        self.env.update(config_to_env_vars(self.env_config))


# %% Initial and boundary condition

class Hycom3dIBCRunTime(Expresso):
    """Algo component for the temporal interpolation of IBC netcdf files."""

    _footprint = [
        date,
        dict(
            info="Run the initial and boundary conditions time interpolator",
            attr=dict(
                kind=dict(
                    values=["hycom3d_ibc_run_time"],
                ),
                terms=dict(
                    type=FPList,
                ),
            ),
        ),
    ]

    def prepare(self, rh, opts):
        super().prepare(rh, opts)

        ncinputs = self.context.sequence.effective_inputs(role=["Input"])
        self._ncins = ','.join(
            [sec.rh.container.localpath() for sec in ncinputs])
        self._dates = ','.join(
            [(self.date + vdate.Time(term)).isoformat() for term in self.terms])

    def spawn_command_options(self):
        return dict(
            ncins=self._ncins,
            dates=self._dates)


class Hycom3dIBCRunHorizRegridcdf(BlindRun, Hycom3dSpecsFileDecoMixin):
    """TODO Class Documentation."""

    _footprint = [
        dict(
            info="Run the initial and boundary conditions horizontal fortran interpolator",
            attr=dict(
                kind=dict(values=["hycom3d_ibc_run_horiz_regridcdf"]),
                method=dict(type=int),
                density_corr=dict(type=int),
                bathy_corr=dict(type=int),
                regridvars=dict(
                    default=["ssh", "saln", "temp"],
                    type=FPList)
            ),
        ),
    ]

    def prepare(self, rh, opts):
        """Get specs data from JSON and setup args."""
        super().prepare(rh, opts)
        specs = self._get_specs_and_link("regridcdf.json")
        resfiles = specs["resfiles"]
        self.csteps = range(len(resfiles["ssh"]))

    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        return dict(method=self.method,
                    density_corr=self.density_corr,
                    bathy_corr=self.bathy_corr,
                    **self._clargs)

    def execute(self, rh, opts):
        """We execute several times the executable with different arguments"""
        for varname in self.regridvars:
            print(varname)
            for cstep in self.csteps:
                self._clargs = dict(varname=varname, cstep=cstep)
                print(self._clargs)
                super().execute(rh, opts)


class Hycom3dIBCRunVerticalInicon(BlindRun, Hycom3dSpecsFileDecoMixin):
    """TODO Class Documentation.

    :note: Inputs::
        ${repmod}/regional.depth.a
        ${repmod}/regional.grid.a
        ${repparam}/ports.input
        ${repparam}/blkdat.input
        ${repparam}/defstrech.input

    :note: Exe::
        ${repbin}/inicon $repdatahorgrille ssh_hyc.cdf temp_hyc.cdf saln_hyc.cdf "$idm" "$jdm" "$kdm" "$CMOY" "$SSHMIN"

    """

    _footprint = [
        dict(
            info="Run the initial and boundary conditions vertical interpolator",
            attr=dict(
                kind=dict(values=["hycom3d_ibc_run_vert_inicon"]),
                sshmin=dict(),
                cmoy=dict(),
                bathy_corr=dict(type=int)
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_ibc_run_vert_inicon"

    def prepare(self, rh, opts):
        """Get specs data from JSON."""
        super().prepare(rh, opts)
        self._specs = self._get_specs_and_link("inicon.json")

    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        # Note LFM: It will be more generic to have this data in the footprint.
        return dict(
            datadir="./",
            sshfile="ssh_hyc.cdf",
            tempfile="temp_hyc.cdf",
            salnfile="saln_hyc.cdf",
            nx=self._specs["nx"],
            ny=self._specs["ny"],
            nz=self._specs["nz"],
            cmoy=self.cmoy,
            sshmin=self.sshmin,
            bathy_corr=self.bathy_corr,
            cstep="0")


# %% River preprocessing steps

class Hycom3dRiversFlowRate(Expresso):
    """TODO Class Documentation."""

    _footprint = [
        date,
        dict(
            info=("Get the river tar/cfg/ini files"
                  ", run the time interpolator"
                  " and compute river fluxes"),
            attr=dict(
                kind=dict(
                    values=["hycom3d_rivers_flowrate"],
                ),
                rank=dict(
                    optional=True,
                    default=0,
                    type=int,
                ),
                terms=dict(
                    optional=False,
                    type=FPList,
                ),
            ),
        ),
    ]

    def prepare(self, rh, opts):
        super().prepare(rh, opts)

        gettarfile = self.context.sequence.effective_inputs(
            role=["Input"])
        if len(gettarfile) == 0:
            raise AlgoComponentError(
                "No tar file available for rivers data"
            )
        self._tarname = [sec.rh.container.localpath() for sec in
                         gettarfile][0]
        self._dates = [self.date + vdate.Time(term) for term in self.terms]

    def spawn_command_options(self):
        return dict(
            rank=self.rank,
            tarfile=self._tarname,
            dates=",".join([date.isoformat() for date in self._dates])
        )


# %% Atmospheric forcing preprocessing steps

class Hycom3dAtmFrcTime(Expresso):
    """TODO Class Documentation."""

    _footprint = [
        date,
        dict(
            info=("Get the atmospheric fluxes conditions from grib files "
                  "and run the time interpolator"),
            attr=dict(
                kind=dict(
                    values=["AtmFrcTime"],
                ),
                terms=dict(
                    type=FPList,
                ),
            ),
        ),
    ]

    def prepare(self, rh, opts):
        super().prepare(rh, opts)

        # Input insta files
        insta_rhs = [sec.rh for sec in
                     self.context.sequence.effective_inputs(role="InputInsta")]
        insta_rhs.sort(key=lambda rh: (rh.resource.date, rh.resource.term))
        self._insta_files = []
        for rh in insta_rhs:
            if not rh.container.localpath() in self._insta_files:
                self._insta_files.append(rh.container.localpath())

        # Input cumul files
        cumul_rhs = [sec.rh for sec in
                     self.context.sequence.effective_inputs(role="InputCumul")]
        cumul_rhs.sort(key=lambda rh: (rh.resource.date, rh.resource.term))
        self._cumul_files = defaultdict(list)
        for rh in cumul_rhs:
            self._cumul_files[rh.resource.date].append(
                rh.container.localpath())

        # Output dates
        self._interp_dates = [
            self.date + vdate.Time(term) for term in self.terms
        ]

    def spawn_command_options(self):
        return dict(
            ncins_insta=','.join(self._insta_files),
            ncins_cumul=','.join([
                "+".join(fterms) for fterms in self._cumul_files.values()
            ]),
            dates=','.join([
                date.isoformat() for date in self._interp_dates
            ]),
        )


# %% Spectral nudging

class Hycom3dSpectralNudgingRunPrepost(Expresso):
    """Algo component for preparing files before the demerliac filter."""

    _footprint = dict(
        info="Run the spectral nudging demerliac preprocessing",
        attr=dict(
            kind=dict(
                values=["hycom3d_spnudge_prepost"],
            ),
        ),
    )

    def prepare(self, rh, opts):
        super().prepare(rh, opts)

        ncinputs = self.context.sequence.effective_inputs(role=["Input"])
        self._ncins = ','.join(
            [sec.rh.container.localpath() for sec in ncinputs]
        )

    def spawn_command_options(self):
        return dict(
            ncins=self._ncins,
        )


class Hycom3dSpectralNudgingRunDemerliac(BlindRun, Hycom3dSpecsFileDecoMixin):
    """Demerliac filtering over Hycom3d outputs."""

    _footprint = [
        dict(
            info="Run the demerliac filtering over Hycom3d outputs",
            attr=dict(
                kind=dict(
                    values=["hycom3d_spnudge_demerliac"],
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_spnudge_demerliac"

    def prepare(self, rh, opts):
        """Get specs data from JSON and setup args."""
        super().prepare(rh, opts)
        specs = self._get_specs_and_link("demerliac.json")
        self.ncins = specs["ncins"]
        self.ncout_patt = specs["ncout_patt"]
        self.varnames = list(self.ncins.keys())
        self.date_demerliac = specs["date_demerliac"]
        self.otype = specs["otype"]

    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        return dict(date=self.date_demerliac,
                    output_type=self.otype)

    def execute(self, rh, opts):
        """We execute several times the executable with different inputs"""
        for varname in self.varnames:
            self.system.symlink(self.ncins[varname], "input.nc")
            super().execute(rh, opts)
            self.system.rm("input.nc")
            self.system.mv("output.nc", self.ncout_patt.format(**locals()))


class Hycom3dSpectralNudgingRunSpectralPreproc(Expresso):
    """Algo component for preparing files before the spectral filter"""

    _footprint = dict(
        info="Run the spectral nudging spectral filter preprocessing",
        attr=dict(
            kind=dict(
                values=["hycom3d_spnudge_spectral_preproc"],
            ),
        ),
    )

    def prepare(self, rh, opts):
        super().prepare(rh, opts)

        ncinputs_hycom3d = self.context.sequence.effective_inputs(
            role=["Input_hycom3d"])
        ncinputs_mercator = self.context.sequence.effective_inputs(
            role=["Input_mercator"])
        self._ncins_hycom3d = ','.join(
            [sec.rh.container.localpath() for sec in ncinputs_hycom3d]
        )
        self._ncins_mercator = ','.join(
            [sec.rh.container.localpath() for sec in ncinputs_mercator]
        )

    def spawn_command_options(self):
        return dict(
            nchycom3d=self._ncins_hycom3d,
            ncmercator=self._ncins_mercator,
        )


class Hycom3dSpectralNudgingRunSpectralMixin(AlgoComponentDecoMixin):

    def _nudging_prepare(self, rh, opts):
        """Get specs data from JSON and setup args."""
        self._specs = self._get_specs_and_link("spectral.json")
        self.varnames = list(self._specs["ncfiles"].keys())
        self.ncfiles = self._specs["ncfiles"]
        self.ncout_patt = self._specs["ncout_patt"]
        # Get command line options
        self._clargs = self.system.json_load(self._specs["clargs"])
        self._links = self._specs["links"] if "links" in self._specs.keys() else []

    _MIXIN_PREPARE_PREHOOKS = (_nudging_prepare, )

    def _nudging_cli_opts_extend(self, prev):
        """Prepare options for the resource's command line."""
        prev.update(self._clargs)
        return prev

    _MIXIN_CLI_OPTS_EXTEND = (_nudging_cli_opts_extend, )


class Hycom3dSpectralNudgingRunSpectral(BlindRun,
                                        Hycom3dSpectralNudgingRunSpectralMixin,
                                        Hycom3dSpecsFileDecoMixin):
    """Spectral filtering over Hycom3d and Mercator outputs."""

    _footprint = dict(
        info="Run the spectral filtering over Hycom3d outputs",
        attr=dict(
            kind=dict(
                values=["hycom3d_spnudge_spectral"],
            ),
        ),
    )

    @property
    def realkind(self):
        return "hycom3d_spnudge_spectral"

    def execute(self, rh, opts):
        """We execute several times the executable with different inputs."""
        for varname in self.varnames:
            for source in list(self.ncfiles[varname].keys()):
                self.system.symlink(self.ncfiles[varname][source], "input.nc")
                super().execute(rh, opts)
                self.system.rm("input.nc")
                self.system.mv("output.nc", self.ncout_patt.format(**locals()))


class Hycom3dSpectralNudgingRunSpectralPara(ParaBlindRun,
                                            Hycom3dSpectralNudgingRunSpectralMixin,
                                            Hycom3dSpecsFileDecoMixin):
    """Spectral filtering over Hycom3d and Mercator outputs in parallel."""

    _footprint = dict(
        info="Run the spectral filtering over Hycom3d outputs in parallel",
        attr=dict(
            kind=dict(
                values=["hycom3d_spnudge_spectral_para"],
            ),
            outfiles=dict(
                optional=True,
                type=FPList,
                default=[]
            ),
        ),
    )

    @property
    def realkind(self):
        return "hycom3d_spnudge_spectral_para"

    def _default_common_instructions(self, rh, opts):
        """Create a common instruction dictionary that will be used by the workers."""
        ddict = super()._default_common_instructions(rh, opts)
        del ddict['progname']
        del ddict['progargs']
        return ddict

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""
        scheduler_instructions = defaultdict(list)
        sh = self.system
        workdir = sh.pwd()
        progname = rh.container.localpath()
        iworker = 0
        for varname in self.varnames:
            for source in list(self.ncfiles[varname].keys()):
                iworker += 1
                subdir = "worker_{}".format(iworker)
                outfiles = self.outfiles.copy()
                outfiles.append(self.ncout_patt.format(**locals()))
                with sh.cdcontext(subdir, create=True):
                    if not sh.path.exists(progname):
                        sh.softlink(sh.path.join(workdir, progname),
                                    progname)
                    sh.softlink(
                        sh.path.join(workdir, self.ncfiles[varname][source]),
                        "input.nc")
                    if len(self._links) > 0:
                        for link in self._links:
                            sh.softlink(sh.path.join(workdir, link),
                                        sh.path.basename(link))
                    scheduler_instructions['name'].append('{:s}'.format(subdir))
                    scheduler_instructions['progname'].append(sh.path.join(workdir, subdir, progname))
                    scheduler_instructions['progargs'].append(footprints.FPList(self.spawn_command_line(rh)))
                    scheduler_instructions['base'].append(subdir)
                    scheduler_instructions['subdir'].append(subdir)
                    scheduler_instructions['files_out'].append(outfiles)
        self._default_pre_execute(rh, opts)
        common_i = self._default_common_instructions(rh, opts)
        logger.info("common_i %s", common_i)
        common_i.update(dict(workdir=workdir, ))
        self._add_instructions(common_i, scheduler_instructions)
        logger.info('scheduler_instruction %s', scheduler_instructions)
        self._default_post_execute(rh, opts)


class SpnudgeWorker(VortexWorkerBlindRun):
    """Include utility methods to run a basic program (i.e no MPI)."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['hycom3d_spnudge_spectral_para'],
            ),
            subdir = dict(
                info = 'work in this particular subdirectory',
                optional = True
            ),
            files_out = dict(
                info = 'names of the output files',
                optional = True,
                type=FPList,
            ),
        )
    )

    def vortex_task(self, **kwargs):
        """TODO: documentation."""
        logger.info("self.subdir %s", self.subdir)
        logger.info("files_out %s", self.files_out)

        sh = self.system
        rundir = sh.getcwd()
        thisdir = sh.path.join(rundir, self.subdir)
        logger.info('thisdir %s', thisdir)
        with sh.cdcontext(thisdir, create=False):
            self.local_spawn('log.out')
            sh.mv("output.nc", sh.path.join(rundir, self.files_out[-1]))
            for file_out in self.files_out[:-1]:
                if not sh.path.exists(sh.path.join(rundir, file_out)):
                    sh.mv(file_out, sh.path.join(rundir, file_out))


# %% Model run AlgoComponents

class Hycom3dModelRunPrepost(Expresso):

    _footprint = dict(
        info="Pre- and post-processings of Hycom run",
        attr=dict(
            kind=dict(
                values=["hycom3d_model_prepost"],
            ),
            clargs=dict(
                type=FPDict,
            ),
        ),
    )

    def spawn_command_options(self):
        return self.clargs


class Hycom3dModelRun(Parallel, Hycom3dSpecsFileDecoMixin):

    _footprint = dict(
        info="Run the model",
        attr=dict(
            binary=dict(
                values=["hycom3d_model_runner"],
            ),
            env_config=dict(
                info="Environment variables and options for running the model",
                optional=True,
                type=FPDict,
                default=FPDict(),
            ),
        ),
    )

    @property
    def realkind(self):
        return "hycom3d_model_run"

    def prepare(self, rh, opts):
        super(Parallel, self).prepare(rh, opts)
        specs = self._get_specs_data("specs.json")

        for copy in specs["copy"]:
            self.system.cp(copy[0], copy[1], intent="inout")
        self.system.mkdir(specs["mkdir"])
        self._clargs = specs["clargs"]
        self.mpiopts = specs["mpiopts"]
        self.namempi = specs["mpiname"]
        # Update the environment
        self.env.update(config_to_env_vars(self.env_config))

    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        return dict(**self._clargs)

    def execute(self, rh, opts):
        # LFM: I think it's a bad idea. mpiopts and mpiname should be provided
        #      during the call to the run method. With this piece of code, this
        #      is not possible anymore.
        #      If vortex.layout.nodes.Node.component_runner is used, these variables
        #      are read from the application's configuration file.
        #      This execute method should simply not exists.
        opts = dict(
            mpiopts=self.mpiopts,
            mpiname=self.namempi
        )
        super().execute(rh, opts)


# %% Post-production run algo component

class Hycom3dPostprodPreproc(Expresso):
    """TODO Class Documentation."""

    _footprint = dict(
        info="Prepare Hycom output for postproduction",
        attr=dict(
            kind=dict(
                values=["hycom3d_postprod_preproc",
                        "hycom3d_postprod_filter_preproc"],
            ),
            rank=dict(
                default=0,
                type=int,
                optional=True,
            ),
            postprod=dict(
                default="datashom_forecast",
                optional=True,
            ),
            rundate=dict(
                # Note LFM: rundate is a string since no explict type is specified.
                #           This is odd.
                default=0,
                optional=True,
            ),
        ),
    )

    def prepare(self, rh, opts):
        super().prepare(rh, opts)
        # Input files
        rhs = [sec.rh for sec in
               self.context.sequence.effective_inputs(role="Input")]
        self._files = [rh.container.localpath() for rh in rhs]

    def spawn_command_options(self):
        return dict(
            ncins=','.join(self._files),
            rank=self.rank,
            postprod=self.postprod,
            rundate=self.rundate,
        )


class Hycom3dPostprodConcat(Hycom3dPostprodPreproc):
    """TODO Class Documentation."""

    _footprint = dict(
        info="Prepare Hycom output for postproduction",
        attr=dict(
            kind=dict(
                values=["hycom3d_postprod_concat"],
            ),
            vapp=dict(
                default="hycom3d",
                optional=True,
            ),
            vconf=dict(
                default="manga",
                optional=True,
            ),
        ),
    )

    def spawn_command_options(self):
        clopts = super().spawn_command_options()
        clopts['vapp'] = self.vapp
        clopts['vconf'] = self.vconf
        return clopts


class Hycom3dPostprodMixin(AlgoComponentDecoMixin):

    def _postprod_prepare(self, rh, opts):
        self._specs = self._get_specs_data("specs.json")
        self._clargs = self._specs["clargs"]

    _MIXIN_PREPARE_PREHOOKS = (_postprod_prepare, )

    def _postprod_cli_opts_extend(self, prev):
        """Prepare options for the resource's command line."""
        prev.clear()
        for kopt, vopt in self._clargs.items():
            if isinstance(vopt, dict):
                prev.update(vopt)
            else:
                prev[kopt] = vopt
        return prev

    _MIXIN_CLI_OPTS_EXTEND = (_postprod_cli_opts_extend, )


class Hycom3dPostprod(BlindRun, Hycom3dPostprodMixin, Hycom3dSpecsFileDecoMixin):
    """Post-production filter over hycom3d outputs."""

    _footprint = dict(
        info="Run the postprod filtering over Hycom3d outputs",
        attr=dict(
            kind=dict(
                values=[
                    "hycom3d_postprod_filter",
                    "hycom3d_postprod_tempconversion"],
            ),
        ),
    )

    @property
    def realkind(self):
        return "hycom3d_postprod"

    def execute(self, rh, opts):
        """We execute several times the executable with different inputs."""
        for arg in self._clargs:
            self._clarg = arg
            super().execute(rh, opts)


class Hycom3dParaPostprod(ParaBlindRun, Hycom3dPostprodMixin, Hycom3dSpecsFileDecoMixin):
    """Hycom3d algo component running post-production
    Fortran executables in parallel
    """

    _footprint = dict(
        info="Run the postprod Fortran executable over Hycom3d outputs",
        attr=dict(
            kind=dict(
                values=["hycom3d_postprod_para", ]
            ),
        ),
    )

    @property
    def realkind(self):
        return "hycom3d_postprod"

    def prepare(self, rh, opts):
        super().prepare(rh, opts)
        self._links = self._specs["links"] if "links" in self._specs.keys() else []

    def _default_common_instructions(self, rh, opts):
        """Create a common instruction dictionary that will be used by the workers."""
        ddict = super()._default_common_instructions(rh, opts)
        del ddict['progname']
        del ddict['progargs']
        return ddict

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""
        scheduler_instructions = defaultdict(list)
        sh = self.system
        workdir = sh.pwd()
        progname = rh.container.localpath()
        for iclarg, clarg in enumerate(self._clargs):
            self._clarg = clarg
            subdir = "worker_{}".format(iclarg)
            with sh.cdcontext(subdir, create=True):
                if not sh.path.exists(progname):
                    sh.softlink(sh.path.join(workdir, progname),
                                progname)
                if "ncins" in clarg.keys():
                    for nc in clarg["ncins"]:
                        fin = clarg["ncins"][nc]
                        if not sh.path.exists(fin):
                            sh.softlink(sh.path.join(workdir, fin),
                                        fin)
                else:
                    fin = clarg["ncin"]
                    if not self.system.path.exists(fin):
                        sh.softlink(sh.path.join(workdir, fin),
                                    fin)
                for link in self._links:
                    if "traductions_noms_longs" in link:
                        sh.softlink(sh.path.join(workdir, link),
                                    "traductions_noms_longs")
                    else:
                        sh.softlink(sh.path.join(workdir, link),
                                    sh.path.basename(link))
                scheduler_instructions['name'].append('{:s}'.format(subdir))
                scheduler_instructions['progname'].append(sh.path.join(workdir, subdir, progname))
                scheduler_instructions['progargs'].append(footprints.FPList(self.spawn_command_line(rh)))
                scheduler_instructions['base'].append(subdir)
                scheduler_instructions['subdir'].append(subdir)
                scheduler_instructions['file_out'].append(clarg["ncout"])
        self._default_pre_execute(rh, opts)
        common_i = self._default_common_instructions(rh, opts)
        logger.info("common_i %s", common_i)
        common_i.update(dict(workdir=workdir, ))
        self._add_instructions(common_i, scheduler_instructions)
        logger.info('scheduler_instruction %s', scheduler_instructions)
        self._default_post_execute(rh, opts)


class PostprodWorker(VortexWorkerBlindRun):
    """Include utility methods to run a basic program (i.e no MPI)."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['hycom3d_postprod_para'],
            ),
            subdir = dict(
                info = 'work in this particular subdirectory',
                optional = True
            ),
            file_out = dict(
                info = 'name of the output file',
                optional = True
            ),
        )
    )

    def vortex_task(self, **kwargs):
        """TODO: documentation."""
        logger.info("self.subdir %s", self.subdir)
        logger.info("file_out %s", self.file_out)

        rundir = self.system.getcwd()
        thisdir = self.system.path.join(rundir, self.subdir)
        logger.info('thisdir %s', thisdir)
        with self.system.cdcontext(thisdir, create=False):
            self.local_spawn('log.out')
            self.system.mv(self.file_out, self.system.path.join(rundir, self.file_out))


class Hycom3dPostprodInterpolation(Hycom3dPostprodPreproc):
    """
    Post-production interpolation over hycom3d outputs
    """
    _footprint = dict(
        info="Run the postprod interpolation over Hycom3d outputs",
        attr=dict(
            kind=dict(
                values=["hycom3d_postprod_interpolation"],
            ),
        ),
    )

    @property
    def realkind(self):
        return "hycom3d_postprod_interpolation"

    def prepare(self, rh, opts):
        super().prepare(rh, opts)
        # Link to regional and blkdat files
        for path in self._specs["links"]:
            local_path = self.system.path.basename(path)
            if not self.system.path.exists(local_path):
                if "traductions_noms_longs" in local_path:
                    self.system.symlink(path, "traductions_noms_longs")
                else:
                    self.system.symlink(path, local_path)


class Hycom3dPostprodExtract(Hycom3dPostprodPreproc):
    """TODO Class Documentation."""

    _footprint = dict(
        info="Prepare Hycom output for postproduction",
        attr=dict(
            kind=dict(
                values=["hycom3d_postprod_extract"]
            ),
            geometries=dict(
                default="geometries.ini",
                optional=True
            ),
        ),
    )

    @property
    def realkind(self):
        return "hycom3d_postprod_extract"

    def postfix(self, rh, opts):
        super(Hycom3dPostprodPreproc, self).postfix(rh, opts)
        geometries.load(self.geometries)
