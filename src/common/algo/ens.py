#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import collections
import re
import copy

import footprints
logger = footprints.loggers.getLogger(__name__)

from .ifsroot import IFSParallel
from vortex.util.structs import ShellEncoder
from vortex.algo.components import BlindRun
from vortex.layout.dataflow import intent
from vortex.tools import grib


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


class Combi(BlindRun, grib.GribApiComponent):
    """Build the initial conditions of the EPS."""

    _abstract = True

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(Combi, self).prepare(rh, opts)
        self.gribapi_setup(rh, opts)

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
        for namsec in self.context.sequence.effective_inputs(kind='namelist'):
            namsec.rh.reset_contents()
            if 'NAMCOEF' + kind.upper() in namsec.rh.contents:
                logger.info("Extract the " + msg + " coefficient from the updated namelist.")
                coeff = {'rcoef' + kind: float(namsec.rh.contents['NAMCOEF' + kind.upper()]['RCOEF' + kind.upper()])}
                self.system.json_dump(coeff, 'coeff' + kind + '.out', indent=4, cls=ShellEncoder)


class CombiPert(Combi):
    """Build the initial perturbations of the EPS initial conditions."""

    _abstract = True
    _footprint = dict(
        attr = dict(
            nbpert = dict(
                type      = int,
            ),
        )
    )

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(CombiPert, self).prepare(rh, opts)

        # Tweak the namelists
        for namsec in self.context.sequence.effective_inputs(role = re.compile('Namelist'),
                                                             kind = 'namelist'):
            logger.info("Add the NBPERT coefficient to the NAMENS namelist entry")
            namsec.rh.contents['NAMENS']['NBPERT'] = self.nbpert
            namsec.rh.save()


