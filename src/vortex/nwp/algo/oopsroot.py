"""
AlgoComponents for OOPS.
"""

import itertools
from collections import OrderedDict, defaultdict, namedtuple
import functools

import footprints
from bronx.fancies.dump import lightdump, fulldump
from bronx.stdtypes.date import Date, Time, Period
from bronx.compat.functools import cached_property

from vortex.algo.components import (
    AlgoComponentError,
    AlgoComponentDecoMixin,
    Parallel,
)
from vortex.algo.components import algo_component_deco_mixin_autodoc
from vortex.data import geometries
from vortex.tools import grib
from ..syntax.stdattrs import ArpIfsSimplifiedCycle as IfsCycle
from ..syntax.stdattrs import algo_member, oops_members_terms_lists
from ..tools import drhook, odb, satrad

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


OOPSMemberInfos = namedtuple("OOPSMemberInfos", ("member", "date"))


class EnsSizeAlgoComponentError(AlgoComponentError):
    """Exception raised when the ensemble is too small."""

    def __init__(self, nominal_ens_size, actual_ens_size, min_ens_size):
        self.nominal_ens_size = nominal_ens_size
        self.actual_ens_size = actual_ens_size
        self.min_ens_size = min_ens_size
        super().__init__(
            "{:d} found ({:d} required)".format(actual_ens_size, min_ens_size)
        )

    def __reduce__(self):
        red = list(super().__reduce__())
        red[1] = (
            self.nominal_ens_size,
            self.actual_ens_size,
            self.min_ens_size,
        )
        return tuple(red)


@algo_component_deco_mixin_autodoc
class OOPSMemberDecoMixin(AlgoComponentDecoMixin):
    """Add a member footprints' attribute and use it in the configuration files."""

    _MIXIN_EXTRA_FOOTPRINTS = (algo_member,)

    def _algo_member_deco_setup(self, rh, opts):  # @UnusedVariable
        """Update the configuration files."""
        if self.member is not None:
            self._generic_config_subs["member"] = self.member
            for namrh in self.updatable_namelists:
                namrh.contents.setmacro("MEMBER", self.member)
                namrh.contents.setmacro("PERTURB", self.member)

    _MIXIN_PREPARE_HOOKS = (_algo_member_deco_setup,)


