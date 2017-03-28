#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.data.flow import FlowResource, GeoFlowResource
from vortex.data.outflow import NoDateResource
from vortex.data.resources import Resource
from common.data.consts import GenvModelResource
from common.data.obs import Observations
from vortex.syntax.stdattrs import term, a_date

_domain_map = dict(alp='_al', pyr='_py', cor='_co')



class DomCoords(GenvModelResource):
    """Class for the ebauche file (P ou E file) that is used by SAFRAN."""

    _footprint = dict(
        info = 'Safran ebauche',
        attr = dict(
            kind = dict(
                values = ['domdesc'],
            ),
            nativefmt = dict(
                values  = ['ascii'],
                default = 'ascii',
            ),
            model = dict(
                values  = ['safran'],
            ),
        )
    )

    @property
    def realkind(self):
        return 'domdesc'

class List(Resource):
    
    _footprint = dict(
        info = 'Listing file used by  Safran.',
        attr = dict(
            kind = dict(
                values = ['listem', 'lystem', 'listeo', 'lysteo', 'listeml', 'lysteml', 'rsclim', 'icrccm'],
            ),
            nativefmt = dict(
                values  = ['ascii'],
                default = 'ascii',
            ),
        )
    )


    def genv_basename(self):
        return self.kind.upper()


class Dirext(NoDateResource):

    _footprint = dict(
        info = 'Safran directives for the BDAP extraction of P files',
        attr = dict(
            kind = dict(
                values = ['dirext'],
            ),
            nativefmt = dict(
                values  = ['ascii'],
                default = 'ascii',
            ),
        )
    )

    @property
    def realkind(self):
        return 'domdesc'


class Ebauche(GeoFlowResource):
    """Class for the ebauche file (P ou E file) that is used by SAFRAN."""

    _footprint = [
        term,
        dict(
            info = 'Safran ebauche',
            attr = dict(
                kind = dict(
                    values = ['ebauche'],
                ),
                nativefmt = dict(
                    values  = ['ascii'],
                    default = 'ascii',
                ),
                model = dict(
                    values = ['pearp', 'arpege', 'cep'],
                ),
                vconf = dict(
                    values = ['alp', 'pyr', 'cor'],
                ),
                realdate = a_date,
            )

        ) 
    ]

    @property
    def realkind(self):
        return 'ebauche'

    @property
    def path_suffixe(self):
        return _domain_map[self.vconf]

#    def vortex_basename(self):
#        return 'mb' + member + '/P' + self.date.yymdh + str(self.term)[:2] 

    def basename_info(self):
        return dict(
            radical = self.realkind,
            geo     = self.vconf,
            src     = self.model,
            term    = self.term,
            date    = self.date,
        )
#        return 'P' + self.date.yymdh + str(self.term)[:2]


class Sapfile(Resource):
    """Class for the sapxxx files used by SAFRAN."""

    _footprint = [
#        term,
        dict(
            info = 'description for Safran',
            attr = dict(
                kind = dict(
                    values = ['sapdat', 'sapfich'],
                ),
                nativefmt = dict(
                    values  = ['ascii'],
                    default = 'ascii',
                ),
            )
        )
    ]
    
    @property
    def realkind(self):
        return self.kind


class OPfile(Resource):
    """Class for the 'OPxxxx' files containing links used by SAFRAN."""

    _footprint = [
        dict(
            info = 'OPxxxx files for Safran',
            attr = dict(
                kind = dict(
                    values = ['opfile'],
                ),
                nativefmt = dict(
                    values  = ['ascii'],
                    default = 'ascii',
                ),
            )
        )
    ]


class Safran(GeoFlowResource):
    """Class for the safrane output files."""

    _footprint = [
        term,
        dict(
            info = 'Safrane output',
            attr = dict(
                kind = dict(
                    values = ['analysis', 'interpolation', 'interp'],
                ),
                nativefmt = dict(
                    values  = ['netcdf'],
                    default = 'netcdf',
                ),
                model = dict(
                    values = ['s2m', 'safran'],
                ),
                vconf = dict(
                    values = ['alp', 'pyr', 'cor'],
                ),
                realdate = a_date,
            )
        )
    ]



    @property
    def realkind(self):
        return 'analysis'
#
#    @property
#    def path_suffixe(self):
#        return _domain_map[self.vconf]
#
#    def vortex_basename(self):
#        return 'P' + self.date.yymdh + str(self.term)[:2]
#
    def basename_info(self):
        return dict(
            radical = self.realkind,
            geo     = self.vconf,
            src     = self.model,
            term    = self.term,
        )




class Met(GeoFlowResource):
    """Class for the met or MET files produced by SAFRAN."""

    _footprint = [
        term,
        dict(
            info = 'Safran ebauche',
            attr = dict(
                kind = dict( 
                    values = ['met', 'MET', 'metcli'],
                ),
                nativefmt = dict(
                    values  = ['grib', 'netcdf', 'unknown'],
                    default = 'grib',
                ),
                model = dict(
                    values = ['safran'],
                ),
                vconf = dict(
                    values = ['alp', 'pyr', 'cor'],
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'met'

    @property
    def path_suffixe(self):
        return _domain_map[self.vconf]

    def vortex_basename(self):
        return 'met' + self.path_suffixe + '.tar.xz'

    def basename_info(self):
        return dict(
            radical = self.realkind,
            geo     = self.vconf,
            src     = self.model,
            term    = self.term,
        )



class RadioSondages(Observations):
    """Alti files (A files)"""

    _footprint = dict(
        info = 'Safran Alti',
        attr = dict(
            kind = dict(
                values = ['alti', 'altitude', 'radiosondage', 'RS'],    
            ),
            nativefmt = dict(
                values  = ['ascii'],
                default = 'ascii',
            ),
            part = dict(
                info     = 'The name of this subset of observations.',
                optional = True,
                values   = ['full', 'all'],
                default  = 'all',                 
            ),
            stage = dict(
                info     = 'The processing stage for this subset of observations.',
                optional = True,
                stage    = ['safrane', 'analysis'],
                default  = 'analysis',
            ),
        )
    )

    @property
    def realkind(self):
        return 'radiosondage'

    def basename_info(self):
        return dict(
            radical = 'A' + self.date.yymdh,
        )

 
