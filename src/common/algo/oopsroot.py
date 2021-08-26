# -*- coding: utf-8 -*-

"""
Common AlgoComponents for OOPS.
"""

from __future__ import print_function, absolute_import, division, unicode_literals

from collections import OrderedDict, defaultdict

import footprints
from bronx.fancies.dump import lightdump, fulldump
from bronx.stdtypes.date import Date, Time

from vortex.algo.components import AlgoComponentError, AlgoComponentDecoMixin, Parallel
from vortex.algo.components import algo_component_deco_mixin_autodoc
from vortex.tools import grib
from gco.syntax.stdattrs import ArpIfsSimplifiedCycle as IfsCycle
from common.syntax.stdattrs import oops_members_terms_lists
from common.tools import drhook, odb, satrad

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


@algo_component_deco_mixin_autodoc
class OOPSMemberDetectDecoMixin(AlgoComponentDecoMixin):
    """Tries to detect a members/terms list using the sequence's inputs

    This mixin class is intended to be used with AlgoComponnent classes. It will
    automatically add footprints' attributes related to this feature, crawl into
    the sequence's input after the ``prepare`` step and, depending on the result
    of the members/terms detection add ``members`` and ``effterms`` entries into
    the configuration file substitutions dictionary ``_generic_config_subs``.

    :note: Effective terms are considered (i.e term - (current_date - resource_date))
    """

    _membersdetect_roles = ('ModelState',
                            'Guess',
                            'InitialCondition',
                            'Background',
                            'SurfaceModelState',
                            'SurfaceGuess',
                            'SurfaceInitialCondition',
                            'SurfaceBackground',)

    _MIXIN_EXTRA_FOOTPRINTS = (footprints.Footprint(
        info="Abstract mbdetect footprint",
        attr=dict(
            ens_minsize=dict(
                info="For a multi-member algocomponnent, the minimum of the ensemble.",
                optional=True,
                type=int
            ),
            strict_mbdetect=dict(
                info="Performs a strict members/terms detection",
                type=bool,
                optional=True,
                default=True,
                doc_zorder=-60,
            )
        )
    ),)

    @staticmethod
    def _stateless_members_detect(smap, basedate, ensminsize=None, utest=False):
        """
        This method does not really needs to be static but this way it allows for
        unit-testing (see ``tests.tests_algo.test_oopspara.py``).
        """
        l_members = []
        r_members = []
        l_effterms = []

        # Look for members
        allmembers = list()
        for arole, srole in smap.items():
            members = set([getattr(s.rh.provider, 'member', None) for s in srole])
            if None in members:
                # Ignore sections when some of the sections have no members defined
                if len(members) > 1:
                    logger.warning('Role: %s. Only some sections have a member number.', arole)
                members = []
            if members:
                allmembers.append([members, arole])

        if allmembers:
            # Consistency check
            if not all([mset[0] == allmembers[0][0] for mset in allmembers]):
                raise AlgoComponentError('Inconsistent members numbering')
            l_members = sorted(allmembers[0][0])
            r_members = sorted([md[1] for md in allmembers])
            logger.info('Members detected: %s', ','.join([str(m) for m in l_members]))
            logger.info('Members roles: %s', ','.join(r_members))

        # Look for effective terms
        alleffterms = list()
        for arole, srole in smap.items():
            members = [getattr(s.rh.provider, 'member', None) for s in srole]
            terms = [getattr(s.rh.resource, 'term', None) for s in srole]
            dates = [getattr(s.rh.resource, 'date', None) for s in srole]
            effterms = defaultdict(set)
            for m, t, d in zip(members, terms, dates):
                effterms[m].add(t - (basedate - d)
                                if t is not None and d is not None else None)
            for m, et in effterms.items():
                # Ignore sections when some of the sections have no effective time defined
                if None in et:
                    if len(et) > 1:
                        logger.warning('Role: %s, Member: %s. Only some sections have an effective term.',
                                       arole, str(m))
                    effterms = []
                    break
            if effterms:
                alleffterms.append([effterms, arole])

        if alleffterms:
            if len(l_members) > 1:
                t_effterms2 = [(ets, r) for ets, r in alleffterms
                               if any([len(et) > 1 for et in ets.values()])]
                # Multiple members and multiple terms: select members with multiple
                # values only
                if t_effterms2:
                    alleffterms = t_effterms2
            # Consistency check
            t_effterms = [et for ets, r in alleffterms for et in ets.values()]
            if t_effterms:
                if not all([tset == t_effterms[0] for tset in t_effterms]):
                    raise AlgoComponentError('Inconsistent terms between members sets')
                l_effterms = sorted(t_effterms[0])
                logger.info('Effective terms detected: %s', ','.join([str(t) for t in l_effterms]))
                logger.info('Terms roles: %s', ','.join([md[1] for md in alleffterms]))

        # Theoretical ensemble size
        nominal_ens_size = len(l_members)
        if nominal_ens_size:
            eff_members = list()
            for mb in l_members:
                # Look for missing resoures
                broken = list()
                for arole in r_members:
                    broken.extend([s for s in smap[arole]
                                   if (s.rh.provider.member == mb and
                                       (s.stage != 'get' or not s.rh.container.exists()))])
                for s in broken:
                    if not utest:
                        logger.warning('Missing items: %s', s.rh.container.localpath())
                if broken:
                    logger.warning('Throwing away member number %d', mb)
                else:
                    eff_members.append(mb)
            # Sanity checks depending on ensminsize
            if ensminsize is None and len(eff_members) != nominal_ens_size:
                raise AlgoComponentError('Some members are missing')
            elif ensminsize is not None and len(eff_members) < ensminsize:
                raise AlgoComponentError('The ensemble size is too small ({:d} < {:d}).'
                                         .format(len(eff_members), ensminsize))
            l_members = eff_members

        return l_members, l_effterms

    def members_detect(self):
        """Detect the members/terms list and update the substitution dictionary."""
        sectionsmap = {r: self.context.sequence.filtered_inputs(role=r)
                       for r in self._membersdetect_roles}
        try:
            (self._members,
             self._effterms) = self._stateless_members_detect(sectionsmap,
                                                              self.date, self.ens_minsize)
        except AlgoComponentError as e:
            if self.strict_mbdetect:
                raise
            else:
                logger.warning("Members detection failed: %s", str(e))
                logger.info("'strict_mbdetect' is False... going on with empty lists.")
                self._members = []
                self._effterms = []
        if self._members:
            self._generic_config_subs['members'] = self._members
        if self._effterms:
            self._generic_config_subs['effterms'] = self._effterms

    def _membersd_setup(self, rh, opts):  # @UnusedVariable
        """Setup the members/terms detection."""
        self.members_detect()

    _MIXIN_PREPARE_HOOKS = (_membersd_setup, )


