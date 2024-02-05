"""
Various resources for executables used by SLOOP.
"""

from gco.syntax.stdattrs import gdomain, gvar
from vortex.data.executables import Script, Binary, OceanographicModel

#: No automatic export
__all__ = []


# %% Binaries

class Hycom3dIBCRegridcdfBinary(Binary):
    """Tool to horizontaly regrid initial and boundary conditions."""

    _footprint = [
        gvar,
        gdomain,
        dict(
            info="Binary regridding netcdf files",
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
    """Tool to verticaly project initial and boundary condictions."""

    _footprint = [
        gvar,
        gdomain,
        dict(
            info="Binary that computes initial conditions for hycom3d",
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
    """Tool to apply a Demerliac filter on hycom3d model outputs in
    the spectral nudging perspective.

    """

    _footprint = [
        gvar,
        dict(
            info="Binary that apply Demerliac filter.",
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
    """Tool to apply a spectral filter on hycom3d model outputs in the
    spectral nudging perspective.

    """

    _footprint = [
        gvar,
        dict(
            info="Binary that apply spectral filter.",
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
    """Hycom3d model."""

    _footprint = [
        gvar,
        gdomain,
        dict(
            info="Binary of the model.",
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
    """Tool to apply a time filtering over the hycom3d outputs."""

    _footprint = [
        gvar,
        dict(
            info="Binary that applies a time filtering over the hycom3d outputs.",
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
    """Tool to verticaly interpolate and convert hycom3d outputs
    in the SOAP and dataSHOM formats.
    """

    _footprint = [
        gvar,
        dict(
            info="Binary that verticaly interpolates.",
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
    """Tool to convert potential to insitu temperature."""

    _footprint = [
        gvar,
        dict(
            info="Binary that converts potential to insitu temperature.",
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
    """Sloop task executable to timely interpolate
    initial and boundary conditions.
    """

    _footprint = dict(
        info="Python script ",
        attr=dict(kind=dict(values=["hycom3d_ibc_time_script"]))
    )

    def command_line(self, **opts):
        return "{ncins} {dates}".format(**opts)


class Hycom3dAtmfrcTimeScript(Script):
    """Sloop task executable to timely interpolate
    atmospheric parameters.
    """

    _footprint = dict(
        info="Python script ",
        attr=dict(kind=dict(values=["hycom3d_atmfrc_time_script"]))
    )

    def command_line(self, **opts):
        return "{ncins_insta} {ncins_cumul} {dates}".format(**opts)


class Hycom3dRiversFlowrateScript(Script):
    """Sloop task executable to timely interpolate flow rate of rivers
    or compute it from climatological data.

    """

    _footprint = dict(
        info="Python script ",
        attr=dict(kind=dict(values=["hycom3d_rivers_flowrate_script"]))
    )

    def command_line(self, **opts):
        return "--rank {rank} {tarfile} {dates}".format(**opts)


class Hycom3dModelPreprocScript(Script):
    """Sloop task executable to prepare namelist used by hycom3d."""

    _footprint = dict(
        info="Python script ",
        attr=dict(kind=dict(values=["hycom3d_model_preproc_script"]))
    )

    def command_line(self, **opts):
        return "--rank {rank} --mode {mode} --restart {restart} --delday {delday} --mpiname {mpiname}".format(**opts)


class Hycom3dModelPostprocScript(Script):
    """Sloop task executable to check whether
    a hycom3d run is ok at the end.
    """

    _footprint = dict(
        info="Python script ",
        attr=dict(kind=dict(values=["hycom3d_model_postproc_script"]))
    )

    def command_line(self, **opts):
        return "--model-log {log_file}".format(**opts)


class Hycom3dSpnudgePrepostScript(Script):
    """Sloop task executables to pre- or post-process
    data for spectral nudging.
    """

    _footprint = dict(
        info="Python script ",
        attr=dict(kind=dict(values=["hycom3d_spnudge_prepost_script"]))
    )

    def command_line(self, **opts):
        return "{ncins}".format(**opts)


class Hycom3dSpnudgeSpectralPreprocScript(Script):
    """Sloop task executables to pre-process data before spectral filter
    for spectral nudging.
    """

    _footprint = dict(
        info="Python script ",
        attr=dict(kind=dict(values=["hycom3d_spnudge_spectral_preproc_script"]))
    )

    def command_line(self, **opts):
        return "{nchycom3d} {ncmercator}".format(**opts)


class Hycom3dPostprodPreprocScript(Script):
    """Sloop task executables to pre-process data for the post-production."""

    _footprint = dict(
        info="Python script ",
        attr=dict(kind=dict(values=["hycom3d_postprod_preproc_script"]))
    )

    def command_line(self, **opts):
        return "{ncins} --rank {rank} --postprod {postprod} --rundate {rundate}".format(**opts)


class Hycom3dPostprodPreprocInterpScript(Script):
    """Sloop task executables to pre-process data for the post-production."""

    _footprint = dict(
        info="Python script ",
        attr=dict(kind=dict(values=["hycom3d_postprod_preproc_interp_script"]))
    )

    def command_line(self, **opts):
        return (
            "{ncins} --rank {rank} --postprod {postprod} "
            "--rundate {rundate} --offset {cmoy}"
        ).format(**opts)


class Hycom3dPostprodConcatScript(Script):
    """Sloop task executables to concatenate data for the post-production."""

    _footprint = dict(
        info="Python script ",
        attr=dict(kind=dict(values=["hycom3d_postprod_concat_script"]))
    )

    def command_line(self, **opts):
        return (
            "{ncins} --rank {rank} --postprod {postprod} "
            "--rundate {rundate} --vapp {vapp} --vconf {vconf}"
        ).format(**opts)
