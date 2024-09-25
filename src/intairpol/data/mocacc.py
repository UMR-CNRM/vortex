"""
Resources used with MOCAGE Accident (tarfiles, txtfiles, json).
"""

from vortex.data.contents import JsonDictContent, AlmostListContent
from vortex.data.geometries import LonlatGeometry
from vortex.data import geometries
from vortex.data.outflow import ModelResource
from vortex.data.flow import FlowResource, GeoFlowResource

from vortex.syntax.stdattrs import term_deco
from vortex.syntax.stddeco import namebuilding_append
from bronx.stdtypes import date
import footprints as fp


class MocaccInputs(FlowResource):
    """Tar with emission config file and nwp gribs"""

    # fmt: off
    _footprint = [
        dict(
            info = "Tar from soprano used in mocage accident suite",
            attr = dict(
                kind = dict(
                    values = ["mocacc_emis_and_nwp_inputs"]
                ),
                model = dict(
                    values = ['mocage', ]
                ),
                nativefmt = dict(
                    values = ["tar"],
                    default = "tar"
                ),
            ),
        )
    ]
    # fmt: on

    @property
    def realkind(self):
        return "mocacc_emis_and_nwp_inputs"


class MocaccOuputs(FlowResource):
    """Tar with gribs mocacc outputs, emission and other files."""

    # fmt: off
    _footprint = [
        term_deco,
        dict(
            info = "Mocacc outputs",
            attr = dict(
                kind = dict(
                    values = ["mocacc_outputs"]
                ),
                model = dict(
                    values = ['mocage', ]
                ),
                nativefmt = dict(
                    values = ["tar"],
                    default = "tar"
                ),
            ),
        )
    ]
    # fmt: on

    @property
    def realkind(self):
        return "mocacc_outputs"


class EnsembleMocaccPlots(ModelResource):
    """Tar with plots from ensemble (diagnostics, runs, ...)."""

    # fmt: off
    _footprint = [
        dict(
            info = "Ensemble Mocacc Plots",
            attr = dict(
                kind = dict(
                    values = ["ensemble_mocacc_plots", "ensemble_mocacc_plots2"]
                ),
                model = dict(
                    values = ['mocage', ]
                ),
                nativefmt = dict(
                    values = ["tar"],
                    default = "tar"
                ),
            ),
        )
    ]
    # fmt: on

    @property
    def realkind(self):
        return "ensemble_mocacc_plots"


class CtbtoOuputs(FlowResource):
    """Tar with txt files asked by CTBTO."""

    # fmt: off
    _footprint = [
        term_deco,
        dict(
            info = "CTBTO outputs",
            attr = dict(
                kind = dict(
                    values = ["ctbto_outputs"]
                ),
                model = dict(
                    values = ['mocage', ]
                ),
                nativefmt = dict(
                    values = ["tar"],
                    default = "tar"
                ),
            ),
        )
    ]
    # fmt: on

    @property
    def realkind(self):
        return "ctbto_outputs"


@namebuilding_append("src", lambda s: s.field)
class MocaccContours(GeoFlowResource):
    """Contours files for MOCAGE Accident fields."""

    # fmt: off
    _footprint = [
        dict(
            info = "Tar from soprano used in mocage accident suite",
            attr = dict(
                kind = dict(
                    values = ["plume_contours"]
                ),
                model = dict(
                    values = ['mocage', ]
                ),
                field = dict(
                    values = ['conc_max', ]
                ),
                nativefmt = dict(
                    values = ["txt"],
                    default = "txt"
                ),
            ),
        )
    ]
    # fmt: on

    @property
    def realkind(self):
        return "plume_contours"


class EnsembleMocaccDiagNetcdf(FlowResource):
    """Tar with netcdf diags."""

    # fmt: off
    _footprint = [
        dict(
            info = "Ensemble Mocacc Netcdf Diagnostics",
            attr = dict(
                kind = dict(
                    values = ["ensemble_mocacc_diag_netcdf"]
                ),
                model = dict(
                    values = ['mocage', ]
                ),
                nativefmt = dict(
                    values = ["tar", "netcdf"],
                    default = "tar"
                ),
            ),
        )
    ]
    # fmt: on

    @property
    def realkind(self):
        return "ensemble_mocacc_diag_netcdf"


