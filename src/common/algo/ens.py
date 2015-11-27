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
        return 'svector'
    

class Combi(BlindRun):
    """Build the initial conditions of the EPS."""

    _abstract = True
    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['combi'],
            ),
        )
    )

    def execute(self, rh, opts):
        """Standard Combi execution."""
        self.system.ls(output='dirlst')
        namrh = self.setlink(initrole='Namelist', initkind='namelist')
        namrh[0].container.cat()
        super(Combi, self).execute(rh, opts)    

    def addNmod(self, namrh, msg):
        namrh.contents['NAMMOD']['NMOD'] = self.nmod
        logger.info("NMOD set to %d: %s.", self.nmod, msg)        

    def analysis_cp(self, nb, msg):
        # Copy the analysis
        initrh = self.setlink(initkind='analysis')
        for num in footprints.util.rangex(1, nb):
            self.system.cp(initrh[0].container.localpath(), re.sub('[0-9]*$', '{:03d}'.format(num), initrh[0].container.localpath()), 
                    fmt=initrh[0].container.actualfmt, intent=intent.INOUT)
        logger.info("Copy the analysis for the %d %s.", nb, msg)

    def coeff_picking(self, kind, msg):
        # Pick up the coeff in the namelist
        namrh = self.setlink(initkind='namelist')
        print 'NAMCOEF' + kind.upper()
        for nam in [ x for x in namrh if 'NAMCOEF' + kind.upper() in x.contents ]:
                logger.info("Exctract the " + msg + " coefficient from the updated namelist.")
                coeff = {'rcoef' + kind: float(nam.contents['NAMCOEF' + kind.upper()]['RCOEF' + kind.upper()])}
                self.system.json_dump(coeff, 'coeff' + kind + '.out', indent=4, cls=ShellEncoder)