@algo_component_deco_mixin_autodoc
class OOPSMembersTermsDetectDecoMixin(AlgoComponentDecoMixin):
    """Tries to detect a members/terms list using the sequence's inputs

    This mixin class is intended to be used with AlgoComponent classes. It will
    automatically add footprints' attributes related to this feature, crawl into
    the sequence's input after the ``prepare`` step and, depending on the result
    of the members/terms detection add ``members`` and ``effterms`` entries into
    the configuration file substitutions dictionary ``_generic_config_subs``.

    :note: Effective terms are considered (i.e term - (current_date - resource_date))
    """

    _membersdetect_roles = tuple(
        p + r
        for p in ("", "Ensemble")
        for r in (
            "ModelState",
            "Guess",
            "InitialCondition",
            "Background",
            "SurfaceModelState",
            "SurfaceGuess",
            "SurfaceInitialCondition",
            "SurfaceBackground",
        )
    )

    _MIXIN_EXTRA_FOOTPRINTS = (
        footprints.Footprint(
            info="Abstract mbdetect footprint",
            attr=dict(
                ens_minsize=dict(
                    info="For a multi-member algocomponent, the minimum of the ensemble.",
                    optional=True,
                    type=int,
                ),
                ens_failure_conf_objects=dict(
                    info="For a multi-member algocomponent, alternative config file when the ensemble is too small.",
                    optional=True,
                ),
                strict_mbdetect=dict(
                    info="Performs a strict members/terms detection",
                    type=bool,
                    optional=True,
                    default=True,
                    doc_zorder=-60,
                ),
            ),
        ),
    )

    @staticmethod
    def _stateless_members_detect(
        smap, basedate, section_check_cb, ensminsize=None, utest=False
    ):
        """
        This method does not really need to be static but this way it allows for
        unit-testing (see ``tests.tests_algo.test_oopspara.py``).
        """

        # Look for members
        # The ensemble is possibly lagged... be careful
        allmembers = defaultdict(
            functools.partial(defaultdict, functools.partial(defaultdict, set))
        )
        members = set()
        r_members = []
        for arole, srole in smap.items():
            # Gather data
            for s in srole:
                minfo = OOPSMemberInfos(
                    getattr(s.rh.provider, "member", None),
                    getattr(s.rh.resource, "date", None),
                )
                allmembers[arole][minfo][
                    getattr(s.rh.resource, "term", None)
                ].add(s)
            # Sanity checks and filtering
            role_members_info = set(allmembers[arole].keys())
            if None in {a_member.member for a_member in role_members_info}:
                # Ignore sections when some sections have no members defined
                if len(role_members_info) > 1:
                    logger.warning(
                        "Role: %s. Only some sections have a member number.",
                        arole,
                    )
                role_members_info = set()
            if len(role_members_info) > 1:
                if not members:
                    members = role_members_info
                else:
                    # Consistency check on members numbering
                    if members != role_members_info:
                        raise AlgoComponentError(
                            "Inconsistent members numbering"
                        )
            else:
                # If there is only one member, ignore it: it's not really an ensemble!
                del allmembers[arole]

        lagged = False
        if members:
            # Is it a lagged ensemble ?
            members_by_date = defaultdict(set)
            for m in members:
                members_by_date[m.date].add(m.member)
            lagged = len(members_by_date.keys()) > 1
            # Be verbose...
            if lagged:
                for a_date, a_mset in members_by_date.items():
                    logger.info(
                        "Members detected from date=%s: %s",
                        a_date,
                        ",".join(sorted(str(m) for m in a_mset)),
                    )
            else:
                logger.info(
                    "Members detected: %s",
                    ",".join(sorted(str(m[0]) for m in members)),
                )
            logger.info("Total number of detected members: %d", len(members))
            r_members = sorted(allmembers.keys())
            logger.info("Members roles: %s", ",".join(r_members))

        # Look for effective terms
        alleffterms = dict()
        for arole, srole in allmembers.items():
            first_effterms = None
            for minfo, mterms in srole.items():
                effterms = set()
                for term in mterms.keys():
                    effterms.add(
                        term - (basedate - minfo.date)
                        if term is not None and minfo.date is not None
                        else None
                    )
                # Intra-role consistency
                if first_effterms is None:
                    first_effterms = effterms
                else:
                    # Consistency check on members numbering
                    if effterms != first_effterms:
                        raise AlgoComponentError(
                            "Inconsistent effective terms between members sets (role={:s})".format(
                                arole
                            )
                        )
            # If there are more than one term, consider it
            if len(first_effterms) > 1:
                # Check that there is no None in the way
                if None in first_effterms:
                    raise AlgoComponentError(
                        "For a given role, all of the resources or none of then should have a term (role={:s})".format(
                            arole
                        )
                    )
            # Remove Nones
            first_effterms = {e for e in first_effterms if e is not None}
            if len(first_effterms):
                alleffterms[arole] = first_effterms

        # Check consistency and be verbose
        r_effterms = []
        l_effterms = []
        if alleffterms:
            # Hard check only when multiple effetive terms are found
            multieffterms = {
                r: ets for r, ets in alleffterms.items() if len(ets) > 1
            }
            if multieffterms:
                if (
                    sum(1 for _ in itertools.groupby(multieffterms.values()))
                    > 1
                ):
                    raise AlgoComponentError(
                        "Inconsistent effective terms between relevant roles"
                    )
                r_effterms = sorted(multieffterms.keys())
                _, l_effterms = multieffterms.popitem()
            else:
                if (
                    sum(1 for _ in itertools.groupby(alleffterms.values()))
                    == 1
                ):
                    r_effterms = sorted(alleffterms.keys())
                    _, l_effterms = alleffterms.popitem()
            l_effterms = sorted(l_effterms)
            logger.info(
                "Effective terms detected: %s",
                ",".join([str(t) for t in effterms]),
            )
            logger.info(
                "Terms roles: %s", ",".join(sorted(alleffterms.keys()))
            )

        # Theoretical ensemble size
        nominal_ens_size = len(members)
        if nominal_ens_size:
            eff_members = set()
            for mb in members:
                # Look for missing resources in the various relevant roles
                broken = list()
                for arole in allmembers.keys():
                    broken.extend(
                        [
                            (s, arole)
                            for t, slist in allmembers[arole][mb].items()
                            for s in slist
                            if not section_check_cb(s)
                        ]
                    )
                for s, arole in broken:
                    if not utest:
                        logger.warning(
                            "Missing items: %s (role: %s).",
                            s.rh.container.localpath(),
                            arole,
                        )
                if broken:
                    logger.warning("Throwing away member: %s", mb)
                else:
                    eff_members.add(mb)
            # Sanity checks depending on ensminsize
            if ensminsize is None and len(eff_members) != nominal_ens_size:
                raise EnsSizeAlgoComponentError(
                    nominal_ens_size, len(eff_members), nominal_ens_size
                )
            elif ensminsize is not None and len(eff_members) < ensminsize:
                raise EnsSizeAlgoComponentError(
                    nominal_ens_size, len(eff_members), ensminsize
                )

            members = eff_members

        l_members = [m.member for m in sorted(members)]
        l_members_d = [m.date for m in sorted(members)]
        l_members_o = [
            None if m.date is None else (basedate - m.date)
            for m in sorted(members)
        ]

        return (
            l_members,
            l_members_d,
            l_members_o,
            l_effterms,
            lagged,
            nominal_ens_size,
            r_members,
            r_effterms,
        )

    def members_detect(self):
        """Detect the members/terms list and update the substitution dictionary."""
        sectionsmap = {
            r: self.context.sequence.filtered_inputs(
                role=r, no_alternates=True
            )
            for r in self._membersdetect_roles
        }
        try:
            (
                self._ens_members_num,
                self._ens_members_date,
                self._ens_members_offset,
                self._ens_effterms,
                self._ens_is_lagged,
                self._ens_nominal_size,
                _,
                _,
            ) = self._stateless_members_detect(
                sectionsmap,
                self.date,
                self.context.sequence.is_somehow_viable,
                self.ens_minsize,
            )
        except EnsSizeAlgoComponentError as e:
            if self.strict_mbdetect and self.ens_failure_conf_objects is None:
                raise
            else:
                logger.warning("Members detection failed: %s", str(e))
                logger.info(
                    "'strict_mbdetect' is False... going on with empty lists."
                )
                self._ens_members_num = []
                self._ens_members_date = []
                self._ens_members_offset = []
                self._ens_is_lagged = False
                self._ens_effterms = []
                self._ens_nominal_size = e.nominal_ens_size
                if self.ens_failure_conf_objects:
                    # Find the new configuration object
                    main_conf = None
                    for sconf, ssub in self._individual_config_subs.items():
                        if (
                            getattr(sconf.rh.resource, "objects", "")
                            == self.ens_failure_conf_objects
                        ):
                            main_conf = sconf
                            main_conf_sub = ssub
                            break
                    if main_conf is None:
                        raise AlgoComponentError(
                            "Alternative configuration file was not found"
                        )
                    # Update the config ordered dictionary
                    del self._individual_config_subs[main_conf]
                    new_individual_config_subs = OrderedDict()
                    new_individual_config_subs[main_conf] = main_conf_sub
                    for sconf, ssub in self._individual_config_subs.items():
                        new_individual_config_subs[sconf] = ssub
                    self._individual_config_subs = new_individual_config_subs
                    logger.info(
                        "Using an alternative configuration file (objects=%s, role=%s)",
                        self.ens_failure_conf_objects,
                        main_conf.role,
                    )

        self._generic_config_subs["ens_members_num"] = self._ens_members_num
        self._generic_config_subs["ens_members_date"] = self._ens_members_date
        self._generic_config_subs["ens_members_offset"] = (
            self._ens_members_offset
        )
        self._generic_config_subs["ens_is_lagged"] = self._ens_is_lagged
        # Legacy:
        self._generic_config_subs["members"] = self._ens_members_num
        # Namelist stuff
        for namrh in self.updatable_namelists:
            namrh.contents.setmacro("ENS_MEMBERS", len(self._ens_members_num))
            if self._ens_members_num:
                namrh.contents.setmacro(
                    "ENS_AUTO_NSTRIN", len(self._ens_members_num)
                )
            else:
                namrh.contents.setmacro(
                    "ENS_AUTO_NSTRIN", self._ens_nominal_size
                )
        self._generic_config_subs["ens_effterms"] = self._ens_effterms
        # Legacy:
        self._generic_config_subs["effterms"] = self._ens_effterms

    def _membersd_setup(self, rh, opts):  # @UnusedVariable
        """Set up the members/terms detection."""
        self.members_detect()

    _MIXIN_PREPARE_HOOKS = (_membersd_setup,)


