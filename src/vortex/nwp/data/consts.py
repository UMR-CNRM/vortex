"""
Various Resources for constant files used in NWP.
"""

import footprints
from ..syntax.stdattrs import gvar
from vortex.data.contents import DataRaw, JsonDictContent, TextContent
from vortex.data.geometries import GaussGeometry, LonlatGeometry
from vortex.data.outflow import ModelGeoResource, ModelResource, StaticResource
from vortex.syntax.stdattrs import month_deco
from vortex.syntax.stddeco import (
    namebuilding_append,
    namebuilding_delete,
    namebuilding_insert,
)

#: No automatic export
__all__ = []


class GenvModelResource(ModelResource):
    """Abstract class for gget driven resources."""

    _abstract = True
    _footprint = [
        gvar,
    ]


class GenvModelGeoResource(ModelGeoResource):
    """Abstract class for gget driven resources."""

    _abstract = True
    _footprint = [
        gvar,
    ]


class GPSList(GenvModelResource):
    """
    Class of a GPS satellite ground coefficients. A Genvkey can be given.
    """

    _footprint = dict(
        info="Set of GPS coefficients",
        attr=dict(
            kind=dict(
                values=["gpslist", "listgpssol"],
                remap=dict(listgpssol="gpslist"),
            ),
            clscontents=dict(
                default=TextContent,
            ),
            gvar=dict(default="list_gpssol"),
        ),
    )

    @property
    def realkind(self):
        return "gpslist"


class MODESList(GenvModelResource):
    """
    Class of a MODE-S satellite white list for Bator.
    """

    _footprint = dict(
        info="Set of MODE-S coefficients",
        attr=dict(
            kind=dict(
                values=["modeslist", "listmodes"],
                remap=dict(listmodes="modeslist"),
            ),
            clscontents=dict(
                default=TextContent,
            ),
            gvar=dict(
                default="list_modes",
            ),
        ),
    )

    @property
    def realkind(self):
        return "modeslist"


class BatodbConf(GenvModelResource):
    """
    Default parameters for BATOR execution. A Genvkey can be given.
    """

    _footprint = dict(
        info="Batodb parametrization",
        attr=dict(
            kind=dict(
                values=["batodbconf", "batorconf", "parambator"],
                remap=dict(
                    parambator="batodbconf",
                    batorconf="batodbconf",
                ),
            ),
            clscontents=dict(
                default=TextContent,
            ),
            gvar=dict(default="param_bator_cfg"),
        ),
    )

    @property
    def realkind(self):
        return "batodbconf"


class BatorAveragingMask(GenvModelResource):
    """
    Configuration file that drives the averaging of radiances in Bator.'''
    """

    _footprint = dict(
        info="Definition file for the bator averaging",
        attr=dict(
            kind=dict(
                values=[
                    "avgmask",
                ]
            ),
            sensor=dict(),
            clscontents=dict(
                default=TextContent,
            ),
            gvar=dict(
                default="MASK_[sensor]",
            ),
        ),
    )

    @property
    def realkind(self):
        return "avgmask"


class AtmsMask(BatorAveragingMask):
    """Kept for backward compatibility with cy40 (see BatorAveragingMask)."""

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=["atms", "atmsmask"],
                remap=dict(atms="atmsmask"),
            ),
            sensor=dict(
                default="atms",
                optional=True,
            ),
        )
    )

    @property
    def realkind(self):
        return "atmsmask"


class RtCoef(GenvModelResource):
    """
    Class of a tar-zip file of satellite coefficients. A Genvkey can be given.
    """

    _footprint = dict(
        info="Set of satellite  coefficients",
        attr=dict(
            kind=dict(values=["rtcoef", "mwave_rtcoef"]),
            gvar=dict(default="[kind]_tgz"),
        ),
    )

    @property
    def realkind(self):
        return "rtcoef"


