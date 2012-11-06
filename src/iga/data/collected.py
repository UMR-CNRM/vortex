#!/bin/env python
# -*- coding:Utf-8 -*-

from vortex.data.resources import Resource
from vortex.data.flow import FlowResource


#: No automatic export
__all__ = []

class Collected(Resource):

    _footprint = dict(
        info = 'Resource stored in a collector file (ex: entree.tar)',
        attr = dict(
            collected = dict(
                optional = True,
            ),
            collector = dict(
                optional = True,
                default = 'entree.tar',
            ),
            kind = dict(
                values = [ 'collected' ]
            )
        )
    )
    
 
    @classmethod
    def realkind(cls):
        return 'collected'
    
    def archive_basename(self):
        return self.collector
    
    def archive_urlquery(self):
        return 'extract=' + self.collected

  
class BlackListDiap(FlowResource):  
    
    _footprint = dict(
        info = 'Blacklist file for observations',
        attr = dict(
            kind = dict(
                values = [ 'blacklistdiap' ],
            )
        )
    )
    
    @classmethod
    def realkind(cls):
        return 'blacklistdiap'
    
    def basename_info(self):
        return dict(
            radical='blacklistdiap',
        )

    def iga_pathinfo(self):
        return dict(
            model=self.model
        )
   

class BlackListLoc(FlowResource):  
    
    _footprint = dict(
        info = 'Listloc file for observations',
        attr = dict(
            kind = dict(
                values = [ 'blacklistloc' ],
            )
        )
    )
    
    @classmethod
    def realkind(cls):
        return 'blacklistloc'
    
    def basename_info(self):
        return dict(
            radical='blacklistloc',
        )

    def iga_pathinfo(self):
        return dict(
            model=self.model
        )
 

class Obsmap(FlowResource):  
    
    _footprint = dict(
        info = 'Bator map file',
        attr = dict(
            stage = dict(
                optional = True,
                default = 'void'
            ),
            kind = dict(
                values = [ 'obsmap' ],
            )
        )
    )
    
    @classmethod
    def realkind(cls):
        return 'obsmap'

    def olive_basename(self):
        return 'OBSMAP_' + self.stage
    
    def basename_info(self):
        return dict(
            style='obsmap',
            radical='obsmap',
            stage=self.stage
        )
   
    
   
class Bcor(FlowResource):  
    
    _footprint = dict(
        info = 'Bcor file',
        attr = dict(
            category = dict(
                values = [ 'noaa','ssmi','mtop','bcor_noaa.dat', 'bcor_ssmi.dat', 'bcor_mtop.dat' ],
                remap = dict(
                   noaa = 'bcor_noaa.dat',
                   ssmi = 'bcor_ssmi.dat',
                   mtop = 'bcor_mtop.dat'
                ),
            ),
            kind = dict(
                values = [ 'bcor' ],
            )
        )
    )
    
    @classmethod
    def realkind(cls):
        return 'bcor'
    
    def basename_info(self):
        return dict(
            radical=self.collected,
        )