@algo_component_deco_mixin_autodoc
class OOPSMembersTermsDecoMixin(AlgoComponentDecoMixin):
    """Adds members/terms footprints' attributes and use them in configuration files.

    This mixin class is intended to be used with AlgoComponent classes. It will
    automatically add footprints' attributes ``members`` and ``terms`` and add
    the corresponding ``members`` and ``effterms`` entries into
    the configuration file substitutions dictionary ``_generic_config_subs``.
    """

    _MIXIN_EXTRA_FOOTPRINTS = (oops_members_terms_lists,)

    def _membersterms_deco_setup(self, rh, opts):  # @UnusedVariable
        """Setup the configuration file."""
        actualmembers = [
            m if isinstance(m, int) else int(m) for m in self.members
        ]
        actualterms = [
            t if isinstance(t, Time) else Time(t) for t in self.terms
        ]
        self._generic_config_subs["members"] = actualmembers
        self._generic_config_subs["effterms"] = actualterms

    _MIXIN_PREPARE_HOOKS = (_membersterms_deco_setup,)


@algo_component_deco_mixin_autodoc
class OOPSTimestepDecoMixin(AlgoComponentDecoMixin):
    """Add a timsestep attribute and handle substitutions."""

    _MIXIN_EXTRA_FOOTPRINTS = (
        footprints.Footprint(
            info="Abstract timestep footprint",
            attr=dict(
                timestep=dict(
                    info="A possible model timestep (in seconds).",
                    optional=True,
                    type=float,
                ),
            ),
        ),
    )

    def _timestep_deco_setup(self, rh, opts):  # @UnusedVariable
        """Set up the timestep in config and namelists."""
        if self.timestep is not None:
            self._generic_config_subs["timestep"] = Period(
                seconds=self.timestep
            )
            logger.info("Set macro TIMESTEP=%f in namelists.", self.timestep)
            for namrh in self.updatable_namelists:
                namrh.contents.setmacro("TIMESTEP", self.timestep)

    _MIXIN_PREPARE_HOOKS = (_timestep_deco_setup,)


