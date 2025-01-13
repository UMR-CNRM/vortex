"""
Functions and tools to handle resources names or other kind of names.

Any "name building" object, must conform to the :class:`AbstractVortexNameBuilder`
abstract class interface.
"""

from bronx.fancies import loggers
import footprints
from footprints import proxy as fpx

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class VortexNameBuilderError(ValueError):
    """Raised whenever the name building process fails."""

    pass


class AbstractVortexNameBuilder(footprints.FootprintBase):
    """Abstract class for any name building class."""

    _abstract = True
    _collector = ("vortexnamebuilder",)
    _footprint = dict(
        info="Abstract Vortex NameBuilder",
        attr=dict(
            name=dict(
                info="The NameBuilder's name.",
            ),
        ),
        fastkeys={"name"},
    )

    def __init__(self, *args, **kw):
        logger.debug("Init VortexNameBuilder %s", self.__class__)
        super().__init__(*args, **kw)
        self._default = dict(
            radical="vortexdata",
        )
        # List of known defaults
        for k in [
            "flow",
            "src",
            "term",
            "period",
            "cen_period",
            "geo",
            "suffix",
            "stage",
            "fmt",
            "part",
            "compute",
            "number",
            "filtername",
        ]:
            self._default[k] = None
        self.setdefault(**kw)

    def setdefault(self, **kw):
        """Update or set new default values as the background description used in packing."""
        self._default.update(kw)

    @property
    def defaults(self):
        """List of currently declared defaults (defined or not)."""
        return self._default.keys()

    def as_dump(self):
        """Nicely formated view of the current class in dump context."""
        return str(self._default)

    def pack(self, d):
        """A shortcut to :meth:`pack_basename` (legacy)."""
        return self.pack_basename(d)

    def pack_basename(self, d):
        """Returns a basename given the **d** info dictionary."""
        raise NotImplementedError("This is an abstract method !")

    def pack_pathname(self, d):
        """Returns a pathname given the **d** info dictionary."""
        raise NotImplementedError("This is an abstract method !")


# Activate the footprint's fasttrack on the resources collector
vbcollect = footprints.collectors.get(tag="vortexnamebuilder")
vbcollect.fasttrack = ("name",)
del vbcollect


class AbstractVortexNameBuilderProxy(AbstractVortexNameBuilder):
    """Abstract class for any "proxy" builder object.

    Given the input dictionary, find the appropriate builder object and delegate
    the work.
    """

    _abstract = True

    def __init__(self, *kargs, **kwargs):
        # Cache for actual builder objects
        self._instanciated_builders = dict()
        super().__init__(*kargs, **kwargs)

    def setdefault(self, **kw):
        """Update or set new default values as the background description used in packing."""
        self._default.update(kw)
        for builder in self._instanciated_builders.values():
            builder.setdefault(**kw)

    def _get_builder(self, name):
        """Return a builder object given a name.

        A cache is used in order for faster computations.
        """
        if name not in self._instanciated_builders:
            builder = fpx.vortexnamebuilder(name=name)
            if self._default:
                builder.setdefault(**self._default)
            self._instanciated_builders[name] = builder
        return self._instanciated_builders[name]

    def _pick_actual_builder(self, d):
        """Given the input dictionary, returns the appropriate builder object."""
        raise NotImplementedError("This is an abstract method !")

    def pack_basename(self, d):
        """Returns a basename given the **d** info dictionary."""
        components = dict()
        components.update(self._default)
        components.update(d)
        return self._pick_actual_builder(components).pack_basename(d)

    def pack_pathname(self, d):
        """Returns a pathname given the **d** info dictionary."""
        components = dict()
        components.update(self._default)
        components.update(d)
        return self._pick_actual_builder(components).pack_pathname(d)