class DeterministicMocaccRunNetcdf(FlowResource):
    """Tar with control run netcdf."""

    # fmt: off
    _footprint = [
        dict(
            info = "Netcdf Control Run Outputs",
            attr = dict(
                kind = dict(
                    values = ["deterministic_mocacc_run_netcdf"]
                ),
                model = dict(
                    values = ['mocage', ]
                ),
                nativefmt = dict(
                    values = ["tar"],
                    default = "tar"
                ),
            ),
        )
    ]
    # fmt: on

    @property
    def realkind(self):
        return "deterministic_mocacc_run_netcdf"


class DeterministicMocaccRunGeojson(FlowResource):
    """Tar with control run geojsons."""

    # fmt: off
    _footprint = [
        dict(
            info = "Geojson Control Run Outputs",
            attr = dict(
                kind = dict(
                    values = ["deterministic_mocacc_run_geojson"]
                ),
                model = dict(
                    values = ['mocage', ]
                ),
                nativefmt = dict(
                    values = ["tar"],
                    default = "tar"
                ),
            ),
        )
    ]
    # fmt: on

    @property
    def realkind(self):
        return "deterministic_mocacc_run_geojson"


class MocaccTableChemContent(AlmostListContent):
    """Content of MocaccTableChem."""

    @property
    def nbpolls(self):
        """Number of atomic release in MOCAGE.CFG."""
        return len([line for line in self._data if "POLLUT" in line])


class MocaccTableChem(ModelResource):
    """Pollutants table for MOCAGE Accident run."""

    # fmt: off
    _footprint = [
        dict(
            info = "Pollutants table for MOCAGE Accident run.",
            attr = dict(
                kind = dict(
                    values = ["mocacc_table_chem"]
                ),
                model = dict(
                    values = ['mocage', ]
                ),
                nativefmt = dict(
                    values = ["ascii"],
                    default = "ascii"
                ),
                clscontents = dict(
                    default = MocaccTableChemContent
                ),

            ),
        )
    ]
    # fmt: on

    @property
    def realkind(self):
        return "mocacc_table_chem"