class RRTM(GenvModelResource):
    """
    Class of a tar-zip file of coefficients for radiative transfers computations.
    A Genvkey can be given.
    """

    _footprint = dict(
        info="Coefficients of RRTM scheme",
        attr=dict(
            kind=dict(
                values=[
                    "rrtm",
                ]
            ),
            gvar=dict(default="rrtm_const"),
        ),
    )

    @property
    def realkind(self):
        return "rrtm"


class CoefModel(GenvModelResource):
    """
    TODO.
    A Genvkey can be given.
    """

    _footprint = dict(
        info="Coefficients for some purpose... but which one ?",
        attr=dict(
            kind=dict(
                values=["coef_model", "coefmodel"],
                remap=dict(autoremap="first"),
            ),
            gvar=dict(default="coef_model"),
        ),
    )

    @property
    def realkind(self):
        return "coef_model"


class ScatCMod5(GenvModelResource):
    """
    TODO.
    A Genvkey can be given.
    """

    _footprint = dict(
        info="Coefficients for some purpose... but which one ?",
        attr=dict(
            kind=dict(
                values=["cmod5", "cmod5table", "scat_cmod5", "scatcmod5"],
                remap=dict(autoremap="first"),
            ),
            gvar=dict(default="scat_cmod5_table"),
        ),
    )

    @property
    def realkind(self):
        return "cmod5"


class BcorIRSea(GenvModelResource):
    """
    Obsolete.
    A Genvkey can be given.
    """

    _footprint = dict(
        info="Some bias ?",
        attr=dict(
            kind=dict(
                values=["bcor"],
            ),
            scope=dict(
                values=["irsea"],
            ),
            gvar=dict(default="bcor_meto_[scope]"),
        ),
    )

    @property
    def realkind(self):
        return "bcor_irsea"


class RmtbError(GenvModelResource):
    """
    Obsolete.
    A Genvkey can be given.
    """

    _footprint = dict(
        info="Some bias ?",
        attr=dict(
            kind=dict(
                values=["rmtberr"],
            ),
            scope=dict(
                values=["airs", "noaa"],
            ),
            gvar=dict(default="[scope]_rmtberr"),
        ),
    )

    @property
    def realkind(self):
        return "rmtberr"


class ChanSpectral(GenvModelResource):
    """
    Obsolete.
    A Genvkey can be given.
    """

    _footprint = dict(
        info="Coefficients for some purpose... but which one ?",
        attr=dict(
            kind=dict(
                values=["chanspec", "chan_spec"],
                remap=dict(autoremap="first"),
            ),
            scope=dict(
                optional=True,
                default="noaa",
                values=["noaa"],
            ),
            gvar=dict(default="[scope]_chanspec"),
        ),
    )

    @property
    def realkind(self):
        return "chanspec"


class Correl(GenvModelResource):
    """
    TODO.
    A Genvkey can be given.
    """

    _footprint = dict(
        info="Coefficients for some purpose... but which one ?",
        attr=dict(
            kind=dict(
                values=["correl"],
            ),
            scope=dict(
                optional=True,
                default="misc",
            ),
            gvar=dict(default="[scope]_correl"),
        ),
    )

    @property
    def realkind(self):
        return "correl"


class CstLim(GenvModelResource):
    """
    Obsolete.
    A Genvkey can be given.
    """

    _footprint = dict(
        info="Coefficients for some purpose... but which one ?",
        attr=dict(
            kind=dict(
                values=["cstlim", "cst_lim"],
                remap=dict(autoremap="first"),
            ),
            scope=dict(
                optional=True,
                default="noaa",
                values=["noaa"],
            ),
            gvar=dict(default="[scope]_cstlim"),
        ),
    )

    @property
    def realkind(self):
        return "cstlim"


class RszCoef(GenvModelResource):
    """
    Obsolete.
    A Genvkey can be given.
    """

    _footprint = dict(
        info="Coefficients for some purpose... but which one ?",
        attr=dict(
            kind=dict(
                values=["rszcoef", "rsz_coef"],
                remap=dict(autoremap="first"),
            ),
            gvar=dict(default="rszcoef_fmt"),
        ),
    )

    @property
    def realkind(self):
        return "rszcoef"


