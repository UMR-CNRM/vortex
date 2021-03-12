#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr  4 17:32:49 2019 by sraynaud
"""

from collections import defaultdict
import json

import vortex.tools.date as vdate
from vortex.syntax.stdattrs import date_deco
from vortex.algo.components import (
    Expresso, AlgoComponentError, BlindRun, Parallel)

from ..util.env import config_to_env_vars, stripout_conda_env


__all__ = []


# %% Compilation


class Hycom3dCompilator(Expresso):

    _footprint = dict(
        info="Compile inicon",
        attr=dict(
            kind=dict(
                values=["hycom3d_compilator"],
            ),
            env_config=dict(
                info="Environment variables and options for compilation",
                optional=True,
                type=dict,
                default={},
            ),
            env_context=dict(
                info="hycom3d context",
                values=["prepost", "model"]
            ),
        ),
    )

    def prepare(self, rh, kw):
        super(Hycom3dCompilator, self).prepare(rh, kw)
        self._env_vars = config_to_env_vars(self.env_config)

    def execute(self, rh, kw):
        with self.env.clone() as e:
            stripout_conda_env(e)
            e.update(self._env_vars)
            super(Hycom3dCompilator, self).execute(rh, kw)


# %% Initial and boundary condition

class Hycom3dIBCRunTime(Expresso):
    """Algo component for the temporal interpolation of IBC netcdf files"""

    _footprint = [
        date_deco,
        dict(
            info="Run the initial and boundary conditions time interpolator",
            attr=dict(
                kind=dict(
                    values=["hycom3d_ibc_run_time"],
                ),
                rank=dict(
                    default=0,
                    type=int,
                    optional=True,
                ),
                terms=dict(type=list),
            ),
        ),
    ]

    def prepare(self, rh, opts):
        super(Hycom3dIBCRunTime, self).prepare(rh, opts)

        ncinputs = self.context.sequence.effective_inputs(role=["Input"])
        self._ncins = ','.join(
            [sec.rh.container.localpath() for sec in ncinputs])
        self._dates = ','.join(
            [(self.date+vdate.Time(term)).isoformat() for term in self.terms])

    def spawn_command_options(self):
        return dict(
            ncins=self._ncins,
            dates=self._dates)


class Hycom3dIBCRunHorizRegridcdf(BlindRun):

    _footprint = [
        dict(
            info="Run the initial and boundary conditions horizontal fortran interpolator",
            attr=dict(
                kind=dict(values=["hycom3d_ibc_run_horiz_regridcdf"]),
                method=dict(type=int),
                pad=dict(type=float),
            ),
        ),
    ]

    def prepare(self, rh, opts):
        super(Hycom3dIBCRunHorizRegridcdf, self).prepare(rh, opts)

        # Get specs from json
        with open("regridcdf.json") as f:
            specs = json.load(f)

        # Link to regional files
        for path in specs["links"]:
            local_path = self.system.path.basename(path)
            if not self.system.path.exists(local_path):
                self.system.symlink(path, local_path)

        # Setup args
        resfiles = specs["resfiles"]
        self.varnames = list(resfiles.keys())
        self.csteps = range(len(resfiles["ssh"]))

    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        return dict(method=self.method, **self._clargs)

    def execute(self, rh, opts):
        """We execute several times the executable with different arguments"""
        for varname in ["ssh", "saln", "temp"]:
            for cstep in self.csteps:
                self._clargs = dict(varname=varname, cstep=cstep)
                super(Hycom3dIBCRunHorizRegridcdf, self).execute(rh, opts)


class Hycom3dIBCRunVerticalInicon(BlindRun):
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
                kind=dict(values=["hycom3d_ibc_run_vert_inicon"]),
                sshmin=dict(),
                cmoy=dict()
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_ibc_run_vert_inicon"

    def prepare(self, rh, opts):
        super(Hycom3dIBCRunVerticalInicon, self).prepare(rh, opts)

        # Get specs from json
        with open("inicon.json") as f:
            self._specs = json.load(f)

        # Link to regional files
        for path in self._specs["links"]:
            local_path = self.system.path.basename(path)
            if not self.system.path.exists(local_path):
                self.system.symlink(path, local_path)

    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        return dict(
            datadir="./",
            sshfile="ssh_hyc.cdf",
            tempfile="temp_hyc.cdf",
            salnfile="saln_hyc.cdf",
            nx=self._specs["nx"],
            ny=self._specs["ny"],
            nz=self._specs["nz"],
            sshmin=str(self.sshmin),
            cmoy=str(self.cmoy),
            cstep="0")


# %% River preprocessing steps

class Hycom3dRiversFlowRate(Expresso):

    _footprint = [
        date_deco,
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
                    type=list,
                ),
            ),
        ),
    ]

    def prepare(self, rh, opts):
        super(Hycom3dRiversFlowRate, self).prepare(rh, opts)

        gettarfile = self.context.sequence.effective_inputs(
            role=["Input"])
        if len(gettarfile) == 0:
            raise AlgoComponentError(
                "No tar file available for rivers data"
            )
        self._tarname = [sec.rh.container.localpath() for sec in
                         gettarfile][0]
        self._dates = [(self.date+vdate.Time(term)) for term in self.terms]

    def spawn_command_options(self):
        return dict(
            rank=self.rank,
            tarfile=self._tarname,
            dates=",".join([date.isoformat() for date in self._dates])
            )


# %% Atmospheric forcing preprocessing steps


class Hycom3dAtmFrcTime(Expresso):

    _footprint = [
        date_deco,
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
            ),
        ),
    ]

    def prepare(self, rh, opts):
        super(Hycom3dAtmFrcTime, self).prepare(rh, opts)

        # Input insta files
        insta_rhs = [sec.rh for sec in
                     self.context.sequence.effective_inputs(role="InputInsta")]
        insta_rhs.sort(key=lambda rh: (rh.resource.date, rh.resource.term))
        self._insta_files = [rh.container.localpath() for rh in insta_rhs]

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
            self.date+vdate.Time(term) for term in self.terms]

    def spawn_command_options(self):
        return dict(
            ncins_insta=','.join(self._insta_files),
            ncins_cumul=','.join([
                "+".join(fterms) for fterms in self._cumul_files.values()]),
            dates=','.join([
                date.isoformat() for date in self._interp_dates]),
            )


#%% Spectral nudging
class Hycom3dSpectralNudgingRunDemerliac(BlindRun):
    """
    Demerliac filtering over Hycom3d outputs
    """
    _footprint = [
        dict(
            info="Run the demerliac filtering over Hycom3d outputs",
            attr=dict(
                kind=dict(
                    values=["hycom3d_spnudge_demerliac"],
                ),
                rank=dict(
                    default=0,
                    type=int,
                    optional=True,
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_spnudge_demerliac"

    def prepare(self, rh, opts):
        super(Hycom3dSpectralNudgingRunDemerliac, self).prepare(rh, opts)

        # Input netcdf file
        ncfiles = [ei.rh.container.localpath() for ei in
                   self.context.sequence.effective_inputs(role="Input")]

        # Constant files
        for cfile in (f"FORCING{self.rank}./regional.grid.a",
                      f"FORCING{self.rank}./regional.grid.b",
                      f"FORCING{self.rank}./regional.depth.a",
                      f"PARAMETERS{self.rank}./blkdat.input",
                      f"PARAMETERS{self.rank}./blkdat_cmo.input"):
            if not self.system.path.exists(self.system.path.basename(cfile)):
                self.system.symlink(cfile, self.system.path.basename(cfile))

        from sloop.models.hycom3d.spnudge import Demerliac
        date_demerliac = Demerliac().time_sel(ncfiles=ncfiles)
        self._clargs = dict(
            date=date_demerliac,
            output_type=0)

    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        return dict(**self._clargs)

    def execute(self, rh, opts):
        """We execute several times the executable with different inputs"""
        for varname in ["h", "saln", "temp"]:
            self.system.symlink(f"{varname}_3D.nc", "input.nc")
            super(Hycom3dSpectralNudgingRunDemerliac, self).execute(rh, opts)
            self.system.rm("input.nc")
            self.system.mv("output.nc", f"{varname}-demerliac.nc")


class Hycom3dSpectralNudgingRunSpectral(BlindRun):
    """
    Spectral filtering over Hycom3d and Mercator outputs
    """
    _footprint = [
        dict(
            info="Run the spectral filtering over Hycom3d outputs",
            attr=dict(
                kind=dict(
                    values=["hycom3d_spnudge_spectral"],
                ),
                rank=dict(
                    default=0,
                    type=int,
                    optional=True,
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_spnudge_spectral"

    def prepare(self, rh, opts):
        super(Hycom3dSpectralNudgingRunSpectral, self).prepare(rh, opts)

        # Input netcdf file
        ncfiles = [ei.rh.container.localpath() for ei in
                   self.context.sequence.effective_inputs(role="Input_nest")]

        # Constant files
        for cfile in (f"FORCING{self.rank}./regional.grid.a",
                      f"FORCING{self.rank}./regional.grid.b",
                      f"FORCING{self.rank}./regional.depth.a",
                      f"PARAMETERS{self.rank}./blkdat.input",
                      f"PARAMETERS{self.rank}./blkdat_cmo.input"):
            if not self.system.path.exists(self.system.path.basename(cfile)):
                self.system.symlink(cfile, self.system.path.basename(cfile))

        import xarray as xr
        ds = xr.open_dataset("h-demerliac.nc")
        Spectral().extract_mercator(ds.time)

        import json
        with open(f"PARAMETERS{self.rank}./spnudging_parameters.json", "r") as json_file:
            self._clargs = json.load(json_file)

    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        return dict(**self._clargs)

    def postfix(self, rh, opts):
        super(Hycom3dSpectralNudgingRunSpectral, self).postfix(rh, opts)
        from sloop.models.hycom3d.io import nc2hycom
        for varname in ["h", "saln", "temp"]:
            ncout = Spectral.diff(varname,
                                  f'{varname}-nest_timesel_filtered.nc',
                                  f'{varname}-demerliac_filtered.nc')
            nc2hycom(varname, ncout, f"differences {varname}: Hycom-Mercator")

    def execute(self, rh, opts):
        """We execute several times the executable with different inputs"""

        for varname in ["h", "saln", "temp"]:
            for source in ['demerliac', 'nest_timesel']:
                self.system.symlink(f"{varname}-{source}.nc", "input.nc")
                super(Hycom3dSpectralNudgingRunSpectral, self).execute(rh, opts)
                self.system.rm("input.nc")
                self.system.mv("output.nc", f"{varname}-{source}_filtered.nc")


# %% Model run

class Hycom3dModelRun(Parallel):

    _footprint = [
        dict(
            info="Run the model",
            attr=dict(
                binary=dict(
                    values=["hycom3d_model_runner"],
                ),
                rank=dict(
                    default=0,
                    type=int,
                    optional=True,
                ),
                restart=dict(
                    default=False,
                    type=bool,
                ),
                delday=dict(
                    default=1,
                    type=int,
                ),
                mode=dict(
                    values=["spinup", "forecast",
                            "spnudge_free", "spnudge_relax"],
                    default="spinup",
                    type=str,
                ),
                env_config=dict(
                    info="Environment variables and options for running the model",
                    optional=True,
                    type=dict,
                    default={},
                ),
                env_context=dict(
                    info="hycom3d context",
                    values=["prepost", "model"]
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_model_run"

    def prepare(self, rh, opts):

        super(Parallel, self).prepare(rh, opts)
        from sloop.models.hycom3d import (
            HYCOM3D_RUN_INPUT_TPL_FILE,
            HYCOM3D_BLKDAT_CMO_INPUT_FILE,
            HYCOM3D_BLKDAT_CMO_INPUT_FILES,
            HYCOM3D_SAVEFIELD_INPUT_FILE,
            HYCOM3D_SAVEFIELD_INPUT_FILES
        )
        from string import Template
        from sloop.io import concat_ascii_files

        tpl_runinput = HYCOM3D_RUN_INPUT_TPL_FILE.format(rank=self.rank)
        rpl = dict(
            lsave=1 if self.restart else 0,
            delday=self.delday,
        )
        with open(tpl_runinput, 'r') as tpl, open(tpl_runinput[:-4], 'w') as f:
                s = Template(tpl.read())
                f.write(s.substitute(rpl))

        self.system.cp(HYCOM3D_BLKDAT_CMO_INPUT_FILES[self.mode].format(rank=self.rank),
                       HYCOM3D_BLKDAT_CMO_INPUT_FILE.format(rank=self.rank),
                       intent='inout')

        concat_ascii_files([fin.format(rank=self.rank) for fin in HYCOM3D_SAVEFIELD_INPUT_FILES[self.mode]],
                           HYCOM3D_SAVEFIELD_INPUT_FILE.format(rank=self.rank))
        self._env_vars = config_to_env_vars(self.env_config)

    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        return dict(
            datadir    = "./",
            tmpdir     = "./",
            localdir   = "./",
            rank       = self.rank,
        )

    def execute(self, rh, opts):
        opts = dict(mpiopts=dict(np=381))
        with self.env as e:
            e.update(self._env_vars)
            super(Hycom3dModelRun, self).execute(rh, opts)
