#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Apr  4 17:32:49 2019 by sraynaud
"""
import os
import tarfile

from bronx.stdtypes.date import daterange, Period, daterangex, Date
from vortex.syntax.stdattrs import dateperiod_deco
import vortex.tools.date as vdate

from vortex.algo.components import (
    Expresso, AlgoComponent, AlgoComponentError, BlindRun)

import xarray as xr, numpy as np, pandas as pd

from sloop.times import convert_to_julian_day, running_time
from sloop.filters import erode_coast, erode_coast_vec
from sloop.interp import nc_interp_at_freq_to_nc, Regridder, interp_time
from sloop.models.hycom3d import (
    HYCOM3D_MODEL_DIMENSIONSH_TEMPLATE,
    HYCOM3D_SIGMA_TO_STMT_FNS,
    HYCOM3D_MASK_FILE,
    HYCOM3D_GRID_AFILE,
    check_grid_dimensions,
    setup_stmt_fns,
    HYCOM3D_SIGMA_TO_STMT_FNS,
    format_ds,
    read_regional_grid,
    AtmFrc,
    Rivers
)
from sloop.phys import (windstress, radiativeflux, celsius2kelvin,
                        watervapormixingratio)

from ..util.config import config_to_env_vars

import sys
__all__ = []
# from vortex.data.executables import Script
# from gco.syntax.stdattrs import gvar

# from hycomvortex import (HYCOM_IBC_COMPILE_SCRIPT)


# %% Compilation


class Hycom3dCompilator(Expresso):

    _footprint = dict(
        info="Compile inicon",
        attr=dict(
            kind=dict(values=["hycom_3d_compilator"]),
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
            env_context=dict(info="hycom3d context",
                             values=["prepost", "model"])
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
            kind=dict(values=['hycom3d_ibc_compilator']),
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
                info="Dictionary of the model dimensions", optional=False, type=dict,
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
                kind=dict(values=["hycom3d_ibc_run_time"]),
                # ncfmt_out=dict(optional=True, default="ibc.time-%Y%m%dT%H%M.nc"),
                rank=dict(default=0, type=int, optional=True)
            ),
        ),
    ]

    def prepare(self, rh, opts):
        super(Hycom3dIBCRunTime, self).prepare(rh, opts)

        # Input netcdf files
        ncinputs = self.context.sequence.effective_inputs(role="ibc_input")
        self._ncfiles = [sec.rh.container.localpath() for sec in ncinputs]

        # Read hycom grid extents
        from sloop.models.hycom3d import read_regional_grid_b
        from sloop.grid import GeoSelector
        rg = read_regional_grid_b(f"PARAMATERS{self.rank}./regional.grid.b")
        self._geo_selector = GeoSelector(lon=(rg["plon_min"], rg["plon_max"]),
                                         lat=(rg["plat_min"], rg["plat_max"]),
                                         pad=self.conf.ibc_pad)

    def execute(self, rh, opts):
        super(Hycom3dIBCRunTime, self).execute(rh, opts)

        from sloop.interp import nc_interp_at_freq_to_nc
        # Interpolate in time
        nc_interp_at_freq_to_nc(
            self._ncfiles, self.freq, ncfmt=self.ncfmt_out,
            preproc=self._geo_selector, postproc=format_ds)


class Hycom3dIBCRunHoriz(BlindRun):
    _footprint = [
        dateperiod_deco,
        dict(
            info="Run the initial and boundary conditions horizontal interpolator",
            attr=dict(
                nc_out=dict(optional=True, default="ibc.horiz.nc"),
                rank=dict(default=0, type=int, optional=True),
                method=dict(default=0, type=int, optional=True),
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
            role="ibc_horiz")[0].rh.container.localpath()

        # Conversion .res files
        from sloop.io import nc_to_res
        resfiles = nc_to_res(
            [ncinput], outfile_pattern='{var_name}.res{ifile:03d}')
        self.varnames = list(resfiles.keys())
        self.csteps = range(1, len(resfiles[self.varnames[0]])+1)

        # Constant files
        cdir = f"PARAMATERS{self.rank}."
        for cfile in "regional.grid.a", "regional.grid.b", "regional.depth.a":
            if not os.path.exists(cfile):
                os.symlink(os.path.join(cdir, cfile), cfile)

    def spawn_command_options(self):
        """Prepare options for the resource's command line."""
        return dict(method=self.method, **self._clargs)

    def execute(self, rh, opts):
        """We execute several times the executable with different arguments"""
        for varname in self.varnames:
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

    @property
    def realkind(self):
        return "hycom3d_ibc_run_vertical"

    def prepare(self, rh, opts):
        super(Hycom3dIBCRunVertical, self).prepare(rh, opts)

        # Input netcdf file
        ncfiles = [ei.rh.container.localpath() for ei in
                   self.context.sequence.effective_inputs(role="ibc_vert")]

        # Constant files
        for cfile in (f"FORCING{self.rank}./regional.grid.a",
                      f"FORCING{self.rank}./regional.grid.b",
                      f"FORCING{self.rank}./regional.depth.a",
                      f"PARAMETERS{self.rank}./blkdat.input",
                      f"PARAMETERS{self.rank}./defstrech.input",
                      f"PARAMETERS{self.rank}./ports.input"):
            if not os.path.exists(cfile):
                os.symlink(cfile, os.path.basename(cfile))

        # Read dimensions
        from sloop.models.hycom3d import read_blkdat_input
        dsb = read_blkdat_input("blkdat.input")

        # Command line arguments
        self._clargs = dict(sshfile=ncfiles[0],
                            tempfile=ncfiles[1],
                            salnfile=ncfiles[2],
                            nx=dsb.idm,
                            ny=dsb.jdm,
                            nz=dsb.kdm,
                            cmoy=self.conf.cmoy,
                            sshmin=self.conf.sshmin,
                            cstep=1)

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
                kind=dict(values=["RiversFlowRate"]),
                nc_out=dict(optional=True, default="{river}.flx.nc"),
                begindate=dict(type=str),
                maxterm=dict(type=str),
                step=dict(type=str),
                engine=dict(values=["current" ], default="current"),
            ),
        ),
    ]

    def prepare(self, rh, opts):
        super(Hycom3dRiversFlowRate, self).prepare(rh, opts)

        gettarfile = self.context.sequence.effective_inputs(
            role=["GetTarFile"])
        if len(gettarfile) == 0:
            raise AlgoComponentError(
                "No tar file available for rivers data"
            )
        tarname = [sec.rh.container.localpath() for sec in
                            gettarfile][0]

        self.rivers, self.platforms = Rivers(tarname=tarname).platforms_nc2datasets()

    def execute(self, rh, opts):
        super(Hycom3dRiversFlowRate, self).execute(rh, opts)

        time = running_time(start=self.begindate,
                            maxterm=self.maxterm,
                            step=self.step)
        for river in self.rivers.keys():
            for platform in self.rivers[river]['platform']['Id']:
                ds = interp_time(self.platforms[platform]['dataset'],
                                 time, keep_flag=True)
                ds.update({'RVFL': ds['RVFL']*self.rivers[river]['platform'][platform]['debcoef']})
                ds.update({'flag': ds['flag']/len(self.rivers[river]['platform']['Id'])})
                if self.rivers[river]['dataset']:
                    for var in ['RVFL','flag']:
                        self.rivers[river]['dataset'][var] += ds[var]
                else:
                    self.rivers[river]['dataset'] = ds
        for river in self.rivers.keys():
            self.rivers[river]['dataset'][['RVFL','flag']].to_netcdf(self.nc_out.format(**locals()))

    @property
    def realkind(self):
        return 'RiversFlowRate'