class RtCoefAirs(GenvModelResource):
    """
    Obsolete.
    A Genvkey can be given.
    """

    _footprint = dict(
        info="Coefficients for some purpose... but which one ?",
        attr=dict(
            kind=dict(
                values=["rtcoef_airs"],
            ),
            gvar=dict(default="rtcoef_airs_ieee"),
        ),
    )

    @property
    def realkind(self):
        return "rtcoef_airs"


class RtCoefAtovs(GenvModelResource):
    """
    Obsolete.
    A Genvkey can be given.
    """

    _footprint = dict(
        info="Coefficients for some purpose... but which one ?",
        attr=dict(
            kind=dict(
                values=["rtcoef_atovs"],
            ),
            gvar=dict(default="rtcoef_ieee_atovs"),
        ),
    )

    @property
    def realkind(self):
        return "rtcoef_atovs"


class SigmaB(GenvModelResource):
    """
    Obsolete.
    A Genvkey can be given.
    """

    _footprint = dict(
        info="Coefficients for some purpose... but which one ?",
        attr=dict(
            kind=dict(
                values=["sigmab", "sigma", "sigma_b"],
                remap=dict(autoremap="first"),
            ),
            gvar=dict(default="misc_sigmab"),
        ),
    )

    @property
    def realkind(self):
        return "sigmab"


class AtlasEmissivity(GenvModelResource):
    """
    Abstract class for any Emissivity atlas.
    """

    _abstract = True
    _footprint = dict(
        attr=dict(
            kind=dict(
                values=[
                    "atlas_emissivity",
                    "atlasemissivity",
                    "atlasemiss",
                    "emiss",
                    "emissivity_atlas",
                ],
                remap=dict(autoremap="first"),
            ),
        )
    )

    @property
    def realkind(self):
        return "atlas_emissivity"


class AtlasEmissivityGeneric(AtlasEmissivity):
    """
    A yearly emissivity atlas from a specific source.
    A Genvkey can be given.
    """

    _footprint = dict(
        info="Yearly emissivity atlas from a given source.",
        attr=dict(
            source=dict(
                values=["uwir", "telsem"],
            ),
            gvar=dict(default="[source]_emis_atlas"),
            month=dict(
                # This is a fake attribute that avoid warnings...
                values=[
                    None,
                ],
                optional=True,
                default=None,
                doc_visibility=footprints.doc.visibility.GURU,
            ),
        ),
    )


class AtlasEmissivityInstrument(AtlasEmissivity):
    """
    A yearly emissivity atlas for a specific instrument/sensor.
    A Genvkey can be given.
    """

    _footprint = dict(
        info="Yearly emissivity atlas for a given instrument(s).",
        attr=dict(
            instrument=dict(
                values=[
                    "seviri",
                    "ssmis",
                    "iasi",
                    "amsua",
                    "amsub",
                    "an1",
                    "an2",
                ],
                remap=dict(an1="amsua", an2="amsub"),
            ),
            gvar=dict(default="emissivity_atlas_[instrument]"),
            month=dict(
                # This is a fake attribute that avoid warnings...
                values=[
                    None,
                ],
                optional=True,
                default=None,
                doc_visibility=footprints.doc.visibility.GURU,
            ),
        ),
    )


class AtlasMonthlyEmissivityInstrument(AtlasEmissivityInstrument):
    """
    A monthly emissivity atlas for a specific instrument/sensor.
    A Genvkey can be given.
    """

    _footprint = [
        month_deco,
        dict(
            info="Monthly emissivity atlas for a given instrument(s).",
            attr=dict(
                gvar=dict(default="emissivity_atlas_[instrument]_monthly"),
            ),
        ),
    ]


