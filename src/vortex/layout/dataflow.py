"""
This modules defines the low level physical layout for data handling.
"""

from collections import namedtuple, defaultdict
import collections.abc
import json
import pprint
import re
import traceback
import weakref

from bronx.fancies import loggers
from bronx.patterns import observer
from bronx.syntax import mktuple
from bronx.syntax.pretty import EncodedPrettyPrinter
import footprints

from vortex.util.roles import setrole

#: No automatic export.
__all__ = []

logger = loggers.getLogger(__name__)

_RHANDLERS_OBSBOARD = "Resources-Handlers"


class SectionFatalError(Exception):
    """Exception when fatal mode is activated."""

    pass


#: Definition of a named tuple INTENT
IntentTuple = namedtuple("IntentTuple", ["IN", "OUT", "INOUT"])

#: Predefined INTENT values IN, OUT and INOUT.
intent = IntentTuple(IN="in", OUT="out", INOUT="inout")

#: Definition of a named tuple IXO sequence
IXOTuple = namedtuple("IXOTuple", ["INPUT", "OUTPUT", "EXEC"])

#: Predefined IXO sequence values INPUT, OUTPUT and EXEC.
ixo = IXOTuple(INPUT=1, OUTPUT=2, EXEC=3)

#: Arguments specific to a section (to be striped away from a resource handler description)
section_args = ["role", "alternate", "intent", "fatal", "coherentgroup"]


def stripargs_section(**kw):
    """
    Utility function to separate the named arguments in two parts: the one that
    describe section options and any other ones. Return a tuple with
    ( section_options, other_options ).
    """
    opts = dict()
    for opt in [x for x in section_args if x in kw]:
        opts[opt] = kw.pop(opt)
    return (opts, kw)


class _ReplaceSectionArgs:
    """
    Trigger the footprint's replacement mechanism on some of the section arguments.
    """

    _REPL_TODO = ("coherentgroup",)

    def __init__(self):
        self._fptmp = footprints.Footprint(
            attr={k: dict(optional=True) for k in self._REPL_TODO}
        )

    def __call__(self, rh, opts):
        if any(
            {
                footprints.replattr.search(opts[k])
                for k in self._REPL_TODO
                if k in opts
            }
        ):
            # The "description"
            desc = opts.copy()
            if rh is not None:
                desc.update(rh.options)
                desc["container"] = rh.container
                desc["provider"] = rh.provider
                desc["resource"] = rh.resource
            # Resolve
            resolved, _, _ = self._fptmp.resolve(desc, fatal=False, fast=False)
            # ok, let's use the resolved values
            for k in self._REPL_TODO:
                if resolved[k] is not None:
                    opts[k] = resolved[k]


_default_replace_section_args = _ReplaceSectionArgs()