class AbstractActualVortexNameBuilder(AbstractVortexNameBuilder):
    """Abstract class for any "concrete" builder object (as opposed to proxies)."""

    _abstract = True

    def _pack_generic(self, d, what, default="std"):
        """
        Build the resource vortex basename/pathname or whatever according to
        ``style`` value.
        """
        components = dict()
        components.update(self._default)
        components.update(d)

        packstyle = getattr(
            self,
            "_pack_{!s}_{!s}".format(what, components.get("style", default)),
        )
        return packstyle(components)

    def pack_basename(self, d):
        """Build the resource vortex basename according to ``style`` value."""
        return self._pack_generic(d, "basename")

    def pack_pathname(self, d):
        """Build the resource vortex pathname according to ``style`` value."""
        return "/".join(self._pack_generic(d, "pathname"))

    # A Vortex pathname may include the following bits

    def _pack_pathname_init(self, d):
        """Mandatory things to be packed into the pathname."""
        pathbits = []
        for k in ["vapp", "vconf", "experiment"]:
            if k not in d:
                raise VortexNameBuilderError(
                    "The {!r} info key is mandatory".format(k)
                )
            pathbits.append(str(d[k]))
        return pathbits

    def _pack_pathname_append_flowdate(self, pathbits, d):
        """Pack the date/cutoff that characterise the resource's flow."""
        if "flow" in d and d["flow"] is not None:
            pathbits.append(
                self._pack_std_items_datestuff(d["flow"], fatal=True)
            )
        else:
            raise VortexNameBuilderError("The flow info key is mandatory")

    def _pack_pathname_append_flowperiod(self, pathbits, d):
        """Pack the period/cutoff that characterise the resource's flow."""
        if "flow" in d and d["flow"] is not None:
            pathbits.append(
                self._pack_std_items_periodstuff(d["flow"], fatal=True)
            )
        else:
            raise VortexNameBuilderError("The flow info key is mandatory")

    def _pack_pathname_append_member(self, pathbits, d):
        """Pack the provider's member number (optional)."""
        if "member" in d and d["member"] is not None:
            pathbits.append(self._pack_std_item_member(d["member"]))

    def _pack_pathname_append_scenario(self, pathbits, d):
        """Pack the provider's scenario identifier (optional)."""
        if "scenario" in d and d["scenario"] is not None:
            pathbits.append(self._pack_std_item_scenario(d["scenario"]))

    def _pack_pathname_append_block(self, pathbits, d):
        """Pack the provider's block name."""
        if "block" in d:
            if d["block"]:
                pathbits.append("_".join(self._pack_std_items(d["block"])))
        else:
            raise VortexNameBuilderError("The block info key is mandatory")

    # A bunch of utility methods that prepares values

    def _pack_void_item(self, value):
        """The most trivial conversion mechanism: the ``value`` as string."""
        return str(value)

    def _pack_std_item_seta(self, value):
        """Packing of a MPI-task number in first direction."""
        return "a{:04d}".format(int(value))

    def _pack_std_item_setb(self, value):
        """Packing of a MPI-task number in second direction."""
        return "b{:04d}".format(int(value))

    def _pack_std_item_mpi(self, value):
        """Packing of a MPI-task number."""
        return "n{:04d}".format(int(value))

    def _pack_std_item_openmp(self, value):
        """Packing of an OpenMP id number."""
        return "omp{:02d}".format(int(value))

    def _pack_std_item_month(self, value):
        """Packing of a month-number value."""
        return "m{!s}".format(value)

    def _pack_std_item_stretching(self, value):
        """Packing of the stretching factor in spectral geometry."""
        return "c{!s}".format(int(value * 10))

    def _pack_std_item_truncation(self, value):
        """Packing of the geometry's truncation value."""
        if isinstance(value, tuple):
            return "t{1:s}{2:s}{0!s}".format(*value)
        else:
            return "tl{!s}".format(value)

    def _pack_std_item_filtering(self, value):
        """Packing of the geometry's filtering value."""
        return "f{!s}".format(value)

    def _pack_std_item_time(self, value):
        """Packing of a Time object."""
        return value.fmthm if hasattr(value, "fmthm") else str(value)

    _pack_std_item_begintime = _pack_std_item_time
    _pack_std_item_endtime = _pack_std_item_time

    def _pack_std_item_date(self, value):
        """Packing of a Time object."""
        return value.stdvortex if hasattr(value, "stdvortex") else str(value)

    _pack_std_item_begindate = _pack_std_item_date
    _pack_std_item_enddate = _pack_std_item_date

    def _pack_std_item_cutoff(self, value):
        """Abbreviate the cutoff name."""
        cutoff_map = dict(production="prod")
        return cutoff_map.get(value, value)

    def _pack_std_item_shortcutoff(self, value, default="X"):
        """Abbreviate the cutoff name."""
        return value[0].upper() if value is not None else default

    def _pack_std_item_member(self, value):
        return "mb{:03d}".format(value)

    def _pack_std_item_scenario(self, value):
        return "s{:s}".format(value)

    def _pack_std_items(self, items):
        """
        Go through all items and pack them according to the so-called standard way.
        Result is always a list of string values.
        """
        if not isinstance(items, list):
            items = [items]
        packed = list()
        for i in items:
            if isinstance(i, dict):
                for k, v in i.items():
                    packmtd = getattr(
                        self, "_pack_std_item_" + k, self._pack_void_item
                    )
                    packed.append(packmtd(v))
            else:
                packed.append(self._pack_void_item(i))
        return packed

    def _pack_std_items_negativetimes(self, items):
        return [
            (t[1:] + "ago" if t[0] == "-" else t)
            for t in self._pack_std_items(items)
        ]

    def _pack_std_items_datestuff(self, d, fatal=False):
        """Specialised version of _pack_std_items that deals with date/cutoff pairs."""
        flowdate = None
        flowcut = None
        if isinstance(d, (tuple, list)):
            for flowitem in [x for x in d if isinstance(x, dict)]:
                if "date" in flowitem:
                    flowdate = flowitem["date"]
                if "shortcutoff" in flowitem:
                    flowcut = flowitem["shortcutoff"]
        if flowdate is None:
            if fatal:
                raise VortexNameBuilderError("A date is mandatory here...")
            else:
                return ""
        return self._pack_std_item_date(
            flowdate
        ) + self._pack_std_item_shortcutoff(flowcut)

    def _pack_std_items_periodstuff(self, d, fatal=False):
        """Specialised version of _pack_std_items that deals with begindate/enddate/cutoff pairs."""
        flowbegin = None
        flowend = None
        flowcut = None
        if isinstance(d, (tuple, list)):
            for flowitem in [x for x in d if isinstance(x, dict)]:
                if "begindate" in flowitem:
                    flowbegin = flowitem["begindate"]
                if "enddate" in flowitem:
                    flowend = flowitem["enddate"]
                if "shortcutoff" in flowitem:
                    flowcut = flowitem["shortcutoff"]
        if flowbegin is None or flowend is None:
            if fatal:
                raise VortexNameBuilderError(
                    "A begindate/enddate pair is mandatory here..."
                )
            else:
                return ""
        return "-".join(
            [
                self._pack_std_item_date(flowbegin)
                + self._pack_std_item_shortcutoff(flowcut, default=""),
                self._pack_std_item_date(flowend),
            ]
        )

    # A Vortex basename may include the following bits

    def _pack_std_basename_prefixstuff(self, d):  # @UnusedVariable
        """Adds any info about date, cutoff ..."""
        name0 = d["radical"]
        name0 += self._join_basename_bit(d, "src", prefix=".", sep="-")
        name0 += self._join_basename_bit(d, "filtername", prefix=".", sep="-")
        name0 += self._join_basename_bit(d, "geo", prefix=".", sep="-")
        name0 += self._join_basename_bit(d, "compute", prefix=".", sep="-")
        return name0

    def _pack_std_basename_flowstuff(self, d):  # @UnusedVariable
        """Adds any info about date, cutoff ..."""
        return ""

    def _pack_std_basename_timestuff(self, d):  # @UnusedVariable
        """Adds any info about term, period, ..."""
        name = ""
        if d["term"] is not None:
            name += self._join_basename_bit(
                d,
                "term",
                prefix="+",
                sep=".",
                packcb=self._pack_std_items_negativetimes,
            )
        else:
            if d["period"] is not None:
                name += self._join_basename_bit(
                    d,
                    "period",
                    prefix="+",
                    sep="-",
                    packcb=self._pack_std_items_negativetimes,
                )
            elif d["cen_period"] is not None:
                name += self._join_basename_bit(
                    d,
                    "cen_period",
                    prefix="_",
                    sep="_",
                    packcb=self._pack_std_items_negativetimes,
                )
        return name

    def _pack_std_basename_suffixstuff(self, d):  # @UnusedVariable
        """Adds any info about date, cutoff ..."""
        name1 = ""
        name1 += self._join_basename_bit(d, "number", prefix=".", sep="-")
        name1 += self._join_basename_bit(d, "fmt", prefix=".", sep=".")
        name1 += self._join_basename_bit(d, "suffix", prefix=".", sep=".")
        return name1

    def _join_basename_bit(self, d, entry, prefix=".", sep="-", packcb=None):
        if d[entry] is not None:
            if packcb is None:
                return prefix + sep.join(self._pack_std_items(d[entry]))
            else:
                return prefix + sep.join(packcb(d[entry]))
        else:
            return ""

    # Methods that generates basenames

    def _pack_basename_std(self, d):
        """
        Main entry point to convert a description into a file name
        according to the so-called standard style.
        """
        return (
            self._pack_std_basename_prefixstuff(d).lower()
            + self._pack_std_basename_flowstuff(d)
            + self._pack_std_basename_timestuff(d)
            + self._pack_std_basename_suffixstuff(d).lower()
        )

    # Methods that generates pathnames

    def _pack_pathname_std(self, d):
        """
        Main entry point to convert a description into a path name
        according to the so-called standard style.
        """
        raise NotImplementedError("This is an abstract method !")