class AtlasEmissivityPack(AtlasEmissivity):
    """
    Legacy yearly emissivity atlases for Amsu-A/B. DEPRECIATED.
    A Genvkey can be given.
    """

    _footprint = dict(
        info="Atlas of emissivity according to some pack of instrument(s).",
        attr=dict(
            pack=dict(
                values=["1", "2"],
            ),
            gvar=dict(default="emissivity[pack]"),
        ),
    )


class SeaIceLonLat(GenvModelGeoResource):
    """
    Coordinates of the file containing sea ice observations.
    It is used to create the ice_content file.
    """

    _footprint = dict(
        info="Coordinates used for ice_concent creation.",
        attr=dict(
            kind=dict(values=["seaice_lonlat"]),
            gvar=dict(default="sea_ice_lonlat"),
        ),
    )


class ODBRaw(GenvModelResource):
    """
    Class for static ODB layouts RSTBIAS, COUNTRYRSTRHBIAS, SONDETYPERSTRHBIAS.
    A GenvKey can be given.
    """

    _footprint = dict(
        info="ODB Raw bias",
        attr=dict(
            kind=dict(
                values=["odbraw"],
            ),
            layout=dict(
                values=[
                    "rstbias",
                    "countryrstrhbias",
                    "sondetyperstrhbias",
                    "RSTBIAS",
                    "COUNTRYRSTRHBIAS",
                    "SONDETYPERSTRHBIAS",
                ],
                remap=dict(
                    RSTBIAS="rstbias",
                    COUNTRYRSTRHBIAS="countryrstrhbias",
                    SONDETYPERSTRHBIAS="sondetyperstrhbias",
                ),
            ),
            gvar=dict(
                default="rs_bias_odbtable_[layout]",
            ),
        ),
    )

    @property
    def realkind(self):
        return "odbraw"


@namebuilding_delete("fmt")
@namebuilding_insert("radical", lambda s: "matfil")
@namebuilding_append(
    "geo",
    lambda s: [
        s.scope.area,
    ],
)
class MatFilter(GenvModelGeoResource):
    """
    Class of a filtering matrix. A GaussGeometry object is needed,
    as well as the LonlatGeometry of the scope domain (containing the
    filtering used).
    A GenvKey can be given.
    """

    _footprint = dict(
        info="Filtering matrix",
        attr=dict(
            model=dict(
                optional=True,
            ),
            kind=dict(values=["matfilter"]),
            geometry=dict(type=GaussGeometry),
            scope=dict(
                type=LonlatGeometry,
            ),
            gvar=dict(default="mat_filter_[scope::area]"),
        ),
    )

    @property
    def realkind(self):
        return "matfilter"

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return (
            "matrix.fil."
            + self.scope.area
            + ".t{!s}".format(self.geometry.truncation)
            + ".c{!s}".format(self.geometry.stretching)
        )


class WaveletTable(GenvModelGeoResource):
    """
    Wavelet covariance operators: auto-correlations of the control variable.
    A GenvKey can be given.
    """

    _footprint = dict(
        info="Wavelet covariance operators",
        attr=dict(
            kind=dict(
                values=[
                    "wtable",
                    "wavelettable",
                    "wavelet_table",
                    "rtable",
                    "rtabwavelet",
                ],
                remap=dict(autoremap="first"),
            ),
            gvar=dict(default="RTABLE_WAVELET"),
        ),
    )

    @property
    def realkind(self):
        return "wtable"


class AmvError(GenvModelGeoResource):
    """
    TODO.
    A Genvkey can be given.
    """

    _footprint = dict(
        info="AMV Tracking Error",
        attr=dict(
            kind=dict(
                values=["amvtrackingerror", "amvtr", "amverror", "amv_error"],
                remap=dict(
                    amvtrackingerror="amv_error",
                    amvtr="amv_error",
                    amverror="amv_error",
                ),
            ),
            gvar=dict(
                default="amv_tracking_error",
            ),
        ),
    )

    @property
    def realkind(self):
        return "amv_error"


