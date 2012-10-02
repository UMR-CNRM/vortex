#!/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

from vortex.data.resources import Resource
from vortex.data.flow import FlowResource
from vortex.data.outflow import NoDateResource
from vortex.syntax.stdattrs import domain, model, month, truncation
from vortex.syntax.stdattrs import cutoff, date


class Analysis(FlowResource):

    _footprint = [
        model,
        cutoff,
        date,
        dict(
            info = 'Atmospheric Analysis',
            attr = dict(
                kind = dict(
                    values = [ 'analysis', 'analyse', 'atm_analysis' ]
                ),
                geometry = dict(
                    values = [ 'france' ]
                ),
            )
        )
    ]
    
    @classmethod
    def realkind(cls):
        return 'analysis'

    def iga_basename(self):
        """
        The cutoff value was validated. It can be used so as to create the
        dictionary for creating the correct suffix.
        """
        if self.cutoff == 'assim':
            map_suffix = dict(
                zip(
                    zip(
                        (self.cutoff,)*4,
                        (0, 6, 12, 18)
                    ),
                    ('r00', 'r06', 'r12','r18')
                )
            )
        else:
            map_suffix = dict(
                zip(
                    zip(
                        (self.cutoff,)*4,
                        (0, 6, 12, 18)
                    ),
                    ('rAM', 'rSX' , 'rPM', 'rDH')
                )
            )
        reseau = self.date.hour
        #suffix choice
        suffix = map_suffix[(self.cutoff, reseau)]
        if self.model == 'arpege':
            model_info = 'ARPE'
        elif self.model == 'arome':
            model_info = 'AROM'
        elif self.model == 'aladin':
            model_info = 'ALAD'
        localname = 'ICMSH' + model_info + 'INIT.' + suffix
        return localname

    def iga_pathinfo(self):
        return dict(
            model = self.model,
            geometry = self.geometry
        )

    def olive_basename(self):
        return 'analyse'


class MatFilter(Resource):

    _footprint = [
        domain,
        model,
        dict(
            info = 'Filtering matrix',
            attr = dict(
              	kind = dict(
                    values = [ 'matfilter',  ]
              	),
                geometry = dict(
                    values = [ 'france' ]
                )
            )
        )
    ]

    @classmethod
    def realkind(cls):
        return 'matfilter'

    def iga_basename(self):
        localname = 'matrix.fil.' + self.domain
        return localname

    def iga_pathinfo(self):
        return dict(
            kind = self.realkind(),
            model = self.model,
            geometry = self.geometry
        )

class RtCoef(Resource):

    _footprint = [
        model,
        dict(
            info = 'Satellite  coefficients',
            attr = dict(
              	kind = dict(
                    values = [ 'rtcoef' ]
              	),
                geometry = dict(
                    values = [ 'france' ]
                )
            )
        )
    ]

    @classmethod
    def realkind(cls):
        return 'rtcoef'

    def iga_basename(self):
        return self.realkind() + '.tar'

    def iga_pathinfo(self):
        return dict(
            model = self.model,
            geometry = self.geometry
        )

class Namelist(Resource):
        
    _footprint = [
        model,
        dict(
            info = 'Namelist',
            attr = dict(
                kind = dict(
                    values = [ 'namelist', 'namel' ]
                ),
                geometry = dict(
                    values = [ 'france' ]
                )
            )
        )
    ]

    @classmethod
    def realkind(cls):
        return 'namelist'

    def iga_pathinfo(self):
        return dict(
            model = self.model,
            geometry = self.geometry
        )

class NamFcp(Namelist):

    _footprint = dict(
        info = 'Namelist fcp',
        attr = dict(
            kind = dict(
                values = [ 'namelistfcp' ]
            )
        )
    )

    def iga_basename(self):
        return 'namelistfcp'
     

class NamSelect(Namelist):

    _footprint = dict(
        info = 'Namelist select',
        attr = dict(
            kind = dict(
        	    values = [ 'namselect', 'namel_select']
            )
        )
    )

    def iga_basename(self):
        return 'namelselect'
     

class Clim(NoDateResource):

    _footprint = [
        model,
        month,
        dict(
            info = 'Climatology file',
            attr = dict(
                kind = dict(
                    values = [ 'clim' ],
                ),
                geometry = dict(
                    values = [ 'france' ]
                )
            )
        )
    ]

    @classmethod
    def realkind(cls):
        return 'clim'

class ClimModel(Clim):

    _footprint = [
        truncation,
        model,
        dict(
            info = 'Model climatology',
            attr = dict(
                kind = dict(
                    values = [ 'clim_model', 'climmodel', 'climodel','modelclim', 'model_clim' ]
                )
            )
        )
    ]

    @classmethod
    def realkind(cls):
        return 'climmodel'

    def iga_basename(self):
        localname = 'clim_t' + str(self.truncation) + '_isba' + str(self.month)
        return localname

    def iga_pathinfo(self):
        return dict(
            model = self.model,
            geometry = self.geometry
        )

class ClimBDAP(Clim):

    _footprint = [
        domain,
        dict(
            info = 'BDAP climatology',
            attr = dict(
                kind = dict(
                    values = [ 'clim_bdap', 'climbdap','bdapclim','bdap_clim' ]
                )
            )
        )
    ]

    @classmethod
    def realkind(cls):
        return 'climdomain'

    def iga_basename(self):
        localname = 'const.clim.' + self.domain + '_m' + str(self.month)
        return localname

    def iga_pathinfo(self):
        return dict(
            model = self.model,
            geometry = self.geometry
        )
