#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import re
from operator import attrgetter

from bronx.fancies import loggers
from bronx.stdtypes.date import Month, Time
import footprints

from vortex.algo.components import AlgoComponentError
from common.algo.ifsroot import IFSParallel

#: Automatic export off
__all__ = []

logger = loggers.getLogger(__name__)


class IFSEdaAbstractAlgo(IFSParallel):
    """Base class for any EDA related task wrapped into an IFS/Arpege binary."""

    _abstract = True
    _footprint = dict(
        info='Base class for any EDA related task',
        attr=dict(
            inputnaming = dict(
                info = 'Prescribe your own naming template for input files.',
                optional = True,
                doc_visibility  = footprints.doc.visibility.ADVANCED,
            ),
        )
    )

    def naming_convention(self, kind, rh, actualfmt=None, **kwargs):
        """Take into account the *inputnaming* attribute."""
        if kind == 'edainput':
            return super(IFSEdaAbstractAlgo, self).naming_convention(kind, rh,
                                                                     actualfmt=actualfmt,
                                                                     namingformat=self.inputnaming,
                                                                     **kwargs)
        else:
            return super(IFSEdaAbstractAlgo, self).naming_convention(kind, rh,
                                                                     actualfmt=actualfmt,
                                                                     **kwargs)


class IFSEdaEnsembleAbstractAlgo(IFSEdaAbstractAlgo):
    """Base class for any EDA related task wrapped into an IFS/Arpege binary.

    This extends the :class:`IFSEdaAbstractAlgo` with a *nbmember* attribute and
    the ability to detect the input files and re-number them (in order to be able
    to deal with missing members).
    """

    _INPUTS_ROLE = 'ModelState'

    _abstract = True
    _footprint = dict(
        info='Base class for any EDA related task',
        attr=dict(
            nbmember = dict(
                type = int,
                optional = True,
            ),
            nbmin = dict(
                type = int,
                optional = True,
                default = 2,
            )
        )
    )

    def __init__(self, *kargs, **kwargs):
        super(IFSEdaEnsembleAbstractAlgo, self).__init__(*kargs, **kwargs)
        self._actual_nbe = self.nbmember

    @property
    def actual_nbe(self):
        return self._actual_nbe

    def modelstate_numbering(self, rh):
        eff_sections = self.context.sequence.effective_inputs(role = self._INPUTS_ROLE)
        eff_members = set([sec.rh.provider.member for sec in eff_sections])
        eff_formats = set([sec.rh.container.actualfmt for sec in eff_sections])
        if self.nbmember is None:
            self.algoassert(len(eff_formats) <= 1, 'Mixed formats are not allowed !')
        elif self.nbmember and len(eff_formats) > 1:
            logger.info('%s have mixed formats... please correct that.', self._INPUTS_ROLE)
        if eff_members and self.nbmember is not None:
            # Consistency check
            if len(eff_members) != self.nbmember:
                logger.warning('Discrepancy between *nbmember* and effective input files...' +
                               ' sticking with *nbmember*')
            else:
                logger.info("The input files number checks out !")
            return False  # Ok, apparently the user knows what she/he is doing
        elif self.nbmember and not eff_members:
            return False  # Ok, apparently the user knows what she/he is doing
        elif eff_members and self.nbmember is None:
            self._actual_nbe = len(eff_members)
            innc = self.naming_convention(kind='edainput', variant=self.kind, rh=rh, actualfmt=eff_formats.pop())
            checkfiles = [m for m in range(1, self.actual_nbe + 1)
                          if self.system.path.exists(innc(number=m))]
            if len(checkfiles) == self._actual_nbe:
                logger.info("The input files numbering checks out !")
                return False  # Ok, apparently the user knows what she/he is doing
            elif len(checkfiles) == 0:
                return True
            else:
                raise AlgoComponentError('Members renumbering is needed but some files are blocking the way !')
        elif len(eff_members) == 0 and self.nbmember is None:
            raise AlgoComponentError('No input files where found !')

    def prepare_namelist_delta(self, rh, namcontents, namlocal):
        nam_updated = super(IFSEdaAbstractAlgo, self).prepare_namelist_delta(rh, namcontents, namlocal)
        if self.actual_nbe is not None:
            namcontents.setmacro('NBE', self.actual_nbe)
            logger.info('Setup macro NBE=%s in %s', self.actual_nbe, namlocal)
            nam_updated = True
        return nam_updated

    def prepare(self, rh, opts):
        # Check if member's renumbering is needed
        self.system.subtitle('Solving the input files nightmare...')
        if self.modelstate_numbering(rh):
            eff_sections = sorted(self.context.sequence.effective_inputs(role = self._INPUTS_ROLE),
                                  key=attrgetter('rh.provider.member'))
            logger.info("Starting input files renumbering. %d members found", len(eff_sections))
            if len(eff_sections) < self.nbmin:
                raise AlgoComponentError('Not enough input files to continue...')
            eff_format = eff_sections[0].rh.container.actualfmt
            innc = self.naming_convention(kind='edainput', variant=self.kind, rh=rh, actualfmt=eff_format)
            for i, s in enumerate(eff_sections):
                logger.info("Copying (intent=in) %s to %s", s.rh.container.localpath(), innc(number=i + 1))
                self.system.cp(s.rh.container.localpath(), innc(number=i + 1),
                               fmt=eff_format, intent='in')
        self.system.subtitle('Other IFS related settings')
        super(IFSEdaEnsembleAbstractAlgo, self).prepare(rh, opts)


