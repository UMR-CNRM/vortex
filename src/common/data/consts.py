#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

from vortex.data.resources  import Resource
from vortex.data.outflow    import ModelResource, StaticGeoResource
from vortex.data.geometries import LonlatGeometry, GaussGeometry
from vortex.data.contents   import TextContent, JsonDictContent

from gco.syntax.stdattrs    import gvar


class GenvModelResource(ModelResource):
    """Abstract class for gget driven resources."""

    _abstract  = True
    _footprint = [ gvar, ]


class GenvStaticGeoResource(StaticGeoResource):
    """Abstract class for gget driven resources."""

    _abstract  = True
    _footprint = [ gvar, ]


class GPSList(GenvModelResource):
    """
    Class of a GPS satellite ground coefficients. A Genvkey can be given.
    """
    _footprint = dict(
        info = 'Set of GPS coefficients',
        attr = dict(
            kind = dict(
                values  = ['gpslist', 'listgpssol'],
                remap   = dict(listgpssol = 'gpslist'),
            ),
            clscontents = dict(
                default = TextContent,
            ),
            gvar = dict(
                default = 'list_gpssol'
            ),
        )
    )

    @property
    def realkind(self):
        return 'gpslist'


class BatodbConf(GenvModelResource):
    """
    Default parameters for BATOR execution. A Genvkey can be given.
    """
    _footprint = dict(
        info = 'Batodb parametrization',
        attr = dict(
            kind = dict(
                values  = ['batodbconf', 'batorconf', 'parambator'],
                remap   = dict(
                    parambator = 'batodbconf',
                    batorconf  = 'batodbconf',
                ),
            ),
            clscontents = dict(
                default = TextContent,
            ),
            gvar = dict(
                default = 'param_bator_cfg'
            ),
        )
    )

    @property
    def realkind(self):
        return 'batodbconf'


class BatorAveragingMask(GenvModelResource):
    """
    Configuration file that drives the averaging of radiances in Bator.'''
    """
    _footprint = dict(
        info = 'Definition file for the bator averaging',
        attr = dict(
            kind = dict(
                values  = [ 'avgmask', ]
            ),
            sensor = dict(
                values  = [ 'atms', 'ssmis', ]
            ),
            clscontents = dict(
                default = TextContent,
            ),
            gvar = dict(
                default = 'MASK_[sensor]',
            ),
        )
    )

    @property
    def realkind(self):
        return 'avgmask'


class AtmsMask(BatorAveragingMask):
    """Kept for backward compatibility with cy40 (see BatorAveragingMask)."""
    _footprint = dict(
        attr = dict(
            kind = dict(
                values   = [ 'atms', 'atmsmask', ],
                remap    = dict(atms='atmsmask'),
            ),
            sensor = dict(
                default  = 'atms',
                optional = True,
            ),
        )
    )

    @property
    def realkind(self):
        return 'atmsmask'


class RtCoef(GenvModelResource):
    """
    Class of a tar-zip file of satellite coefficients. A Genvkey can be given.
    """
    _footprint = dict(
        info = 'Set of satellite  coefficients',
        attr = dict(
            kind = dict(
                values  = [ 'rtcoef' ]
            ),
            gvar = dict(
                default = 'rtcoef_tgz'
            ),
        )
    )

    @property
    def realkind(self):
        return 'rtcoef'


class RRTM(GenvModelResource):
    """
    Class of a tar-zip file of coefficients for radiative transfers computations.
    A Genvkey can be given.
    """
    _footprint = dict(
        info = 'Coefficients of RRTM scheme',
        attr = dict(
            kind = dict(
                values  = [ 'rrtm' ]
            ),
            gvar = dict(
                default = 'rrtm_const'
            ),
        )
    )

    @property
    def realkind(self):
        return 'rrtm'


