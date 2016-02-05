#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re

from vortex.data.flow       import SpectralGeoFlowResource
from vortex.syntax.stdattrs import term
from vortex.tools.date      import Time

from common.tools.igastuff  import archive_suffix


class Analysis(SpectralGeoFlowResource):
    """
    Class for analysis resource. It can be an atmospheric or surface or full
    analysis (full = atmospheric + surface).
    The analysis can be filtered (filling attribute).
    """
    _footprint = dict(
        info = 'Analysis',
        attr = dict(
            kind = dict(
                values   = ['analysis', 'analyse', 'atm_analysis']
            ),
            nativefmt = dict(
                values   = ['fa', 'grib', 'lfi'],
                default  = 'fa',
            ),
            filtering = dict(
                optional = True,
                values   = ['dfi'],
            ),
            filling = dict(
                optional = True,
                default  = 'full',
                values   = ['surface', 'surf', 'atmospheric', 'atm', 'full'],
                remap    = dict(
                    surface     = 'surf',
                    atmospheric = 'atm',
                ),
            )
        )
    )

    @property
    def realkind(self):
        return 'analysis'

    @property
    def term(self):
        """Fake term for duck typing."""
        return Time(0)

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        ananame = 'analyse'
        if 'surf' in self.filling:
            if re.match('aladin|arome', self.model):
                ananame = 'analyse_surf'
            else:
                ananame = 'analyse_surface1'

        if self.filtering is not None:
            if 'aladin' in self.model:
                ananame = 'ANALYSE_DFI'

        if self.model == 'surfex':
            ananame += '.sfx'

        return ananame

    def olive_basename(self):
        """OLIVE specific naming convention."""
        olivename_map = { 'atm':  'TRAJ' + self.model[:4].upper() + '+0000',
                          'surf': 'surfanalyse',
                          'full': 'analyse'}
        if self.model != 'arpege':
            olivename_map['surf'] = 'analyse'
            if self.model == 'surfex':
                olivename_map = { k: x + '.sfx' for k, x in olivename_map.items() }
        return olivename_map[self.filling]

    def basename_info(self):
        """Generic information, radical = ``analysis``."""
        if self.geometry.lam:
            lgeo = [self.geometry.area, self.geometry.rnice]
        else:
            lgeo = [{'truncation': self.geometry.truncation}, {'stretching': self.geometry.stretching}]

        return dict(
            fmt     = self.nativefmt,
            geo     = lgeo,
            radical = self.realkind,
            src     = [self.filling, self.model],
        )

    def iga_pathinfo(self):
        """Standard path information for IGA inline cache."""
        if self.model == 'arome':
            if self.filling == 'surf':
                directory = 'fic_day'
            else:
                directory = 'workdir/analyse'
        elif self.model == 'arpege':
            if self.filling == 'surf':
                directory = 'workdir/analyse'
            else:
                directory = 'autres'
        else:
            if self.filling == 'surf':
                directory = 'autres'
            else:
                directory = 'workdir/analyse'
        return dict(
            fmt       = directory,
            model     = self.model,
            nativefmt = self.nativefmt,
        )


class InitialCondition(Analysis):
    """
    Class for initial condition resources : anything from which a model run can be performed.
    """
    _footprint = dict(
        info = 'Initial condition',
        attr = dict(
            kind = dict(
                values   = ['initial_condition', 'ic', 'starting_point'],
                remap    = dict(autoremap = 'first'),
            ),
        )
    )

    @property
    def realkind(self):
        return 'ic'

    def olive_basename(self):
        """OLIVE specific naming convention."""
        raise NotImplementedError("The number is only known by the provider, not supported yet.")

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        raise NotImplementedError("The number is only known by the provider, not supported yet.")


class Historic(SpectralGeoFlowResource):
    """
    Class for historical state of a model (e.g. from a forecast).
    """
    _footprint = [
        term,
        dict(
            info = 'Historic forecast file',
            attr = dict(
                kind = dict(
                    values = ['historic', 'modelstate'],
                    remap = dict(
                        modelstate = 'historic'
                    )
                ),
                nativefmt = dict(
                    values = ['fa', 'grib', 'lfi'],
                    default = 'fa',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'historic'

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        prefix = 'icmsh'
        midfix = '(histfix:igakey)'
        suffix = ''
        if self.geometry.lam and re.match('testms1|testmp1|testmp2', self.geometry.area):
            suffix = '.r' + archive_suffix(self.model, self.cutoff, self.date)

        if re.match('aladin|arome|surfex', self.model):
            prefix = prefix.upper()

        return prefix + midfix + '+' + self.term.fmthour + suffix

    def olive_basename(self):
        """OLIVE specific naming convention."""
        if self.model == 'mesonh':
            return '.'.join(
                (self.model.upper(), self.geometry.area[:4].upper() + '+' + self.term.fmthour, self.nativefmt)
            )
        else:
            return 'ICMSH' + self.model[:4].upper() + '+' + self.term.fmthour

    def basename_info(self):
        """Generic information, radical = ``historic``."""
        if self.geometry.lam:
            lgeo = [self.geometry.area, self.geometry.rnice]
        else:
            lgeo = [{'truncation': self.geometry.truncation}, {'stretching': self.geometry.stretching}]

        return dict(
            fmt     = self.nativefmt,
            geo     = lgeo,
            radical = self.realkind,
            src     = self.model,
            term    = self.term.fmthm,
        )


class BiasDFI(SpectralGeoFlowResource):
    """
    Class for some kind of DFI bias (please add proper documentation).
    """
    _footprint = [
        term,
        dict(
            info = 'DFI bias file',
            attr = dict(
                kind = dict(
                    values = ['biasdfi', 'dfibias'],
                    remap = dict(
                        dfibias = 'biasdfi'
                    )
                ),
                nativefmt = dict(
                    values = ['fa'],
                    default = 'fa',
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'biasdfi'

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return 'BIASDFI+{1:04d}'.format(self.term)

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return 'BIASDFI{0:s}+{1:04d}'.format(self.model[:4].upper(), self.term)

    def basename_info(self):
        """Generic information, radical = ``historic``."""
        if self.geometry.lam:
            lgeo = [self.geometry.area, self.geometry.rnice]
        else:
            lgeo = [{'truncation': self.geometry.truncation}, {'stretching': self.geometry.stretching}]

        return dict(
            fmt     = self.nativefmt,
            geo     = lgeo,
            radical = 'biasdfi',
            src     = self.model,
            term    = self.term.fmthm,
        )