class Section:
    """Low level unit to handle a resource."""

    def __init__(self, **kw):
        logger.debug("Section initialisation %s", self)
        self.kind = ixo.INPUT
        self.intent = intent.INOUT
        self.fatal = True
        # Fetch the ResourceHandler
        self._rh = kw.pop("rh", None)
        # We realy need a ResourceHandler...
        if self.rh is None:
            raise AttributeError("A proper rh attribute have to be provided")
        # Call the footprint's replacement mechanism if needed
        _default_replace_section_args(self._rh, kw)
        # Process the remaining options
        self._role = setrole(kw.pop("role", "anonymous"))
        self._alternate = setrole(kw.pop("alternate", None))
        self._coherentgroups = kw.pop("coherentgroup", None)
        self._coherentgroups = set(
            self._coherentgroups.split(",") if self._coherentgroups else []
        )
        self._coherentgroups_opened = {g: True for g in self._coherentgroups}
        self.stages = [
            kw.pop("stage", "load"),
        ]
        self.__dict__.update(kw)
        # If alternate is specified role have to be removed
        if self._alternate:
            self._role = None

    @property
    def role(self):
        return self._role

    @property
    def alternate(self):
        return self._alternate

    @property
    def coherentgroups(self):
        """The list of belonging coherent groups."""
        return self._coherentgroups

    @property
    def any_coherentgroup_opened(self):
        """Is, at least, one belonging coherent group opened ?"""
        return not self.coherentgroups or any(
            self._coherentgroups_opened.values()
        )

    def coherent_group_close(self, group):
        """Close the coherent group (get and put will fail from now and on)."""
        if group in self._coherentgroups_opened:
            self._coherentgroups_opened[group] = False
        # Another group's resource failed, re-checking and possibly deleting myself !
        if (
            self.stage in ("expected", "get")
            and not self.any_coherentgroup_opened
        ):
            logger.info(
                "Clearing %s because of the coherent group failure.",
                str(self.rh.container),
            )
            self.rh.clear()

    def check_groupstatus(self, info):
        """Given the updstage's info dict, check that a coherent group still holds"""
        return info.get("stage") != "void"

    @property
    def rh(self):
        return self._rh

    @property
    def stage(self):
        """The last stage of the current section."""
        return self.stages[-1]

    def _updignore(self, info):
        """Fake function for undefined information driven updates."""
        logger.warning("Unable to update %s with info %s", self, info)

    def _updstage_void(self, info):
        """Upgrade current section to 'checked' level."""
        if info.get("stage") == "void" and self.kind in (ixo.INPUT, ixo.EXEC):
            self.stages.append("void")

    def _updstage_checked(self, info):
        """Upgrade current section to 'checked' level."""
        if info.get("stage") == "checked" and self.kind in (
            ixo.INPUT,
            ixo.EXEC,
        ):
            self.stages.append("checked")

    def _updstage_get(self, info):
        """Upgrade current section to 'get' level."""
        if info.get("stage") == "get" and self.kind in (ixo.INPUT, ixo.EXEC):
            self.stages.append("get")

    def _updstage_expected(self, info):
        """Upgrade current section to 'expected' level."""
        if info.get("stage") == "expected" and self.kind in (
            ixo.INPUT,
            ixo.EXEC,
        ):
            self.stages.append("expected")

    def _updstage_put(self, info):
        """Upgrade current section to 'put' level."""
        if info.get("stage") == "put" and self.kind == ixo.OUTPUT:
            self.stages.append("put")

    def _updstage_ghost(self, info):
        """Upgrade current section to 'ghost' level."""
        if info.get("stage") == "ghost" and self.kind == ixo.OUTPUT:
            self.stages.append("ghost")

    def updstage(self, info):
        """Upgrade current section level according to information given in dict ``info``."""
        updmethod = getattr(
            self, "_updstage_" + info.get("stage"), self._updignore
        )
        updmethod(info)

    def _stronglocate(self, **kw):
        """A locate call that can not fail..."""
        try:
            loc = self.rh.locate(**kw)
        except Exception:
            loc = "???"
        return loc

    def _fatal_wrap(self, sectiontype, callback, **kw):
        """Launch **callback** and process the returncode/exceptions according to **fatal**."""
        action = {"input": "get", "output": "put"}[sectiontype]
        rc = False
        try:
            rc = callback(**kw)
        except Exception as e:
            logger.error(
                "Something wrong (%s section): %s. %s",
                sectiontype,
                str(e),
                traceback.format_exc(),
            )
            logger.error("Resource %s", self._stronglocate())
        if not rc and self.fatal:
            logger.critical(
                "Fatal error with action %s on %s",
                action,
                self._stronglocate(),
            )
            raise SectionFatalError(
                "Could not {:s} resource {!s}".format(action, rc)
            )
        return rc

    def _just_fail(self, sectiontype, **kw):  # @UnusedVariable
        """Check if a resource exists but fails anyway."""
        action = {"input": "get", "output": "put"}[sectiontype]
        rc = False
        if self.fatal:
            logger.critical(
                "Fatal error with action %s on %s",
                action,
                self._stronglocate(),
            )
            raise SectionFatalError(
                "Could not {:s} resource {!s}".format(action, rc)
            )
        return rc

    def get(self, **kw):
        """Shortcut to resource handler :meth:`~vortex.data.handlers.get`."""
        if self.kind == ixo.INPUT or self.kind == ixo.EXEC:
            if self.any_coherentgroup_opened:
                kw["intent"] = self.intent
                if self.alternate:
                    kw["alternate"] = self.alternate
                rc = self._fatal_wrap("input", self.rh.get, **kw)
            else:
                logger.info("The coherent group is closed... doing nothing.")
                rc = self._just_fail("input")
        else:
            rc = False
            logger.error("Try to get from an output section")
        return rc

    def finaliseget(self):
        """Shortcut to resource handler :meth:`~vortex.data.handlers.finaliseget`."""
        if self.kind == ixo.INPUT or self.kind == ixo.EXEC:
            if self.any_coherentgroup_opened:
                rc = self._fatal_wrap("input", self.rh.finaliseget)
            else:
                logger.info("The coherent group is closed... doing nothing.")
                rc = self._just_fail("input")
        else:
            rc = False
            logger.error("Try to get from an output section")
        return rc

    def earlyget(self, **kw):
        """Shortcut to resource handler :meth:`~vortex.data.handlers.earlyget`."""
        rc = False
        if self.kind == ixo.INPUT or self.kind == ixo.EXEC:
            if self.any_coherentgroup_opened:
                kw["intent"] = self.intent
                if self.alternate:
                    kw["alternate"] = self.alternate
                rc = self.rh.earlyget(**kw)
            else:
                rc = None
        return rc

    def put(self, **kw):
        """Shortcut to resource handler :meth:`~vortex.data.handlers.put`."""
        if self.kind == ixo.OUTPUT:
            if self.any_coherentgroup_opened:
                kw["intent"] = self.intent
                rc = self._fatal_wrap("output", self.rh.put, **kw)
            else:
                logger.info("The coherent group is closed... failing !.")
                rc = False
                if self.fatal:
                    logger.critical(
                        "Fatal error with action put on %s",
                        self._stronglocate(),
                    )
                    raise SectionFatalError(
                        "Could not get resource {!s}".format(rc)
                    )
        else:
            rc = False
            logger.error("Try to put from an input section.")
        return rc

    def show(self, **kw):
        """Nice dump of the section attributes and contents."""
        for k, v in sorted(vars(self).items()):
            if k != "rh":
                print(" ", k.ljust(16), ":", v)
        self.rh.quickview(indent=1)

    def as_dict(self):
        """Export the section in a dictionary"""
        outdict = dict()
        for k, v in sorted(vars(self).items()):
            if k == "_rh":
                outdict["rh"] = v.as_dict()
            elif k == "_coherentgroups":
                outdict["coherentgroup"] = ",".join(sorted(v))
            elif k == "_coherentgroups_opened":
                continue
            elif k.startswith("_"):
                outdict[k[1:]] = v
            else:
                outdict[k] = v
        # Add the latest stage
        outdict["stage"] = self.stage
        return outdict