class AmvBias(GenvModelGeoResource):
    """
    TODO.
    A Genvkey can be given.
    """

    _footprint = dict(
        info="AMV Tracking Error",
        attr=dict(
            kind=dict(
                values=["amvbias", "amv_bias"],
                remap=dict(amvbias="amv_bias"),
            ),
            gvar=dict(default="amv_bias_info"),
        ),
    )

    @property
    def realkind(self):
        return "amv_bias"


class LFIScripts(StaticResource):
    """
    The LFI scripts. A Genvkey can be given.
    """

    _footprint = [
        gvar,
        dict(
            info="LFI scripts",
            attr=dict(
                kind=dict(
                    values=[
                        "lfiscripts",
                    ],
                ),
                gvar=dict(default="tools_lfi"),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "lfiscripts"


class FilteringRequest(GenvModelResource):
    """
    Class of a JSON file that describes a resource filter. A Genvkey can be given.
    """

    _footprint = dict(
        info="Description of a resource's data filter",
        attr=dict(
            kind=dict(
                values=[
                    "filtering_request",
                ],
            ),
            filtername=dict(),
            nativefmt=dict(
                values=[
                    "json",
                ],
                default="json",
            ),
            clscontents=dict(
                default=JsonDictContent,
            ),
            gvar=dict(default="filtering_request"),
        ),
    )

    @property
    def realkind(self):
        return "filtering_request"

    def gget_urlquery(self):
        """GGET specific query : ``extract``."""
        return "extract=filter_{:s}.json".format(self.filtername)


class GribAPIConfig(StaticResource):
    """
    Configuration files for the Grib-API (samples or definitions)
    """

    _footprint = [
        gvar,
        dict(
            info="Grib-API configuration files",
            attr=dict(
                kind=dict(
                    values=[
                        "gribapiconf",
                    ],
                ),
                target=dict(
                    values=["samples", "def", "definitions"],
                    remap=dict(definitions="def"),
                ),
                gvar=dict(default="grib_api_[target]"),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "gribapiconf"


class StdPressure(GenvModelGeoResource):
    """
    Standard pressure profile for standard error truncation extrapolation.
    A GenvKey can be given.
    """

    _footprint = dict(
        info="Standard pressure profile",
        attr=dict(
            kind=dict(
                values=["stdpressure"],
            ),
            level=dict(
                type=int,
                optional=True,
                default=60,
                values=[60],
            ),
            gvar=dict(default="std_pressure"),
        ),
    )

    @property
    def realkind(self):
        return "stdpressure"


class TruncObj(GenvModelGeoResource):
    """
    Standard error truncation (spectral filtering).
    A GenvKey can be given.
    """

    _footprint = dict(
        info="Standard error truncation",
        attr=dict(
            kind=dict(
                values=["truncobj", "stderr_trunc"],
            ),
            gvar=dict(default="trunc_obj"),
        ),
    )

    @property
    def realkind(self):
        return "truncobj"


class InterChannelsCorrelations(GenvModelResource):
    """
    Inter channels correlations for a specific instrument/sensor.
    A Genvkey can be given.
    """

    _footprint = dict(
        info="Inter channel correlations for a given instrument.",
        attr=dict(
            kind=dict(
                values=[
                    "correlations",
                ],
            ),
            instrument=dict(
                values=[
                    "cris",
                    "iasi",
                ],
            ),
            gvar=dict(default="correlations_[instrument]"),
            clscontents=dict(
                default=DataRaw,
            ),
        ),
    )

    @property
    def realkind(self):
        return "correlations"


class SunMoonPositionCoeff(StaticResource):
    """
    Coefficients of the Chebyshev polynomials used to calculate the position of the moon and the sun.
    """

    _footprint = [
        gvar,
        dict(
            info="Chebyshev polynomials for the moon and sun position",
            attr=dict(
                kind=dict(
                    values=[
                        "sunmoonpositioncoeffs",
                    ],
                ),
                gvar=dict(
                    default="sun_moon_position_tgz",
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "sunmoonpositioncoeffs"
