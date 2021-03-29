# -*- coding: utf-8 -*-
"""
Hycom3d files
"""

from gco.syntax.stdattrs import gdomain, gvar
from vortex.data.executables import Script, Binary, OceanographicModel

__all__ = []



# %% Binaries

class Hycom3dIBCRegridcdfBinary(Binary):
    """Binary that regrids initial conditions netcdf files"""

    _footprint = [
        gvar,
        #        hgeometry_deco,
        dict(
            info="Binary that regrids initial conditions netcdf files",
            attr=dict(
                gvar=dict(default="master_hycom3d_ibc_regridcdf", optional=True),
                kind=dict(values=["horizontal_regridder"]),
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
                gvar=dict(default="master_hycom3d_ibc_inicon", optional=True),
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
                    default="master_hycom3d_spnudge_demerliac",
                    optional=True
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
                    default="master_hycom3d_spnudge_spectral",
                    optional=True
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
        gdomain,
        dict(
            info="Binary of the model",
            attr= dict(
                gvar = dict(
                    default='master_hycom3d_oceanmodel_[gdomain]',
                    optional=True
                ),
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
                    default="master_hycom3d_postprod_timefilter",
                    optional=True
                ),
                kind=dict(
                    values=["postprod_filter"],
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_postprod_timefilter_binary"

    def command_line(self, **opts):
        if "ncin_back" not in list(opts.keys()):
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
                    default="master_hycom3d_postprod_vertinterpolation",
                    optional=True
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
                    default="master_hycom3d_postprod_tempconversion",
                    optional=True
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


class Hycom3dModelPreprocScript(Script):

    _footprint = dict(
        info="Python script ",
        attr=dict(kind=dict(values=["hycom3d_model_preproc_script"]))
        )

    def command_line(self, **opts):
        return "--rank {rank} --mode {mode} --restart {restart} --delday {delday} --mpiname {mpiname}".format(**opts)


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