class ExtraConfMocaccContent(JsonDictContent):
    """Contents of a json used to store non permanent config.

    These infos can change between runs, but not within a single run.
    """

    @property
    def launched_at(self):
        """When the simulation was launched by forecaster."""
        return self._data["launched_at"]

    @property
    def basetime_forcing(self):
        """Basetime for FM files."""
        return self._data["basetime_forcing"]

    @property
    def basetime_forecast(self):
        """Basetime for MOCAGE Accident."""
        return self._data["basetime_forecast"]

    @property
    def release_start(self):
        """Start of release."""
        return self._data["release_start"]

    @property
    def terms_forcing(self):
        """Expected terms of FM files (inputs of MOCAGE)."""
        return self._data["terms_forcing"]

    @property
    def terms_forecast(self):
        """Expected terms of HM files (outputs of MOCAGE)."""
        return self._data["terms_forecast"]

    @property
    def fullpos_previous_runs(self):
        """Runs used for FULLPOS (except last run).

        Terms are differents from those of forecast run.
        """
        return self._data.get("basetime_previous_runs_fullpos", [])

    @property
    def fullpos_previous_runs_terms(self):
        """Terms used for FULLPOS (except last run).

        Terms are differents from those of forecast run.
        """
        return self._data.get("basetime_previous_runs_terms_fullpos", [])

    @property
    def fullpos_previous_runs_terms_but_last(self):
        """Terms used for FULLPOS (except last run).
        """
        if self.fullpos_previous_runs_terms:
            return self.fullpos_previous_runs_terms[0:-1]
        return []

    @property
    def fullpos_last_run(self):
        """Last run used for FULLPOS.
        """
        return self._data.get("basetime_last_run_fullpos", None)

    @property
    def fullpos_last_run_terms(self):
        """Terms used for FULLPOS with last run."""
        return self._data.get("basetime_last_run_terms_fullpos", [])

    @property
    def terms_routing(self):
        """Terms of routing outputs."""
        return self._data["terms_routing"]

    @property
    def terms_restart(self):
        """Expected terms of HM files (eventually used for restart later)."""
        return self._data["terms_restart"]

    @property
    def validities_restart_iso(self):
        """Expected restart validities."""
        return [
            (
                date.Date(self._data["basetime_forecast"]) + date.Period(hours=term)
            ).iso8601()
            for term in self._data["terms_restart"]
        ]

    @property
    def is_restart_enabled(self):
        """Is restart enabled."""
        return self._data["restart"]["enabled"]

    @property
    def restart_scenario(self):
        """Scenario used for restart."""
        return self._data["restart"]["scenario"]

    @property
    def restart_valid_at(self):
        """Validity of restart."""
        return self._data["restart"]["valid_at"]

    @property
    def source_vertical_profile(self):
        """Vertical profile of emission source."""
        return self._data["source_vertical_profile"]

    @property
    def members(self):
        """Membres disponibles."""
        return fp.util.rangex(0, len(self._data["members"]) - 1)

    @property
    def geometries_moc(self):
        """Get dict stored in geometries_moc key."""
        return self._data["geometries_moc"]

    @property
    def geometries_fullpos(self):
        """Geometries for FULLPOS."""
        return list([geometries.get(tag=geom["name"]) for geom in self.geometries_moc])

    def get_hm_term_from_valid_at(self, valid_at):
        """Calculate term from validity to find corresponding HM file."""
        return date.Date(valid_at) - date.Date(self.basetime_forecast)

    def set_mocage_geometries(self):
        """Create the needed vortex geometries for MOCAGE.

        .. warning::
           As MOCAGE expect 6 characters domains in file names, area must be
           used in resource handler for the local name (area of course must
           contain 6 characters).

        .. warning::
           Within json, list of geometries must be in decreasing order
           (global domain first)
        """
        geometries = []
        for idx, geom in enumerate(self._data["geometries_moc"]):
            if idx == 0:
                area = "M_GLOB"
                tag = "mocacc-global-domain-{:3.1f}".format(geom["resolution"])
                info = "Global {:3.1f} degree domain for MOCAGE Accident".format(
                    geom["resolution"]
                )
            else:
                area = "M_NST{}".format(idx)
                tag = "mocacc-nested-domain{}-{:5.3f}".format(idx, geom["resolution"])
                info = "Nested {:5.3f} degree domain for MOCAGE Accident".format(
                    geom["resolution"]
                )

            geometries.append(
                LonlatGeometry(
                    tag=tag,
                    info=info,
                    lam=(geom["nlon"] + 1) * geom["resolution"] <= 360.0,
                    resolution=geom["resolution"],
                    nlon=geom["nlon"],
                    nlat=geom["nlat"],
                    lonmin=geom["first_lon"],
                    latmin=geom["last_lat"],
                    area=area,
                    new=True,
                )
            )

        return geometries

    def set_bdap_extracted_nwp_geometries(self):
        """Create the needed vortex geometries for BDAP extracted fields.

        .. warning::
           Within json, list of geometries must be in decreasing order
           (global domain first).
        """
        geometries = []
        for idx, geom in enumerate(self._data["geometries_bdap_nwp"]):
            if idx == 0:
                area = "GLOB-{:3.1f}-BDAPNWP".format(geom["resolution"])
                tag = "nwp_global_domain_from_bdap"
                info = "Global {:3.1f} degree domain of NWP used for MOCAGE Accident".format(
                    geom["resolution"]
                )
            else:
                area = "NESTED{}-{:5.3f}-NWPBDAP".format(idx, geom["resolution"])
                tag = "nwp_nested_domain_{}_{:5.3f}_from_bdap".format(
                    idx, geom["resolution"]
                )
                info = "Nested {:5.3f} degree domain of NWP used for MOCAGE Accident".format(
                    geom["resolution"]
                )

            geometries.append(
                LonlatGeometry(
                    tag=tag,
                    info=info,
                    lam=(geom["nlon"] + 1) * geom["resolution"] <= 360.0,
                    resolution=geom["resolution"],
                    nlon=geom["nlon"],
                    nlat=geom["nlat"],
                    area=area,
                    lonmin=geom["first_lon"],
                    latmin=geom["last_lat"],
                    new=True,
                )
            )
        return geometries

    def set_merged_geometries(self, min_res=0.25):
        """Create the needed vortex geometries when global and nested geometries
        are merged.

        .. warning::
           As extent of grids is unknown (extent of plume vary between simulation), nlon,
           nlat, lonmin, lonmat are also unknown and populated with fake values.

        """
        geometries = []
        for idx, geom in enumerate(self._data["geometries_moc"]):
            if idx == 0:
                area = f"MERGED_OFFICIAL_{min_res:5.3f}"
                tag = f"mocacc-merged-official-{min_res:5.3f}"
                info = f"{min_res:5.3f} degree reglementary domain covering plume for MOCAGE Accident"
            else:
                area = f"MERGED_{geom['resolution']:5.3f}"
                tag = f"mocacc-merged-{geom['resolution']:5.3f}"
                info = f"{geom['resolution']:5.3f} degree domain domain covering plume for MOCAGE Accident"

            geometries.append(
                LonlatGeometry(
                    tag=tag,
                    info=info,
                    lam=(geom["nlon"] + 1) * geom["resolution"] <= 360.0,
                    resolution=min(geom["resolution"], min_res),
                    nlon=geom["nlon"],
                    nlat=geom["nlat"],
                    lonmin=geom["first_lon"],
                    latmin=geom["last_lat"],
                    area=area,
                    new=True,
                )
            )

        return geometries


