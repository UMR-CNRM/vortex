#!/bin/env python
# -*- coding:Utf-8 -*-

#: No automatic export
__all__ = []

import os
from vortex.algo.components import Parallel, Expresso
from common.algo.forecasts import IFSModelParallel



class Coupling(IFSModelParallel):
    """Coupling for IFS-like LAM Models."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = [ 'coupling' ],
            ),
            xpname = dict(
                default = 'FPOS'
            ),
            conf = dict(
                default = 1,
            )
        )
    )
        
    
    def prepare(self, rh, ctx, opts):
        
        
        """Default pre-link for climatological files"""
        climfrh = [ x.rh for x in ctx.sequence.effective_inputs(role='Fatherclim', kind='clim_model') ]
        self.system.symlink(climfrh[0].container.localpath(),'Const.Clim')
        
        climsrh = [ x.rh for x in ctx.sequence.effective_inputs(role='Sonclim', kind='clim_model') ]
        self.system.symlink(climsrh[0].container.localpath(),'const.clim.AREA')
        
        """Default pre-link for namelist"""
        namrh = [ x.rh for x in ctx.sequence.effective_inputs(kind='namelist') ]
        self.system.symlink(namrh[0].container.localpath(),'fort.4')
        

    def execute(self, rh, ctx, kw):
        
        r"""
        Preparation of the coupling files and call to the execute method of the father
        """
        self.system.mkdir('PFFPOS')
        cplrh = [ x.rh for x in ctx.sequence.effective_inputs(role='Couplingfile', kind='historic') ]
        cplrh.sort(lambda a, b: cmp(a.resource.term, b.resource.term))
        i = 0
        for r in cplrh:
            self.system.symlink(r.container.localpath(),'ICMSHFPOSINIT')
            super(Coupling, self).execute(rh, ctx, kw)
            self.system.mv('PFFPOSAREA+0000','PFFPOS/PFFPOSAREA+' + str(r.resource.term) )
            self.system.mv('NODE.001_01','NODE.001_01.' + str(r.resource.term) )
            self.system.remove('ICMSHFPOSINIT')
            i=i+1
            
    def postfix(self, rh, ctx, opts):
        
        self.system.mvglob('PFFPOS/*', '.')
        os.system('cat NODE.001_01.* >> NODE.001')
        self.system.rmglob('NODE.001_01.*')
        self.system.rmglob('-rf','PFFPOS') 

                
                
        
        
        
    
