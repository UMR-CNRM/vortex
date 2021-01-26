#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr  4 17:32:49 2019 by sraynaud
"""

from collections import defaultdict
from functools import partial
import json

import vortex.tools.date as vdate
from vortex.syntax.stdattrs import date_deco
from vortex.layout.dataflow import Section
from vortex.algo.components import (
    Expresso, AlgoComponent, AlgoComponentError, BlindRun, Parallel)

from ..util.env import config_to_env_vars, stripout_conda_env

from sloop.io import nc_get_time
from sloop.models.hycom3d import (
    HYCOM3D_MASK_FILE,
    HYCOM3D_GRID_AFILE,
)

from sloop.models.hycom3d.io import (
    read_regional_grid,
    run_bin2hycom,
    rest_head
)
from sloop.models.hycom3d.atmfrc import AtmFrc
from sloop.models.hycom3d.rivers import Rivers


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
                ncout=dict(
                    default="forecast.nc",
                    optional=True,
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
            ncins=self._ncins, ncout=self.ncout,
            dates=self._dates, rank=self.rank)


class Hycom3dIBCRunHorizRegridcdf(BlindRun):

    _footprint = [
        dict(
            info="Run the initial and boundary conditions horizontal fortran interpolator",
            attr=dict(
                kind=dict(
                    values=["hycom3d_ibc_run_horiz_regridcdf"],
                ),
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
            self._restart_time = nc_get_time(ncfiles[0])[0].data

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
        from sloop.models.hycom3d.io import read_blkdat_input
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

        run_bin2hycom(self._nx, self._ny, self._nz)

    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        return dict(**self._clargs)


# %% River preprocessing steps

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
            role=["Input"])
        if len(gettarfile) == 0:
            raise AlgoComponentError(
                "No tar file available for rivers data"
            )
        self.tarname = [sec.rh.container.localpath() for sec in
                            gettarfile][0]

    def execute(self, rh, opts):
        super(Hycom3dRiversFlowRate, self).execute(rh, opts)

        time = [self.rundate+vdate.Time(term) for term in self.terms]
        Rivers().write_flowrate(self.tarname, time, self.nc_out)

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
        Rivers().write_tempsaln(self.nc_in, self.nc_out)

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
        Rivers().write_ncfiles(self.nc_in)

    @property
    def realkind(self):
        return 'RiversOut'


# %% Atmospheric forcing preprocessing steps


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
                netw_ana=dict(
                    type=list,
                ),
            ),
        ),
    ]

    @property
    def _sorted_inputs(self):
        """Build a dictionary containing a list of sections for each
        cumul/term/origin"""

        insec = self.context.sequence.effective_inputs(
            role='Input')
        outsec = defaultdict(partial(defaultdict, partial(defaultdict, Section)))
        for sec in insec:
            real_term = sec.rh.resource.date.time() + sec.rh.resource.term
            outsec[sec.rh.resource.cumul][real_term][sec.rh.resource.origin] = sec
        return outsec

    def prepare(self, rh, opts):
        super(Hycom3dAtmFrcTime, self).prepare(rh, opts)

        self.insta = []
        self.cumul = defaultdict(partial(list))
        for cumul, cumul_d in self._sorted_inputs.items():
            for term, term_d in cumul_d.items():
                if "ana" in term_d.keys():
                    origin = "ana"
                else:
                    origin = "fcst"
                sec = term_d[origin]
                sec_path = sec.rh.container.localpath()
                if cumul=='insta':
                    self.insta.append(sec_path)
                else:
                    self.cumul[sec.rh.resource.date.ymdh].append(sec_path)
        print(self.insta)
        print(self.cumul)

    def execute(self, rh, opts):
        super(Hycom3dAtmFrcTime, self).execute(rh, opts)

        time = [self.rundate+vdate.Time(term) for term in self.terms]
        AtmFrc(self.insta,
               self.cumul,
               ).interp_time(time, self.nc_out)

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
        AtmFrc.parameters(self.nc_in, self.nc_out)

    @property
    def realkind(self):
        return 'AtmFrcParam'


class Hycom3dAtmFrcMask(AlgoComponent):

    _footprint = [
        dict(
            info="Create the land/sea mask and add correction to parameters",
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
                rank=dict(
                    default=0,
                    type=int,
                    optional=True,
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
        AtmFrc.regridmask(HYCOM3D_MASK_FILE.format(rank=self.rank),
                          self.nc_in, self.nc_out, self._weightsfile)

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
                rank=dict(
                    default=0,
                    type=int,
                    optional=True,
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
        hycom_grid = read_regional_grid(HYCOM3D_GRID_AFILE.format(rank=self.rank),
                                        grid_loc='p')
        AtmFrc.regridvar(self.nc_in, self.nc_out, hycom_grid, self._weightsfile)

    @property
    def realkind(self):
        return 'AtmFrcSpace'


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
                    default="atmfrc.space.nc",
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
        AtmFrc.outgen(self.nc_in, freq=self.freq)

    @property
    def realkind(self):
        return 'AtmFrcOut'

# %% Model run

class Hycom3dModelRun(Parallel):

    _footprint = [
        dict(
            info="Run the model",
            attr=dict(
                binary=dict(
                    values=["hycom3d_model_run"],
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
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_model_run"

    def prepare(self, rh, opts):
        super(Hycom3dModelRun, self).prepare(rh, opts)

        from string import Template
        tpl_runinput = 'FORCING{self.rank}./run.input.tpl'.format(**locals())
        rpl = dict(
            lsave=1 if self.restart else 0,
            delday=self.delday,
        )
        with open(tpl_runinput, 'r') as tpl, open(tpl_runinput[:-4], 'w') as f:
                s = Template(tpl.read())
                f.write(s.substitute(rpl))

    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        return dict(**self._clargs)

    def execute(self, rh, opts):
        """Model execution"""
        self._clargs = dict(
            datadir    = "./",
            tmpdir     = "./",
            localdir   = "./",
            rank       = self.rank,
        )
        super(Hycom3dModelRun, self).execute(rh, opts)
