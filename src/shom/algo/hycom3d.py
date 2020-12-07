#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr  4 17:32:49 2019 by sraynaud
"""

from collections import defaultdict
from functools import partial

import vortex.tools.date as vdate
from vortex.layout.dataflow import Section
from vortex.algo.components import (
    Expresso, AlgoComponent, AlgoComponentError, BlindRun)

from sloop.io import nc_get_time
from sloop.interp import nc_interp_at_freq_to_nc
from sloop.models.hycom3d import (
    HYCOM3D_MODEL_DIMENSIONSH_TEMPLATE,
    HYCOM3D_SIGMA_TO_STMT_FNS,
    HYCOM3D_MASK_FILE,
    HYCOM3D_GRID_AFILE,
    check_grid_dimensions,
    setup_stmt_fns,
    format_ds,
    read_regional_grid,
    AtmFrc,
    Rivers,
    run_bin2hycom
)


from ..util.config import config_to_env_vars

__all__ = []
# from vortex.data.executables import Script
# from gco.syntax.stdattrs import gvar

# from hycomvortex import (HYCOM_IBC_COMPILE_SCRIPT)


# %% Compilation


class Hycom3dCompilator(Expresso):

    _footprint = dict(
        info="Compile inicon",
        attr=dict(
            kind=dict(
                values=["hycom_3d_compilator"],
            ),
            compilation_script=dict(
                info="Shell script that makes the compilation.",
                optional=False,
            ),
            env_config=dict(
                info="Environment variables and options for compilation",
                option=True,
                type=dict,
                default={},
            ),
            env_context=dict(
                info="hycom3d context",
                values=["prepost", "model"]
            ),
        ),
    )

    def valid_executable(self, rh):
        return True

    def prepare(self, rh, kw):
        super(Hycom3dCompilator, self).prepare(rh, kw)
        self.env["HPC_TARGET"] = self.env["RD_HPC_TARGET"]
        env_vars = config_to_env_vars(self.env_config)
        for name, value in env_vars.items():
            print(f'SETTING ENV: {name}={value}')
            self.env[name] = value

    def execute(self, rh, kw):
        # super(Hycom3dCompilator, self).execute(rh, kw)
        print(self.spawn([self.compilation_script], {"outsplit": False}))

    @property
    def realkind(self):
        # return self.__class__.__name__.lower()
        return "hycom3d_compilator"


class Hycom3dIBCCompilator(Hycom3dCompilator):
    _footprint = dict(
        info="Compile IBC executables",
        attr=dict(
            kind=dict(
                values=['hycom3d_ibc_compilator'],
            ),
            sigma=dict(
                info="sigma value",
                optional=False,
                values=list(HYCOM3D_SIGMA_TO_STMT_FNS.keys()),
            ),
        ),
    )

    def prepare(self, rh, kw):
        super().prepare(rh, kw)

        # Setup the stmt_fns.h file
        for context in "ibc_hor", "ibc_ver":
            setup_stmt_fns(self.sigma, context)

    @property
    def realkind(self):
        # return self.__class__.__name__.lower()
        return "hycom3d_ibc_compilator"


class Hycom3dModelCompilator(Hycom3dCompilator):

    _footprint = dict(
        info="Compile the 3d model",
        attr=dict(
            dimensions=dict(
                info="Dictionary of the model dimensions",
                optional=False,
                type=dict,
            ),
            sigma=dict(
                info="sigma value",
                optional=False,
                values=list(HYCOM3D_SIGMA_TO_STMT_FNS.keys()),
            ),
        ),
    )

    def prepare(self, rh, kw):
        # super(Hycom3dModel3DCompilator, self).prepare(rh, kw)

        # Check dimensions
        check_grid_dimensions(self.dimensions, HYCOM3D_GRID_AFILE)

        # Fill dimensions.h.template
        dimensionsh = HYCOM3D_MODEL_DIMENSIONSH_TEMPLATE.replace(".template", "")
        with open(HYCOM3D_MODEL_DIMENSIONSH_TEMPLATE, "r") as f:
            content = f.read()
        content = content.format(**self.dimensions)
        with open(dimensionsh, "w") as f:
            f.write(content)

        # Setup the stmt_fns.h file
        setup_stmt_fns(self.sigma, "model")

    @property
    def realkind(self):
        # return self.__class__.__name__.lower()
        return "hycom3d_model_compilator"


# %% Initial and boundary condition AlgoComponents


class Hycom3dIBCRunTime(AlgoComponent):
    """Algo component for the temporal interpolation of IBC netcdf files"""

    _footprint = [
        #        dateperiod_deco,
        dict(
            info="Run the initial and boundary conditions time interpolator",
            attr=dict(
                kind=dict(
                    values=["hycom3d_ibc_run_time"],
                ),
                begindate=dict(),
                ncout=dict(
                    default="forecast.nc",
                    optional=True,
                ),
                rank=dict(
                    default=0,
                    type=int,
                    optional=True,
                ),
                step=dict(),
            ),
        ),
    ]

    def prepare(self, rh, opts):
        super(Hycom3dIBCRunTime, self).prepare(rh, opts)

        # Input netcdf files
        ncinputs = self.context.sequence.effective_inputs(role=["Input"])
        self._ncfiles = [sec.rh.container.localpath() for sec in ncinputs]

    def execute(self, rh, opts):
        super(Hycom3dIBCRunTime, self).execute(rh, opts)

        # Interpolate in time
        nc_interp_at_freq_to_nc(
            self._ncfiles,
            self.step,
            begindate=self.conf.rundate,
            ncout=self.ncout,
            # preproc=self._geo_selector,
            postproc=format_ds)


class Hycom3dIBCRunHoriz(BlindRun):

    _footprint = [
        dict(
            info="Run the initial and boundary conditions horizontal interpolator",
            attr=dict(
                kind=dict(
                    values=["hycom3d_ibc_run_horiz"],
                ),
                rank=dict(
                    default=0,
                    type=int,
                    optional=True,
                ),
                method=dict(
                    default=0,
                    type=int,
                    optional=True,
                ),
                pad=dict(
                    default=1,
                    type=float,
                    optional=True,
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_ibc_run_horiz"

    def prepare(self, rh, opts):
        super(Hycom3dIBCRunHoriz, self).prepare(rh, opts)

        # Input netcdf file
        ncinput = self.context.sequence.effective_inputs(
            role="Input")[0].rh.container.localpath()

        # Read hycom grid extents
        from sloop.models.hycom3d import read_regional_grid_b
        from sloop.grid import GeoSelector
        rg = read_regional_grid_b(f"FORCING{self.rank}./regional.grid.b")
        geo_selector = GeoSelector((rg["plon_min"], rg["plon_max"]),
                                   (rg["plat_min"], rg["plat_max"]),
                                   pad=self.pad)

        # Conversion to .res files
        from sloop.models.hycom3d import nc_to_res
        resfiles = nc_to_res(
            [ncinput], outfile_pattern='{var_name}_merc.res{ifile:03d}',
            preproc=geo_selector)
        self.varnames = list(resfiles.keys())
        self.csteps = range(len(resfiles["ssh"]))

        # Constant files
        cdir = f"FORCING{self.rank}."
        for cfile in "regional.grid.a", "regional.grid.b", "regional.depth.a":
            if not self.system.path.exists(cfile):
                self.system.symlink(self.system.path.join(cdir, cfile), cfile)

    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        return dict(method=self.method, **self._clargs)

    def execute(self, rh, opts):
        """We execute several times the executable with different arguments"""
        for varname in ["ssh", "saln", "temp"]:
            for cstep in self.csteps:
                self._clargs = dict(varname=varname, cstep=cstep)
                super(Hycom3dIBCRunHoriz, self).execute(rh, opts)


class Hycom3dIBCRunVertical(BlindRun):
    """

    Inputs:

    ${repmod}/regional.depth.a
    ${repmod}/regional.grid.a
    ${repparam}/ports.input
    ${repparam}/blkdat.input
    ${repparam}/defstrech.input

    Exe:
    ${repbin}/inicon $repdatahorgrille ssh_hyc.cdf temp_hyc.cdf saln_hyc.cdf "$idm" "$jdm" "$kdm" "$CMOY" "$SSHMIN"
    """
    _footprint = [
        dict(
            info="Run the initial and boundary conditions vertical interpolator",
            attr=dict(
                kind=dict(
                    values=["hycom3d_ibc_run_vert"],
                ),
                rank=dict(
                    default=0,
                    type=int,
                    optional=True,
                ),
                sshmin=dict(),
                cmoy=dict(),
                restart=dict(type=bool)
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_ibc_run_vert"

    def prepare(self, rh, opts):
        super(Hycom3dIBCRunVertical, self).prepare(rh, opts)

        # Input netcdf file
        ncfiles = [ei.rh.container.localpath() for ei in
                   self.context.sequence.effective_inputs(role="Input")]

        # Restart time is taken from input files
        if self.restart:
            self._restart_time = nc_get_time(ncfiles[0])[0]

        # Constant files
        for cfile in (f"FORCING{self.rank}./regional.grid.a",
                      f"FORCING{self.rank}./regional.grid.b",
                      f"FORCING{self.rank}./regional.depth.a",
                      f"PARAMETERS{self.rank}./blkdat.input",
                      f"PARAMETERS{self.rank}./defstrech.input",
                      f"PARAMETERS{self.rank}./ports.input"):
            if not self.system.path.exists(self.system.path.basename(cfile)):
                self.system.symlink(cfile, self.system.path.basename(cfile))

        # Read dimensions
        from sloop.models.hycom3d import read_blkdat_input
        dsb = read_blkdat_input("blkdat.input")
        self._nx = int(dsb.idm)
        self._ny = int(dsb.jdm)
        self._nz = int(dsb.kdm)

        # Command line arguments
        self._clargs = dict(
            datadir="./",
            sshfile=ncfiles[0],
            tempfile=ncfiles[1],
            salnfile=ncfiles[2],
            nx=self._nx,
            ny=self._ny,
            nz=self._nz,
            cmoy=self.cmoy,
            sshmin=self.sshmin,
            cstep=0)

    def postfix(self, rh, opts):
        super().postfix(rh, opts)
        if self.restart:
            rest_head(self._restart_time)
        else:
            run_bin2hycom(self._nx, self._ny, self._nz)

    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        return dict(**self._clargs)


# %% AlgoComponents regarding the River preprocessing steps

class Hycom3dRiversFlowRate(AlgoComponent):

    _footprint = [
        dict(
            info="Get the river tar/cfg/ini files"\
                ", run the time interpolator"\
                " and compute river fluxes",
            attr=dict(
                kind=dict(
                    values=["RiversFlowRate"],
                ),
                nc_out=dict(
                    optional=True,
                    default="{river}.flx.nc",
                ),
                terms=dict(
                    optional=False,
                    type=list,
                ),
                rundate=dict(
                    optional=False,
                    type=vdate.Date,
                ),
                engine=dict(
                    values=["current" ],
                    default="current",
                ),
            ),
        ),
    ]

    def prepare(self, rh, opts):
        super(Hycom3dRiversFlowRate, self).prepare(rh, opts)

        gettarfile = self.context.sequence.effective_inputs(
            role=["GetRivers"])
        if len(gettarfile) == 0:
            raise AlgoComponentError(
                "No tar file available for rivers data"
            )
        self.tarname = [sec.rh.container.localpath() for sec in
                            gettarfile][0]

    def execute(self, rh, opts):
        super(Hycom3dRiversFlowRate, self).execute(rh, opts)

        time = [self.rundate+vdate.Time(term) for term in self.terms]
        Rivers(tarname=self.tarname).flowrate(time, self.nc_out)

    @property
    def realkind(self):
        return 'RiversFlowRate'


class Hycom3dRiversTempSaln(AlgoComponent):

    _footprint = [
        dict(
            info="Compute temperature and salinity characteristics"\
                " of rivers",
            attr=dict(
                kind=dict(
                    values=["RiversTempSaln"]
                ),
                nc_in=dict(
                    optional=True,
                    default="{river}.flx.nc",
                ),
                nc_out=dict(
                    optional=True,
                    default="{river}.flx.ts.nc",
                ),
                engine=dict(
                    values=["current" ],
                    default="current",
                ),
            ),
        ),
    ]

    def execute(self, rh, opts):
        super(Hycom3dRiversTempSaln, self).execute(rh, opts)
        Rivers().tempsaln(self.nc_in, self.nc_out)

    @property
    def realkind(self):
        return 'RiversTempSaln'


class Hycom3dRiversOut(AlgoComponent):

    _footprint = [
        dict(
            info="Create the output files for Hycom",
            attr=dict(
                kind=dict(
                    values=["RiversOut"],
                ),
                nc_in=dict(
                    optional=True,
                    default="{river}.flx.ts.nc",
                ),
                engine=dict(
                    values=["current" ],
                    default="current",
                ),
            ),
        ),
    ]

    def execute(self, rh, opts):
        super(Hycom3dRiversOut, self).execute(rh, opts)
        Rivers().write_rfiles(self.nc_in)

    @property
    def realkind(self):
        return 'RiversOut'


# %% AlgoComponents regarding the Atmospheric forcing preprocessing steps


class Hycom3dAtmFrcTime(AlgoComponent):

    _footprint = [
        dict(
            info="Get the atmospheric fluxes conditions from grib files "\
                "and run the time interpolator",
            attr=dict(
                kind=dict(
                    values=["AtmFrcTime"],
                ),
                terms=dict(
                    optional=False,
                    type=list,
                ),
                rundate=dict(
                    optional=False,
                    type=vdate.Date,
                ),
                nc_out=dict(
                    optional=True,
                    default="atmfrc.time.nc",
                ),
                engine=dict(
                    values=["current" ],
                    default="current",
                ),
            ),
        ),
    ]

    @property
    def _sorted_inputs(self):
        """Build a dictionary containing a list of sections for each
        cumul/term/origin"""

        insec = self.context.sequence.effective_inputs(
            role='GetAtmFrc')
        outsec = defaultdict(partial(defaultdict, partial(defaultdict, Section)))
        for sec in insec:
            real_term = sec.rh.resource.date.time() + sec.rh.resource.term
            outsec[sec.rh.resource.cumul][real_term][sec.rh.resource.origin] = sec
        return outsec

    def prepare(self, rh, opts):
        super(Hycom3dAtmFrcTime, self).prepare(rh, opts)

        self.sections = defaultdict(partial(list))
        for cumul, cumul_d in self._sorted_inputs.items():
            for term, term_d in cumul_d.items():
                if "ana" in term_d.keys():
                    self.sections[cumul].append(term_d["ana"])
                else:
                    self.sections[cumul].append(term_d["fcst"])

    def execute(self, rh, opts):
        super(Hycom3dAtmFrcTime, self).execute(rh, opts)

        time = [self.rundate+vdate.Time(term) for term in self.terms]
        insta_files=[sec.rh.container.localpath() for sec in self.sections["insta"]]
        cumul_files=[sec.rh.container.localpath() for sec in self.sections["cumul"]]
        AtmFrc(insta_files=insta_files,
               cumul_files=cumul_files,).interp_time(time, self.nc_out)

    @property
    def realkind(self):
        return 'AtmFrcTime'


class Hycom3dAtmFrcParameters(AlgoComponent):

    _footprint = [
        dict(
            info="Compute atmospheric flux parameters necessary"\
                " for a Hycom3d run",
            attr=dict(
                kind=dict(
                    values=["AtmFrcParam"],
                ),
                nc_in=dict(
                    optional=True,
                    default="atmfrc.time.nc",
                ),
                nc_out=dict(
                    optional=True,
                    default="atmfrc.completed.nc",
                ),
                engine=dict(
                    values=["current" ],
                    default="current",
                ),
            ),
        ),
    ]

    def execute(self, rh, opts):
        super(Hycom3dAtmFrcParameters, self).execute(rh, opts)
        AtmFrc().parameters(self.nc_in, self.nc_out)

    @property
    def realkind(self):
        return 'AtmFrcParam'


class Hycom3dAtmFrcMask(AlgoComponent):

    _footprint = [
        dict(
            info="Create the land/sea mask"\
                "and add correction to parameters",
            attr=dict(
                kind=dict(
                    values=["AtmFrcMask"],
                ),
                nc_in=dict(
                    optional=True,
                    default="atmfrc.completed.nc",
                ),
                nc_out=dict(
                    optional=True,
                    default="atmfrc.masked.nc",
                ),
                engine=dict(
                    values=["current" ],
                    default="current",
                    ),
            ),
        ),
    ]

    def prepare(self, rh, opts):
        super(Hycom3dAtmFrcMask, self).prepare(rh, opts)

        weightsfile = self.context.sequence.filtered_inputs(
            role=["MaskInterpWeights"])
        if len(weightsfile) == 0:
            print(
                "No weight file available to interpolate"
                " the land/sea mask on hycom grid"
            )
        self._weightsfile = [sec.rh.container.localpath() for sec in
                            weightsfile][0]

    def execute(self, rh, opts):
        super(Hycom3dAtmFrcMask, self).execute(rh, opts)
        AtmFrc().regridmask(HYCOM3D_MASK_FILE, self.nc_out, self.nc_in, self._weightsfile)

    @property
    def realkind(self):
        return 'AtmFrcMask'


class Hycom3dAtmFrcSpace(AlgoComponent):

    _footprint = [
        dict(
            info="Run the horizontal interpolator",
            attr=dict(
                kind=dict(
                    values=["AtmFrcSpace"],
                ),
                nc_in=dict(
                    optional=True,
                    default="atmfrc.masked.nc",
                ),
                nc_out=dict(
                    optional=True,
                    default="atmfrc.space.nc",
                ),
                engine=dict(
                    values=["current" ],
                    default="current",
                ),
            ),
        ),
    ]

    def prepare(self, rh, opts):
        super(Hycom3dAtmFrcSpace, self).prepare(rh, opts)

        weightsfile = self.context.sequence.filtered_inputs(
            role=["AtmFrcInterpWeights"])
        if len(weightsfile) == 0:
            print(
                "No weight file available to interpolate"
                " the land/sea mask on hycom grid"
            )
        self._weightsfile = [sec.rh.container.localpath() for sec in
                            weightsfile][0]


    def execute(self, rh, opts):
        super(Hycom3dAtmFrcSpace, self).execute(rh, opts)
        hycom_grid = read_regional_grid(HYCOM3D_GRID_AFILE, grid_loc='p')
        AtmFrc().regridvar(self.nc_in, self.nc_out, hycom_grid, self._weightsfile)

    @property
    def realkind(self):
        return 'AtmFrcSpace'


class Hycom3dAtmFrcFinal(AlgoComponent):

    _footprint = [
        dict(
            info="Prepare the dataset for Hycom",
            attr=dict(
                kind=dict(
                    values=["AtmFrcFinal"],
                ),
                nc_in=dict(
                    optional=True,
                    default="atmfrc.space.nc",
                ),
                nc_out=dict(
                    optional=True,
                    default="atmfrc.final.nc",
                ),
                engine=dict(
                    values=["current" ],
                    default="current",
                ),
            ),
        ),
    ]

    def execute(self, rh, opts):
        super(Hycom3dAtmFrcFinal, self).execute(rh, opts)
        AtmFrc().rename_vars(self.nc_in, self.nc_out)

    @property
    def realkind(self):
        return 'AtmFrcFinal'


class Hycom3dAtmFrcOut(AlgoComponent):
    _footprint = [
        dict(
            info="Create the output files for Hycom",
            attr=dict(
                kind=dict(
                    values=["AtmFrcOut"],
                ),
                nc_in=dict(
                    optional=True,
                    default="atmfrc.final.nc",
                ),
                freq=dict(
                    optional=True,
                    default=1,
                ),
                engine=dict(
                    values=["current" ],
                    default="current",
                ),
            ),
        ),
    ]

    def execute(self, rh, opts):
        super(Hycom3dAtmFrcOut, self).execute(rh, opts)
        AtmFrc().write_abfiles(self.nc_in, freq=self.freq)

    @property
    def realkind(self):
        return 'AtmFrcOut'