class Sequence(observer.Observer):
    """
    Logical sequence of sections such as inputs or outputs sections.
    Instances are iterable and callable.
    """

    def __init__(self, *args, **kw):
        logger.debug("Sequence initialisation %s", self)
        self.sections = list()
        # This hash table will be used to speedup the searches...
        # If one uses the remove method, a WeakSet is not usefull. However,
        # nothing will prevent the user from trashing the sections list...
        # consequently a WealSet is safer !
        self._sections_hash = defaultdict(weakref.WeakSet)
        self._coherentgroups = defaultdict(weakref.WeakSet)
        self._coherentgroups_openings = defaultdict(lambda: True)
        observer.get(tag=_RHANDLERS_OBSBOARD).register(self)

    def __del__(self):
        observer.get(tag=_RHANDLERS_OBSBOARD).unregister(self)

    def __iter__(self):
        yield from self.sections

    def __call__(self):
        return self.sections[:]

    def free_resources(self):
        """Free contents and io descriptors on every sections."""
        for section in self.sections:
            section.rh.reset_contents()
            if section.rh.container is not None:
                section.rh.container.close()

    def clear(self):
        """Clear the internal list of sections."""
        self.sections = list()
        self._sections_hash.clear()

    def add(self, candidate):
        """
        Push the ``candidate`` to the internal list of sections
        as long as it is a :class:`Section` object.
        """
        if isinstance(candidate, Section):
            self.sections.append(candidate)
            self._sections_hash[candidate.rh.simplified_hashkey].add(candidate)
            for cgroup in candidate.coherentgroups:
                self._coherentgroups[cgroup].add(candidate)
                if not self._coherentgroups_openings[cgroup]:
                    candidate.coherent_group_close(cgroup)
        else:
            logger.warning(
                "Try to add a non-section object %s in sequence %s",
                candidate,
                self,
            )

    def remove(self, candidate):
        """
        Remove the ``candidate`` from the internal list of sections
        as long as it is a :class:`Section` object.
        """
        if isinstance(candidate, Section):
            self.sections.remove(candidate)
            self._sections_hash[candidate.rh.simplified_hashkey].discard(
                candidate
            )
            for cgroup in candidate.coherentgroups:
                self._coherentgroups[cgroup].discard(candidate)
        else:
            logger.warning(
                "Try to remove a non-section object %s in sequence %s",
                candidate,
                self,
            )

    def section(self, **kw):
        """Section factory wrapping a given ``rh`` (Resource Handler)."""
        rhset = kw.get("rh", list())
        if not isinstance(rhset, list):
            rhset = [
                rhset,
            ]
        ralter = kw.get("alternate", kw.get("role", "anonymous"))
        newsections = list()
        for rh in rhset:
            kw["rh"] = rh
            this_section = Section(**kw)
            self.add(this_section)
            newsections.append(this_section)
            kw["alternate"] = ralter
            if "role" in kw:
                del kw["role"]
        return newsections

    def input(self, **kw):
        """Create a section with default kind equal to ``ixo.INPUT``."""
        if "kind" in kw:
            del kw["kind"]
        kw.setdefault("intent", intent.IN)
        return self.section(kind=ixo.INPUT, **kw)

    def output(self, **kw):
        """Create a section with default kind equal to ``ixo.OUTPUT`` and intent equal to ``intent.OUT``."""
        if "kind" in kw:
            del kw["kind"]
        kw.setdefault("intent", intent.OUT)
        return self.section(kind=ixo.OUTPUT, **kw)

    def executable(self, **kw):
        """Create a section with default kind equal to to ``ixo.EXEC``."""
        if "kind" in kw:
            del kw["kind"]
        kw.setdefault("intent", intent.IN)
        return self.section(kind=ixo.EXEC, **kw)

    @staticmethod
    def _fuzzy_match(stuff, allowed):
        """Check if ``stuff`` is in ``allowed``. ``allowed`` may contain regex."""
        if isinstance(allowed, str) or not isinstance(
            allowed, collections.abc.Iterable
        ):
            allowed = [
                allowed,
            ]
        for pattern in allowed:
            if (isinstance(pattern, re.Pattern) and pattern.search(stuff)) or (
                pattern == stuff
            ):
                return True
        return False

    def _section_list_filter(self, sections, **kw):
        if not kw:
            return list(sections)
        inrole = list()
        inkind = list()
        with_alternates = not kw.get("no_alternates", False)
        if "role" in kw and kw["role"] is not None:
            selectrole = mktuple(kw["role"])
            inrole = [
                x
                for x in sections
                if (
                    (
                        x.role is not None
                        and self._fuzzy_match(x.role, selectrole)
                    )
                    or (
                        with_alternates
                        and x.alternate is not None
                        and self._fuzzy_match(x.alternate, selectrole)
                    )
                )
            ]
        if not inrole and "kind" in kw:
            selectkind = mktuple(kw["kind"])
            inkind = [
                x
                for x in sections
                if self._fuzzy_match(x.rh.resource.realkind, selectkind)
            ]
        return inrole or inkind

    def inputs(self):
        """Return a list of current sequence sections with ``ixo.INPUT`` or ``ixo.EXEC`` kind."""
        for s in self.sections:
            if s.kind == ixo.INPUT or s.kind == ixo.EXEC:
                yield s

    def rinputs(self):
        """The reversed list of input sections."""
        for s in reversed(self.sections):
            if s.kind == ixo.INPUT or s.kind == ixo.EXEC:
                yield s

    def inputs_report(self):
        """Return a SequenceInputsReport object built using the current sequence."""
        return SequenceInputsReport(self.inputs())

    def effective_inputs(self, **kw):
        """
        Similar to :meth:`filtered_inputs` but only walk through the inputs of
        that reached the 'get' or 'expected' stage.
        """
        return [
            x
            for x in self._section_list_filter(list(self.inputs()), **kw)
            if (x.stage == "get" or x.stage == "expected")
            and x.rh.container.exists()
        ]

    def filtered_inputs(self, **kw):
        """Walk through the inputs of the current sequence.

        If a ``role`` or ``kind`` (or both) is provided as named argument,
        it operates as a filter on the inputs list. If both keys are available
        the ``role`` applies first, and then the ``kind`` in case of empty match.

        The ``role`` or ``kind`` named arguments are lists that may contain
        strings and/or compiled regular expressions. Regular expressions are c
        hacked against the input's attributes using the 'search' function
        (i.e.  ^ should be explicitly added if one wants to match the beginning
        of the string).
        """
        return self._section_list_filter(list(self.inputs()), **kw)

    def is_somehow_viable(self, section):
        """Tells wether *section* is ok or has a viable alternate."""
        if section.role is None:
            raise ValueError(
                "An alternate section was given ; this is incorrect..."
            )
        if (
            section.stage in ("get", "expected")
            and section.rh.container.exists()
        ):
            return section
        else:
            for isec in self.inputs():
                if (
                    isec.alternate == section.role
                    and isec.stage in ("get", "expected")
                    and isec.rh.container.localpath()
                    == section.rh.container.localpath()
                    and isec.rh.container.exists()
                ):
                    return isec
        return None

    def executables(self):
        """Return a list of current sequence sections with ``ixo.EXEC`` kind."""
        return [x for x in self.sections if x.kind == ixo.EXEC]

    def outputs(self):
        """Return a list of current sequence sections with ``ixo.OUTPUT`` kind."""
        for s in self.sections:
            if s.kind == ixo.OUTPUT:
                yield s

    def effective_outputs(self, **kw):
        """
        Walk through the outputs of the current sequence whatever the stage value is.
        If a ``role`` or ``kind`` (or both) is provided as named argument,
        it operates as a filter on the inputs list. If both keys are available
        the ``role`` applies first, and then the ``kind`` in case of empty match.
        """
        return self._section_list_filter(list(self.outputs()), **kw)

    def coherentgroup_iter(self, cgroup):
        """Iterate over sections belonging to a given coherentgroup."""
        c_sections = self._coherentgroups[cgroup]
        yield from c_sections

    def section_updstage(self, a_section, info):
        """
        Update the section's stage but also check other sections from the same
        coherent group.
        """
        a_section.updstage(info)

        def _s_group_check(s):
            return s.check_groupstatus(info)

        for cgroup in a_section.coherentgroups:
            if self._coherentgroups_openings[cgroup]:
                if not all(
                    map(_s_group_check, self.coherentgroup_iter(cgroup))
                ):
                    for c_section in self.coherentgroup_iter(cgroup):
                        c_section.coherent_group_close(cgroup)
                    self._coherentgroups_openings[cgroup] = False

    def updobsitem(self, item, info):
        """
        Resources-Handlers observing facility.
        Track hashkey alteration for the resource handler ``item``.
        """
        if info["observerboard"] == _RHANDLERS_OBSBOARD and "oldhash" in info:
            logger.debug("Notified %s upd item %s", self, item)
            oldhash = info["oldhash"]
            # First remove the oldhash
            if oldhash in self._sections_hash:
                for section in [
                    s for s in self._sections_hash[oldhash] if s.rh is item
                ]:
                    self._sections_hash[oldhash].discard(section)
            # Then add the new hash: This is relatively slow so that it should not be used much...
            for section in [s for s in self.sections if s.rh is item]:
                self._sections_hash[section.rh.simplified_hashkey].add(section)

    def fastsearch(self, skeleton):
        """
        Uses the sections hash table to significantly speed-up searches.

        The fastsearch method returns a list of possible candidates (given the
        skeleton). It is of the user responsibility to check each of the
        returned sections to verify if it exactly matches or not.
        """
        try:
            hkey = skeleton.simplified_hashkey
            trydict = False
        except AttributeError:
            trydict = True
        if not trydict:
            return self._sections_hash[hkey]
        elif trydict and isinstance(skeleton, dict):
            # We assume it is a resource handler dictionary
            try:
                hkey = (
                    skeleton["resource"].get("kind", None),
                    skeleton["container"].get("filename", None),
                )
            except KeyError:
                logger.critical(
                    "This is probably not a ResourceHandler dictionary."
                )
                raise
            return self._sections_hash[hkey]
        raise ValueError(
            "Cannot process a {!s} type skeleton".format(type(skeleton))
        )


