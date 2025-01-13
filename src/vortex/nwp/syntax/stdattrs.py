"""
This module provides some pre-defined attributes descriptions or combined sets
of attributes description that could be used in the footprint definition of any
class which follow the :class:`footprints.Footprint` syntax.
"""

import re
from functools import total_ordering

import footprints
from bronx.stdtypes.date import Time

from vortex.syntax.stddeco import namebuilding_append

#: Export some new class for attributes in footprint objects, eg : GenvKey
__all__ = ["GenvKey", "GenvDomain"]

#: Usual Footprint for a single member (in an algo Component)
a_algo_member = dict(
    info=(
        "The current member's number "
        + "(may be omitted in deterministic configurations)."
    ),
    optional=True,
    type=int,
)

#: Usual Footprint of the ``outputid`` attribute.
algo_member = footprints.Footprint(attr=dict(member=a_algo_member))

#: Known OOPS testcomponent ``run``
known_oops_testcomponent_runs = ["ootestcomponent", "testcomponent", "testvar"]

#: Usual definition of the ``run`` attribute for OOPS binaries.
a_oops_run = dict(
    info="The OOPS run (== task).",
    optional=False,
)
#: Usual Footprint of the ``run`` attribute for OOPS binaries.
oops_run = footprints.Footprint(
    info="OOPS kind of run", attr=dict(run=a_oops_run)
)

#: Usual definition of the ``test_type`` attribute.
a_oops_test_type = dict(
    info="Sub-test or family of sub-tests to be ran.",
    optional=False,
)
#: Usual Footprint of the ``test_type`` attribute.
oops_test_type = footprints.Footprint(
    info="OOPS type of test", attr=dict(test_type=a_oops_test_type)
)

#: Usual definition of the ``expected_target`` attribute.
an_oops_expected_target = dict(
    info=("Expected target for the test success"),
    type=footprints.FPDict,
    optional=True,
    default=None,
)
#: Usual Footprint of the ``expected_target`` attribute.
oops_expected_target = footprints.Footprint(
    attr=dict(expected_target=an_oops_expected_target)
)

#: Usual Footprint of a combined lists of members and terms
oops_members_terms_lists = footprints.Footprint(
    info="Abstract footprint for a members/terms list.",
    attr=dict(
        members=dict(
            info="A list of members.",
            type=footprints.FPList,
        ),
        terms=dict(
            info="A list of effective terms.",
            type=footprints.FPList,
            optional=True,
            default=footprints.FPList(
                [
                    Time(0),
                ]
            ),
        ),
    ),
)

#: Usual definition of the ``outputid`` attribute
a_outputid = dict(
    info="The identifier for the encoding of post-processed fields.",
    optional=True,
)

#: Usual Footprint of the ``outputid`` attribute.
outputid = footprints.Footprint(attr=dict(outputid=a_outputid))


def _apply_outputid(cls):
    """Decorator that tweak the class in order to add OUTPUTID on the namelist"""
    orig_pnd = getattr(cls, "prepare_namelist_delta", None)
    if orig_pnd is None:
        raise ImportError(
            "_apply_outputid can not be applied on {!s}".format(cls)
        )

    def prepare_namelist_delta(self, rh, namcontents, namlocal):
        namw = orig_pnd(self, rh, namcontents, namlocal)
        if self.outputid is not None and any(
            ["OUTPUTID" in nam_b.macros() for nam_b in namcontents.values()]
        ):
            self._set_nam_macro(
                namcontents, namlocal, "OUTPUTID", self.outputid
            )
            namw = True
        return namw

    cls.prepare_namelist_delta = prepare_namelist_delta
    return cls


#: Decorated footprint for the ``outputid`` attribute
outputid_deco = footprints.DecorativeFootprint(
    outputid,
    decorator=[
        _apply_outputid,
    ],
)


def show():
    """Returns available items and their type."""
    dmod = globals()
    for stda in sorted(
        filter(
            lambda x: x.startswith("a_")
            or isinstance(dmod[x], footprints.Footprint),
            dmod.keys(),
        )
    ):
        print(
            "{} ( {} ) :\n  {}\n".format(
                stda, type(dmod[stda]).__name__, dmod[stda]
            )
        )


domain_remap = dict()


def _lowerattr(matchobj):
    """Internal and technical function returning lower case value of the complete match item."""
    return matchobj.group(0).lower()


