#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import collections
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
        namsec = self.setlink(initrole='Namelist', initkind='namelist')
        namsec[0].rh.container.cat()
        super(Combi, self).execute(rh, opts)

    @property
    def nmod(self):
        raise NotImplementedError("Abstract property")

    def _addNmod(self, namrh, msg):
        namrh.contents['NAMMOD']['NMOD'] = self.nmod
        logger.info("NMOD set to %d: %s.", self.nmod, msg)

    def _analysis_cp(self, nb, msg):
        # Copy the analysis
        initsec = self.setlink(initkind='analysis')
        for num in footprints.util.rangex(1, nb):
            self.system.cp(initsec[0].rh.container.localpath(),
                           re.sub('[0-9]*$', '{:03d}'.format(num),
                                  initsec[0].rh.container.localpath()),
                           fmt=initsec[0].rh.container.actualfmt, intent=intent.INOUT)
        logger.info("Copy the analysis for the %d %s.", nb, msg)

    def _coeff_picking(self, kind, msg):
        # Pick up the coeff in the namelist
        nam_sections = self.context.sequence.effective_inputs(kind='namelist')
        for nam in [ x.rh for x in nam_sections if 'NAMCOEF' + kind.upper() in x.rh.contents ]:
            logger.info("Extract the " + msg + " coefficient from the updated namelist.")
            coeff = {'rcoef' + kind: float(nam.contents['NAMCOEF' + kind.upper()]['RCOEF' + kind.upper()])}
            self.system.json_dump(coeff, 'coeff' + kind + '.out', indent=4, cls=ShellEncoder)


class CombiSV(Combi):
    """Combine the SV to create perturbations by gaussian sampling."""

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
        nbVect = collections.defaultdict(int)
        svec_sections = self.context.sequence.effective_inputs(role='SingularVectors', kind='svector')
        for num, svecsec in enumerate(svec_sections):
            componoms = re.split("[\.,\+]", svecsec.rh.container.localpath())
            if len(componoms) < 3:
                logger.critical("The SV name does not contain the information 'zone.numero': %s",
                                svecsec.rh.container.actualpath())
            radical = componoms[0]
            sufix = re.sub('^' + radical + '[\+,\.]' + componoms[1] + '[\+,\.]' + componoms[2],
                           '', svecsec.rh.container.localpath())
            nbVect[componoms[1]] += 1
            self.system.softlink(svecsec.rh.container.localpath(),
                                 radical + '{:03d}'.format(num + 1) + sufix)

        totalVects = sum(nbVect.values())
        logger.info("Number of vectors :\n" + '\n'.join(['- %s: %d' % (z, n) for z, n in nbVect.iteritems()]))

        # Tweak the namelist
        namsec = self.setlink(initrole='Namelist', initkind='namelist')
        logger.info("Added to NVSZONE namelist entry")
        namsec[0].rh.contents['NAMOPTI']['NVSZONE'] = nbVect.values()

        nbVectNam = namsec[0].rh.contents['NAMENS']['NBVECT']
        if int(nbVectNam) != totalVects:
            logger.warning("%s singular vectors expected but only %d accounted for.", nbVectNam, totalVects)
            logger.info("Update the total number of vectors in the NBVECT namelist entry")
            namsec[0].rh.contents['NAMENS']['NBVECT'] = totalVects

        self._addNmod(namsec[0].rh, "combination of the SV")
        namsec[0].rh.save()

        # Copy the analysis to give all the perturbations a basis
        self._analysis_cp(self.nbpert, 'perturbations')


class CombiSVunit(CombiSV):
    """Combine the unit SV to create the raw perturbations by gaussian sampling."""

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
    """Compute a norm consistent with the background error and combine the normed SV to create the SV perturbations."""

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
        self._coeff_picking('vs', 'SV')

    @property
    def nmod(self):
        return 2