class ExtraConfMocacc(ModelResource):
    """Expected outputs or grid for MOCAGE Accident.

    Several infos cannot be stored within conf as they would be usually :
    - terms
    - runtime (it depends on the release start)
    - grids (global with or without a nested grid, the nested grid is not known in advance)

    These infos can be inferred from input gribs in operation for MOCAGE Accident.
    """

    # fmt: off
    _footprint = [
        dict(
            info = "Expected outputs (basetime, outputs periods, grids...) that cannot be in conf",
            attr = dict(
                kind = dict(
                    values = ["extra_conf_mocacc"]
                ),
                model = dict(
                    values = ['mocage', ]
                ),
                nativefmt = dict(
                    values = ["json"],
                    default = "json"
                ),
                clscontents = dict(
                    default = ExtraConfMocaccContent
                ),
            ),
        )
    ]
    # fmt: on

    @property
    def realkind(self):
        return "extra_conf_mocacc"


class ExtraConfMocaccCtbtoContent(JsonDictContent):
    """Contents of a json used to store non permanent config for CTBTO.

    These infos can change between runs, but not within a single run.
    In this case geometry is fixed and there is no restart.
    """

    @property
    def basetime_forecast(self):
        """Basetime for MOCAGE Accident."""
        return self._data["basetime_forecast"]

    @property
    def backward_to(self):
        """Last validity expected by CTBTO."""
        return self._data["backward_to"]

    @property
    def mail_ctbto(self):
        """CTBTO mail."""
        return self._data["mail_ctbto"]

    @property
    def source_vertical_profile(self):
        """Profil vertical pour le CTBTO."""
        return "uniform"

    @property
    def last_term(self):
        """Last forecast term."""
        return date.Date(self.backward_to) - date.Date(self.basetime_forecast)

    def get_first_basetime_forcing(self, coupling_step, couplings_delta):
        """Calculate first forcing basetime.

        Coupling_step and couplings_delta are date.Period or "PTXH"
        """
        basetime_forecast = date.Date(self.basetime_forecast)
        first_basetime_forcing = date.Date(
            basetime_forecast.year,
            basetime_forecast.month,
            basetime_forecast.day,
        )

        while (
            first_basetime_forcing + couplings_delta - coupling_step < basetime_forecast
        ):
            first_basetime_forcing += date.Period(couplings_delta)

        return first_basetime_forcing

    def get_basetimes_forcing(self, coupling_step, couplings_delta):
        """Get basetimes forcing needed for forecast."""
        tmp_basetime = self.get_first_basetime_forcing(coupling_step, couplings_delta)
        basetimes_forcing = []
        backward_to = date.Date(self.backward_to)

        while tmp_basetime >= backward_to:
            basetimes_forcing.append(tmp_basetime)
            tmp_basetime -= couplings_delta

        return basetimes_forcing


class ExtraConfMocaccCtbto(ModelResource):
    """Extra conf for CTBTO (MOCAGE Accident with transinv).

    Several infos cannot be stored within conf as they would be usually :
    - terms
    - runtime (it depends on the release start)
    - ctbto mail (depends on the CTBTO request)
    """

    # fmt: off
    _footprint = [
        dict(
            info = "Extra conf for CTBTO that cannot be stored in normal conf",
            attr = dict(
                kind = dict(
                    values = ["extra_conf_mocacc_ctbto"]
                ),
                model = dict(
                    values = ['mocage', ]
                ),
                nativefmt = dict(
                    values = ["json"],
                    default = "json"
                ),
                clscontents = dict(
                    default = ExtraConfMocaccCtbtoContent
                ),
            ),
        )
    ]
    # fmt: on

    @property
    def realkind(self):
        return "extra_conf_mocacc_ctbto"