class Hycom3dRiversTempSaln(AlgoComponent):
    _footprint = [
        dict(
            info="Compute temperature and salinity characteristics"\
                " of rivers",
            attr=dict(
                kind=dict(values=["RiversTempSaln"]),
                nc_in=dict(optional=True, default="{river}.flx.nc"),
                nc_out=dict(optional=True, default="{river}.flx.ts.nc"),
                engine=dict(values=["current" ], default="current"),
            ),
        ),
    ]

    def execute(self, rh, opts):
        super(Hycom3dRiversTempSaln, self).execute(rh, opts)

        rivers = Rivers().rivers
        const = 2.0 * np.pi / 365.0
        for river in rivers.keys():
            ds_river = xr.open_dataset(self.nc_in.format(**locals()))
            for var in ['temperature','salinity']:
                tmax = xr.DataArray(vdate.Date(str(ds_river.time.values[0])[:4]+
                                  rivers[river][var]['datemax']),
                                    name="tmax")
                DeltaT = tmax-ds_river["time"]
                DeltaT = DeltaT.astype('float')/(86400.0*1e9)*const      
                VAR = rivers[river][var]['avg']+rivers[river][var]['amp']*DeltaT
                xa = xr.DataArray(VAR, coords=[ds_river.time], dims=["time"], name=var)
                ds_river = xr.merge([ds_river,xa])

            ds_river.to_netcdf(self.nc_out.format(**locals()))


    @property
    def realkind(self):
        return 'RiversTempSaln'


