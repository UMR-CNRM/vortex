#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re

import footprints
logger = footprints.loggers.getLogger(__name__)

from .ifsroot import IFSParallel
from vortex.util.structs import ShellEncoder
from vortex.algo.components import BlindRun
from vortex.layout.dataflow import intent


class Svect(IFSParallel):
    """Singular vectors computation."""

    _footprint = dict(
        info='Computation of the singular vectors.',
        attr=dict(
            kind=dict(
                values=['svectors', 'svector', 'sv', 'svect', 'svarpe'],
                remap=dict(autoremap='first'),
            ),
            conf=dict(
                type     = int,
                optional = True,
                default=601,
            ),
            xpname=dict(
                optional = True,
                default='SVEC',
            ),
        )
    )
    
    @property
    def realkind(self):
        return 'svectors'
    

class CombiSV(BlindRun):
    """Combine the SV to form perturbations by gaussian sampling."""

    _abstract = True
    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['combi'],
            ),
            nbpert = dict(
                type      = int,
                optionnal = False
            ),
        )
    )

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(CombiSV, self).prepare(rh, opts)
        self.export('drhook_not_mpi')
        
        sh = self.system
        
        # Check the number of singular vectors and link them in succession
        nbVect = {} 
        for num, svecrh in enumerate([ x.rh for x in self.context.sequence.effective_inputs(
                role = 'SingularVectors',
                kind = 'svector',
            )]):
            componoms = re.split("[\.,\+]",svecrh.container.localpath())
            if len(componoms) < 3:
                logger.critical("The SV name do not contain the information 'zone.numero': %s", svecrh.container.actualpath())
            radical = componoms[0]
            sufix = re.sub('^' + componoms[0] + '[\+,\.]' + componoms[1] + '[\+,\.]' + componoms[2],'',svecrh.container.localpath())                   
            if componoms[1] in nbVect.keys():
                nbVect[componoms[1]] += 1
            else:
                nbVect[componoms[1]] = 1
                
            sh.softlink(svecrh.container.localpath(), radical + '{:03d}'.format(num+1) + sufix)
        totalVects = sum(nbVect.values())        
        logger.info("Number of vectors :\n" + '\n'.join(['- %s: %d' % (z, n) for z, n in nbVect.iteritems()]))
            
        # Tweak the namelist
        namrh = self.setlink(initrole='Namelist', initkind='namelist')
        logger.info("Added to NVSZONE namelist entry")
        namrh[0].contents['NAMOPTI']['NVSZONE'] = nbVect.values()
        
        nbVectNam = namrh[0].contents['NAMENS']['NBVECT']
        if int(nbVectNam) != totalVects:
            logger.warning("%s singular vectors expected and %d present.", (nbVectNam, totalVects))
            logger.info("Substitute the total number of vectors to NBVECT namelist entry")
            namrh[0].contents['NAMENS']['NBVECT'] = totalVects
        
        namrh[0].contents['NAMMOD']['NMOD'] = self.nmod
        logger.info("NMOD set to %s: combination of the SV.", self.nmod)
        namrh[0].save()        
        
        # Copy the analysis to give all the members a basis
        initrh = [ x.rh for x in self.context.sequence.effective_inputs(
            kind = ('analysis'),
        ) ]
        for num in footprints.util.rangex(1,self.nbpert):
            sh.cp(initrh[0].container.localpath(), re.sub('[0-9]*$', '{:03d}'.format(num), initrh[0].container.localpath()), 
                    fmt=initrh[0].container.actualfmt, intent=intent.INOUT)
        logger.info("Copy the analysis for the %d perturbations.", self.nbpert)

    def execute(self, rh, opts):
        """Standard Combi execution."""
        self.system.ls(output='dirlst')
        namrh = self.setlink(initrole='Namelist', initkind='namelist')
        namrh[0].container.cat()
        super(CombiSV, self).execute(rh, opts)
    
class CombiSVunit(CombiSV):
    """Combine the unit SV to form the raw perturbations by gaussian sampling."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['sv2unitpert', 'init', 'combi_init', ],
                remap = dict(
                    combi_init = 'init',
                ),
            ),
        )
    )

    @property
    def nmod(self):
        return 1
        
        
class CombiSVnorm(CombiSV):
    """Compute a norm consistent with the background error and combine the normed SV to form the SV perturbations."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['sv2normedpert', 'optim', 'combi_optim', ],
                remap = dict(
                    remap=dict(autoremap='first'),
                ),
            ),
        )
    )

    def postfix(self, rh, opts):
        """Post processing cleaning."""
        super(CombiSVnorm, self).postfix(rh, opts)
        
        # Pick up the coeff in the namelist
        namrh = self.setlink(initrole='Updated Namelist', initkind='namelist')
        for nam in [ x for x in namrh if 'NAMCOEFVS' in x.contents ]:
            logger.info("Exctract the VS coefficient from the updated namelist.")
            coeffvs = {'rcoefvs': int(nam.contents['NAMCOEFVS']['RCOEFVS'])}
            self.system.json_dump(coeffvs, 'coeffvs.out', indent=4, cls=ShellEncoder)

    @property
    def nmod(self):
        return 2


