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

import xarray as xr, numpy as np
import cfgrib

from sloop.times import convert_to_julian_day
from sloop.filters import erode_coast
from sloop.interp import nc_interp_at_freq_to_nc, Regridder, interp_time
from sloop.models.hycom3d import (
    HYCOM3D_MODEL_DIMENSIONSH_TEMPLATE,
    check_grid_dimensions,
    setup_stmt_fns,
    HYCOM3D_SIGMA_TO_STMT_FNS,
    format_ds,
    rename_atmfrc_vars
)
from sloop.phys import windstress, radiativeflux, celsius2kelvin
from sloop.phys import watervapormixingratio

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

        # Check dimensions
        regional_grid_basename = "FORCING0./regional.grid.a"
        check_grid_dimensions(self.dimensions, regional_grid_basename)

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

class Hycom3dRiversTime(AlgoComponent):
    _footprint = [
        dict(
            info="Get the river tar/cfg/ini files"\
                ", run the time interpolator"\
                " and compute river fluxes",
            attr=dict(
                kind=dict(values=["RiversTime"]),
                nc_out=dict(optional=True, default="{river}.flx.nc"),
                dates=dict(type=list),
                engine=dict(values=["current" ], default="current"),
            ),
        ),
    ]

    def prepare(self, rh, opts):
        super(Hycom3dRiversTime, self).prepare(rh, opts)

        tarfile = self.context.sequence.effective_inputs(
            role=["GetTarFile"])

        if len(tarfile) == 0:
            raise AlgoComponentError(
                "No tar file available for rivers data"
            )

        self.tarfile = [sec.rh.container.localpath() for sec in
                            tarfile][0]

    def execute(self, rh, opts):
        super(Hycom3dRiversTime, self).execute(rh, opts)

        from sloop.models.hycom3d import read_inicfg_files
        rivers = read_inicfg_files('FORCING0./nest/rivers.ini',
                                   'FORCING0./nest/rivers.cfg')

        tmp_tar = tarfile.open(self.tarfile,mode='r:gz')
        nc_pattern = 'GL_TS_RF_{platform}_{date.ymd}.nc'
        for river in rivers.keys():
            print(river)
            ds_platforms = []
            for platform in rivers[river]['platform']['Id']:
                print(platform)
                ds = []
                for date in daterangex((Date(self.dates[0].ymd)-Period('P14D')).ymd, self.dates[-1].ymd, 'P1D'):
                    nc_file = nc_pattern.format(**locals())
                    nc_dir = os.path.join(date.ymd,nc_file)
                    try:
                        tmp_tar.extract(nc_dir)#, path=self.tarfile)
                    except:
                        print('No data available the '+str(date.ymd))
                    else:
                        #nc_dir = os.path.join(nc_dir)
                        dataset = xr.open_dataset(nc_dir)
                        dataset['LONGITUDE'] = dataset.LONGITUDE.swap_dims({'LONGITUDE':'TIME'})
                        dataset['LATITUDE'] = dataset.LATITUDE.swap_dims({'LATITUDE':'TIME'})
                        dataset = dataset.squeeze()
                        ds = xr.combine_nested(
                                        [ds,dataset['RVFL'].to_dataset(name='RVFL')],
                                        concat_dim='TIME',
                                        combine_attrs='override',
                                        )
                ds = ds.swap_dims({'TIME':'time'})
                ds = ds.rename({'TIME':'time','LONGITUDE':'lon','LATITUDE':'lat'})
                ds['time'] = np.asarray( ds.time , dtype='M8')
                ds = interp_time(ds, self.dates, time_name = 'time')
                ds *= rivers[river]['platform'][platform]['debcoef']
                ds_platforms.append(ds)

            for iplatform in range(len(ds_platforms)):
                if iplatform == 0:
                    ds_river = ds_platforms[iplatform]
                else:
                    ds_river = ds_river + ds_platforms[iplatform]
            ds_river['flag'] /= len(ds_platforms)

            ds_river.to_netcdf(self.nc_out.format(**locals()))
            print(ds_river)
        tmp_tar.close()

    @property
    def realkind(self):
        return 'RiversTime'


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

        from sloop.models.hycom3d import read_inicfg_files
        rivers = read_inicfg_files('FORCING0./nest/rivers.ini',
                                   'FORCING0./nest/rivers.cfg')

        cste = 2.0 * np.pi / 365.0
        for river in rivers.keys():
            print(river)
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
                VAR = rivers[river][var]['avg'] + rivers[river][var]['amp'] * cste * DeltaT
                xa = xr.DataArray(VAR, coords=[ds_river.time], dims=["time"], name=var)
                ds_river = xr.merge([ds_river,xa])
            julianday = (ds_river.time.data - np.datetime64("1950-01-01")) / np.timedelta64(1, "D")
            xa = xr.DataArray(julianday, coords=[ds_river.time], dims=["time"], name='julianday')
            ds_river = xr.merge([ds_river,xa])
            ds_river.to_netcdf(self.nc_out.format(**locals()))
            print(ds_river)

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

        from sloop.models.hycom3d import write_river_rfiles
        write_river_rfiles(self.nc_in, 'FORCING0./nest/rivers.ini',
                                       'FORCING0./nest/rivers.cfg')

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
        self.insta=[sec.rh.container.localpath() for sec in insta]
        self.cumul=[sec.rh.container.localpath() for sec in cumul]

    def execute(self, rh, opts):
        super(Hycom3dAtmFrcTime, self).execute(rh, opts)

        ds_cumul = []
        for data in self.cumul:
            ds = xr.open_dataset(data, engine='cfgrib',
                              backend_kwargs={"indexpath": ""} )
            ds_cumul.append(ds)

        ds_cumul = xr.combine_nested(ds_cumul,
                            concat_dim='valid_time',
                            combine_attrs='override')

        ds_insta = []
        for data in self.insta:
            ds = []
            for level in [0,2,10]:
                ds.append(cfgrib.open_dataset(data,
                                      backend_kwargs={'indexpath': '',
                                      'filter_by_keys':{'edition':2,
                                                       'level':level}},
                                      drop_variables=['heightAboveGround',
                                                      'meanSea',
                                                      'surface']
                                      ))
            ds_insta.append(xr.merge(ds,combine_attrs='override'))

        ds_insta = xr.combine_nested(ds_insta,
                            concat_dim='valid_time',
                            combine_attrs='override')

        ds_insta = ds_insta.drop(['step','time'])
        ds_cumul = ds_cumul.drop(['step','time'])
        ds_insta = ds_insta.rename({'longitude':'lon',
                                'latitude':'lat',
                                'valid_time':'time'})
        ds_cumul = ds_cumul.rename({'longitude':'lon',
                            'latitude':'lat',
                            'valid_time':'time'})

        time_step = ds_cumul.time.diff('time').data[0]
        ds_cumul = ds_cumul.differentiate('time',1,datetime_unit='s')
        ds_cumul['time'] = ds_cumul['time'].data + time_step/2.0

        ds_cumul = interp_time(ds_cumul, self.dates, time_name='time')
        ds_insta = interp_time(ds_insta, self.dates, time_name='time')

        ds = xr.merge([ds_cumul,ds_insta], combine_attrs='override',
                      compat='override')
        ds = ds.drop('flag')
        ds.to_netcdf(self.nc_out)
        print(ds)

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
                nc_out=dict(optional=True, default="atmfrc.complete.nc"),
                engine=dict(values=["current" ], default="current"),
            ),
        ),
    ]

    def execute(self, rh, opts):
        super(Hycom3dAtmFrcParameters, self).execute(rh, opts)

        ds = xr.open_dataset(self.nc_in)
        ds = celsius2kelvin(ds)
        ds = windstress(ds,method='Speich')
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
                nc_in=dict(optional=True, default="atmfrc.complete.nc"),
                nc_out=dict(optional=True, default="atmfrc.mask.nc"),
                grid_file=dict(optional=True, default='regional.grid.b'),
                dates=dict(type=list),
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
        mask = xr.open_dataset('FORCING0./mask.nc')
        regridder = Regridder(mask,ds,regridder=None,filename=self._weightsfile)
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
                nc_in=dict(optional=True, default="atmfrc.mask.nc"),
                nc_out=dict(optional=True, default="atmfrc.space.nc"),
                grid_file=dict(optional=True, default="regional.grid.b"),
                dates=dict(type=list),
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
        tau = ( ds.taux**2 + ds.tauy**2 )**0.5
        rhocd = tau / ds.si10**2
        rhocd1 = rhocd.where(ds.mask==0)
        rhocd2 = erode_coast(rhocd1, kernel=kernel, niter=1)
        w = rhocd2/rhocd
        for var in ['taux', 'tauy']:
            ds[var] = ds[var] * w

        for var in ['t2m','r2','prmsl','ssr','str','tp',
                    'si10','vapmix','radflx']:
            ds[var] = ds[var].where(ds.mask==0)
            ds[var] = erode_coast(ds[var], kernel=kernel, niter=1)

        hycom_grid = read_regional_grid('FORCING0./regional.grid.a', grid_loc='p')
        hycom_grid = hycom_grid.rename({'plon':'lon','plat':'lat'})

        regridder = Regridder(ds, hycom_grid,
                              regridder=None,filename=self._weightsfile)
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
        ds = rename_atmfrc_vars(ds, 'FORCING0./atmfrc_param.json')
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
        write_atmfrc_abfiles(ds,freq=self.freq)

    @property
    def realkind(self):
        return 'AtmFrcOut'