#: Class of a list of statuses
InputsReportStatusTupple = namedtuple(
    "InputsReportStatusTupple",
    ("PRESENT", "EXPECTED", "CHECKED", "MISSING", "UNUSED"),
)


#: Possible statuses used in :class:`SequenceInputsReport` objects
InputsReportStatus = InputsReportStatusTupple(
    PRESENT="present",
    EXPECTED="expected",
    CHECKED="checked",
    MISSING="missing",
    UNUSED="unused",
)


class SequenceInputsReport:
    """Summarize data about inputs (missing resources, alternates, ...)."""

    _TranslateStage = dict(
        get=InputsReportStatus.PRESENT,
        expected=InputsReportStatus.EXPECTED,
        checked=InputsReportStatus.CHECKED,
        void=InputsReportStatus.MISSING,
        load=InputsReportStatus.UNUSED,
    )

    def __init__(self, inputs):
        self._local_map = defaultdict(lambda: defaultdict(list))
        for insec in inputs:
            local = insec.rh.container.localpath()
            # Determine if the current section is an alternate or not...
            kind = "alternate" if insec.alternate is not None else "nominal"
            self._local_map[local][kind].append(insec)

    def _local_status(self, local):
        """Find out the local resource status (see InputsReportStatus).

        It returns a tuple that contains:

        * The local resource status (see InputsReportStatus)
        * The resource handler that was actually used to get the resource
        * The resource handler that should have been used in the nominal case
        """
        desc = self._local_map[local]
        # First, check the nominal resource
        if len(desc["nominal"]) > 0:
            nominal = desc["nominal"][-1]
            status = self._TranslateStage[nominal.stage]
            true_rh = nominal.rh
        else:
            logger.warning(
                "No nominal section for < %s >. This should not happened !",
                local,
            )
            nominal = None
            status = None
            true_rh = None
        # Look for alternates:
        if status not in (
            InputsReportStatus.PRESENT,
            InputsReportStatus.EXPECTED,
        ):
            for alter in desc["alternate"]:
                alter_status = self._TranslateStage[alter.stage]
                if alter_status in (
                    InputsReportStatus.PRESENT,
                    InputsReportStatus.EXPECTED,
                ):
                    status = alter_status
                    true_rh = alter.rh
                    break
        return status, true_rh, (nominal.rh if nominal else None)

    def synthetic_report(self, detailed=False, only=None):
        """Returns a string that describes each local resource with its status.

        :param bool detailed: when alternates are used, tell which resource handler
                              is actually used and which one should have been used
                              in the nominal case.
        :param list[str] only: Output only the listed statuses (statuses are defined in
                               :data:`InputsReportStatus`). By default (*None*), output
                               everything. Note that "alternates" are always shown.
        """
        if only is None:
            # The default is to display everything
            only = list(InputsReportStatus)
        else:
            # Convert a single string to a list
            if isinstance(only, str):
                only = [
                    only,
                ]
            # Check that the provided statuses exist
            if not all([f in InputsReportStatus for f in only]):
                return "* The only attribute is wrong ! ({!s})".format(only)

        outstr = ""
        for local in sorted(self._local_map):
            # For each and every local file, check alternates and find out the status
            status, true_rh, nominal_rh = self._local_status(local)
            extrainfo = ""
            # Detect alternates
            is_alternate = status != InputsReportStatus.MISSING and (
                true_rh is not nominal_rh
            )
            if is_alternate:
                extrainfo = "(ALTERNATE USED)"
            # Alternates are always printed. Otherwise rely on **only**
            if is_alternate or status in only:
                outstr += "* {:8s} {:16s} : {:s}\n".format(
                    status, extrainfo, local
                )
                if detailed and extrainfo != "":
                    outstr += "  * The following resource is used:\n"
                    outstr += true_rh.idcard(indent=4) + "\n"
                    if nominal_rh is not None:
                        outstr += "  * Instead of:\n"
                        outstr += nominal_rh.idcard(indent=4) + "\n"

        return outstr

    def print_report(self, detailed=False, only=None):
        """Print a list of each local resource with its status.

        :param bool detailed: when alternates are used, tell which resource handler
                              is actually used and which one should have been used
                              in the nominal case.
        :param list[str] only: Output only the listed statuses (statuses are defined in
                               :data:`InputsReportStatus`). By default (*None*), output
                               everything. Note that "alternates" are always shown.
        """
        print(self.synthetic_report(detailed=detailed, only=only))

    def active_alternates(self):
        """List the local resource for which an alternative resource has been used.

        It returns a dictionary that associates the local resource name with
        a tuple that contains:

        * The resource handler that was actually used to get the resource
        * The resource handler that should have been used in the nominal case
        """
        outstack = dict()
        for local in self._local_map:
            status, true_rh, nominal_rh = self._local_status(local)
            if status != InputsReportStatus.MISSING and (
                true_rh is not nominal_rh
            ):
                outstack[local] = (true_rh, nominal_rh)
        return outstack

    def missing_resources(self):
        """List the missing local resources."""
        outstack = dict()
        for local in self._local_map:
            (
                status,
                true_rh,  # @UnusedVariable
                nominal_rh,
            ) = self._local_status(local)
            if status == InputsReportStatus.MISSING:
                outstack[local] = nominal_rh
        return outstack