class CombiSV(Combi):
    """Combine the SV to form perturbations by gaussian sampling."""

    _abstract = True
    _footprint = dict(
        attr = dict(
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
                
        # Check the number of singular vectors and link them in succession
        nbVect = {} 
        for num, svecrh in enumerate(self.setlink(initrole='SingularVectors', initkind='svector')):
            componoms = re.split("[\.,\+]",svecrh.container.localpath())
            if len(componoms) < 3:
                logger.critical("The SV name do not contain the information 'zone.numero': %s", svecrh.container.actualpath())
            radical = componoms[0]
            sufix = re.sub('^' + componoms[0] + '[\+,\.]' + componoms[1] + '[\+,\.]' + componoms[2],'',svecrh.container.localpath())                   
            if componoms[1] in nbVect.keys():
                nbVect[componoms[1]] += 1
            else:
                nbVect[componoms[1]] = 1
                
            self.system.softlink(svecrh.container.localpath(), radical + '{:03d}'.format(num+1) + sufix)
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
        
        self.addNmod(namrh[0], "combination of the SV")
        namrh[0].save()        
        
        # Copy the analysis to give all the perturbations a basis
        self.analysis_cp(self.nbpert, 'perturbations')

    
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
        self.coeff_picking('vs', 'SV')

    @property
    def nmod(self):
        return 2


class CombiIC(Combi):
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
        if self.setlink(initrole='CoeffBreeding'):
            pr = sh.json_load('coeffbd.out')
            logger.info("Add the breeding coefficient to the NAMCOEFBM namelist entry")
            namrh[0].contents.newblock('NAMCOEFBM')
            namrh[0].contents['NAMCOEFBM']['RCOEFBM'] = pr.get('rcoefbm')
            namrh[0].contents['NAMMOD']['LANAP'] = False
            namrh[0].contents['NAMMOD']['LBRED'] = True
        if self.setlink(initrole='CoeffSV'):
            pr = sh.json_load('coeffsv.out')
            logger.info("Add the SV coefficient to the NAMCOEFVS namelist entry")
            namrh[0].contents.newblock('NAMCOEFVS')
            namrh[0].contents['NAMCOEFVS']['RCOEFVS'] = pr.get('rcoefvs')
            namrh[0].contents['NAMMOD']['LVS'] = True
        self.addNmod(namrh[0], "final combination of the perturbations")
        namrh[0].save()
        
        # Copy the analysis to give all the members a basis
        self.analysis_cp(self.nbruns - 1, 'perturbed states')
        
        
class CombiBreeding(Combi):
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
                
        # Consistent naming with the Fortran execution
        for num, grib in enumerate(self.setlink(initkind='historic')):
            self.system.softlink(grib.container.localpath(), re.sub('[0-9]*$', '{:03d}'.format(num+1), grib.container.localpath()) + '.grb')
        logger.info("Rename the %d grib files consecutively.", num)
        
        # Tweak the namelist
        namrh = self.setlink(initrole='Namelist', initkind='namelist')
        namrh[0].contents['NAMMOD']['LANAP'] = False
        namrh[0].contents['NAMMOD']['LBRED'] = True
        self.addNmod(namrh[0], "compute the coefficient of the bred modes")
        namrh[0].save()
        
    def postfix(self, rh, opts):
        """Post processing cleaning."""
        super(CombiBreeding, self).postfix(rh, opts)
        # Pick up the coeff in the namelist
        self.coeff_picking('bm', 'breeding')


# class LAMCombiIC(BlindRun):
#     """TODO"""
# 
#     _footprint = dict(
#         attr = dict(
#             kind = dict(
#                 values = ['lam_pert2ic', 'lampert2ic', ],
#                 remap=dict(autoremap='first'),
#             ),
#         )
#     )
 
 
class SurfCombiIC(BlindRun):
    """Combine the deterministic surface with the perturbed surface to form the initial surface conditions."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['surf_pert2ic', 'surf2ic', ],
                remap=dict(autoremap='first'),
            ),
            member = dict(
                type = int,
            ),    
        )
    )
    
    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(SurfCombiIC, self).prepare(rh, opts)


        icrh = self.setlink(initrole='SurfaceAnalysis', initkind='ic')
        actualdate = icrh[0].resource.date        
        seed = int(actualdate.ymdh) + (actualdate.hour + 1) * (self.member + 1)
        
        # Tweak the namelist
        namrh = self.setlink(initrole='Namelist', initkind='namelist')
        logger.info("ISEED added to NAMSFC namelist entry: %d", seed)
        namrh[0].contents['NAMSFC']['ISEED'] = seed
        namrh[0].save()
        
        
class Clustering(BlindRun):
    """Select by clustering a sample of members among the whole set."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['clustering', 'clust', ],
                remap=dict(autoremap='first'),
            ),
            fileoutput = dict(
                optional = True,
                default = '_griblist',
            ),
            nbclust = dict(
                type = int,
            ),                
        )
    )
    
    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(Clustering, self).prepare(rh, opts)
        
        fileList = []
        for grib in self.setlink(initrole='Model state', initkind='gridpoint'):
            fileList.append(grib.container.localpath())
        
        # Tweak the namelist
        namrh = self.setlink(initrole='Namelist', initkind='namelist')
        logger.info("NBRCLUST added to NAMCLUST namelist entry: %d", self.nbclust)
        namrh[0].contents['NAMCLUST']['NBRCLUST'] = self.nbclust

        namrh[0].save()
        namrh[0].container.cat()

        fileList.sort()
        with open(self.fileoutput, 'w') as optFile:
            optFile.write('\n'.join(fileList))
            
            
class Addpearp(BlindRun):
    """Select by clustering a sample of members among the whole set."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['addpearp', ],
                remap=dict(autoremap='first'),
            ),
            nbpert = dict(
                type = int,
            ),                
        )
    )
    
    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(Addpearp, self).prepare(rh, opts)
        
        # Tweak the namelist
        namrh = self.setlink(initrole='Namelist', initkind='namelist')
        logger.info("NAMIC added to NBE namelist entry: %d", self.nbpert)
        namrh[0].contents['NAMIC']['NBPERT'] = self.nbpert
        namrh[0].save()
        namrh[0].container.cat()