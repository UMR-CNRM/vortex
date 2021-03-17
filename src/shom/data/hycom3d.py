#/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hycom3d files
"""

from gco.syntax.stdattrs import gvar
from bronx.stdtypes.date import Date

from common.data.consts import GenvModelGeoResource
from vortex.data.executables import Script, Binary, OceanographicModel
from vortex.data.resources import Resource
from vortex.data.flow import GeoFlowResource
from vortex.syntax.stddeco import namebuilding_append

__all__ = []


# %% Generic

class _Hycom3dGeoResource(GenvModelGeoResource):

    _abstract = True
    _footprint = dict(
        attr=dict(
            model=dict(
                info="The model name (from a source code perspective).",
                alias=("turtle",),
                optional=False,
                values=["hycom3d"],
                default="hycom3d",
            ),
        ),
    )


# %% Parameters

class Hycom3dConsts(_Hycom3dGeoResource):

    _footprint = dict(
        info="Hycom3d constant tar file",
        attr=dict(
            kind=dict(
                values=["hycom3d_consts"],
            ),
            gvar=dict(
                default="hycom3d_consts_tar",
            ),
            rank=dict(
                default=0,
                type=int,
                optional=True
            ),
        ),
    )

    @property
    def realkind(self):
        return "hycom3d_consts"


@namebuilding_append('src', lambda self: self.grids)
class Hycom3dAtmFrcInterpWeights(Resource):

    _footprint = [
        dict(
            info="Hycom3d atmfrc interpolation weights nc file",
            attr=dict(
                kind=dict(
                    values=["interp_weights"],
                ),
                nativefmt=dict(
                    values=['netcdf','nc'],
                ),
                grids=dict(
                    values=["a2o","o2a"],
                    optional=False,
                    default='a2o',
                ),
            ),
        )
    ]

    @property
    def realkind(self):
        return "interp_weights"


# %% Binaries

class Hycom3dIBCRegridcdfBinary(Binary):
    """Binary that regrids initial conditions netcdf files"""

    _footprint = [
        gvar,
        #        hgeometry_deco,
        dict(
            info="Binary that regrids initial conditions netcdf files",
            attr=dict(
                gvar=dict(
                    default="hycom3d_ibc_regridcdf_binary",
                ),
                kind=dict(
                    values=["horizontal_regridder"],
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_ibc_regridcdf_binary"

    def command_line(self, **opts):
        varname = opts["varname"]
        method = opts.get("method", 0)
        cstep = int(opts.get("cstep", 1))
        return f"{varname} {method} {cstep:03d}"


class Hycom3dIBCIniconBinary(Binary):
    """Binary that computes initial condictions for HYCOM"""

    _footprint = [
        gvar,
        dict(
            info="Binary that computes initial conditions for HYCOM",
            attr=dict(
                gvar=dict(default="hycom3d_ibc_inicon_binary"),
                kind=dict(values=["vertical_regridder"]),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_ibc_inicon_binary"

    def command_line(self, **opts):
        return ("{datadir} {sshfile} {tempfile} {salnfile} "
                "{nx} {ny} {nz} {cmoy} "
                "{sshmin} {cstep}").format(**opts)


class Hycom3dSpNudgeDemerliacBinary(Binary):
    """Binary that apply Demerliac filter HYCOM Spectral Nugding"""

    _footprint = [
        gvar,
        dict(
            info="Binary that apply Demerliac filter HYCOM Spectral Nugding",
            attr=dict(
                gvar=dict(
                    default="hycom3d_spnudge_demerliac_binary",
                ),
                kind=dict(
                    values=["demerliac_filter"],
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_spnudge_demerliac_binary"

    def command_line(self, **opts):
        return ("{date} {output_type}").format(**opts)


class Hycom3dSpNudgeSpectralBinary(Binary):
    """Binary that apply spectral filter HYCOM Spectral Nugding"""

    _footprint = [
        gvar,
        dict(
            info="Binary that apply spectral filter HYCOM Spectral Nugding",
            attr=dict(
                gvar=dict(
                    default="hycom3d_spnudge_spectral_binary",
                ),
                kind=dict(
                    values=["spectral_filter"],
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_spnudge_spectral_binary"

    def command_line(self, **opts):
        return ("{wave_sp} {genmask} {min_depth} {relax_sp}").format(**opts)


class Hycom3dModelBinary(OceanographicModel):
    """Binary of the 3d model"""

    _footprint = [
        gvar,
        dict(
            info="Binary of the model",
            attr= dict(
                gvar = dict(default='oceanmodel'),
            ),
        )
    ]

    def command_line(self, **opts):
        return ("{datadir} {tmpdir} {localdir} {rank}").format(**opts)


class Hycom3dPostProdFilterBinary(Binary):
    """Binary that applies filtering in time over Hycom outputs"""

    _footprint = [
        gvar,
        dict(
            info="Binary that applies filtering in time over Hycom outputs",
            attr=dict(
                gvar=dict(
                    default="hycom3d_postprod_filter_binary",
                ),
                kind=dict(
                    values=["postprod_filter"],
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_postprod_filter_binary"

    def command_line(self, **opts):
        if not "ncin_back" in list(opts.keys()):
            return ("{filter} {ncout} "
                    "{ncin_for} {ncin_mid}").format(**opts)
        else:
            return ("{filter} {ncout} "
                    "{ncin_for} {ncin_mid} {ncin_back}").format(**opts)
           

class Hycom3dPostProdVertInterpolationBinary(Binary):
    """Binary that verticaly interpolates and
    converts HYCOM output in SOAP and dataShom formats"""

    _footprint = [
        gvar,
        dict(
            info="Binary that verticaly interpolates",
            attr=dict(
                gvar=dict(
                    default="hycom3d_postprod_vertinterpolation_binary",
                ),
                kind=dict(
                    values=["postprod_vertinterpolation"],
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_postprod_vertinterpolation_binary"

    def command_line(self, **opts):
        if not "zgrid" in list(opts.keys()):
            return ("{offset} {ncin} {ncout} {config} "\
                    "{h}").format(**opts)
        else:
            return ("{offset} {ncin} {ncout} {config} "\
                    "{h} {zgrid}").format(**opts)


class Hycom3dPostProdTempConversionBinary(Binary):
    """Binary that converts potential to insitu temperature for dataSHOM production"""

    _footprint = [
        gvar,
        dict(
            info="Binary that converts potential to insitu temperature for dataSHOM production",
            attr=dict(
                gvar=dict(
                    default="hycom3d_postprod_tempconversion_binary",
                ),
                kind=dict(
                    values=["postprod_tempconversion"],
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_postprod_tempconversion_binary"

    def command_line(self, **opts):
        return ("{nctemp} {ncsaln} {ncout}").format(**opts)

# %% Task-specific executable scripts

class Hycom3dIBCTimeScript(Script):

    _footprint = dict(
        info="Python script ",
        attr=dict(kind=dict(values=["hycom3d_ibc_time_script"]))
        )

    def command_line(self, **opts):
        return "{ncins} {dates}".format(**opts)


class Hycom3dAtmfrcTimeScript(Script):

    _footprint = dict(
        info="Python script ",
        attr=dict(kind=dict(values=["hycom3d_atmfrc_time_script"]))
        )

    def command_line(self, **opts):
        return "{ncins_insta} {ncins_cumul} {dates}".format(**opts)


class Hycom3dRiversFlowrateScript(Script):

    _footprint = dict(
        info="Python script ",
        attr=dict(kind=dict(values=["hycom3d_rivers_flowrate_script"]))
        )

    def command_line(self, **opts):
        return "--rank {rank} {tarfile} {dates}".format(**opts)


class Hycom3dSpnudgePrepostScript(Script):

    _footprint = dict(
        info="Python script ",
        attr=dict(kind=dict(values=["hycom3d_spnudge_prepost_script"]))
        )

    def command_line(self, **opts):
        return "{ncins}".format(**opts)
            

class Hycom3dSpnudgeSpectralPreprocScript(Script):

    _footprint = dict(
        info="Python script ",
        attr=dict(kind=dict(values=["hycom3d_spnudge_spectral_preproc_script"]))
        )

    def command_line(self, **opts):
        return "{nchycom3d} {ncmercator}".format(**opts)
    
    
class Hycom3dPostprodPreprocScript(Script):

    _footprint = dict(
        info="Python script ",
        attr=dict(kind=dict(values=["hycom3d_postprod_preproc_script"]))
        )

    def command_line(self, **opts):
        return "{ncins} --rank {rank} --postprod {postprod} --rundate {rundate}".format(**opts)


# %% Pre-processing intermediate files

@namebuilding_append('geo', lambda self: self.field)
class Hycom3dRegridcdfOutputFile(GeoFlowResource):

    _footprint = [
        dict(
            info="Single variable netcdf file created by regridcdf",
            attr=dict(
                kind=dict(
                    values=["boundary"],
                ),
                field=dict(
                    values=["saln", "temp", "thdd", "vaisa", "ssh"],
                ),
                nativefmt=dict(
                    values=["netcdf", "nc"],
                    default="netcdf",
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_regridcdf_output"


# %% Model inputs

@namebuilding_append('src', lambda self: self.fields)
class Hycom3dAtmFrcInputFiles(GeoFlowResource):
    """Atmospheric forcing input files for the Hycom3d model"""

    _footprint = [
        dict(
            info="Hycom Atmospheric Forcing Input Files",
            attr=dict(
                kind=dict(
                    values=['gridpoint', 'hycom3d_atmfrc_input']
                ),
                fields=dict(
                    values=['shwflx','radflx','precip','preatm','airtmp',
                            'wndspd','tauewd','taunwd','vapmix'],
                ),
                format=dict(values=["a", "b", "nc"]),
                nativefmt=dict(
                    values=["binary", "ascii", "netcdf"],
                    remap={"a": "binary", "b": "ascii", "nc": "netcdf"}
                ),
                actualfmt=dict(
                    values=["binary", "ascii", "netcdf"],
                    remap={"a": "binary", "b": "ascii", "nc": "netcdf"}
                ),
            ),
        )
    ]

    @property
    def realkind(self):
        return 'hycom3d_atmfrc_input'


@namebuilding_append('src', lambda self: self.rivers)
class Hycom3dRiversInputFiles(GeoFlowResource):
    """Rivers input files for the Hycom3d model"""

    _footprint = [
        dict(
            info='Hycom Rivers Files',
            attr=dict(
                kind=dict(
                    values = ['observations'],
                ),
                rivers=dict(
                    optional=False,
                ),
                model=dict(
                     values=["cmems"]
                ),
                format=dict(
                     values=['r','nc']
                ),
                nativefmt=dict(
                    values=['ascii','netcdf'],
                    remap={'r':'ascii','nc':'netcdf'}
                ),
                actualfmt=dict(
                    values=['ascii','netcdf'],
                    remap={'r':'ascii','nc':'netcdf'}
                ),
            ),
        )
    ]

    @property
    def realkind(self):
        return 'hycom3d_rivers_input'


@namebuilding_append('geo', lambda self: self.field)
class Hycom3dIBCField(GeoFlowResource):
    _footprint = [
        dict(
            info="Single variable IBC .a and .b files",
            attr=dict(
                kind=dict(
                    values=["boundary"],
                ),
                field=dict(
                    values=["s", "t", "u", "v", "h"],
                ),
                format=dict(values=["a", "b"]),
                nativefmt=dict(
                    values=["binary", "ascii"],
                    remap={"a": "binary", "b": "ascii"}
                ),
                actualfmt=dict(
                    values=["binary", "ascii"],
                    remap={"a": "binary", "b": "ascii"}
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_ibc_field"


@namebuilding_append('geo', lambda self: self.field)
class Hycom3dRestartField(GeoFlowResource):

    _footprint = [
        dict(
            info="Single variable netcdf and restart file created by inicon",
            attr=dict(
                kind=dict(
                    values=["restart_field"],
                ),
                field=dict(
                    values=["saln", "temp", "th3d", "u", "v", "ut", "vt", "h", "dpmixl"],
                ),
                format=dict(
                    values=["cdf", "res"],
                ),
                nativefmt=dict(
                    remap={"cdf": "netcdf", "res": "binary"},
                    values=["binary", "netcdf"],
                ),
                actualfmt=dict(
                    remap={"cdf": "netcdf", "res": "binary"},
                    values=["binary", "netcdf"],
                )
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_restart_field"


@namebuilding_append('geo', lambda self: "rest_new_head")
class Hycom3dRestartDate(GeoFlowResource):

    _footprint = [
        dict(
            info="Restart date in a binary file",
            attr=dict(
                kind=dict(
                    values=["restart_date"],
                ),
                format=dict(
                    values=["binary"]
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_restart_date"


@namebuilding_append('src', lambda self: self.field)
@namebuilding_append('src', lambda self: self.dim)
@namebuilding_append('src', lambda self: self.filter)
@namebuilding_append('src', lambda self: self.source)
class Hycom3dSpnudgeFilterOutput(GeoFlowResource):
    _footprint = [
        dict(
            info="Spnudge filter output nc files",
            attr=dict(
                kind=dict(
                    values=["spnudge_filter_output"],
                ),
                field=dict(
                    values=["saln", "temp", "h", "s", "t"],
                ),
                filter=dict(
                    values=["demerliac", "spectral"],
                ),
                format=dict(
                    values=["nc", "netcdf"],
                ),
                dim=dict(
                    values=["3D", "2D"],
                    optional=True,
                ),
                source=dict(
                    values=["hycom3d", "mercator"],
                    optional=True
                ),
                nativefmt=dict(
                    values=["nc", "netcdf"],
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "spnudge_filter_output"
    
  
@namebuilding_append('src', lambda self: self.field)
class Hycom3dSpnudgeOutput(GeoFlowResource):
    _footprint = [
        dict(
            info="Spectral filter outputs .a and .b files",
            attr=dict(
                kind=dict(
                    values=["spnudge_postproc_output"],
                ),
                field=dict(
                    values=["s", "t", "h", "rmu"],
                ),
                format=dict(values=["a", "b", "nc"]),
                nativefmt=dict(
                    values=["binary", "ascii", "netcdf"],
                    remap={"a": "binary", "b": "ascii", "nc": "netcdf"}
                ),
                actualfmt=dict(
                    values=["binary", "ascii", "netcdf"],
                    remap={"a": "binary", "b": "ascii", "nc": "netcdf"}
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "spnudge_postproc_output"


# %% Model outputs


@namebuilding_append('src', lambda self: self.dim)
@namebuilding_append('geo', lambda self: self.field)
class Hycom3dModelOutput(GeoFlowResource):
    """Model output"""

    _footprint = [
        dict(
            info="Model output",
            attr=dict(
                kind=dict(
                    values=["model_output"],
                ),
                field=dict(
                    values=["ssh", "sss", "sst", "u", "v", "ubavg", "vbavg",
                            "h", "saln", "sigma", "temp"],
                ),
                dim=dict(
                    values=["3D", "2D"],
                    type=str,
                    default="3D",
                ),
                cutoff=dict(
                    values=["production", "assim", "spnudge"],
                    default="production",
                ),
                format=dict(
                    values=["nc", "netcdf"],
                ),
                nativefmt=dict(
                    values=["netcdf", "nc"],
                    default="netcdf"
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return "hycom3d_model_output"


# %% Postprod outputs


@namebuilding_append('src', lambda self: self.dim)
@namebuilding_append('src', lambda self: self.ppdate)
@namebuilding_append('src', lambda self: self.field)
class Hycom3dPostprodPreprocOutput(GeoFlowResource):
    """Post-production preprocessing outputs"""

    _footprint = [
        dict(
            info="Post-production preprocessing outputs",
            attr=dict(
                kind=dict(
                    values=["postprod_preproc_output"],
                ),
                field=dict(
                    values=["ssh", "sss", "sst", "u", "v",
                            "h", "saln", "sigma", "temp", "tempis"],
                ),
                dim=dict(
                    values=["3D", "2D"],
                    type=str,
                    default="3D",
                ),
                ppdate=dict(
                     type=Date,
                     optional=False,
                ),
                cutoff=dict(
                    values=["production"],
                    default="production",
                ),
                format=dict(
                    values=["nc", "netcdf"],
                ),
                nativefmt=dict(
                    values=["netcdf", "nc"],
                    default="netcdf"
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return "hycom3d_postprod_preproc"


@namebuilding_append('geo', lambda self: self.filter)
class Hycom3dPostprodFilterOutput(Hycom3dPostprodPreprocOutput):
    """Post-production filtering outputs"""

    _footprint = [
        dict(
            info="Post-production filtering outputs",
            attr=dict(
                kind=dict(
                    values=["postprod_filter_output"],
                ),
                filter=dict(
                    values=["none", "mean", "demerliac", "godin"],
                    type=str,
                    default="none",
                )
            )
        )
    ]

    @property
    def realkind(self):
        return "hycom3d_postprod_filter"


class Hycom3dPostprodInterpolationOutput(Hycom3dPostprodFilterOutput):
    """Post-production interpolation outputs"""

    _footprint = [
        dict(
            info="Post-production interpolation outputs",
            attr=dict(
                kind=dict(
                    values=["postprod_interpolation_output",
                            "postprod_tempconversion_output"],
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return "hycom3d_postprod_interpolation"
    
    
@namebuilding_append('src', lambda self: self.dim)
@namebuilding_append('src', lambda self: self.ppdate)
@namebuilding_append('geo', lambda self: self.filter)
class Hycom3dPostprodConcatOutput(GeoFlowResource):
    """Post-production concatenation outputs"""

    _footprint = [
        dict(
            info="Post-production concatenation outputs",
            attr=dict(
                kind=dict(
                    values=["postprod_concat_output"],
                ),
                dim=dict(
                    values=["3D", "2D"],
                    type=str,
                    default="3D",
                ),
                ppdate=dict(
                     type=Date,
                     optional=False,
                ),
                filter=dict(
                    values=["none", "mean", "demerliac", "godin"],
                    type=str,
                    default="none",
                ),
                cutoff=dict(
                    values=["production"],
                    default="production",
                ),
                format=dict(
                    values=["nc", "netcdf"],
                ),
                nativefmt=dict(
                    values=["netcdf", "nc"],
                    default="netcdf"
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return "hycom3d_postprod_concatenation"
    

@namebuilding_append('geo', lambda self: self.area)
class Hycom3dPostprodExtractOutput(Hycom3dPostprodConcatOutput):
    """Post-production extraction outputs"""

    _footprint = [
        dict(
            info="Post-production extraction outputs",
            attr=dict(
                kind=dict(
                    values=["postprod_extract_output"],
                ),
                area=dict(
                    values=["MANGA", "BretagneSud"],
                    type=str,
                    default="MANGA",
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return "hycom3d_postprod_extraction"