@algo_component_deco_mixin_autodoc
class OOPSIncrementalDecoMixin(AlgoComponentDecoMixin):
    """Add incremental attributes and handle substitutions."""

    _MIXIN_EXTRA_FOOTPRINTS = (
        footprints.Footprint(
            info="Abstract incremental_* footprint",
            attr=dict(
                incremental_tsteps=dict(
                    info="Timestep for each of the outer loop iteration (in seconds).",
                    optional=True,
                    type=footprints.FPList,
                    default=footprints.FPList(),
                ),
                incremental_niters=dict(
                    info="Inner loop size for each of the outer loop iteration.",
                    optional=True,
                    type=footprints.FPList,
                    default=footprints.FPList(),
                ),
                incremental_geos=dict(
                    info="Geometry for each of the outer loop iteration.",
                    optional=True,
                    type=footprints.FPList,
                    default=footprints.FPList(),
                ),
            ),
        ),
    )

    def _incremental_deco_setup(self, rh, opts):  # @UnusedVariable
        """Set up the incremental DA settings in config and namelists."""
        if self.incremental_tsteps or self.incremental_niters:
            sizes = {
                len(t)
                for t in [
                    self.incremental_tsteps,
                    self.incremental_niters,
                    self.incremental_geos,
                ]
                if t
            }
            if len(sizes) != 1:
                raise ValueError(
                    "Inconsistent sizes between incr_tsteps and incr_niters"
                )
            actual_tsteps = [float(t) for t in (self.incremental_tsteps or ())]
            actual_tsteps_p = [Period(seconds=t) for t in actual_tsteps]
            actual_niters = [int(t) for t in (self.incremental_niters or ())]
            actual_geos = [
                g
                if isinstance(g, geometries.Geometry)
                else geometries.get(tag=g)
                for g in (self.incremental_geos or ())
            ]
            if actual_tsteps:
                self._generic_config_subs["incremental_tsteps"] = (
                    actual_tsteps_p
                )
                for upd_i, tstep in enumerate(actual_tsteps, start=1):
                    logger.info(
                        "Set macro UPD%d_TIMESTEP=%f macro in namelists.",
                        upd_i,
                        tstep,
                    )
                    for namrh in self.updatable_namelists:
                        namrh.contents.setmacro(
                            "UPD{:d}_TIMESTEP".format(upd_i), tstep
                        )
            if actual_niters:
                self._generic_config_subs["incremental_niters"] = actual_niters
                for upd_i, niter in enumerate(actual_niters, start=1):
                    logger.info(
                        "Set macro UPD%d_NITER=%d macro in namelists.",
                        upd_i,
                        niter,
                    )
                    for namrh in self.updatable_namelists:
                        namrh.contents.setmacro(
                            "UPD{:d}_NITER".format(upd_i), niter
                        )
            if actual_geos:
                self._generic_config_subs["incremental_geos"] = actual_geos

    _MIXIN_PREPARE_HOOKS = (_incremental_deco_setup,)