class CoefModel(GenvModelResource):
    """
    TODO.
    A Genvkey can be given.
    """
    _footprint = dict(
        info = 'Coefficients for some purpose... but which one ?',
        attr = dict(
            kind = dict(
                values  = ['coef_model', 'coefmodel'],
                remap   = dict(autoremap = 'first'),
            ),
            gvar = dict(
                default = 'coef_model'
            ),
        )
    )

    @property
    def realkind(self):
        return 'coef_model'


class ScatCMod5(GenvModelResource):
    """
    TODO.
    A Genvkey can be given.
    """
    _footprint = dict(
        info = 'Coefficients for some purpose... but which one ?',
        attr = dict(
            kind = dict(
                values  = ['cmod5', 'cmod5table', 'scat_cmod5', 'scatcmod5'],
                remap   = dict(autoremap = 'first'),
            ),
            gvar = dict(
                default = 'scat_cmod5_table'
            ),
        )
    )

    @property
    def realkind(self):
        return 'cmod5'


class BcorIRSea(GenvModelResource):
    """
    TODO.
    A Genvkey can be given.
    """
    _footprint = dict(
        info = 'Some bias ?',
        attr = dict(
            kind = dict(
                values  = ['bcor'],
            ),
            scope = dict(
                values  = ['irsea'],
            ),
            gvar = dict(
                default = 'bcor_meto_[scope]'
            ),
        )
    )

    @property
    def realkind(self):
        return 'bcor_irsea'


class RmtbError(GenvModelResource):
    """
    TODO.
    A Genvkey can be given.
    """
    _footprint = dict(
        info = 'Some bias ?',
        attr = dict(
            kind = dict(
                values  = ['rmtberr'],
            ),
            scope = dict(
                values  = ['airs', 'noaa'],
            ),
            gvar = dict(
                default = '[scope]_rmtberr'
            ),
        )
    )

    @property
    def realkind(self):
        return 'rmtberr'


class ChanSpectral(GenvModelResource):
    """
    TODO.
    A Genvkey can be given.
    """
    _footprint = dict(
        info = 'Coefficients for some purpose... but which one ?',
        attr = dict(
            kind = dict(
                values   = ['chanspec', 'chan_spec'],
                remap    = dict(autoremap = 'first'),
            ),
            scope = dict(
                optional = True,
                default  = 'noaa',
                values   = ['noaa'],
            ),
            gvar = dict(
                default  = '[scope]_chanspec'
            ),
        )
    )

    @property
    def realkind(self):
        return 'chanspec'


class Correl(GenvModelResource):
    """
    TODO.
    A Genvkey can be given.
    """
    _footprint = dict(
        info = 'Coefficients for some purpose... but which one ?',
        attr = dict(
            kind = dict(
                values   = ['correl'],
            ),
            scope = dict(
                optional = True,
                default  = 'misc',
                values   = ['misc'],
            ),
            gvar = dict(
                default  = '[scope]_correl'
            ),
        )
    )

    @property
    def realkind(self):
        return 'correl'


class CstLim(GenvModelResource):
    """
    TODO.
    A Genvkey can be given.
    """
    _footprint = dict(
        info = 'Coefficients for some purpose... but which one ?',
        attr = dict(
            kind = dict(
                values   = ['cstlim', 'cst_lim' ],
                remap    = dict(autoremap = 'first'),
            ),
            scope = dict(
                optional = True,
                default  = 'noaa',
                values   = ['noaa'],
            ),
            gvar = dict(
                default  = '[scope]_cstlim'
            ),
        )
    )

    @property
    def realkind(self):
        return 'cstlim'


class RszCoef(GenvModelResource):
    """
    TODO.
    A Genvkey can be given.
    """
    _footprint = dict(
        info = 'Coefficients for some purpose... but which one ?',
        attr = dict(
            kind = dict(
                values  = ['rszcoef', 'rsz_coef' ],
                remap   = dict(autoremap = 'first'),
            ),
            gvar = dict(
                default = 'rszcoef_fmt'
            ),
        )
    )

    @property
    def realkind(self):
        return 'rszcoef'


