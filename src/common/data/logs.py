#!/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []


from vortex.data.flow import FlowResource


class Listing(FlowResource):
        
    _footprint = [
        dict(
             info = 'Listing',
             attr = dict(
                task = dict(),
                kind = dict(
                    values = [ 'listing' ]
                )
            )
        )
    ] 
    
    @classmethod
    def realkind(cls):
        return 'listing'
    
    def basename_info(self):
        """Generic information, radical = ``listing``."""
        return dict(
            radical = 'listing',
            src = self.task,
            suffix = [self.date.ymdh, self.cutoff]
        )