class OOPSParallel(
    Parallel,
    drhook.DrHookDecoMixin,
    grib.EcGribDecoMixin,
    satrad.SatRadDecoMixin,
):
    """Abstract AlgoComponent for any OOPS run."""

    _abstract = True
    _footprint = dict(
        info="Any OOPS Run (abstract).",
        attr=dict(
            kind=dict(
                values=["oorun"],
            ),
            date=dict(
                info="The current run date.",
                access="rwx",
                type=Date,
                doc_zorder=-50,
            ),
            config_subs=dict(
                info="Substitutions to be performed in the config file (before run)",
                optional=True,
                type=footprints.FPDict,
                default=footprints.FPDict(),
                doc_zorder=-60,
            ),
            binarysingle=dict(
                default="basicnwp",
            ),
        ),
    )

    def __init__(self, *kargs, **kwargs):
        """Declare some hidden attributes for a later use."""
        super().__init__(*kargs, **kwargs)
        self._oops_cycle = None
        self._generic_config_subs = dict()
        self._individual_config_subs = OrderedDict()
        self._last_l_subs = dict()

    @property
    def oops_cycle(self):
        """The binary's cycle number."""
        return self._oops_cycle

    def valid_executable(self, rh):
        """Be sure that the specified executable has a cycle attribute."""
        valid = super().valid_executable(rh)
        if hasattr(rh.resource, "cycle"):
            self._oops_cycle = rh.resource.cycle
            return valid
        else:
            logger.error("The binary < %s > has no cycle attribute", repr(rh))
            return False

    def _mpitool_attributes(self, opts):
        conf_dict = super()._mpitool_attributes(opts)
        conf_dict.update({"mplbased": True})
        return conf_dict

    def prepare(self, rh, opts):
        """Preliminary setups."""
        super().prepare(rh, opts)
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
        self.do_namelist_rendering()
        super().spawn_hook()

    def spawn_command_options(self):
        """Prepare options for the binary's command line."""
        mconfig = list(self._individual_config_subs.keys())[0]
        configfile = mconfig.rh.container.localpath()
        options = {"configfile": configfile}
        return options

    @cached_property
    def updatable_namelists(self):
        return [
            s.rh
            for s in self.context.sequence.effective_inputs(role="Namelist")
        ]

    def set_config_rendering(self):
        """
        Look into effective inputs for configuration files and register them for
        a later rendering using bronx' templating system.
        """
        mconfig = self.context.sequence.effective_inputs(role="MainConfig")
        gconfig = self.context.sequence.effective_inputs(role="Config")
        if len(mconfig) > 1:
            raise AlgoComponentError(
                "Only one Main Config section may be provided."
            )
        if len(mconfig) == 0 and len(gconfig) != 1:
            raise AlgoComponentError(
                "Please provide a Main Config section or a unique Config section."
            )
        if len(mconfig) == 1:
            gconfig.insert(0, mconfig[0])
        self._individual_config_subs = {sconf: dict() for sconf in gconfig}

    def do_config_rendering(self):
        """Render registered configuration files using the bronx' templating system."""
        l_first = True
        for sconf, sdict in self._individual_config_subs.items():
            self.system.subtitle(
                "Configuration file rendering for: {:s}".format(
                    sconf.rh.container.localpath()
                )
            )
            l_subs = dict(now=self.date, date=self.date)
            l_subs.update(self._generic_config_subs)
            l_subs.update(sdict)
            l_subs.update(self.config_subs)
            if l_subs != self._last_l_subs.get(sconf, dict()):
                if not hasattr(sconf.rh.contents, "bronx_tpl_render"):
                    logger.error(
                        'The < %s > content object has no "bronx_tpl_render" method. Skipping it.',
                        repr(sconf.rh.contents),
                    )
                    continue
                try:
                    sconf.rh.contents.bronx_tpl_render(**l_subs)
                except Exception:
                    logger.error(
                        "The config file rendering failed. The substitution dict was: \n%s",
                        lightdump(l_subs),
                    )
                    raise
                self._last_l_subs[sconf] = l_subs
                if l_first:
                    print(fulldump(sconf.rh.contents.data))
                sconf.rh.save()
            else:
                logger.info(
                    "It's not necessary to update the file (no changes)."
                )
            l_first = False

    def do_namelist_rendering(self):
        todo = [
            r
            for r in self.updatable_namelists
            if r.contents.dumps_needs_update
        ]
        self.system.subtitle("Updating namelists")
        if todo:
            for namrh in todo:
                logger.info("Rewriting %s.", namrh.container.localpath())
                namrh.save()
        else:
            logger.info("None of the namelists need to be rewritten.")

    def boost_defaults(self):
        """Set defaults for BOOST environment variables.

        Do not overwrite pre-initialised ones. The default list of variables
        depends on the code's cycle number.
        """
        defaults = {
            IfsCycle("cy1"): {
                "BOOST_TEST_CATCH_SYSTEM_ERRORS": "no",
                "BOOST_TEST_DETECT_FP_EXCEPTIONS": "no",
                "BOOST_TEST_LOG_FORMAT": "XML",
                "BOOST_TEST_LOG_LEVEL": "message",
                "BOOST_TEST_OUTPUT_FORMAT": "XML",
                "BOOST_TEST_REPORT_FORMAT": "XML",
                "BOOST_TEST_RESULT_CODE": "yes",
            }
        }
        cydefaults = None
        for k, defdict in sorted(defaults.items(), reverse=True):
            if k < self.oops_cycle:
                cydefaults = defdict
                break
        self.algoassert(
            cydefaults is not None,
            "BOOST defaults not found for cycle: {!s}".format(self.oops_cycle),
        )
        logger.info("Setting up BOOST defaults:%s", lightdump(cydefaults))
        self.env.default(**cydefaults)

    def eckit_defaults(self):
        """Set defaults for eckit environment variables.

        Do not overwrite pre-initialised ones. The default list of variables
        depends on the code's cycle number.
        """
        defaults = {
            IfsCycle("cy1"): {
                "ECKIT_MPI_INIT_THREAD": (
                    "MPI_THREAD_MULTIPLE"
                    if int(self.env.get("OMP_NUM_THREADS", "1")) > 1
                    else "MPI_THREAD_SINGLE"
                ),
            }
        }
        cydefaults = None
        for k, defdict in sorted(defaults.items(), reverse=True):
            if k < self.oops_cycle:
                cydefaults = defdict
                break
        self.algoassert(
            cydefaults is not None,
            "eckit defaults not found for cycle: {!s}".format(self.oops_cycle),
        )
        logger.info("Setting up eckit defaults:%s", lightdump(cydefaults))
        self.env.default(**cydefaults)


