#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.tools.date      import Time
from vortex.data.flow       import SpectralGeoFlowResource, FlowResource
from vortex.data.contents   import JsonDictContent
from vortex.syntax.stdattrs import FmtInt
from common.data.modelstates       import Historic

class SingularVector(SpectralGeoFlowResource):
    """
    Generic class for resources internal to singular vectors.
    """
    _footprint = dict(
        info = 'Singular vector',
        attr = dict(
            kind = dict(
                values  = ['svector'],
            ),
            number = dict(
                type     = int,
            ),
            zone = dict(
                values  = ['ateur', 'hnc', 'hs', 'pno', 'oise', 'an', 'pne', 'oiso', 'ps', 'oin','trop1','trop2','trop3','trop4'],
            ),
            nativefmt = dict(
                values  = ['fa', 'lfi', 'grib'],
                default = 'fa',
            ),
            term = dict(
                type = Time,
                optional = True,
                default = Time(0)    
            )
        )
    )

    @property
    def realkind(self):
        return 'svector'

    def basename_info(self):
        """Generic information for names fabric."""
        return dict(
            radical   = self.realkind + '-' + self.zone,
            fmt     = self.nativefmt,
            geo       = [{'truncation': self.geometry.truncation}, {'stretching': self.geometry.stretching}],
            src       = self.model,
            number    = self.number,
        )

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'SVARPE'  + '{0:03d}'.format(self.number) + '+0000'

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return 'SVARPE'  + '{0:03d}'.format(self.number) + '+0000'

class PerturbedState(Historic):
    """
    Class for numbered historic resources, for example perturbations or perturbed states of the EPS.
    """
    _footprint = dict(
        info = 'Perturbation or perturbed state',
        attr = dict(
            kind = dict(
                values  = ['perturbation', 'perturbed_historic', 'perturbed_state', 'pert'],
                 remap = dict(autoremap = 'first')
            ),
            number = dict(
                type    = FmtInt,
                args    = dict(fmt = '03'),
            ),
            term = dict(
                type = Time,
                optional = True,
                default = Time(0)    
            )
        )
    )

    @property
    def realkind(self):
        return 'perturbation'
    
    def basename_info(self):
        """Generic information for names fabric."""
        d = super(PerturbedState, self).basename_info()
        d['number'] = self.number
        return d
    
    #TODO XXX_basename: pert were previously tar files

class InitialCondition(SpectralGeoFlowResource):
    """
    Class for initial condition resources : anything from which a model run can be performed.
    """
    _footprint = dict(
       info = 'Initial condition',
       attr = dict(
           kind = dict(
               values   = ['initial_condition', 'ic', 'starting_point'],
               remap = dict(
                        remap    = dict(autoremap = 'first'),
                    )
           ),
           nativefmt = dict(
               values   = ['fa', 'grib', 'lfi'],
               default  = 'fa',
           )
        )
    )

    @property
    def realkind(self):
        return 'ic'

    @property
    def term(self):
        """Fake term for duck typing."""
        return Time(0)

#TODO: the number is only known by the provider
#     def archive_basename(self):
#         """OP ARCHIVE specific naming convention."""
#         if self.vapp == 'pearp':
#             icname = 'ICFC_'
#         return icname
# 
#     def olive_basename(self):
#         """OLIVE specific naming convention."""
#         if self.vapp == 'pearp':
#             icname = 'ICFC_'
#         return icname

    def basename_info(self):
        """Generic information, radical = ``analysis``."""
        return dict(
            fmt     = self.nativefmt,
            geo     = [{'truncation': self.geometry.truncation}, {'stretching': self.geometry.stretching}],
            radical = self.realkind,
            src     = self.model,
        )
        
class NormCoeff(FlowResource):
    """
    Coefficient used to normalize the singular vectors or the bred modes.
    """

    _footprint = dict(
        info = 'Perturbations Coefficient',
        attr = dict(
            kind = dict(
                values   = ['coeffnorm', 'coeffpert', 'coeffsv', 'coeffbd'],
                remap = dict(
                        remap = dict(autoremap = 'first'),
                    )
            ),
            clscontents = dict(
                default = JsonDictContent,
            ),
            nativefmt   = dict(
                values  = ['json'],
                default = 'json',
            ),
            pertkind    = dict(
                values  = ['sv', 'bd'],
                default = 'norm',
            ),
        )
    )

    @property
    def realkind(self):
        return 'coeff' + self.pertkind

    def basename_info(self):
        """Generic information for names fabric."""
        return dict(
            radical = self.realkind,
            fmt     = self.nativefmt,
            src     = [self.model],
        )


class SampleContent(JsonDictContent):
    
    def drawing(self, g, x):
        """Return the number of a sampled element according to the local number."""
        n = g.get('number', x.get('number', g.get('member', x.get('member', None))))
        fmt = g.get('localfmt', x.get('localfmt', ':03d'))
        virgin = g.get('untouched', x.get('untouched', []))
        if n is None:
            return None
        else:
            try:
                if type(virgin) is not list:
                    virgin = [int(virgin)]
                else:
                    virgin = map(int, virgin)
                n = int(n)
                print n
            except TypeError:
                return None
            if n in virgin:
                return ('{'+ fmt + '}').format(n)
            else:
                return ('{'+ fmt + '}').format(self.data['drawing'][n - 1])
            
            
class Sample(FlowResource):
    """
    Lot drawn out of a set.
    """

    _footprint = dict(
        abstract = True,
        info = 'Sample',
        attr = dict(
            kind = dict(
                values   = ['mbsample', 'mbselect', 'mbdrawing', 'members_select'],
                remap = dict(
                        remap = dict(autoremap = 'first'),
                    )
            ),
            clscontents = dict(
                default = SampleContent,
            ),
            nativefmt   = dict(
                values  = ['json'],
                default = 'json',
            ),
            nblot = dict(
                type = int,
            ),
            nbset = dict(
                type = int,
            ),            
        )
    )

    def basename_info(self):
        """Generic information for names fabric."""
        return dict(
            radical = self.realkind + '.{:d}outof{:d}'.format(self.nblot, self.nbset),
            fmt     = self.nativefmt,
        )


class MembersSample(Sample):
    """
    List of members selected among a set.
    """

    _footprint = dict(
        info = 'Members sample',
        attr = dict(
            kind = dict(
                values   = ['mbsample', 'mbselect', 'mbdrawing', 'members_select'],
                remap = dict(
                        remap = dict(autoremap = 'first'),
                    )
            ),           
        )
    )

    @property
    def realkind(self):
        return 'mbsample'

            
class MultiphysicsSample(Sample):
    """
    List of physical packages selected among a set.
    """

    _footprint = dict(
        info = 'Physical packages sample',
        attr = dict(
            kind = dict(
                values   = ['physample', 'physelect', 'phydrawing'],
                remap = dict(
                        remap = dict(autoremap = 'first'),
                    )
            ),          
        )
    )

    @property
    def realkind(self):
        return 'physample'
