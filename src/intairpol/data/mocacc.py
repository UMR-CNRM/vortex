# -*- coding:utf-8 -*-

"""
Resources used with MOCAGE Accident (tarfiles, txtfiles, json).
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.data.contents import JsonDictContent
from vortex.data.geometries import LonlatGeometry
from vortex.data.outflow import ModelResource
from vortex.data.flow import FlowResource

from vortex.syntax.stdattrs import term_deco
from bronx.stdtypes import date


class MocaccInputs(ModelResource):
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


class MocaccDateEch(ModelResource):
    """Various step / datetime for mocage accident suite"""

    # fmt: off
    _footprint = [
        dict(
            info = "Various step / datetime for mocage accident suite",
            attr = dict(
                kind = dict(
                    values = ["mocacc_datech"]
                ),
                model = dict(
                    values = ['mocage', ]
                ),
                nativefmt = dict(
                    values = ["ascii"],
                    default = "ascii"
                ),
            ),
        )
    ]
    # fmt: on

    @property
    def realkind(self):
        return "mocacc_datech"


class ExtraConfMocaccContent(JsonDictContent):
    """Contents of a json used to store non permanent config.

    These infos can change between runs, but not within a single run.
    """

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

    def get_hm_term_from_valid_at(self, valid_at):
        """Calculate term from validity to find corresponding HM file.
        """
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
        for (idx, geom) in enumerate(self._data["geometries_moc"]):
            if idx == 0:
                area = "M_GLOB"
                tag = "mocacc-global-domain-{0:3.1f}".format(geom["resolution"])
                info = "Global {0:3.1f} degree domain for MOCAGE Accident".format(
                    geom["resolution"]
                )
            else:
                area = "M_NST{0}".format(idx)
                tag = "mocacc-nested-domain{0}-{1:5.3f}".format(idx, geom["resolution"])
                info = "Nested {0:5.3f} degree domain for MOCAGE Accident".format(
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
        for (idx, geom) in enumerate(self._data["geometries_bdap_nwp"]):
            if idx == 0:
                area = "GLOB-{0:3.1f}-BDAPNWP".format(geom["resolution"])
                tag = "nwp_global_domain_from_bdap"
                info = "Global {0:3.1f} degree domain of NWP used for MOCAGE Accident".format(
                    geom["resolution"]
                )
            else:
                area = "NESTED{0}-{1:5.3f}-NWPBDAP".format(idx, geom["resolution"])
                tag = "nwp_nested_domain_{0}_{1:5.3f}_from_bdap".format(
                    idx, geom["resolution"]
                )
                info = "Nested {0:5.3f} degree domain of NWP used for MOCAGE Accident".format(
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