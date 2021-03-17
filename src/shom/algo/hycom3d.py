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
class Hycom3dSpectralNudgingRunPrepost(Expresso):
    """Algo component for preparing files before the demerliac filter"""

    _footprint = [
        date_deco,
        dict(
            info="Run the spectral  nudging demerliac preprocessing",
            attr=dict(
                kind=dict(
                    values=["hycom3d_spnudge_prepost"],
                ),
                rank=dict(
                    default=0,
                    type=int,
                    optional=True,
                ),
            ),
        ),
    ]

    def prepare(self, rh, opts):
        super(Hycom3dSpectralNudgingRunPrepost, self).prepare(rh, opts)

        ncinputs = self.context.sequence.effective_inputs(role=["Input"])
        self._ncins = ','.join(
            [sec.rh.container.localpath() for sec in ncinputs])

    def spawn_command_options(self):
        return dict(
            ncins=self._ncins,
            )

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

        # Get specs from json
        with open("demerliac.json") as f:
            specs = json.load(f)
            
        # Link to regional and blkdat files
        for path in specs["links"]:
            local_path = self.system.path.basename(path)
            if not self.system.path.exists(local_path):
                self.system.symlink(path, local_path)
                
        # Setup args
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
            self.system.symlink(self.ncins[varname] , "input.nc")
            super(Hycom3dSpectralNudgingRunDemerliac, self).execute(rh, opts)
            self.system.rm("input.nc")
            self.system.mv("output.nc", self.ncout_patt.format(**locals()))


class Hycom3dSpectralNudgingRunSpectralPreproc(Expresso):
    """Algo component for preparing files before the spectral filter"""

    _footprint = [
        date_deco,
        dict(
            info="Run the spectral  nudging spectral filter preprocessing",
            attr=dict(
                kind=dict(
                    values=["hycom3d_spnudge_spectral_preproc"],
                ),
                rank=dict(
                    default=0,
                    type=int,
                    optional=True,
                ),
            ),
        ),
    ]

    def prepare(self, rh, opts):
        super(Hycom3dSpectralNudgingRunSpectralPreproc, self).prepare(rh, opts)

        ncinputs_hycom3d = self.context.sequence.effective_inputs(
            role=["Input_hycom3d"])
        ncinputs_mercator = self.context.sequence.effective_inputs(
            role=["Input_mercator"])
        self._ncins_hycom3d = ','.join(
            [sec.rh.container.localpath() for sec in ncinputs_hycom3d])
        self._ncins_mercator = ','.join(
            [sec.rh.container.localpath() for sec in ncinputs_mercator])
        print(self._ncins_mercator)
        print(self._ncins_hycom3d)
    def spawn_command_options(self):
        return dict(
            nchycom3d=self._ncins_hycom3d,
            ncmercator=self._ncins_mercator,
            )
    
    
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

        # Get specs from json
        with open("spectral.json") as f:
            specs = json.load(f)
            
        # Link to regional and blkdat files
        for path in specs["links"]:
            local_path = self.system.path.basename(path)
            if not self.system.path.exists(local_path):
                self.system.symlink(path, local_path)
                
        self.varnames = list(specs["ncfiles"].keys())
        self.ncfiles = specs["ncfiles"]
        self.ncout_patt = specs["ncout_patt"]
        
        # Get command line options
        with open(specs["clargs"], "r") as f:
            self._clargs = json.load(f)
        
    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        return dict(**self._clargs)

    def execute(self, rh, opts):
        """We execute several times the executable with different inputs"""
        
        for varname in self.varnames:
            for source in list(self.ncfiles[varname].keys()):
                self.system.symlink(self.ncfiles[varname][source], "input.nc")
                super(Hycom3dSpectralNudgingRunSpectral, self).execute(rh, opts)
                self.system.rm("input.nc")
                self.system.mv("output.nc", self.ncout_patt.format(**locals()))
    
    
# %% Model run AlgoComponents


