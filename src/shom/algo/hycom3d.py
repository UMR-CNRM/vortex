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
    Expresso, AlgoComponent, AlgoComponentError)

import xarray as xr, numpy as np

from sloop.times import convert_to_julian_day
from sloop.filters import erode_coast, erode_coast_vec
from sloop.interp import interp_time, Regridder
from sloop.models.hycom3d import (
    HYCOM3D_MODEL_DIMENSIONSH_TEMPLATE,
    HYCOM3D_SIGMA_TO_STMT_FNS,
    HYCOM3D_MASK_FILE,
    HYCOM3D_GRID_AFILE, HYCOM3D_GRID_BFILE,
    check_grid_dimensions,
    setup_stmt_fns,
    read_regional_grid,
    AtmFrc,
    Rivers,
    read_inicfg_files,
)
from sloop.phys import (windstress, radiativeflux, celsius2kelvin,
                        watervapormixingratio)

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
            compilation_script=dict(
                info="Shell script that makes the compilation.",
                optional=False,
                # default = HYCOM_IBC_COMPILE_SCRIPT,
            ),
            env_vars=dict(
                info="Environment variables and options for compilation",
                option=True,
                type=dict,
                default={},
            ),
        ),
    )

    def valid_executable(self, rh):
        return True

    def prepare(self, rh, kw):
        super(Hycom3dCompilator, self).prepare(rh, kw)
        self.env["HPC_TARGET"] = self.env["RD_HPC_TARGET"]

    def execute(self, rh, kw):
        # super(Hycom3dCompilator, self).execute(rh, kw)
        for name, value in self.env_vars.items():
            self.env[name.upper()]=value
        print(self.spawn([self.compilation_script], {"outsplit": False}))

    @property
    def realkind(self):
        # return self.__class__.__name__.lower()
        return "hycom3d_compilator"


class Hycom3dIBCCompilator(Hycom3dCompilator):
    _footprint = dict(
        info="Compile IBC executables",
        attr=dict(
            #            kind=dict(values=['hycom3d_ibc_compilator']),
            sigma=dict(
                info="sigma value",
                optional=False,
                values=list(HYCOM3D_SIGMA_TO_STMT_FNS.keys()),
            ),
        ),
    )

    def prepare(self, rh, kw):
        super(Hycom3dCompilator, self).prepare(rh, kw)

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
        print(self.env_vars)
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


# class Hycom3dIBCRegridcdfCompilator(Hycom3dCompilator):

#     _footprint = dict(
#         info = 'Compile regridcdf',
#         attr = dict(
#             compilation_script = dict(
#                 info   = 'Shell script that makes the compilation.',
#                 optional = False,
#                 #default = HYCOM_IBC_COMPILE_SCRIPT,
#             ),
#         )
#     )

#     def valid_executable(self, rh):
#         return True

#     def prepare(self, rh, kw):
#         super(Hycom3dIBCIniconCompilator, self).prepare(rh, kw)
#         self.env['HPC_TARGET'] = self.env['RD_HPC_TARGET']
#         Expresso.prepare(self, rh, kw)

#     def execute(self, rh, kw):
#         super(Hycom3dIBCIniconCompilator, self).execute(rh, kw)
#         print('\n'.join(self.system.spawn(
#                 self.compilation_script, output=True, stdin=True, fatal=True)))


# %%


class Hycom3dIBCRunTime(AlgoComponent):
    _footprint = [
        #        dateperiod_deco,
        dict(
            info="Run the initial and boundary conditions time interpolator",
            attr=dict(
                kind=dict(values=["hycom3d_ibc_run_time"]),
                ncpat_out=dict(optional=True, default="ibc.time-%Y%m%dT%H%M.nc"),
                dates=dict(type=list),
            ),
        ),
    ]

    def prepare(self, rh, opts):
        super(Hycom3dIBCRunTime, self).prepare(rh, opts)

        # Input netcdf files
        ncibcsecs = self.context.sequence.effective_inputs(role="IBCForecast")
        print(ncibcsecs)
        if len(ncibcsecs) == 0:
            raise AlgoComponentError(
                "No forecast file available to create"
                " initial  and boundary conditions"
            )
        self._ncfiles = [sec.rh.container.localpath() for sec in ncibcsecs]
        print("ncfiles", self._ncfiles)

    def execute(self, rh, opts):
        super(Hycom3dIBCRunTime, self).execute(rh, opts)

        # Open all
        # dss = xr.open_mfdataset(self._ncfiles)
        dss = [xr.open_dataset(ncfile, chunks={}) for ncfile in self._ncfiles]
        dss = xr.concat(
            dss, "time", compat="no_conflicts", coords="different", data_vars="all"
        )

        # Interpolate and save
        interp_time(dss, self.dates, ncpat=self.ncpat_out)