class VortexDateNameBuilder(AbstractActualVortexNameBuilder):
    """A Standard Vortex NameBuilder (with date and cutoff)."""

    _footprint = dict(
        info="A Standard Vortex NameBuilder (with date and cutoff)",
        attr=dict(
            name=dict(
                values=[
                    "date@std",
                ],
            ),
        ),
    )

    # A Vortex basename may include the following bits

    def _pack_std_basename_flowstuff(self, d):
        """Adds any info about term and period, ..."""
        name = ""
        if d["flow"] is not None:
            pstuff = self._pack_std_items_periodstuff(d["flow"])
            if pstuff:
                name += "." + pstuff
        return name

    # Methods that generates basenames

    def _pack_basename_obs(self, d):
        """
        Main entry point to convert a description into a file name
        according to the so-called observation style.
        """
        obsfmt = d.get("nativefmt", d.get("fmt", None))
        if obsfmt is None:
            raise VortexNameBuilderError()
        name = ".".join(
            [
                obsfmt + "-" + d.get("layout", "std"),
                "void" if d["stage"] is None else d["stage"],
                "all" if d["part"] is None else d["part"],
            ]
        )
        if d["suffix"] is not None:
            name = name + "." + d["suffix"]

        return name.lower()

    def _pack_basename_obsmap(self, d):
        """
        Main entry point to convert a description into a file name
        according to the so-called observation-map style.
        """
        name = ".".join(
            (
                d["radical"],
                "-".join(self._pack_std_items(d["stage"])),
                "txt" if d["fmt"] is None else d["fmt"],
            )
        )
        return name.lower()

    # Methods that generates pathnames

    def _pack_pathname_std(self, d):
        """
        Main entry point to convert a description into a path name
        according to the so-called standard style.
        """
        pathbits = self._pack_pathname_init(d)
        self._pack_pathname_append_flowdate(pathbits, d)
        self._pack_pathname_append_scenario(pathbits, d)
        self._pack_pathname_append_member(pathbits, d)
        self._pack_pathname_append_block(pathbits, d)
        return pathbits

    _pack_pathname_obs = _pack_pathname_std
    _pack_pathname_obsmap = _pack_pathname_std