class IFSEdaFemars(IFSEdaAbstractAlgo):
    """Convert some FA file in ECMWF-GRIB files. PLEASE DO NOT USE !"""

    _footprint = dict(
        info='Convert some FA file in ECMWF-GRIB files.',
        attr=dict(
            kind=dict(
                values=['femars'],
            ),
            rawfiles = dict(
                type = bool,
                optional = True,
                default = False,
            ),
        )
    )

    def postfix(self, rh, opts):
        """Find out if any special resources have been produced."""
        sh = self.system
        # Gather rawfiles in folders
        if self.rawfiles:
            flist = sh.glob('tmprawfile_D000_L*')
            dest = 'rawfiles'
            logger.info('Creating a rawfiles pack: %s', dest)
            sh.mkdir(dest)
            for fic in flist:
                sh.mv(fic, dest, fmt='grib')
        super(IFSEdaFemars, self).postfix(rh, opts)


class IFSInflationLike(IFSEdaAbstractAlgo):
    """Apply the inflation scheme on a given modelstate."""

    _RUNSTORE = 'RUNOUT'
    _USELESS_MATCH = re.compile('^(?P<target>\w+)\+term\d+:\d+$')

    _footprint = dict(
        info='Operations around the background error covariance matrix',
        attr=dict(
            kind=dict(
                values=['infl', 'pert', ],
            ),
            conf=dict(
                values=[701, ]
            )
        )
    )

    def __init__(self, *kargs, **kwargs):
        super(IFSInflationLike, self).__init__(*kargs, **kwargs)
        self._outputs_shelf = list()

    def _check_effective_terms(self, roles):
        eff_terms = None
        for role in roles:
            eterm = set([sec.rh.resource.term for sec
                         in self.context.sequence.effective_inputs(role = role)])
            if eterm:
                if eff_terms is None:
                    eff_terms = eterm
                else:
                    if eff_terms != eterm:
                        raise AlgoComponentError("Inconsistencies between inputs effective terms.")
        return sorted(eff_terms)

    def _link_stuff_in(self, role, actualterm, targetnc, targetintent='in', wastebasket=None):
        estuff = [sec
                  for sec in self.context.sequence.effective_inputs(role = role)
                  if sec.rh.resource.term == actualterm]
        if len(estuff) > 1:
            logger.warning('Multiple %s  for the same date ! Going on...', role)
        elif len(estuff) == 1:
            # Detect the inputs format
            actfmt = estuff[0].rh.container.actualfmt
            nconv = self.naming_convention(actualfmt=actfmt, **targetnc)
            targetname = nconv(**targetnc)
            if self.system.path.exists(targetname):
                logger.info("%s: %s already exists. Hopping for the best...",
                            role, targetname)
            else:
                logger.info("%s: copying (intent=%s) %s to %s", role, targetintent,
                            estuff[0].rh.container.localpath(), targetname)
                self.system.cp(estuff[0].rh.container.localpath(), targetname,
                               fmt=actfmt, intent=targetintent)
                if wastebasket is not None:
                    wastebasket.append((targetname, actfmt))
            return nconv, targetname, estuff[0]
        return None, None, None

    def execute(self, rh, opts):
        """Loop on the various terms provided."""

        eff_terms = self._check_effective_terms(['ModelState',
                                                 'EnsembleMean',
                                                 'Guess'])
        fix_curclim = self.do_climfile_fixer(rh, convkind='modelclim')
        fix_clclim = self.do_climfile_fixer(rh, convkind='closest_modelclim')

        if eff_terms:
            for actualterm in eff_terms:
                wastebasket = list()
                self.system.title('Loop on term {0!s}'.format(actualterm))
                self.system.subtitle('Solving the input files nightmare...')
                # Ensemble Mean ?
                mean_number = 2 if self.model == 'arome' else 0
                targetnc = dict(kind='edainput', variant='infl', rh=rh, number=mean_number)
                self._link_stuff_in('EnsembleMean', actualterm, targetnc,
                                    wastebasket=wastebasket)
                # Model State ?
                targetnc = dict(kind='edainput', variant='infl', rh=rh, number=1)
                _, _, mstate = self._link_stuff_in('ModelState', actualterm, targetnc,
                                                   wastebasket=wastebasket)
                # Guess ?
                targetnc = dict(kind='edaoutput', variant='infl', rh=rh, number=1, term=Time(0))
                outnc, _, _ = self._link_stuff_in('Guess', actualterm, targetnc,
                                                  targetintent='inout')
                if outnc is None:
                    outnc = self.naming_convention(kind='edaoutput', variant='infl', rh=rh)
                # Fix clim !
                if fix_curclim and mstate:
                    month = Month((mstate.rh.resource.date + actualterm).ymdh)
                    self.climfile_fixer(rh=rh, convkind='modelclim', month=month,
                                        inputrole=('GlobalClim', 'InitialClim'),
                                        inputkind='clim_model')
                if fix_clclim and mstate:
                    closestmonth = Month((mstate.rh.resource.date + actualterm).ymdh + ':closest')
                    self.climfile_fixer(rh=rh, convkind='closest_modelclim', month=closestmonth,
                                        inputrole=('GlobalClim', 'InitialClim'),
                                        inputkind='clim_model')
                # Deal with useless stuff... SADLY !
                useless = [sec
                           for sec in self.context.sequence.effective_inputs(role = 'Useless')
                           if (sec.rh.resource.term == actualterm and
                               self._USELESS_MATCH.match(sec.rh.container.localpath()))]
                for a_useless in useless:
                    targetname = self._USELESS_MATCH.match(a_useless.rh.container.localpath()).group('target')
                    if self.system.path.exists(targetname):
                        logger.warning("Some useless stuff is already here: %s. I don't care...",
                                       targetname)
                    else:
                        logger.info("Dealing with useless stuff: %s -> %s",
                                    a_useless.rh.container.localpath(), targetname)
                        self.system.cp(a_useless.rh.container.localpath(), targetname,
                                       fmt=a_useless.rh.container.actualfmt, intent='in')
                        wastebasket.append((targetname, a_useless.rh.container.actualfmt))

                # Standard execution
                super(IFSInflationLike, self).execute(rh, opts)

                # The concatenated listing
                self.system.cat('NODE.001_01', output='NODE.all')

                # prepares the next execution
                if len(eff_terms) > 1:
                    self.system.mkdir(self._RUNSTORE)
                    # Freeze the current output
                    shelf_label = self.system.path.join(self._RUNSTORE, outnc(number=1, term=actualterm))
                    self.system.move(outnc(number=1, term=Time(0)), shelf_label, fmt = 'fa')
                    self._outputs_shelf.append(shelf_label)
                    # Some cleaning
                    for afile in wastebasket:
                        self.system.remove(afile[0], fmt=afile[1])
                    self.system.rmall('ncf927', 'dirlst')
        else:
            # We should not be here but whatever... some task are poorly written !
            super(IFSInflationLike, self).execute(rh, opts)

    def postfix(self, rh, opts):
        """Post processing cleaning."""
        self.system.title('Finalising the execution...')
        for afile in self._outputs_shelf:
            logger.info("Output found: %s", self.system.path.basename(afile))
            self.system.move(afile, self.system.path.basename(afile), fmt='fa')
        super(IFSInflationLike, self).postfix(rh, opts)


