# -*- coding: utf-8 -*-

"""
Hycom3d files
"""

from gco.syntax.stdattrs import gdomain, gvar
from vortex.data.executables import Script, Binary, OceanographicModel

__all__ = []


# %% Binaries

class Hycom3dIBCRegridcdfBinary(Binary):
    """Binary that regrids initial conditions netcdf files."""

    _footprint = [
        gvar,
        gdomain,
        dict(
            info="Binary that regrids initial conditions netcdf files",
            attr=dict(
                gvar=dict(default="master_hycom3d_ibc_regridcdf_[gdomain]"),
                kind=dict(values=["horizontal_regridder"]),
                model=dict(values=["hycom3d"])
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_ibc_regridcdf_binary"

    def command_line(self, **opts):
        return "{varname} {method} {density_corr} {bathy_corr} {cstep:03d}".format(**opts)


class Hycom3dIBCIniconBinary(Binary):
    """Binary that computes initial condictions for HYCOM."""

    _footprint = [
        gvar,
        gdomain,
        dict(
            info="Binary that computes initial conditions for HYCOM",
            attr=dict(
                gvar=dict(default="master_hycom3d_ibc_inicon_[gdomain]"),
                kind=dict(values=["vertical_regridder"]),
                model=dict(values=["hycom3d"])
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_ibc_inicon_binary"

    def command_line(self, **opts):
        return ("{datadir} {sshfile} {tempfile} {salnfile} " +
                "{nx} {ny} {nz} {cmoy} {sshmin} " +
                "{bathy_corr} {cstep}").format(**opts)


class Hycom3dSpNudgeDemerliacBinary(Binary):
    """Binary that apply Demerliac filter HYCOM Spectral Nugding."""

    _footprint = [
        gvar,
        dict(
            info="Binary that apply Demerliac filter HYCOM Spectral Nugding",
            attr=dict(
                gvar=dict(
                    default="master_hycom3d_spnudge_demerliac"
                ),
                kind=dict(
                    values=["demerliac_filter"],
                ),
                model=dict(
                    values=["hycom3d"],
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_spnudge_demerliac_binary"

    def command_line(self, **opts):
        return "{date} {output_type}".format(**opts)


class Hycom3dSpNudgeSpectralBinary(Binary):
    """Binary that apply spectral filter HYCOM Spectral Nugding."""

    _footprint = [
        gvar,
        dict(
            info="Binary that apply spectral filter HYCOM Spectral Nugding",
            attr=dict(
                gvar=dict(
                    default="master_hycom3d_spnudge_spectral"
                ),
                kind=dict(
                    values=["spectral_filter"],
                ),
                model=dict(
                    values=["hycom3d"],
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_spnudge_spectral_binary"

    def command_line(self, **opts):
        return "{wave_sp} {genmask} {min_depth} {relax_sp}".format(**opts)


class Hycom3dModelBinary(OceanographicModel):
    """Binary of the 3d model."""

    _footprint = [
        gvar,
        gdomain,
        dict(
            info="Binary of the model",
            attr= dict(
                gvar = dict(
                    default='master_hycom3d_oceanmodel_[gdomain]'
                ),
                model=dict(
                    values=["hycom3d"],
                ),
            ),
        )
    ]

    def command_line(self, **opts):
        return "{datadir} {tmpdir} {localdir} {rank}".format(**opts)


class Hycom3dPostProdFilterBinary(Binary):
    """Binary that applies filtering in time over Hycom outputs."""

    _footprint = [
        gvar,
        dict(
            info="Binary that applies filtering in time over Hycom outputs",
            attr=dict(
                gvar=dict(
                    default="master_hycom3d_postprod_timefilter"
                ),
                kind=dict(
                    values=["postprod_filter"],
                ),
                model=dict(
                    values=["hycom3d"],
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_postprod_timefilter_binary"

    def command_line(self, **opts):
        if "ncin_back" not in list(opts.keys()):
            return ("{filter} {ncout} " +
                    "{ncin_for} {ncin_mid}").format(**opts)
        else:
            return ("{filter} {ncout} " +
                    "{ncin_for} {ncin_mid} {ncin_back}").format(**opts)


class Hycom3dPostProdVertInterpolationBinary(Binary):
    """
    Binary that verticaly interpolates and converts HYCOM output in SOAP and
    dataShom formats.
    """

    _footprint = [
        gvar,
        dict(
            info="Binary that verticaly interpolates",
            attr=dict(
                gvar=dict(
                    default="master_hycom3d_postprod_vertinterpolation"
                ),
                kind=dict(
                    values=["postprod_vertinterpolation"],
                ),
                model=dict(
                    values=["hycom3d"],
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_postprod_vertinterpolation_binary"

    def command_line(self, **opts):
        if "zgrid" not in list(opts.keys()):
            return ("{offset} {ncin} {ncout} {config} " +
                    "{h}").format(**opts)
        else:
            return ("{offset} {ncin} {ncout} {config} " +
                    "{h} {zgrid}").format(**opts)


class Hycom3dPostProdTempConversionBinary(Binary):
    """Binary that converts potential to insitu temperature for dataSHOM production."""

    _footprint = [
        gvar,
        dict(
            info="Binary that converts potential to insitu temperature for dataSHOM production",
            attr=dict(
                gvar=dict(
                    default="master_hycom3d_postprod_tempconversion"
                ),
                kind=dict(
                    values=["postprod_tempconversion"],
                ),
                model=dict(
                    values=["hycom3d"],
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "hycom3d_postprod_tempconversion_binary"

    def command_line(self, **opts):
        return "{nctemp} {ncsaln} {ncout}".format(**opts)


# %% Task-specific executable scripts

class Hycom3dIBCTimeScript(Script):
    """TODO Class Documentation."""

    _footprint = dict(
        info="Python script ",
        attr=dict(kind=dict(values=["hycom3d_ibc_time_script"]))
    )

    def command_line(self, **opts):
        return "{ncins} {dates}".format(**opts)


class Hycom3dAtmfrcTimeScript(Script):
    """TODO Class Documentation."""

    _footprint = dict(
        info="Python script ",
        attr=dict(kind=dict(values=["hycom3d_atmfrc_time_script"]))
    )

    def command_line(self, **opts):
        return "{ncins_insta} {ncins_cumul} {dates}".format(**opts)


class Hycom3dRiversFlowrateScript(Script):
    """TODO Class Documentation."""

    _footprint = dict(
        info="Python script ",
        attr=dict(kind=dict(values=["hycom3d_rivers_flowrate_script"]))
    )

    def command_line(self, **opts):
        return "--rank {rank} {tarfile} {dates}".format(**opts)


class Hycom3dModelPreprocScript(Script):
    """TODO Class Documentation."""

    _footprint = dict(
        info="Python script ",
        attr=dict(kind=dict(values=["hycom3d_model_preproc_script"]))
    )

    def command_line(self, **opts):
        return "--rank {rank} --mode {mode} --restart {restart} --delday {delday} --mpiname {mpiname}".format(**opts)


class Hycom3dModelPostprocScript(Script):
    """TODO Class Documentation."""

    _footprint = dict(
        info="Python script ",
        attr=dict(kind=dict(values=["hycom3d_model_postproc_script"]))
    )

    def command_line(self, **opts):
        return "--model-log {log_file}".format(**opts)


class Hycom3dSpnudgePrepostScript(Script):
    """TODO Class Documentation."""

    _footprint = dict(
        info="Python script ",
        attr=dict(kind=dict(values=["hycom3d_spnudge_prepost_script"]))
    )

    def command_line(self, **opts):
        return "{ncins}".format(**opts)


class Hycom3dSpnudgeSpectralPreprocScript(Script):
    """TODO Class Documentation."""

    _footprint = dict(
        info="Python script ",
        attr=dict(kind=dict(values=["hycom3d_spnudge_spectral_preproc_script"]))
    )

    def command_line(self, **opts):
        return "{nchycom3d} {ncmercator}".format(**opts)


class Hycom3dPostprodPreprocScript(Script):
    """TODO Class Documentation."""

    _footprint = dict(
        info="Python script ",
        attr=dict(kind=dict(values=["hycom3d_postprod_preproc_script"]))
    )

    def command_line(self, **opts):
        return "{ncins} --rank {rank} --postprod {postprod} --rundate {rundate}".format(**opts)


class Hycom3dPostprodConcatScript(Script):
    """TODO Class Documentation."""

    _footprint = dict(
        info="Python script ",
        attr=dict(kind=dict(values=["hycom3d_postprod_concat_script"]))
    )

    def command_line(self, **opts):
        return ("{ncins} --rank {rank} --postprod {postprod} " +
                "--rundate {rundate} --vapp {vapp} --vconf {vconf}").format(**opts)
