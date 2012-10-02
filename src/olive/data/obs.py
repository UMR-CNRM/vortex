#!/bin/env python
# -*- coding:Utf-8 -*-

#: Automatic export of Observations class
__all__ = [ 'Observations' ]

import re, logging


from vortex.data.flow import GeoFlowResource, FlowResource


class Observations(GeoFlowResource):
    
    _footprint = dict(
        info = 'Observations file',
        attr = dict(
            kind = dict(
                values = [ 'observations']
            ),
            part = dict(),
            stage = dict(
                values = [ 'void', 'extract', 'screen', 'traj', 'min', 'complete', 'cans', 'raw', 'std' ]
            ),
            nativefmt = dict(
                values = [ 'obsoul', 'grib', 'bufr', 'ascii','odb', 'odb/split', 'odb/compressed', 'ecma', 'ccma' ],
            ),
        )
    )
     
    @classmethod
    def realkind(cls):
        return 'observations'

    def basename_info(self):
        if re.match('^odb|ecma|ccma',self.nativefmt):
            return dict(style='obs', nativefmt=self.nativefmt, stage=self.stage, part=self.part, suffix='tar')
        else:
            return dict(style='obs',nativefmt=self.nativefmt, stage=self.stage, part=self.part)
 
    def olive_basename(self):
        fmt = self.nativefmt
        
        if re.match('^ascii$', fmt) :
            return '_'.join(('ascii', self.stage, self.part))
        elif re.match('^obsoul$', fmt) :
            return '_'.join(('obsoul', self.stage, self.part))
        elif re.match('^grib$', fmt) :
            return '_'.join(('obsgrib', self.stage, self.part))
        elif re.match('^bufr$', fmt) :
            return '_'.join(('obsbufr', self.stage, self.part))
        elif re.match('^odb$', fmt) and re.match('raw', self.stage) : 
            return '_'.join(('ecma', self.stage, self.part)) + '.tar'
        elif re.match('^odb$', fmt) :
            return '_'.join(('ecmascr', self.stage, self.part)) + '.tar'
        elif re.match('^odb\/split$', fmt) :
            return '_'.join(('ecma', self.stage, self.part)) + '.tar'
        elif re.match('^odb\/compressed', fmt) :
            return '_'.join(('ccma', self.stage, self.part)) + '.tar'
        else :
            logging.error('No olive basename defined for such observations format %s', fmt)
            

    def archive_basename(self):
        fmt = self.nativefmt
        part = self.part
        stage = self.stage
        
        if re.match('^(?:bufr|obsoul|grib)$', fmt) and part != 'full' and stage == 'void':
            return '.'.join((fmt, part))
        elif re.match('^obsoul$', fmt) and part == 'full' and stage == 'void':
            return 'obsoul'
        elif re.match('^odb$', fmt) and part == 'full' and stage == 'void':
            return 'ecmascr.tar'
        elif re.match('^odb', fmt) and part == 'full' and stage == 'screen':
            return 'odb_screen.tar'
        elif re.match('^odb', fmt) and re.match('^(?:altitude|mix|full)$', part) and stage == 'traj':    
            return  'odb_traj.tar'
        elif re.match('^odb', fmt) and re.match('^(?:altitude|mix|full)$', part) and stage == 'min ' and self.model == 'aladin':
            return  'odb_cpl.tar'
        elif re.match('^odb', fmt) and re.match('^(?:altitude|mix|full)$', part) and stage == 'complete':   
            return  'odb_cpl.tar'
        elif re.match('^odb', fmt) and part == 'ground' and stage == 'cans':
            return 'odb_canari.tar'
        else :
            logging.error('No archive basename defined for such observations (format=%s, part=%s, stage=%s)', fmt, part, stage)
            

    def archive_urlquery(self):
        if re.match('^odb', self.nativefmt):
            return 'extract=all' 
        else :
            return ''
    
    
class Refdata(FlowResource):
     
    _footprint = dict(
        info = 'Refdata file',
        attr = dict(
            kind = dict(
                values = [ 'refdata']
            ),
            part = dict(
                default = 'all'
            ),
        )
    )
     
    @classmethod
    def realkind(cls):
        return 'refdata'
    
    def basename_info(self):
        return dict(
            radical='refdata',
            suffix=self.part
        )
 
    def olive_basename(self):
        return 'refdata.' + self.part
        
    def archive_basename(self):
        return 'refdata'


class Varbc(FlowResource):
    
    _footprint = dict(
        info = 'Varbc file',
        attr = dict(
            kind = dict(
                values = [ 'varbc' ]
            ),
            stage = dict(
                values = [ 'merge', 'void' ],
                default = 'void'
            ),
        )
    )
     
    @classmethod
    def realkind(cls):
        return 'varbc'
 
    def basename_info(self):
        if self.stage == 'void':
            return dict(
                radical='varbc',
                src=self.model
            )
        else:
            return dict(
                radical='varbc',
                src=self.model,
                suffix=self.stage
            )
 
    def olive_basename(self):
        return 'varbc'
        
    def archive_basename(self):
       
        if self.stage != 'void':
            bname = 'VARBC.' + self.stage
        else:
            bname = 'VARBC' + '(varbc' + self.model + ':inout)'
        return bname