class GenvKey(str):
    """
    Attribute for a GEnv cycle name.
    Implicit attributes inside brackets are translated to lower case.
    See also :mod:`vortex_gco.tools.genv`.
    """

    def __new__(cls, value):
        """Proxy to ``str.__new___`` with attributes inside brackets translated to lower case."""
        return str.__new__(cls, re.sub(r"\[\w+\]", _lowerattr, value.upper()))


a_gvar = dict(
    info="The key that identifies the resource in the Genv database.",
    type=GenvKey,
    optional=True,
    doc_visibility=footprints.doc.visibility.ADVANCED,
)

#: Usual definition of the ``genv`` attribute.
gvar = footprints.Footprint(info="A GENV access key", attr=dict(gvar=a_gvar))


class GenvDomain(str):
    """
    Remap plain area names to specific Genv short domain names.
    See also :mod:`vortex_gco.tools.genv`.
    """

    def __new__(cls, value):
        """Proxy to ``str.__new___`` with on the fly remapping of domain names to short values."""
        return str.__new__(cls, domain_remap.get(value, value))


a_gdomain = dict(
    info="The resource's geographical domain name in the Genv database.",
    type=GenvDomain,
    optional=True,
    default="[geometry::area]",
    doc_visibility=footprints.doc.visibility.ADVANCED,
)

#: Usual definition of the ``gdomain`` attribute.
gdomain = footprints.Footprint(
    info="A domain name in GCO convention", attr=dict(gdomain=a_gdomain)
)


@total_ordering
class ArpIfsSimplifiedCycle:
    """
    Type that holds a simplified representation of an ArpegeIFS cycle.

    It provides basic comparison operators to determine if a given cycle is more recent or not
    compared to another one.

    It can be used in a footprint specification.
    """

    _cy_re = re.compile(
        r"(?:u(?:env|get):)?(?:cy|al)(\d+)(?:t(\d{1,3}))?(?=_|@|\.|$)(?:.*?(?:[_-]op(\d{1,3})))?"
    )
    _hash_shift = 10000

    def __init__(self, cyclestr):
        cy_match = self._cy_re.match(cyclestr)
        if cy_match:
            self._number = int(cy_match.group(1))
            self._toulouse = (
                int(cy_match.group(2)) + 1
                if cy_match.group(2) is not None
                else 0
            )
            self._op = (
                int(cy_match.group(3)) + 1
                if cy_match.group(3) is not None
                else 0
            )
        else:
            raise ValueError("Malformed cycle: {}".format(cyclestr))

    def __hash__(self):
        return (
            self._number * self._hash_shift + self._toulouse
        ) * self._hash_shift + self._op

    def __eq__(self, other):
        if not isinstance(other, ArpIfsSimplifiedCycle):
            try:
                other = ArpIfsSimplifiedCycle(other)
            except (ValueError, TypeError):
                return False
        return hash(self) == hash(other)

    def __gt__(self, other):
        if not isinstance(other, ArpIfsSimplifiedCycle):
            other = ArpIfsSimplifiedCycle(other)
        return hash(self) > hash(other)

    def __str__(self):
        return (
            "cy{:d}".format(self._number)
            + ("t{:d}".format(self._toulouse - 1) if self._toulouse else "")
            + ("_op{:d}".format(self._op - 1) if self._op else "")
        )

    def __repr__(self):
        return "<{} | {!s}>".format(
            object.__repr__(self).lstrip("<").rstrip(">"), self
        )

    def export_dict(self):
        """The pure dict/json output is the raw integer"""
        return str(self)


a_arpifs_cycle = dict(
    info="An Arpege/IFS cycle name",
    type=ArpIfsSimplifiedCycle,
    optional=True,
    default="cy40",  # For "old" Olive configurations to keep working
)

#: Usual definition of the ``cycle`` attribute.
arpifs_cycle = footprints.Footprint(
    info="An abstract arpifs_cycle in GCO convention",
    attr=dict(cycle=a_arpifs_cycle),
)

uget_sloppy_id_regex = re.compile(
    r"(?P<shortuget>(?P<id>\S+)@(?P<location>[-\w]+))"
)
uget_id_regex = (
    r"(?P<fulluget>u(?:get|env):" + uget_sloppy_id_regex.pattern + ")"
)
uget_id_regex_only = re.compile("^" + uget_id_regex + "$")
uget_id_regex = re.compile(r"\b" + uget_id_regex + r"\b")