class CombiIC(Combi):
    """Combine the SV and AE or breeding perturbations to create the initial conditions."""

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

        # Tweak the namelist
        namsec = self.setlink(initrole='Namelist', initkind='namelist')
        bd_sections = self.setlink(initrole='CoeffBreeding')
        if bd_sections:
            logger.info("Add the breeding coefficient to the NAMCOEFBM namelist entry")
            namsec[0].rh.contents.newblock('NAMCOEFBM')
            namsec[0].rh.contents['NAMCOEFBM']['RCOEFBM'] = bd_sections[0].rh.contents['rcoefbm']
            namsec[0].rh.contents['NAMMOD']['LANAP'] = False
            namsec[0].rh.contents['NAMMOD']['LBRED'] = True
        sv_sections = self.setlink(initrole='CoeffSV')
        if sv_sections:
            logger.info("Add the SV coefficient to the NAMCOEFVS namelist entry")
            namsec[0].rh.contents.newblock('NAMCOEFVS')
            namsec[0].rh.contents['NAMCOEFVS']['RCOEFVS'] = sv_sections[0].rh.contents['rcoefvs']
            namsec[0].rh.contents['NAMMOD']['LVS'] = True
        self._addNmod(namsec[0].rh, "final combination of the perturbations")
        namsec[0].rh.save()

        # Copy the analysis to give all the members a basis
        self._analysis_cp(self.nbruns - 1, 'perturbed states')


class CombiBreeding(Combi):
    """Compute a norm consistent with the background error and combine the normed SV to create the SV perturbations."""

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
        hst_sections = self.context.sequence.effective_inputs(kind='historic')
        for num, hst in enumerate(hst_sections):
            self.system.softlink(hst.rh.container.localpath(), re.sub('[0-9]*$',
                                                                      '{:03d}'.format(num + 1),
                                                                      hst.rh.container.localpath()) + '.grb')
        logger.info("Rename the %d grib files consecutively.", num)

        # Tweak the namelist
        namsec = self.setlink(initrole='Namelist', initkind='namelist')
        namsec[0].rh.contents['NAMMOD']['LANAP'] = False
        namsec[0].rh.contents['NAMMOD']['LBRED'] = True
        self._addNmod(namsec[0].rh, "compute the coefficient of the bred modes")
        namsec[0].rh.save()

    def postfix(self, rh, opts):
        """Post processing cleaning."""
        super(CombiBreeding, self).postfix(rh, opts)
        # Pick up the coeff in the namelist
        self._coeff_picking('bm', 'breeding')


class SurfCombiIC(BlindRun):
    """Combine the deterministic surface with the perturbed surface to create the initial surface conditions."""

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

        icsec = self.setlink(initrole='SurfaceAnalysis', initkind='ic')
        actualdate = icsec[0].rh.resource.date
        seed = int(actualdate.ymdh) + (actualdate.hour + 1) * (self.member + 1)

        # Tweak the namelist
        namsec = self.setlink(initrole='Namelist', initkind='namelist')
        logger.info("ISEED added to NAMSFC namelist entry: %d", seed)
        namsec[0].rh.contents['NAMSFC']['ISEED'] = seed
        namsec[0].rh.save()


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

        grib_sections = self.context.sequence.effective_inputs(role='Model state',
                                                               kind='gridpoint')
        fileList = [grib.rh.container.localpath() for grib in grib_sections]

        # Tweak the namelist
        namsec = self.setlink(initrole='Namelist', initkind='namelist')
        logger.info("NBRCLUST added to NAMCLUST namelist entry: %d", self.nbclust)
        namsec[0].rh.contents['NAMCLUST']['NBRCLUST'] = self.nbclust
        namsec[0].rh.save()
        namsec[0].rh.container.cat()

        fileList.sort()
        with open(self.fileoutput, 'w') as optFile:
            optFile.write('\n'.join(fileList))


class Addpearp(BlindRun):
    """Add the selected PEARP perturbations to the deterministic AROME initial conditions."""

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
        namsec = self.setlink(initrole='Namelist', initkind='namelist')
        logger.info("NAMIC added to NBE namelist entry: %d", self.nbpert)
        namsec[0].rh.contents['NAMIC']['NBPERT'] = self.nbpert
        namsec[0].rh.save()
        namsec[0].rh.container.cat()