class RtCoefAirs(GenvModelResource):
    """
    TODO.
    A Genvkey can be given.
    """
    _footprint = dict(
        info = 'Coefficients for some purpose... but which one ?',
        attr = dict(
            kind = dict(
                values  = ['rtcoef_airs'],
            ),
            gvar = dict(
                default = 'rtcoef_airs_ieee'
            ),
        )
    )

    @property
    def realkind(self):
        return 'rtcoef_airs'


class RtCoefAtovs(GenvModelResource):
    """
    TODO.
    A Genvkey can be given.
    """
    _footprint = dict(
        info = 'Coefficients for some purpose... but which one ?',
        attr = dict(
            kind = dict(
                values  = ['rtcoef_atovs'],
            ),
            gvar = dict(
                default = 'rtcoef_ieee_atovs'
            ),
        )
    )

    @property
    def realkind(self):
        return 'rtcoef_atovs'


class SigmaB(GenvModelResource):
    """
    TODO.
    A Genvkey can be given.
    """
    _footprint = dict(
        info = 'Coefficients for some purpose... but which one ?',
        attr = dict(
            kind = dict(
                values  = ['sigmab', 'sigma', 'sigma_b'],
                remap   = dict(autoremap = 'first'),
            ),
            gvar = dict(
                default = 'misc_sigmab'
            ),
        )
    )

    @property
    def realkind(self):
        return 'sigmab'


class AtlasEmissivity(GenvModelResource):
    """
    TODO.
    A Genvkey can be given.
    """
    _abstract  = True
    _footprint = dict(
        info = 'Atlas of emissitivity according to some pack of instrument(s).',
        attr = dict(
            kind = dict(
                values   = ['atlas_emissivity', 'atlasemissivity',
                            'atlasemiss', 'emiss'],
                remap    = dict(autoremap = 'first'),
            ),
        )
    )

    @property
    def realkind(self):
        return 'atlas_emissivity'


class AtlasEmissivityInstrument(AtlasEmissivity):
    """
    TODO.
    A Genvkey can be given.
    """
    _footprint = dict(
        info = 'Atlas of emissitivity according to some pack of instrument(s).',
        attr = dict(
            instrument = dict(
                values  = ['seviri', 'ssmis'],
            ),
            gvar = dict(
                default = 'emissivity_atlas_[instrument]'
            ),
        )
    )


class AtlasEmissivityPack(AtlasEmissivity):
    """
    TODO.
    A Genvkey can be given.
    """
    _footprint = dict(
        info = 'Atlas of emissitivity according to some pack of instrument(s).',
        attr = dict(
            pack   = dict(
                values   = ['1', '2'],
            ),
            gvar = dict(
                default  = 'emissivity[pack]'
            ),
        )
    )


class ODBRaw(GenvModelResource):
    """
    Class for static ODB layouts RSTBIAS, COUNTRYRSTRHBIAS, SONDETYPERSTRHBIAS.
    A GenvKey can be given.
    """
    _footprint = dict(
        info = 'ODB Raw bias',
        attr = dict(
            kind = dict(
                values  = ['odbraw'],
            ),
            layout = dict(
                values  = [
                    'rstbias', 'countryrstrhbias', 'sondetyperstrhbias',
                    'RSTBIAS', 'COUNTRYRSTRHBIAS', 'SONDETYPERSTRHBIAS',
                ],
                remap   = dict(
                    RSTBIAS = 'rstbias',
                    COUNTRYRSTRHBIAS = 'countryrstrhbias',
                    SONDETYPERSTRHBIAS = 'sondetyperstrhbias',
                ),
            ),
            gvar = dict(
                default = 'rs_bias_odbtable_[layout]',
            )
        )
    )

    @property
    def realkind(self):
        return 'odbraw'