class Hycom3dModelRunPreproc(Expresso):

    _footprint = [
        date_deco,
        dict(
            info="Prepare Hycom output for postproduction",
            attr=dict(
                kind=dict(
                    values=["hycom3d_model_preproc"],
                ),
                rank=dict(
                    default=0,
                    type=int,
                    optional=True,
                ),
                restart=dict(
                    default=True,
                    type=bool,
                    optional=True,
                ),
                delday=dict(
                    default=1,
                    type=int,
                    optional=True,
                ),
                mode=dict(
                    default="forecast",
                    type=str,
                    optional=True,
                ),
            ),
        ),
    ]

    def spawn_command_options(self):
        return dict(
            rank=self.rank,
            mode=self.mode,
            delday=self.delday,
            restart=self.restart,
            )


class Hycom3dModelRun(Parallel):

    _footprint = [
        dict(
            info="Run the model",
            attr=dict(
                binary=dict(
                    values=["hycom3d_model_runner"],
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

        with open("specs.json") as f:
            specs = json.load(f)
            
        for copy in specs["copy"]:
            self.system.cp(copy[0], copy[1], intent="inout")

        self._clargs = specs["clargs"]
        self._env_vars = config_to_env_vars(self.env_config)
        self.mpiopts = specs["mpiopts"] 
        
    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        return dict(**self._clargs)

    def execute(self, rh, opts):
        opts = dict(mpiopts=self.mpiopts)
        with self.env as e:
            e.update(self._env_vars)
            super(Hycom3dModelRun, self).execute(rh, opts)



#%% Post-production run algo component

class Hycom3dPostprodPreproc(Expresso):

    _footprint = [
        date_deco,
        dict(
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
                    type=str,
                    optional=True,
                ),
                rundate=dict(
                    default=0,
                    optional=True,
                ),
            ),
        ),
    ]

    def prepare(self, rh, opts):
        super(Hycom3dPostprodPreproc, self).prepare(rh, opts)

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
    
    
class Hycom3dPostprod(BlindRun):
    """
    Post-production filter over hycom3d outputs
    """
    _footprint = [
        dict(
            info="Run the postprod filtering over Hycom3d outputs",
            attr=dict(
                kind=dict(
                    values=["hycom3d_postprod_filter",
                            "hycom3d_postprod_tempconversion"],
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_postprod"

    def prepare(self, rh, opts):
        super(Hycom3dPostprod, self).prepare(rh, opts)

        with open("specs.json") as f:
            specs = json.load(f)
        self.args = specs["clargs"]
        
    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        return dict(**self._clargs)

    def execute(self, rh, opts):
        """We execute several times the executable with different inputs"""
        
        for arg in self.args:
            self._clargs = arg
            super(Hycom3dPostprod, self).execute(rh, opts)
            
            
class Hycom3dPostprodInterpolation(BlindRun):
    """
    Post-production interpolation over hycom3d outputs
    """
    _footprint = [
        dict(
            info="Run the postprod interpolation over Hycom3d outputs",
            attr=dict(
                kind=dict(
                    values=["hycom3d_postprod_interpolation"],
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_postprod_interpolation"

    def prepare(self, rh, opts):
        super(Hycom3dPostprodInterpolation, self).prepare(rh, opts)

        with open("specs.json") as f:
            specs = json.load(f)
        
        # Link to regional and blkdat files
        for path in specs["links"]:
            local_path = self.system.path.basename(path)
            if not self.system.path.exists(local_path):
                if "traductions_noms_longs" in local_path:
                    self.system.symlink(path, "traductions_noms_longs")
                else:
                    self.system.symlink(path, local_path)
        
        self.args = specs["clargs"]
        
    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        return dict(**self._clargs)

    def execute(self, rh, opts):
        """We execute several times the executable with different inputs"""
        
        for arg in self.args:
            self._clargs = arg
            super(Hycom3dPostprodInterpolation, self).execute(rh, opts)