@algo_component_deco_mixin_autodoc
class OOPSMembersTermsDecoMixin(AlgoComponentDecoMixin):
    """Adds members/terms footprints' attributes and use them in configuration files.

    This mixin class is intended to be used with AlgoComponnent classes. It will
    automatically add footprints' attributes ``members`` and ``terms`` and add
    the corresponding ``members`` and ``effterms`` entries into
    the configuration file substitutions dictionary ``_generic_config_subs``.
    """

    _MIXIN_EXTRA_FOOTPRINTS = (oops_members_terms_lists, )

    def _membersterms_deco_setup(self, rh, opts):  # @UnusedVariable
        """Setup the ODB object."""
        actualmembers = [m if isinstance(m, int) else int(m)
                         for m in self.members]
        actualterms = [t if isinstance(t, Time) else Time(t)
                       for t in self.terms]
        self._generic_config_subs['members'] = actualmembers
        self._generic_config_subs['effterms'] = actualterms

    _MIXIN_PREPARE_HOOKS = (_membersterms_deco_setup, )


class OOPSParallel(Parallel,
                   drhook.DrHookDecoMixin,
                   grib.EcGribDecoMixin,
                   satrad.SatRadDecoMixin):
    """Common abstract AlgoComponent for any OOPS run."""

    _abstract = True
    _footprint = dict(
        info = "Any OOPS Run (abstract).",
        attr = dict(
            kind = dict(
                values          = ['oorun'],
            ),
            date = dict(
                info            = 'The current run date.',
                access          = 'rwx',
                type            = Date,
                doc_zorder      = -50,
            ),
            config_subs = dict(
                info            = "Substitutions to be performed in the config file (before run)",
                optional        = True,
                type            = footprints.FPDict,
                default         = footprints.FPDict(),
                doc_zorder      = -60,
            ),
            mpiconflabel = dict(
                default  = 'mplbased'
            )
        )
    )

    def __init__(self, *kargs, **kwargs):
        """Declare some hidden attributes for a later use."""
        super(OOPSParallel, self).__init__(*kargs, **kwargs)
        self._generic_config_subs = dict()
        self._individual_config_subs = OrderedDict()
        self._oops_cycle = None

    @property
    def oops_cycle(self):
        """The binary's cycle number."""
        return self._oops_cycle

    def valid_executable(self, rh):
        """Be sure that the specified executable has a cycle attribute."""
        valid = super(OOPSParallel, self).valid_executable(rh)
        if hasattr(rh.resource, 'cycle'):
            self._oops_cycle = rh.resource.cycle
            return valid
        else:
            logger.error('The binary < %s > has no cycle attribute', repr(rh))
            return False

    def prepare(self, rh, opts):
        """Preliminary setups."""
        super(OOPSParallel, self).prepare(rh, opts)
        # Look for channels namelists and set appropriate links
        self.setchannels()
        # Register all of the config files
        self.set_config_rendering()
        # Looking for low-level-libs defaults...
        self.boost_defaults()
        self.eckit_defaults()

    def spawn_hook(self):
        """Perform configuration file rendering before executing the binary."""
        self.do_config_rendering()
        super(OOPSParallel, self).spawn_hook()

    def spawn_command_options(self):
        """Prepare options for the binary's command line."""
        mconfig = list(self._individual_config_subs.keys())[0]
        configfile = mconfig.rh.container.localpath()
        options = {'configfile': configfile}
        return options

    def set_config_rendering(self):
        """
        Look into effective inputs for configuration files and register them for
        a later rendering using bronx' templating system.
        """
        mconfig = self.context.sequence.effective_inputs(role='MainConfig')
        gconfig = self.context.sequence.effective_inputs(role='Config')
        if len(mconfig) > 1:
            raise AlgoComponentError("Only one Main Config section may be provided.")
        if len(mconfig) == 0 and len(gconfig) != 1:
            raise AlgoComponentError("Please provide a Main Config section or a unique Config section.")
        if len(mconfig) == 1:
            gconfig.insert(0, mconfig[0])
        self._individual_config_subs = {sconf: dict() for sconf in gconfig}

    def do_config_rendering(self):
        """Render registered configuration files using the bronx' templating system."""
        for sconf, sdict in self._individual_config_subs.items():
            self.system.subtitle('Configuration file rendering for: {:s}'
                                 .format(sconf.rh.container.localpath()))
            l_subs = dict(now=self.date, date=self.date)
            l_subs.update(self._generic_config_subs)
            l_subs.update(sdict)
            l_subs.update(self.config_subs)
            if not hasattr(sconf.rh.contents, 'bronx_tpl_render'):
                logger.error('The < %s > content object has no "bronx_tpl_render" method. Skipping it.',
                             repr(sconf.rh.contents))
                continue
            try:
                sconf.rh.contents.bronx_tpl_render(** l_subs)
            except Exception:
                logger.error('The config file rendering failed. The substitution dict was: \n%s',
                             lightdump(l_subs))
                raise
            print(fulldump(sconf.rh.contents.data))
            sconf.rh.save()

    def boost_defaults(self):
        """Set defaults for BOOST environment variables.

        Do not overwrite pre-initialised ones. The default list of variables
        depends on the code's cycle number.
        """
        defaults = {
            IfsCycle('cy1'): {
                'BOOST_TEST_CATCH_SYSTEM_ERRORS': 'no',
                'BOOST_TEST_DETECT_FP_EXCEPTIONS': 'no',
                'BOOST_TEST_LOG_FORMAT': 'XML',
                'BOOST_TEST_LOG_LEVEL': 'message',
                'BOOST_TEST_OUTPUT_FORMAT': 'XML',
                'BOOST_TEST_REPORT_FORMAT': 'XML',
                'BOOST_TEST_RESULT_CODE': 'yes'
            }
        }
        cydefaults = None
        for k, defdict in sorted(defaults.items(), reverse=True):
            if k < self.oops_cycle:
                cydefaults = defdict
                break
        self.algoassert(cydefaults is not None,
                        'BOOST defaults not found for cycle: {!s}'.format(self.oops_cycle))
        logger.info('Setting up BOOST defaults:%s', lightdump(cydefaults))
        self.env.default(**cydefaults)

    def eckit_defaults(self):
        """Set defaults for eckit environment variables.

        Do not overwrite pre-initialised ones. The default list of variables
        depends on the code's cycle number.
        """
        defaults = {
            IfsCycle('cy1'): {
                'ECKIT_MPI_INIT_THREAD': ('MPI_THREAD_MULTIPLE'
                                          if int(self.env.get('OMP_NUM_THREADS', '1')) > 1
                                          else 'MPI_THREAD_SINGLE'),
            }
        }
        cydefaults = None
        for k, defdict in sorted(defaults.items(), reverse=True):
            if k < self.oops_cycle:
                cydefaults = defdict
                break
        self.algoassert(cydefaults is not None,
                        'eckit defaults not found for cycle: {!s}'.format(self.oops_cycle))
        logger.info('Setting up eckit defaults:%s', lightdump(cydefaults))
        self.env.default(**cydefaults)