class VortexPeriodNameBuilder(AbstractActualVortexNameBuilder):
    """A Standard Vortex NameBuilder (with period and cutoff)."""

    _footprint = dict(
        info="A Standard Vortex NameBuilder (with period and cutoff)",
        attr=dict(
            name=dict(
                values=[
                    "period@std",
                ],
            ),
        ),
    )

    # A Vortex basename may include the following bits

    def _pack_std_basename_flowstuff(self, d):
        name = ""
        if d["flow"] is not None:
            dstuff = self._pack_std_items_datestuff(d["flow"])
            if dstuff:
                name += "." + dstuff
        return name

    # Methods that generates pathnames

    def _pack_pathname_std(self, d):
        """
        Main entry point to convert a description into a file name
        according to the so-called standard style.
        """
        pathbits = self._pack_pathname_init(d)
        self._pack_pathname_append_flowperiod(pathbits, d)
        self._pack_pathname_append_scenario(pathbits, d)
        self._pack_pathname_append_member(pathbits, d)
        self._pack_pathname_append_block(pathbits, d)
        return pathbits


class VortexFlatNameBuilder(AbstractActualVortexNameBuilder):
    """'A Standard Vortex NameBuilder (without date or period)."""

    _footprint = dict(
        info="A Standard Vortex NameBuilder (without date or period)",
        attr=dict(
            name=dict(
                values=[
                    "flat@std",
                ],
            ),
        ),
    )

    # A Vortex basename may include the following bits

    def _pack_std_basename_flowstuff(self, d):
        name = ""
        if d["flow"] is not None:
            dstuff = self._pack_std_items_datestuff(d["flow"])
            if dstuff:
                name += "." + dstuff
            pstuff = self._pack_std_items_periodstuff(d["flow"])
            if pstuff:
                name += "." + pstuff
        return name

    # Methods that generates pathnames

    def _pack_pathname_std(self, d):
        """
        Main entry point to convert a description into a file name
        according to the so-called standard style.
        """
        pathbits = self._pack_pathname_init(d)
        self._pack_pathname_append_scenario(pathbits, d)
        self._pack_pathname_append_member(pathbits, d)
        self._pack_pathname_append_block(pathbits, d)
        return pathbits


class VortexNameBuilder(AbstractVortexNameBuilderProxy):
    _explicit = False
    _footprint = dict(
        info="Standard Vortex NameBuilder Proxy",
        attr=dict(
            name=dict(
                values=[
                    "std",
                ],
                optional=True,
                default="std",
            ),
        ),
    )

    def _pick_actual_builder(self, d):
        """Given the input dictionary, returns the appropriate builder object."""
        actual_builder_name = "flat@std"
        if "flow" in d and isinstance(d["flow"], (tuple, list)):
            flowkeys = set()
            for item in [item for item in d["flow"] if isinstance(item, dict)]:
                flowkeys.update(item.keys())
            if "date" in flowkeys:
                actual_builder_name = "date@std"
            elif "begindate" in flowkeys and "enddate" in flowkeys:
                actual_builder_name = "period@std"
        return self._get_builder(actual_builder_name)
