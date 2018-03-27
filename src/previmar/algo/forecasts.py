#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

import re
from vortex.algo.components import Parallel
from previmar.util.polling import PollingMarine


class SurgesCouplingForecasts(Parallel):
    """"""
    _footprint = dict(
        attr = dict(
            binary = dict(
                values = ['hycomcoupling'],
            ),
            config_name = dict(
                info     = "Name of configuration",               
                default  = "",
                optional = True,
                type     = str,
            ),
            numod = dict(
                info     = "model ID",
                optional = True,
                default  = 165,
            ),
            codmod = dict(
                info     = "Data base BDAP Name of modele",
                type     = str,
                optional = True,
                default  = '',
            ),
            fcterm = dict( 
                default  = 6,
                optional = True,
            ),
            freq_forcage = dict(
                info     = "Atmospheric grib forcing frequency (minutes)",
                default  = 180,
                optional = True,
            ),  
            rstfin = dict(
                info     = "Term max of saving restart files",
                default  = 6,
                optional = True,
            ), 
            flyargs = dict(
                default = ('ASUR', 'PSUR',), 
                optional = True,
            ),
            flypoll = dict(
                default = 'iopollmarine',
                optional = True,               
            ),
            nproc_io = dict(
                default = 1,
                optional = True,               
            ), 
            iopath = dict(
                type     = str,
                optional = True,
                default  = '',
            ),
        )
    )


    def prepare(self, rh, opts):
        """Add some defaults env values for mpitool itself.""" 
        super(Parallel, self).prepare(rh, opts)
        if opts.get('mpitool', True):
            self.export('mpitool')
          
        # Tweak the pseudo hycom namelists New version  ! 
        for namsec in self.context.sequence.effective_inputs(role = re.compile('FileConfig')):  

            r = namsec.rh 

            term = str(self.fcterm)           
            basedate = r.resource.date          
            date = basedate.ymdh
            reseau = basedate.hh   

            ## Creation Dico des valeurs/cle à changer selon experience          
            dico = {}
            if r.resource.param == 'ms': # tideonly experiment
                dico["heures"] = term
                dico["savfin"] = term
                dico["rstfin"] = str(self.rstfin)
                dico["dateT0"] = date
            else: # full experiment
                dico["heures"] = term
                dico["savfin"] = term
                dico["h_rese"] = reseau              
                dico["modele"] = r.provider.vconf.upper()[-3:]
                xp = r.provider.vconf[-5:-3]
                mode_map = dict(fc= 'PR', an='AA')
                dico["anapre"] = mode_map.get(xp, xp)
                dico["nmatm"]  = str(self.freq_forcage)
                dico["codmod"] = self.codmod
                dico["imodel"] = str(self.numod)
                dico["kmodel"] = self.config_name

            ## modification du content
            paramct = r.contents
            paramct.substitute(dico)                
            paramct.rewrite(r.container)
    
            ## On sauvegarde
            r.save()
            r.container.cat()
   
   
    def flyput_method(self):
        """Check out what could be a valid io_poll command."""
        sh = self.system 
        self.iopollmarine = footprints.proxy.addon(kind=self.flypoll, shell=sh, io_poll_path=self.iopath, nproc_io=self.nproc_io)   
        iopollmarine = self.iopollmarine 
        return getattr(iopollmarine, 'iopoll_marine', None)
       
       
    def execute(self, rh, opts):
        """Jump into the correct working directory."""
        tmpwd = 'EXEC_OASIS'
        logger.info('Temporarily change the working dir to ./%s', tmpwd)
        with self.system.cdcontext(tmpwd):
            super(SurgesCouplingForecasts, self).execute(rh, opts)




class SurgesCouplingInterp(SurgesCouplingForecasts):
    """Algo for interpolation case, not documented yet"""
    _footprint = dict(
        attr = dict(
            binary = dict(
                values = ['hycominterp'],
            ),
        )
    )