class MatFilter(GenvStaticGeoResource):
    """
    Class of a filtering matrix. A GaussGeometry object is needed,
    as well as the LonlatGeometry of the scope domain (containing the
    filtering used).
    A GenvKey can be given.
    """

    _footprint = dict(
        info = 'Filtering matrix',
        attr = dict(
            model = dict(
                optional = True,
            ),
            kind = dict(
                values   = ['matfilter']
            ),
            geometry = dict(
                type     = GaussGeometry
            ),
            scope = dict(
                type     = LonlatGeometry,
            ),
            gvar = dict(
                default  = 'mat_filter_[scope::area]'
            )
        )
    )

    @property
    def realkind(self):
        return 'matfilter'

    def basename_info(self):
        """Generic information, radical = ``matfil``."""
        return dict(
            geo     = [{'truncation': self.geometry.truncation},
                       {'stretching': self.geometry.stretching},
                       self.scope.area, {'filtering': self.scope.filtering}],
            radical = 'matfil',
            src     = self.model,
        )

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'matrix.fil.' + self.scope.area + '.t' + str(self.geometry.truncation) + \
               '.c' + str(self.geometry.stretching)


class Stabal(GenvStaticGeoResource):
    """
    TODO.
    A GenvKey can be given.
    """

    _footprint = dict(
        info = 'Yeap... some info required for stabal coef.',
        attr = dict(
            kind = dict(
                values = ['stabal'],
            ),
            stat = dict(
                values = ['bal', 'cv'],
            ),
            level = dict(
                type     = int,
                optional = True,
                default  = 96,
                values   = [41, 96],
            ),
            gvar = dict(
                default  = 'stabal[level]_[stat]'
            ),
        )
    )

    @property
    def realkind(self):
        return 'stabal'


class WaveletTable(GenvStaticGeoResource):
    """
    TODO.
    A GenvKey can be given.
    """

    _footprint = dict(
        info = 'Yeap... some info required for wavelet table coefs.',
        attr = dict(
            kind = dict(
                values = ['wtable', 'wavelettable', 'wavelet_table', 'rtable', 'rtabwavelet'],
                remap  = dict(autoremap = 'first'),
            ),
            gvar = dict(
                default  = 'RTABLE_WAVELET'
            ),
        )
    )

    @property
    def realkind(self):
        return 'wtable'


class AmvError(GenvStaticGeoResource):
    """
    TODO.
    A Genvkey can be given.
    """
    _footprint = dict(
        info='AMV Tracking Error',
        attr=dict(
            kind=dict(
                values=['amvtrackingerror', 'amvtr', 'amverror', 'amv_error'],
                remap=dict(
                    amvtrackingerror='amv_error',
                    amvtr='amv_error',
                    amverror='amv_error',
                ),
            ),
            gvar=dict(
                default='amv_tracking_error',
            ),
        )
    )

    @property
    def realkind(self):
        return 'amv_error'


class AmvBias(GenvStaticGeoResource):
    """
    TODO.
    A Genvkey can be given.
    """
    _footprint = dict(
        info='AMV Tracking Error',
        attr=dict(
            kind=dict(
                values=['amvbias', 'amv_bias'],
                remap=dict(amvbias='amv_bias'),
            ),
            gvar=dict(
                default='amv_bias_info'
            ),
        )
    )

    @property
    def realkind(self):
        return 'amv_bias'


class LFIScripts(Resource):
    """
    The LFI scripts. A Genvkey can be given.
    """
    _footprint = [
        gvar,
        dict(
            info='LFI scripts',
            attr=dict(
                kind=dict(
                    values=['lfiscripts', ],
                ),
                gvar=dict(
                    default='tools_lfi'
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'lfiscripts'


class FilteringRequest(GenvModelResource):
    """
    Class of a JSON file that describes a resource filter. A Genvkey can be given.
    """
    _footprint = dict(
        info = "Description of a resource's data filter",
        attr = dict(
            kind = dict(
                values  = ['filtering_request', ],
            ),
            filtername = dict(
            ),
            nativefmt = dict(
                values = ['json', ],
                default = 'json',
            ),
            clscontents = dict(
                default = JsonDictContent,
            ),
            gvar = dict(
                default = 'filtering_request_[filtername]'
            ),
        )
    )

    @property
    def realkind(self):
        return 'filtering_request'
