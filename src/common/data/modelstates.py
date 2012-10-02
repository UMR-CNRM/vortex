#!/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import re

from vortex.data.flow import GeoFlowResource
from vortex.syntax.stdattrs import term
from iga.syntax.stdattrs import archivesuffix

class Analysis(GeoFlowResource):
    
    """
    Class for analysis resource. It can be an atmospheric or surface or full analysis (full = atmospheric + surface).
    The analysis can be filtered (filling attribute).
    """
    _footprint = dict(
       info = 'Analysis',
       attr = dict(
           kind = dict(
               values = [ 'analysis', 'analyse', 'atm_analysis' ]
           ),
           nativefmt = dict(
                values = [ 'fa', 'grib' ],
                default = 'fa',
           ),
           filtering = dict(
               values = [ 'dfi' ],
               optional = True,
           ),
           filling = dict(
               values = [ 'surface', 'surf', 'atmospheric', 'atm', 'full' ],
               remap = dict(
                   surface = 'surf',
                   atmospheric = 'atm'
               ),
               default = 'full',
               optional = True,
           )
        )
    )
     
    @classmethod
    def realkind(cls):
        return 'analysis'

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        if re.match('surf', self.filling):
            if re.match('aladin|arome', self.model):
                return 'analyse_surf'
            else:
                return 'analyse_surface1'
        
        if self.filtering != None:   
            if re.match('aladin', self.model):
                return 'ANALYSE_DFI'
            else:
                return 'analyse'
        else:
            return 'analyse'

    def olive_basename(self):
        """OLIVE specific naming convention."""
        if re.match('surf', self.filling):
            return 'surfanalyse'
        else:
            return 'analyse'

    def basename_info(self):
        """Generic information, radical = ``analysis``."""
        if self.geometry.lam():
            lgeo=[self.geometry.area, self.geometry.resolution]
        else:
            lgeo=[{'truncation':self.geometry.truncation}, {'stretching':self.geometry.stretching}]
            
        return dict(
            radical='analysis',
            src=[self.filling, self.model],
            geo=lgeo,
            format=self.nativefmt
        )

    def iga_pathinfo(self):
        if self.model == 'arome':
            if self.filling == "surf":
                directory = 'fic_day'
            else:
                directory = 'workdir/analyse'
        elif self.model == 'arpege':
            if self.filling == "surf":
                directory = 'workdir/analyse'
            else:
                directory = 'autres'
        else:
            if self.filling == "surf":
                directory = 'autres'
            else:
                directory = 'workdir/analyse'
        return dict(
            nativefmt = self.nativefmt,
            model = self.model,
            fmt =  directory
        )



class Historic(GeoFlowResource):
    
    """
    Class for historical state of a model (e.g. from a forecast). 
    """
    _footprint = [
        term,
        dict(
            info = 'Historic forecast file',
            attr = dict(
                kind = dict(
                    values = ['historic']
                ),
                nativefmt = dict(
                    values = [ 'fa', 'grib', 'lfi' ],
                    default = 'fa',
                ),
            )
        )
    ]
    
    @classmethod
    def realkind(cls):
        return 'historic'

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        prefix = 'icmsh'
        midfix = '(histfix:igakey)'
        suffix = ''   
        if re.match('testms1|testmp1|testmp2', self.geometry.area):
            suffix = '.r' + archivesuffix(self.model, self.cutoff, self.date)
            
        name = prefix + midfix + '+' + str(self.term) 
        
        if re.match('aladin|arome', self.model):  
            name = prefix.upper() + midfix + '+' + str(self.term).upper()
        
        return name + suffix

    def olive_basename(self):
        """OLIVE specific naming convention."""
        if self.model == 'mesonh':
            return self.model.upper() + '.' + self.geometry.area[:4].upper() + '+' + str(self.term) + '.' + self.nativefmt
        else:     
            return 'ICMSH' + self.model[:4].upper() + '+' + str(self.term)

    def basename_info(self):
        """Generic information, radical = ``historic``."""
        if self.geometry.lam():
            lgeo=[self.geometry.area, self.geometry.resolution]
        else:
            lgeo=[{'truncation':self.geometry.truncation}, {'stretching':self.geometry.stretching}]
        
        return dict(
            radical='historic',
            src=self.model,
            geo=lgeo,
            term=self.term,
            format=self.nativefmt
        )

class Histsurf(GeoFlowResource):
    
    """
    Class for historical surface state of a model (using surfex) 
    """
    _footprint = [
        term,
        dict(
            info = 'Historic surface file',
            attr = dict(
                kind = dict(
                    values = [ 'histsurf']
                )
            )
        )
    ]
    
    @classmethod
    def realkind(cls):
        return 'histsurf'

    def archive_basename(self):
        return '(surf' + str(self.term) + ':inout)' + '.' + self.nativefmt       

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return '.'.join(('AROMOUT_SURF', self.geometry.area[:4], str(self.term), self.nativefmt))
   
    def basename_info(self):
        """Generic information, radical = ``histsurf``."""
        if self.geometry.lam():
            lgeo=[self.geometry.area, self.geometry.resolution]
        else:
            lgeo=[{'truncation':self.geometry.truncation}, {'stretching':self.geometry.stretching}]
        
        return dict(
                radical='histsurf',
                src=self.model,
                geo=lgeo,
                term=self.term,
                format=self.nativefmt
            )