class Hycom3dRiversOut(AlgoComponent):
    _footprint = [
        dict(
            info="Create the output files for Hycom",
            attr=dict(
                kind=dict(values=["RiversOut"]),
                nc_in=dict(optional=True, default="{river}.flx.ts.nc"),
                freq=dict(optional=True, default=1),
                engine=dict(values=["current" ], default="current"),
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
                kind=dict(values=["hycom3d_time_interpolation",
                                  "AtmFrcTime"]),
                nc_out=dict(optional=True, default="atmfrc.time.nc"),
                begindate=dict(type=str),
                maxterm=dict(type=str),
                step=dict(type=str),
                engine=dict(values=["current" ], default="current"),
            ),
        ),
    ]

    def prepare(self, rh, opts):
        super(Hycom3dAtmFrcTime, self).prepare(rh, opts)
        insta=self.context.sequence.effective_inputs(
                role=["GetAtmosphericForcingInsta"])
        cumul=self.context.sequence.effective_inputs(
                role=["GetAtmosphericForcingCumul"])
        insta_files=[sec.rh.container.localpath() for sec in insta]
        cumul_files=[sec.rh.container.localpath() for sec in cumul]
        self.cumul, self.insta = AtmFrc(insta_files=insta_files,
                                        cumul_files=cumul_files,
                                        ).grib2dataset()
        
    def execute(self, rh, opts):
        super(Hycom3dAtmFrcTime, self).execute(rh, opts)

        self.cumul = AtmFrc().decumul(self.cumul)
        time = running_time(start=self.begindate,
                            maxterm=self.maxterm,
                            step=self.step)
        self.cumul = interp_time(self.cumul, time)
        self.insta = interp_time(self.insta, time)
        self.atmfrc = xr.merge([self.cumul, self.insta],
                               combine_attrs='override',
                               compat='override')
        self.atmfrc.to_netcdf(self.nc_out)
        print(self.atmfrc)

    @property
    def realkind(self):
        return 'AtmFrcTime'


class Hycom3dAtmFrcParameters(AlgoComponent):
    _footprint = [
        dict(
            info="Compute atmospheric flux parameters necessary"\
                " for a Hycom3d run",
            attr=dict(
                kind=dict(values=["AtmFrcParameters","AtmFrcParam"]),
                nc_in=dict(optional=True, default="atmfrc.time.nc"),
                nc_out=dict(optional=True, default="atmfrc.completed.nc"),
                engine=dict(values=["current" ], default="current"),
            ),
        ),
    ]

    def execute(self, rh, opts):
        super(Hycom3dAtmFrcParameters, self).execute(rh, opts)

        ds = xr.open_dataset(self.nc_in)
        ds = celsius2kelvin(ds)
        ds = windstress(ds, method='Speich')
        ds = radiativeflux(ds)
        ds = watervapormixingratio(ds)
        ds.to_netcdf(self.nc_out)

    @property
    def realkind(self):
        return 'AtmFrcParam'