class OOPSODB(OOPSParallel, odb.OdbComponentDecoMixin):
    """Abstract AlgoComponent for any OOPS run requiring ODB databases."""

    _abstract = True
    _footprint = dict(
        info="OOPS ObsOperator Test run.",
        attr=dict(
            kind=dict(
                values=["oorunodb"],
            ),
            binarysingle=dict(
                default="basicnwpobsort",
            ),
        ),
    )

    #: If ``True``, an empty CCMA database will be created before the run and
    #: necessary environment variables will be added in order for the executable
    #: to populate this database at the end of the run.
    _OOPSODB_CCMA_DIRECT = False

    def prepare(self, rh, opts):
        """Setup ODB stuff."""
        super().prepare(rh, opts)
        sh = self.system

        # Looking for input observations
        allodb = self.lookupodb()
        allcma = [
            x for x in allodb if x.rh.resource.layout.lower() == self.virtualdb
        ]
        if self.virtualdb.lower() == "ccma":
            self.algoassert(
                len(allcma) == 1, "A unique CCMA database is to be provided."
            )
            self.algoassert(
                not self._OOPSODB_CCMA_DIRECT,
                "_OOPSODB_CCMA_DIRECT needs to be False if virtualdb=ccma.",
            )
            cma = allcma[0]
            cma_path = sh.path.abspath(cma.rh.container.localpath())
        else:
            cma_path = self.odb_merge_if_needed(allcma)
            if self._OOPSODB_CCMA_DIRECT:
                ccma_path = self.odb_create_db(layout="CCMA")
                self.odb.fix_db_path("CCMA", ccma_path)

        # Set ODB environment
        self.odb.fix_db_path(self.virtualdb, cma_path)

        if self._OOPSODB_CCMA_DIRECT:
            self.odb.ioassign_gather(cma_path, ccma_path)
        else:
            self.odb.ioassign_gather(cma_path)

        if self.virtualdb.lower() != "ccma":
            self.odb.create_poolmask(self.virtualdb, cma_path)
            self.odb.shuffle_setup(
                self.slots,
                mergedirect=True,
                ccmadirect=self._OOPSODB_CCMA_DIRECT,
            )

        # Fix the input databases intent
        self.odb_rw_or_overwrite_method(*allcma)

        # Look for extras ODB raw
        self.odb_handle_raw_dbs()

        # Allow assimilation window / timeslots configuration
        self._generic_config_subs["window_length"] = self.slots.window
        self._generic_config_subs["window_lmargin"] = Period(-self.slots.start)
        self._generic_config_subs["window_rmargin"] = (
            self.slots.window + self.slots.start
        )
        self._generic_config_subs["timeslot_length"] = self.slots.chunk
        self._generic_config_subs["timeslot_centered"] = self.slots.center
        self._generic_config_subs["timeslot_centers"] = (
            self.slots.as_centers_fromstart()
        )


class OOPSAnalysis(
    OOPSODB,
    OOPSTimestepDecoMixin,
    OOPSIncrementalDecoMixin,
    OOPSMemberDecoMixin,
    OOPSMembersTermsDetectDecoMixin,
):
    """Any kind of OOPS analysis (screening/thining step excluded)."""

    _footprint = dict(
        info="OOPS minimisation.",
        attr=dict(
            kind=dict(
                values=["ooanalysis", "oominim"],
                remap=dict(autoremap="first"),
            ),
            virtualdb=dict(
                default="ccma",
            ),
            withscreening=dict(
                values=[
                    False,
                ],
                type=bool,
                optional=True,
                default=False,
            ),
        ),
    )


class OOPSAnalysisWithScreening(OOPSAnalysis):
    """Any kind of OOPS analysis with screening/thining step."""

    _OOPSODB_CCMA_DIRECT = True

    _footprint = dict(
        attr=dict(
            virtualdb=dict(
                default="ecma",
            ),
            withscreening=dict(
                values=[
                    True,
                ],
                optional=False,
            ),
        )
    )