class CombiSV(CombiPert):
    """Combine the SV to create perturbations by gaussian sampling."""

    _abstract = True

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(CombiSV, self).prepare(rh, opts)

        self.export('drhook_not_mpi')

        # Check the number of singular vectors and link them in succession
        nbVect = collections.OrderedDict()
        svec_sections = self.context.sequence.effective_inputs(role='SingularVectors', kind='svector')
        for num, svecsec in enumerate(svec_sections):
            componoms = re.split(r'[\.,\+]', svecsec.rh.container.localpath())
            if len(componoms) < 3:
                logger.critical("The SV name does not contain the information 'zone.numero': %s",
                                svecsec.rh.container.actualpath())
            radical = componoms[0]
            sufix = re.sub('^' + radical + r'[\+,\.]' + componoms[1] + r'[\+,\.]' + componoms[2],
                           '', svecsec.rh.container.localpath())
            nbVect.setdefault(componoms[1], 0)
            nbVect[componoms[1]] += 1
            self.system.softlink(svecsec.rh.container.localpath(),
                                 radical + '{:03d}'.format(num + 1) + sufix)

        totalVects = sum(nbVect.values())
        logger.info("Number of vectors :\n" + '\n'.join(['- %s: %d' % (z, n) for z, n in nbVect.iteritems()]))

        # Tweak the namelists
        namsecs = self.context.sequence.effective_inputs(role = re.compile('Namelist'), kind = 'namelist')
        # namsecs = self.setlink(initrole = 'Namelist', initkind = 'namelist', initname = 'namcombi'),  TODO PC qd combi aura 1 seule nam
        for namsec in namsecs:
            namsec.rh.contents['NAMMOD']['LVS'] = True
            namsec.rh.contents['NAMMOD']['LANAP'] = False
            namsec.rh.contents['NAMMOD']['LBRED'] = False
            logger.info("Added to NVSZONE namelist entry")
            namsec.rh.contents['NAMOPTI']['NVSZONE'] = nbVect.values()

            nbVectNam = namsec.rh.contents['NAMENS']['NBVECT']
            if int(nbVectNam) != totalVects:
                logger.warning("%s singular vectors expected but only %d accounted for.", nbVectNam, totalVects)
                logger.info("Update the total number of vectors in the NBVECT namelist entry")
                namsec.rh.contents['NAMENS']['NBVECT'] = totalVects

            nbzone = len(nbVect)
            namsec.rh.contents['NAMOPTI']['NBZONE'] = nbzone
            namsec.rh.contents['NAMOPTI']['CNOMZONE'] = nbVect.keys()
            nbrc = len(namsec.rh.contents['NAMOPTI'].RC)
            if nbrc != nbzone:
                logger.critical("%d zones but NAMOPTI/RC has length %d" % (nbzone, nbrc))
            nbrl = len(namsec.rh.contents['NAMOPTI'].RL)
            if nbrl != nbzone:
                logger.critical("%d zones but NAMOPTI/RL has length %d" % (nbzone, nbrl))

            self._addNmod(namsec.rh, "combination of the SV")
            namsec.rh.save()

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
            nbic = dict(
                alias = ('nbruns',),
                type      = int,
            ),
            nbpert = dict(
                type      = int,
                optional = True,
                default = 0,
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
        nammod = namsec[0].rh.contents['NAMMOD']

        # Dealing with initial conditions from the assimilation ensemble
        nbPert = len(self.context.sequence.effective_inputs(role = ('AEPerturbedState',
                                                                    'ModelState')))
        nammod['LANAP'] = (nbPert != 0)

        # Dealing with singular vectors
        sv_sections = self.context.sequence.effective_inputs(role='CoeffSV')
        nammod['LVS'] = bool(sv_sections)
        if sv_sections:
            logger.info("Add the SV coefficient to the NAMCOEFVS namelist entry.")
            namcoefvs = namsec[0].rh.contents.newblock('NAMCOEFVS')
            namcoefvs['RCOEFVS'] = sv_sections[0].rh.contents['rcoefvs']
            nbPert = nbPert or len(self.context.sequence.effective_inputs(role = 'SVPerturbedState') or
                                   [sec for sec in self.context.sequence.effective_inputs(role = 'PerturbedState')
                                    if 'ICHR' in sec.rh.container.filename])

        # The mean value may be present among the AE or SV inputs: subtract it
        nbPert -= 1 if nbPert * 2 == self.nbic + 1 else 0

        # Dealing with breeding method's inputs
        bd_sections = self.context.sequence.effective_inputs(role='CoeffBreeding')
        nammod['LBRED'] = bool(bd_sections)
        if bd_sections:
            logger.info("Add the breeding coefficient to the NAMCOEFBM namelist entry.")
            namcoefbm = namsec[0].rh.contents.newblock('NAMCOEFBM')
            namcoefbm['RCOEFBM'] = bd_sections[0].rh.contents['rcoefbm']
            nbBd = len(self.context.sequence.effective_inputs(role = 'BreedingPerturbedState') or
                       [sec for sec in self.context.sequence.effective_inputs(role = 'PerturbedState')
                        if 'BMHR' in sec.rh.container.filename])
            # symmetric perturbations except if analysis: one more file
            # or zero if one control ic (hypothesis: odd nbic)
            nbPert = nbPert or (nbBd - 1 if nbBd == self.nbic + 1 or
                                (nbBd == self.nbic and self.nbic % 2 != 0)
                                else self.nbic / 2)

        # The footprint's value is always preferred to the calculated one
        nbPert = self.nbpert or nbPert
        logger.info("NAMMOD namelist summary: LANAP=%s, LVS=%s, LBRED=%s.",
                    * [nammod[k] for k in ('LANAP', 'LVS', 'LBRED')])
        logger.info("Add the NBPERT=%d coefficient to the NAMENS namelist entry.", nbPert)
        namsec[0].rh.contents['NAMENS']['NBPERT'] = nbPert

        self._addNmod(namsec[0].rh, "final combination of the perturbations")
        namsec[0].rh.save()

        # Copy the analysis to give all the members a basis
        self._analysis_cp(self.nbic - 1, 'perturbed states')


class CombiBreeding(CombiPert):
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
        hst_sections = self.context.sequence.effective_inputs(kind = ('pert', 'historic'))
        for num, hst in enumerate(hst_sections):
            self.system.softlink(hst.rh.container.localpath(), re.sub('[0-9]*$',
                                                                      '{:03d}'.format(num + 1),
                                                                      hst.rh.container.localpath()) + '.grb')
            logger.info("Rename the %d grib files consecutively.", num)

        # Tweak the namelist
        namsec = self.setlink(initrole='Namelist', initkind='namelist')
        namsec[0].rh.contents['NAMMOD']['LBRED'] = True
        namsec[0].rh.contents['NAMMOD']['LANAP'] = False
        namsec[0].rh.contents['NAMMOD']['LVS'] = False
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


class Clustering(BlindRun, grib.GribApiComponent):
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
            nbmembers = dict(
                type = int,
                optional = True,
                access = 'rwx',
            ),
        )
    )

    def prepare(self, rh, opts):
        """Set some variables according to target definition."""
        super(Clustering, self).prepare(rh, opts)

        self.gribapi_setup(rh, opts)

        grib_sections = self.context.sequence.effective_inputs(role='ModelState',
                                                               kind='gridpoint')
        avail_json = self.context.sequence.effective_inputs(role='AvailableMembers',
                                                            kind='mbpopulation')

        # If no population file is here, just do a sort on the file list,
        # otherwise use the population list
        if avail_json:
            population = avail_json[0].rh.contents.data['population']
            self.nbmembers = len(population)
            fileList = list()
            for elt in population:
                sublist_ids = list()
                for (i, grib) in enumerate(grib_sections):
                    # If the grib file matches, let's go
                    if all([grib.rh.wide_key_lookup(key, exports=True) == value
                            for (key, value) in elt.iteritems()]):
                        sublist_ids.append(i)
                # Stack the gribs in fileList
                fileList.extend(sorted([grib_sections[i].rh.container.localpath()
                                        for i in sublist_ids]))
                for i in reversed(sublist_ids):
                    del grib_sections[i]
        else:
            fileList = sorted([grib.rh.container.localpath()
                               for grib in grib_sections])

        if (self.nbmembers is None or self.nbmembers > self.nbclust):

            # Tweak the namelist
            namsec = self.setlink(initrole='Namelist', initkind='namelist')
            logger.info("NBRCLUST added to NAMCLUST namelist entry: %d", self.nbclust)
            namsec[0].rh.contents['NAMCLUST']['NBRCLUST'] = self.nbclust
            if self.nbmembers is not None:
                logger.info("NBRMB added to NAMCLUST namelist entry: %d", self.nbmembers)
                namsec[0].rh.contents['NAMCLUST']['NBRMB'] = self.nbmembers
            namsec[0].rh.save()
            namsec[0].rh.container.cat()

            with open(self.fileoutput, 'w') as optFile:
                optFile.write('\n'.join(fileList))

    def execute(self, rh, opts):
        # If the number of members is big enough -> normal processing
        if (self.nbmembers is None or self.nbmembers > self.nbclust):
            logger.info("Normal clustering run (%d members, %d clusters)",
                        self.nbmembers, self.nbclust)
            super(Clustering, self).execute(rh, opts)
        # if not, generate face outputs
        else:
            logger.info("Generating fake outputs with %d members", self.nbmembers)
            with open('ASCII_RMCLUST', 'w') as fdrm:
                fdrm.write("\n".join([str(i) for i in range(1, self.nbmembers + 1)]))
            with open('ASCII_POPCLUST', 'w') as fdpop:
                fdpop.write("\n".join(['1', ] * self.nbmembers))

    def postfix(self, rh, opts):
        """Create a JSON with all the clustering informations."""
        avail_json = self.context.sequence.effective_inputs(role='AvailableMembers',
                                                            kind='mbpopulation')
        # If no population file is here, does nothing
        if avail_json:
            logger.info("Creating a JSON output...")
            # Read the clustering information
            with open('ASCII_RMCLUST') as fdrm:
                cluster_members = [int(m) for m in fdrm.readlines()]
            with open('ASCII_POPCLUST') as fdpop:
                cluster_sizes = [int(s) for s in fdpop.readlines()]
            # Update the population JSON
            mycontent = copy.deepcopy(avail_json[0].rh.contents)
            mycontent.data['resource_kind'] = 'mbsample'
            mycontent.data['drawing'] = list()
            for member_no, cluster_size in zip(cluster_members, cluster_sizes):
                mycontent.data['drawing'].append(copy.copy(mycontent.data['population'][member_no - 1]))
                mycontent.data['drawing'][-1]['cluster_size'] = cluster_size
            # Create a clustering output file
            new_container = footprints.proxy.container(filename='clustering_output.json',
                                                       mode='w', actualfmt='json')
            mycontent.rewrite(new_container)

        super(Clustering, self).postfix(rh, opts)


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