class Hycom3dAtmFrcMask(AlgoComponent):
    _footprint = [
        dict(
            info="Create the land/sea mask"\
                "and add correction to parameters",
            attr=dict(
                kind=dict(values=["AtmFrcMask"]),
                nc_in=dict(optional=True, default="atmfrc.completed.nc"),
                nc_out=dict(optional=True, default="atmfrc.masked.nc"),
                engine=dict(values=["current" ], default="current"),
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
                            weightsfile]
    def execute(self, rh, opts):
        super(Hycom3dAtmFrcMask, self).execute(rh, opts)

        ds = xr.open_dataset(self.nc_in)
        mask = xr.open_dataset(HYCOM3D_MASK_FILE)
        regridder = Regridder(mask, ds, regridder=None, filename=self._weightsfile)
        ds = regridder.regrid(mask)
        ds.to_netcdf(self.nc_out)

    @property
    def realkind(self):
        return 'AtmFrcMask'


class Hycom3dAtmFrcSpace(AlgoComponent):
    _footprint = [
        dict(
            info="Run the horizontal interpolator",
            attr=dict(
                kind=dict(values=["AtmFrcSpace"]),
                nc_in=dict(optional=True, default="atmfrc.masked.nc"),
                nc_out=dict(optional=True, default="atmfrc.space.nc"),
                engine=dict(values=["current" ], default="current"),
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
                            weightsfile]


    def execute(self, rh, opts):
        super(Hycom3dAtmFrcSpace, self).execute(rh, opts)

        ds = xr.open_dataset(self.nc_in)
        kernel = {'lon': 1, 'lat': 1}
        ds = erode_coast_vec(ds, kernel, param='wind', niter=1)
        for var in ['t2m','r2','prmsl','ssr','str','tp',
                    'si10','vapmix','radflx']:
            ds[var] = ds[var].where(ds.mask==0)
            ds[var] = erode_coast(ds[var], kernel=kernel, niter=1)
        hycom_grid = read_regional_grid(HYCOM3D_GRID_AFILE, grid_loc='p')
        regridder = Regridder(ds, hycom_grid,
                                  regridder=None,
                                  filename=self._weightsfile)
        ds = regridder.regrid(ds)
        ds.to_netcdf(self.nc_out)

    @property
    def realkind(self):
        return 'AtmFrcSpace'


class Hycom3dAtmFrcFinal(AlgoComponent):
    _footprint = [
        dict(
            info="Prepare the dataset for Hycom",
            attr=dict(
                kind=dict(values=["AtmFrcFinal"]),
                nc_in=dict(optional=True, default="atmfrc.space.nc"),
                nc_out=dict(optional=True, default="atmfrc.final.nc"),
                engine=dict(values=["current" ], default="current"),                
            ),
        ),
    ]

    def execute(self, rh, opts):
        super(Hycom3dAtmFrcFinal, self).execute(rh, opts)

        ds = xr.open_dataset(self.nc_in)
        ds = AtmFrc().rename_vars(ds)
        ds.to_netcdf(self.nc_out)
        print(ds)

    @property
    def realkind(self):
        return 'AtmFrcFinal'


class Hycom3dAtmFrcOut(AlgoComponent):
    _footprint = [
        dict(
            info="Create the output files for Hycom",
            attr=dict(
                kind=dict(values=["AtmFrcOut"]),
                nc_in=dict(optional=True, default="atmfrc.final.nc"),
                freq=dict(optional=True, default=1),
                engine=dict(values=["current" ], default="current"),
            ),
        ),
    ]

    def execute(self, rh, opts):
        super(Hycom3dAtmFrcOut, self).execute(rh, opts)

        ds = xr.open_dataset(self.nc_in)
        AtmFrc().write_abfiles(ds, freq=self.freq)

    @property
    def realkind(self):
        return 'AtmFrcOut'