class GgetId(str):
    """Basestring wrapper for Gget Ids."""

    def __new__(cls, value):
        if uget_id_regex_only.match(value):
            raise ValueError("A GgetId cannot look like a UgetId !")
        return str.__new__(cls, value)


class AbstractUgetId(str):
    """Basestring wrapper for Uget Ids."""

    _ALLOWED_LOCATIONS = ()
    _OUTCAST_LOCATIONS = ()

    def __new__(cls, value):
        vmatch = uget_id_regex_only.match(value)
        if not vmatch:
            raise ValueError('Invalid UgetId (got "{:s}")'.format(value))
        me = str.__new__(cls, value)
        me._id = vmatch.group("id")
        me._location = vmatch.group("location")
        if me._location in set(cls._OUTCAST_LOCATIONS):
            raise ValueError(
                'Invalid UgetId (got "{:s}"). Outcast Location.'.format(value)
            )
        if cls._ALLOWED_LOCATIONS and me._location not in set(
            cls._ALLOWED_LOCATIONS
        ):
            raise ValueError(
                'Invalid UgetId (got "{:s}"). Disallowed location'.format(
                    value
                )
            )
        return me

    @property
    def id(self):
        return self._id

    @property
    def location(self):
        return self._location

    @property
    def short(self):
        return self._id + "@" + self._location

    def monthlyshort(self, month):
        return self._id + ".m{:02d}".format(month) + "@" + self._location


class UgetId(AbstractUgetId):
    _OUTCAST_LOCATIONS = ("demo",)


def genv_ifs_compiler_convention(cls):
    """Add the necessary method to handle compiler version/option in Genv."""
    original_gget_basename = getattr(cls, "gget_basename", None)
    if original_gget_basename is not None:

        def gget_basename(self):
            """GGET specific naming convention."""
            b_dict = original_gget_basename(self)
            if getattr(self, "compiler_version", None):
                b_dict["compiler_version"] = self.compiler_version
            if getattr(self, "compiler_option", None):
                b_dict["compiler_option"] = self.compiler_option
            if getattr(self, "cycle", None):
                b_dict["cycle"] = self.cycle
            return b_dict

        cls.gget_basename = gget_basename
    return cls


#: Usual definition of the ``compiler_version`` and ``compiler_option`` attributes.
gmkpack_compiler_identification = footprints.Footprint(
    info="Add the compiler version/option in the footprint",
    attr=dict(
        compiler_version=dict(
            info="The compiler version in gmkpack convention.", optional=True
        ),
        compiler_option=dict(
            info="The compiler option in gmkpack convention.", optional=True
        ),
    ),
)


#: Usual definition of the ``compiler_version`` and ``compiler_option`` attributes + genv integration.
gmkpack_compiler_identification_deco = footprints.DecorativeFootprint(
    gmkpack_compiler_identification,
    decorator=[
        genv_ifs_compiler_convention,
    ],
)


def genv_executable_flavour(cls):
    """Add the necessary method to the "flavour" in Genv."""
    original_genv_basename = getattr(cls, "genv_basename", None)
    if original_genv_basename is not None:

        def genv_basename(self):
            """Just retrieve a potential gvar attribute."""
            gvar = original_genv_basename(self)
            if getattr(self, "flavour", None):
                gvar += (
                    "_"
                    + {"singleprecision": "SP"}.get(
                        self.flavour, self.flavour
                    ).upper()
                )
            return gvar

        cls.genv_basename = genv_basename
    return cls


#: Usual definition of the ``flavour`` attribute.
executable_flavour = footprints.Footprint(
    info="Add the executable flavour attribute to the resource",
    attr=dict(
        flavour=dict(
            info="The executable flavour (This may influence the Genv's key choice).",
            values=[
                "singleprecision",
            ],
            optional=True,
        ),
    ),
)


#: Usual definition of the ``flavour``.
executable_flavour_deco = footprints.DecorativeFootprint(
    executable_flavour,
    decorator=[
        genv_executable_flavour,
        namebuilding_append(
            "src", lambda self: [self.flavour], none_discard=True
        ),
    ],
)