class OOPSODB(OOPSParallel, odb.OdbComponentDecoMixin):
    """Common abstract AlgoComponent for any OOPS run requiring ODB databases."""

    _abstract = True
    _footprint = dict(
        info = "OOPS ObsOperator Test run.",
        attr = dict(
            kind = dict(
                values      = ['oorunodb'],
            ),
            binarysingle = dict(
                default     = 'basicobsort',
            ),
        )
    )

    #: If ``True``, an empty CCMA database will be created before the run and
    #: necessary environment variables will be added in order for the executable
    #: to populate this database at the end of the run.
    _OOPSODB_CCMA_DIRECT = False

    def prepare(self, rh, opts):
        """Setup ODB stuff."""
        super(OOPSODB, self).prepare(rh, opts)
        sh = self.system

        # Looking for input observations
        allodb = self.lookupodb()
        allcma = [x for x in allodb if x.rh.resource.layout.lower() == self.virtualdb]
        if self.virtualdb.lower() == 'ccma':
            self.algoassert(len(allcma) == 1, 'A unique CCMA database is to be provided.')
            self.algoassert(not self._OOPSODB_CCMA_DIRECT,
                            '_OOPSODB_CCMA_DIRECT needs to be False if virtualdb=ccma.')
            cma = allcma.pop()
            cma_path = sh.path.abspath(cma.rh.container.localpath())
        else:
            cma_path = self.odb_merge_if_needed(allcma)
            if self._OOPSODB_CCMA_DIRECT:
                ccma_path = self.odb_create_db(layout='CCMA')
                self.odb.fix_db_path('CCMA', ccma_path)

        # Set ODB environment
        self.odb.fix_db_path(self.virtualdb, cma_path)

        if self._OOPSODB_CCMA_DIRECT:
            self.odb.ioassign_gather(cma_path, ccma_path)
        else:
            self.odb.ioassign_gather(cma_path)

        if self.virtualdb.lower() != 'ccma':
            self.odb.create_poolmask(self.virtualdb, cma_path)
            self.odb.shuffle_setup(self.slots,
                                   mergedirect=True,
                                   ccmadirect=self._OOPSODB_CCMA_DIRECT)

        # Fix the input databases intent
        self.odb_rw_or_overwrite_method(* allcma)

        # Look for extras ODB raw
        self.odb_handle_raw_dbs()


class OOPSMinim(OOPSODB):
    """Any kind of OOPS minimisation."""

    _footprint = dict(
        info = "OOPS minimisation.",
        attr = dict(
            kind = dict(
                values   = ['oominim'],
            ),
            virtualdb = dict(
                default  = 'ccma',
            ),
        )
    )