class IFSInflationFactor(IFSEdaEnsembleAbstractAlgo):
    """Compute an inflation factor based on individual members."""

    _footprint = dict(
        info='Compute an inflation factor based on individual members',
        attr=dict(
            kind=dict(
                values=['infl_factor', ],
            ),
        )
    )


class IFSInflationFactorLegacy(IFSInflationFactor):
    """Compute an inflation factor based on individual members. KEPT FOR COMPATIBILITY.

    DO NOT USE !
    """

    _footprint = dict(
        info='Compute an inflation factor based on individual members',
        attr=dict(
            kind=dict(
                values=['infl', 'pert'],
            ),
            conf=dict(
                outcast=[701, ]
            )
        )
    )


class IFSEnsembleMean(IFSEdaEnsembleAbstractAlgo):
    """Apply the inflation scheme on a given modelstate."""

    _footprint = dict(
        info='Operations around the background error covariance matrix',
        attr=dict(
            kind=dict(
                values=['mean', ],
            ),
        )
    )


class IFSCovB(IFSEdaEnsembleAbstractAlgo):
    """Operations around the background error covariance matrix."""

    _footprint = dict(
        info='Operations around the background error covariance matrix',
        attr=dict(
            kind=dict(
                values=['covb', ],
            ),
            nblag = dict(
                type = int,
                optional = True,
            ),
        )
    )

    def prepare_namelist_delta(self, rh, namcontents, namlocal):
        nam_updated = super(IFSCovB, self).prepare_namelist_delta(rh, namcontents, namlocal)
        if self.nblag is not None:
            namcontents.setmacro('NRESX', self.nblag)
            logger.info('Setup macro NRESX=%s in %s', self.nblag, namlocal)
            nam_updated = True
        return nam_updated

    def prepare(self, rh, opts):
        """Default pre-link for the initial condition file"""
        super(IFSCovB, self).prepare(rh, opts)

        for num, sec in enumerate(sorted(self.context.sequence.effective_inputs(role = 'Rawfiles'),
                                         key = attrgetter('rh.resource.date', 'rh.provider.member')), start = 1):
            repname = sec.rh.container.localpath()
            radical = repname.split('_')[0] + '_D{:03d}_L{:s}'
            for filename in self.system.listdir(repname):
                level = re.search('_L(\d+)$', filename)
                if level is not None:
                    self.system.softlink(self.system.path.join(repname, filename),
                                         radical.format(num, level.group(1)))

        for num, sec in enumerate(sorted(self.context.sequence.effective_inputs(role = 'LaggedEnsemble'),
                                         key = attrgetter('rh.resource.date', 'rh.provider.member')),
                                  start = 1):
            repname = sec.rh.container.localpath()
            radical = repname.split('_')[0] + '_{:03d}'
            self.system.softlink(repname, radical.format(num))