class CombiIC(BlindRun):
    """Combine the SV and AE or breeding perturbations to form the initial conditions."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['pert2ic', 'sscales', 'combi_sscales', ],
                remap=dict(autoremap='first'),
            ),
            nbruns = dict(
                type      = int,
                optionnal = False
            ),
        )
    )

    @property
    def nmod(self):
        return 3
    
    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(CombiIC, self).prepare(rh, opts)
        
        sh = self.system       
        
        # Tweak the namelist
        namrh = self.setlink(initrole='Namelist', initkind='namelist')
        if 'NAMCOEFBM' in namrh[0].contents:
            pr = sh.json_load('coeffbd.out')
            logger.info("Add the breeding coefficient to the NAMCOEFBM namelist entry")
            namrh[0].contents.newblock('NAMCOEFBM')
            namrh[0].contents['NAMCOEFBM']['RCOEFBM'] = pr.get('rcoefbd')
        if 'NAMCOEFVS' in namrh[0].contents:
            pr = sh.json_load('coeffsv.out')
            logger.info("Add the VS coefficient to the NAMCOEFVS namelist entry")
            namrh[0].contents.newblock('NAMCOEFVS')
            namrh[0].contents['NAMCOEFVS']['RCOEFVS'] = pr.get('rcoefvs')
        namrh[0].contents['NAMMOD']['NMOD'] = self.nmod
        logger.info("NMOD set to 3: final combination of the perturbations.")
        namrh[0].save()
        
        # Copy the analysis to give all the members a basis
        initrh = [ x.rh for x in self.context.sequence.effective_inputs(
            kind = ('analysis'),
        ) ]
        for num in footprints.util.rangex(1,self.nbruns-1):
            sh.cp(initrh[0].container.localpath(), re.sub('[0-9]*$', '{:03d}'.format(num), initrh[0].container.localpath()), 
                    fmt=initrh[0].container.actualfmt, intent=intent.INOUT)
        logger.info("Copy the analysis for the %d perturbations.", self.nbruns)
        
    def execute(self, rh, opts):
        """Standard Combi execution."""
        self.system.ls(output='dirlst')
        namrh = self.setlink(initrole='Namelist', initkind='namelist')
        namrh[0].container.cat()
        super(CombiIC, self).execute(rh, opts)
        
        
class CombiBreeding(BlindRun):
    """Compute a norm consistent with the background error and combine the normed SV to form the SV perturbations."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['fc2bredpert', 'breeding', 'combi_breeding', ],
                remap = dict(
                    remap=dict(autoremap='first'),
                ),
            ),
        )
    )

    @property
    def nmod(self):
        return 6

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(CombiBreeding, self).prepare(rh, opts)
        
        sh = self.system    
        
        # Consistent naming with the Fortran execution
        for num, grib in enumerate([ x.rh for x in self.context.sequence.effective_inputs(
            kind = ('historic'),
        ) ]):
            sh.softlink(grib.container.localpath(), re.sub('[0-9]*$', '{:03d}'.format(num+1), grib.container.localpath()) + '.grb')
        logger.info("Rename the %d grib files consecutively.", num)
        
        # Tweak the namelist
        namrh = self.setlink(initrole='Namelist', initkind='namelist')
        namrh[0].contents['NAMMOD']['NMOD'] = self.nmod
        logger.info("NMOD set to 1: initial combination of the unit SV.")
        namrh[0].save()

    def execute(self, rh, opts):
        """Standard Combi execution."""
        self.system.ls(output='dirlst')
        namrh = self.setlink(initrole='Namelist', initkind='namelist')
        namrh[0].container.cat()
        super(CombiBreeding, self).execute(rh, opts)
        
    def postfix(self, rh, opts):
        """Post processing cleaning."""
        super(CombiBreeding, self).postfix(rh, opts)
        
        # Pick up the coeff in the namelist
        namrh = self.setlink(initrole='Namelist', initkind='namelist')
        for nam in [ x for x in namrh if 'NAMCOEFBM' in x.contents ]:
            logger.info("Exctract the VS coefficient from the updated namelist.")
            coeffvs = {'rcoefbd': int(nam.contents['NAMCOEFBM']['RCOEFBM'])}
            self.system.json_dump(coeffvs, 'coeffbd.out', indent=4, cls=ShellEncoder)