def _fast_clean_uri(store, remote):
    """Clean a URI so that it can be compared with a JSON load version."""
    qsl = remote["query"].copy()
    qsl.update(
        {
            "storearg_{:s}".format(k): v
            for k, v in store.tracking_extraargs.items()
        }
    )
    return {
        "scheme": str(store.scheme),
        "netloc": str(store.netloc),
        "path": str(remote["path"]),
        "params": str(remote["params"]),
        "query": qsl,
        "fragment": str(remote["fragment"]),
    }


class LocalTrackerEntry:
    """Holds the data for a given local container.

    It includes data for two kinds of "actions": get/put. For each "action",
    Involved resource handlers, hook functions calls and get/put from low level
    stores are tracked.
    """

    _actions = (
        "get",
        "put",
    )
    _internals = ("rhdict", "hook", "uri")

    def __init__(self, master_tracker=None):
        """

        :param master_tracker: The LocalTracker this entry belongs to.
        """
        self._data = dict()
        self._master_tracker = master_tracker
        for internal in self._internals:
            self._data[internal] = {act: list() for act in self._actions}

    @classmethod
    def _check_action(cls, action):
        return action in cls._actions

    @staticmethod
    def _jsonize(stuff):
        """Make 'stuff' comparable to the result of a json.load."""
        return json.loads(json.dumps(stuff))

    def _clean_rhdict(self, rhdict):
        if "options" in rhdict:
            del rhdict["options"]
        return self._jsonize(rhdict)

    def update_rh(self, rh, info):
        """Update the entry based on data received from the observer board.

        This method is to be called with data originated from the
        Resources-Handlers observer board (when updates are notified).

        :param rh: :class:`~vortex.data.handlers.Handler` object that sends the update.
        :param info: Info dictionary sent by the :class:`~vortex.data.handlers.Handler` object
        """
        stage = info["stage"]
        if self._check_action(stage):
            if "hook" in info:
                self._data["hook"][stage].append(self._jsonize(info["hook"]))
            elif not info.get("insitu", False):
                # We are using as_dict since this may be written to a JSON file
                self._data["rhdict"][stage].append(
                    self._clean_rhdict(rh.as_dict())
                )

    def _update_store(self, info, uri):
        """Update the entry based on data received from the observer board.

        This method is to be called with data originated from the
        Stores-Activity observer board (when updates are notified).

        :param info: Info dictionary sent by the :class:`~vortex.data.stores.Store` object
        :param uri: A cleaned (i.e. compatible with JSON) representation of the URI
        """
        action = info["action"]
        # Only known action and successfull attempts
        if self._check_action(action) and info["status"]:
            self._data["uri"][action].append(uri)
            if self._master_tracker is not None:
                self._master_tracker.uri_map_append(self, action, uri)

    def dump_as_dict(self):
        """Export the entry as a dictionary."""
        return self._data

    def load_from_dict(self, dumpeddict):
        """Restore the entry from a previous export.

        :param dumpeddict: Dictionary that will be loaded (usually generated by
            the :meth:`dump_as_dict` method)
        """
        self._data = dumpeddict
        for action in self._actions:
            for uri in self._data["uri"][action]:
                self._master_tracker.uri_map_append(self, action, uri)

    def append(self, anotherentry):
        """Append the content of another LocalTrackerEntry object into this one."""
        for internal in self._internals:
            for act in self._actions:
                self._data[internal][act].extend(
                    anotherentry._data[internal][act]
                )

    def latest_rhdict(self, action):
        """Return the dictionary that represents the latest :class:`~vortex.data.handlers.Handler` object involved.

        :param action: Action that is considered.
        """
        if self._check_action(action) and self._data["rhdict"][action]:
            return self._data["rhdict"][action][-1]
        else:
            return dict()

    def match_rh(self, action, rh, verbose=False):
        """Check if an :class:`~vortex.data.handlers.Handler` object matches the one stored internally.

        :param action: Action that is considered
        :param rh: :class:`~vortex.data.handlers.Handler` object that will be checked
        """
        if self._check_action(action):
            cleaned = self._clean_rhdict(rh.as_dict())
            latest = self.latest_rhdict(action)
            res = latest == cleaned
            if verbose and not res:
                for key, item in latest.items():
                    newitem = cleaned.get(key, None)
                    if newitem != item:
                        logger.error("Expected %s:", key)
                        logger.error(pprint.pformat(item))
                        logger.error("Got:")
                        logger.error(pprint.pformat(newitem))
            return res
        else:
            return False

    def _check_uri_remote_delete(self, uri):
        """Called when a :class:`~vortex.data.stores.Store` object notifies a delete.

        The URIs stored for the "put" action are checked against the delete
        request. If a match is found, the URI is deleted.

        :param uri: A cleaned (i.e. compatible with JSON) representation of the URI
        """
        while uri in self._data["uri"]["put"]:
            self._data["uri"]["put"].remove(uri)
            if self._master_tracker is not None:
                self._master_tracker.uri_map_remove(self, "put", uri)

    def _redundant_stuff(self, internal, action, stuff):
        if self._check_action(action):
            return stuff in self._data[internal][action]
        else:
            return False

    def redundant_hook(self, action, hookname):
        """Check of a hook function has already been applied.

        :param action: Action that is considered.
        :param hookname: Name of the Hook function that will be checked.
        """
        return self._redundant_stuff("hook", action, self._jsonize(hookname))

    def redundant_uri(self, action, store, remote):
        """Check if an URI has already been processed.

        :param action: Action that is considered.
        :param store: :class:`~vortex.data.stores.Store` object that will be checked.
        :param remote: Remote path that will be checked.
        """
        return self._redundant_stuff(
            "uri", action, _fast_clean_uri(store, remote)
        )

    def _grep_stuff(self, internal, action, skeleton=dict()):
        stack = []
        for element in self._data[internal][action]:
            if isinstance(element, collections.abc.Mapping):
                succeed = True
                for key, val in skeleton.items():
                    succeed = succeed and (
                        (key in element) and (element[key] == val)
                    )
                if succeed:
                    stack.append(element)
        return stack

    def __str__(self):
        out = ""
        for action in self._actions:
            for internal in self._internals:
                if len(self._data[internal][action]) > 0:
                    out += "+ {:4s} / {}\n{}\n".format(
                        action.upper(),
                        internal,
                        EncodedPrettyPrinter().pformat(
                            self._data[internal][action]
                        ),
                    )
        return out