class Hycom3dIBCRunHor(AlgoComponent):
    _footprint = [
        dateperiod_deco,
        dict(
            info="Run the initial and boundary conditions horizontal interpolator",
            attr=dict(
                ncpat_in=dict(optional=True, default="ibc.time*.nc"),
                nc_out=dict(optional=True, default="ibc.horiz.nc"),
            ),
        ),
    ]

    def prepare(self, rh, opts):
        super(Hycom3dIBCRunTime, self).prepare(rh, opts)

        # Input netcdf files
        ncibcsecs = self.context.sequence.effective_inputs(role="IBCForecastTime")
        print(ncibcsecs)
        if len(ncibcsecs) == 0:
            raise AlgoComponentError(
                "No forecast file available to create"
                " initial  and boundary conditions"
            )
        self._ncfiles = [sec.rh.container.localpath() for sec in ncibcsecs]
        print("ncfiles", self._ncfiles)

    @property
    def realkind(self):
        return "hycom3d_ibc_run_hor"


# class Hycom3dIBCInterpVer(BlindRun):
#    """
#
#    Inputs:
#
#    ${repmod}/regional.depth.a
#    ${repmod}/regional.grid.a
#    ${repparam}/ports.input
#    ${repparam}/blkdat.input
#    ${repparam}/defstrech.input
#
#    Exe:
#    ${repbin}/inicon $repdatahorgrille ssh_hyc.cdf temp_hyc.cdf saln_hyc.cdf "$idm" "$jdm" "$kdm" "$CMOY" "$SSHMIN"
#    """
#
#    _footprint = [
#        dict(
#            info="Run the in/output boundary and initial conditions interpolator",
#            attr=dict(
#                gvar=dict(default="master_inicon"),
#                kind=dict(values=['inicon']),
#                ncfile_ssh = dict(
#                        optional = True,
#                        default = 'ssh_hyc.cdf',
#                        info = "The SSH netcdf file name",
#                        ),
#                ncfile_ssh = dict(
#                        optional = True,
#                        default = 'ssh_hyc.cdf',
#                        info = "The SSH netcdf file name",
#                        ),
#                ncfile_ssh = dict(
#                        optional = True,
#                        default = 'ssh_hyc.cdf',
#                        info = "The SSH netcdf file name",
#                        ),
#            )
#
#        )]
#
#    @property
#    def realkind(self):
#        return 'inicon con conlkagzeh'

# self.context.sequence.effective_inputs(role='Namelist')


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
                dates=dict(type=list),
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
        
        for river in self.rivers.keys():
            for platform in self.rivers[river]['platform']['Id']:
                ds = interp_time(self.platforms[platform]['dataset'],
                                 self.dates,
                                 time_name='time',
                                 flag=True)
                ds.update({'RVFL': ds['RVFL']*self.rivers[river]['platform'][platform]['debcoef']})
                ds.update({'flag': ds['flag']/len(self.rivers[river]['platform']['Id'])})
                if self.rivers[river]['dataset']:
                    self.rivers[river]['dataset'] += ds
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
                dates=dict(type=list),
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
                Tmax = []
                tmax = vdate.Date(str(ds_river.time.values[0])[:4]+
                                  rivers[river][var]['datemax'])
                Tmax.extend([tmax]*len(self.dates))
                DeltaT = np.asarray(Tmax) - np.asarray(self.dates)
                for ite in range(len(DeltaT)):
                    DeltaT[ite] = DeltaT[ite].export_dict()
                    DeltaT[ite] = float(DeltaT[ite][0])+float(DeltaT[ite][1])/86400.
                VAR = rivers[river][var]['avg']+rivers[river][var]['amp']*const*DeltaT
                xa = xr.DataArray(VAR, coords=[ds_river.time], dims=["time"], name=var)
                ds_river = xr.merge([ds_river,xa])  
            ds_river = convert_to_julian_day(ds_river)
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
                dates=dict(type=list),
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
                dates=dict(type=list),
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
        self.cumul = interp_time(self.cumul, 
                                 self.dates, 
                                 time_name='time')
        self.insta = interp_time(self.insta, 
                                 self.dates,
                                 time_name='time')
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
        ds = convert_to_julian_day(ds)
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
                dates=dict(type=list),
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
                dates=dict(type=list),
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