class LocalTracker(defaultdict):
    """Dictionary like structure that gathers data on the various local containers.

    For each local container (identified by the result of its iotarget method), a
    dictionary entry is created. Its value is a :class:`~vortex.layout.dataflow.LocalTrackerEntry`
    object.
    """

    _default_json_filename = "local-tracker-state.json"

    def __init__(self):
        super().__init__()
        # This hash table will be used to speedup searches
        self._uri_map = defaultdict(lambda: defaultdict(weakref.WeakSet))

    def __missing__(self, key):
        self[key] = LocalTrackerEntry(master_tracker=self)
        return self[key]

    def _hashable_uri(self, uri):
        """Produces a version of the URI that is hashable."""
        listuri = list()
        for k in sorted(uri.keys()):
            listuri.append(k)
            if isinstance(uri[k], dict):
                listuri.append(self._hashable_uri(uri[k]))
            elif isinstance(uri[k], list):
                listuri.append(tuple(uri[k]))
            else:
                listuri.append(uri[k])
        return tuple(listuri)

    def uri_map_remove(self, entry, action, uri):
        """Delete an entry in the URI hash table."""
        self._uri_map[action][self._hashable_uri(uri)].discard(entry)

    def uri_map_append(self, entry, action, uri):
        """Add a new entry in the URI hash table."""
        self._uri_map[action][self._hashable_uri(uri)].add(entry)

    def update_rh(self, rh, info):
        """Update the object based on data received from the observer board.

        This method is to be called with data originated from the
        Resources-Handlers observer board (when updates are notified).

        :param rh: :class:`~vortex.data.handlers.Handler` object that sends the update.
        :param info: Info dictionary sent by the :class:`~vortex.data.handlers.Handler` object
        """
        lpath = rh.container.iotarget()
        if isinstance(lpath, str):
            if info.get("clear", False):
                self.pop(lpath, None)
            else:
                self[lpath].update_rh(rh, info)
        else:
            logger.debug(
                "The iotarget is not a str: skipped in %s", self.__class__
            )

    def update_store(self, store, info):
        """Update the object based on data received from the observer board.

        This method is to be called with data originated from the
        Stores-Activity observer board (when updates are notified).

        :param store: :class:`~vortex.data.stores.Store` object that sends the update.
        :param info: Info dictionary sent by the :class:`~vortex.data.stores.Store` object
        """
        lpath = info.get("local", None)
        if lpath is None:
            # Check for file deleted on the remote side
            if info["action"] == "del" and info["status"]:
                clean_uri = _fast_clean_uri(store, info["remote"])
                huri = self._hashable_uri(clean_uri)
                for atracker in list(self._uri_map["put"][huri]):
                    atracker._check_uri_remote_delete(clean_uri)
        else:
            if isinstance(lpath, str):
                clean_uri = _fast_clean_uri(store, info["remote"])
                self[lpath]._update_store(info, clean_uri)
            else:
                logger.debug(
                    "The iotarget isn't a str: It will be skipped in %s",
                    self.__class__,
                )

    def is_tracked_input(self, local):
        """Check if the given `local` container is listed as an input and associated with
        a valid :class:`~vortex.data.handlers.Handler`.

        :param local: Local name of the input that will be checked
        """
        return (
            isinstance(local, str)
            and (local in self)
            and (self[local].latest_rhdict("get"))
        )

    def _grep_stuff(self, internal, action, skeleton=dict()):
        stack = []
        for entry in self.values():
            stack.extend(entry._grep_stuff(internal, action, skeleton))
        return stack

    def grep_uri(self, action, skeleton=dict()):
        """Returns all the URIs that contains the same key/values than `skeleton`.

        :param action: Action that is considered.
        :param skeleton: Dictionary that will be used as a search pattern
        """
        return self._grep_stuff("uri", action, skeleton)

    def json_dump(self, filename=_default_json_filename):
        """Dump the object to a JSON file.

        :param filename: Path to the JSON file.
        """
        outdict = {loc: entry.dump_as_dict() for loc, entry in self.items()}
        with open(filename, "w", encoding="utf-8") as fpout:
            json.dump(outdict, fpout, indent=2, sort_keys=True)

    def json_load(self, filename=_default_json_filename):
        """Restore the object using a JSON file.

        :param filename: Path to the JSON file.
        """
        with open(filename, encoding="utf-8") as fpin:
            indict = json.load(fpin)
        # Start from scratch
        self.clear()
        for loc, adict in indict.items():
            self[loc].load_from_dict(adict)

    def append(self, othertracker):
        """Append the content of another LocalTracker object into this one."""
        for loc, entry in othertracker.items():
            self[loc].append(entry)

    def datastore_inplace_overwrite(self, other):
        """Used by a DataStore object to refill a LocalTracker."""
        self.clear()
        self.append(other)

    def __str__(self):
        out = ""
        for loc, entry in self.items():
            entryout = str(entry)
            if entryout:
                out += "========== {} ==========\n{}".format(loc, entryout)
        return out
