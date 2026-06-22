"""
TODO: Module documentation.
"""

import collections.abc

from bronx.stdtypes.date import Date, Time
from vortex import sessions
from vortex.data.contents import DataContent, JsonDictContent, FormatAdapter
from vortex.data.flow import FlowResource
from vortex.data.resources import Resource
from vortex.syntax.stdattrs import FmtInt, date_deco, cutoff_deco
from vortex.syntax.stddeco import namebuilding_delete, namebuilding_insert
from vortex.util.roles import setrole

#: No automatic export
__all__ = []


class FlowLogsStack(Resource):
    """Stack of miscellaneous log files"""

    _footprint = [
        date_deco,
        cutoff_deco,
        dict(
            info="Stack of miscellaneous log files.",
            attr=dict(
                kind=dict(values=["flow_logs"]),
                nativefmt=dict(
                    values=[
                        "filespack",
                    ],
                    default="filespack",
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "flow_logs"


def use_flow_logs_stack(cls):
    """Setup the decorated class to work with the FlowLogsStack resource."""
    fpattrs = set(cls.footprint_retrieve().attr.keys())
    fpcheck = all([k in fpattrs for k in ("date", "cutoff")])
    if not fpcheck:
        raise ImportError(
            'The "{!s}" class is not compatible with the FlowLogsStack class.'.format(
                cls
            )
        )

    def stackedstorage_resource(self):
        """Use the FlowLogsStack resource for stacked storage."""
        return FlowLogsStack(
            kind="flow_logs", date=self.date, cutoff=self.cutoff
        ), False

    cls.stackedstorage_resource = stackedstorage_resource
    return cls


@use_flow_logs_stack
@namebuilding_insert(
    "src",
    lambda s: [
        s.binary,
        "-".join(s.task.split("/")[s.task_start : s.task_stop]),
    ],
)
@namebuilding_insert("compute", lambda s: s.part)
@namebuilding_delete("fmt")
class Listing(FlowResource):
    """Miscellaneous application output from a task processing."""

    _footprint = [
        dict(
            info="Listing",
            attr=dict(
                task=dict(optional=True, default="anonymous"),
                task_start=dict(
                    optional=True,
                    type=int,
                    default=-1,
                ),
                task_stop=dict(
                    optional=True,
                    type=int,
                    default=None,
                ),
                kind=dict(values=["listing"]),
                part=dict(
                    optional=True,
                    default="all",
                ),
                binary=dict(
                    optional=True,
                    default="[model]",
                ),
                clscontents=dict(
                    default=FormatAdapter,
                ),
            ),
        )
    ]

    @property
    def realkind(self):
        return "listing"

    def olive_basename(self):
        """Fake basename for getting olive listings"""
        if hasattr(self, "_listingpath"):
            return self._listingpath
        else:
            return "NOT_IMPLEMENTED"

    def archive_basename(self):
        return "listing." + self.part


class ParallelListing(Listing):
    """Multi output for parallel MPI and/or OpenMP processing."""

    _footprint = [
        dict(
            attr=dict(
                kind=dict(
                    values=["listing", "plisting", "mlisting"],
                    remap=dict(
                        listing="plisting",
                        mlisting="plisting",
                    ),
                ),
                mpi=dict(
                    optional=True,
                    default=None,
                    type=FmtInt,
                    args=dict(fmt="03"),
                ),
                openmp=dict(
                    optional=True,
                    default=None,
                    type=FmtInt,
                    args=dict(fmt="02"),
                ),
                seta=dict(
                    optional=True,
                    default=None,
                    type=FmtInt,
                    args=dict(fmt="03"),
                ),
                setb=dict(
                    optional=True,
                    default=None,
                    type=FmtInt,
                    args=dict(fmt="02"),
                ),
            )
        )
    ]

    def namebuilding_info(self):
        """From base information of ``listing`` add mpi and openmp values."""
        info = super().namebuilding_info()
        if self.mpi and self.openmp:
            info["compute"] = [{"mpi": self.mpi}, {"openmp": self.openmp}]
        if self.seta and self.setb:
            info["compute"] = [{"seta": self.seta}, {"setb": self.setb}]
        return info


@namebuilding_insert("src", lambda s: [s.binary, s.task.split("/").pop()])
@namebuilding_insert("compute", lambda s: s.part)
@namebuilding_delete("fmt")
class StaticListing(Resource):
    """Miscelanous application output from a task processing, out-of-flow."""

    _footprint = [
        dict(
            info="Listing",
            attr=dict(
                task=dict(optional=True, default="anonymous"),
                kind=dict(values=["staticlisting"]),
                part=dict(
                    optional=True,
                    default="all",
                ),
                binary=dict(
                    optional=True,
                    default="[model]",
                ),
                clscontents=dict(
                    default=FormatAdapter,
                ),
            ),
        )
    ]

    @property
    def realkind(self):
        return "staticlisting"


@namebuilding_insert(
    "compute",
    lambda s: None
    if s.mpi is None
    else [
        {"mpi": s.mpi},
    ],
    none_discard=True,
)
class DrHookListing(Listing):
    """Output produced by DrHook"""

    _footprint = [
        dict(
            attr=dict(
                kind=dict(
                    values=[
                        "drhook",
                    ],
                ),
                mpi=dict(
                    optional=True,
                    type=FmtInt,
                    args=dict(fmt="03"),
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return "drhookprof"


@use_flow_logs_stack
class Beacon(FlowResource):
    """Output indicating the end of a model run."""

    _footprint = [
        dict(
            info="Beacon",
            attr=dict(
                kind=dict(values=["beacon"]),
                clscontents=dict(
                    default=JsonDictContent,
                ),
                nativefmt=dict(
                    default="json",
                ),
            ),
        )
    ]

    @property
    def realkind(self):
        return "beacon"


@use_flow_logs_stack
@namebuilding_insert("src", lambda s: s.task.split("/").pop())
@namebuilding_insert("compute", lambda s: s.scope)
class TaskInfo(FlowResource):
    """Task informations."""

    _footprint = [
        dict(
            info="Task informations",
            attr=dict(
                task=dict(optional=True, default="anonymous"),
                kind=dict(values=["taskinfo"]),
                scope=dict(
                    optional=True,
                    default="void",
                ),
                clscontents=dict(
                    default=JsonDictContent,
                ),
                nativefmt=dict(
                    default="json",
                ),
            ),
        )
    ]

    @property
    def realkind(self):
        return "taskinfo"


@namebuilding_insert("src", lambda s: s.task.split("/").pop())
@namebuilding_insert("compute", lambda s: s.scope)
@namebuilding_delete("fmt")
class StaticTaskInfo(Resource):
    """Task informations."""

    _footprint = [
        dict(
            info="Task informations",
            attr=dict(
                task=dict(optional=True, default="anonymous"),
                kind=dict(values=["statictaskinfo"]),
                scope=dict(
                    optional=True,
                    default="void",
                ),
                clscontents=dict(
                    default=JsonDictContent,
                ),
                nativefmt=dict(
                    default="json",
                ),
            ),
        )
    ]

    @property
    def realkind(self):
        return "statictaskinfo"


class SectionsSlice(collections.abc.Sequence):
    """Hold a list of dictionaries representing Sections."""

    _INDEX_PREFIX = "sslice"
    _INDEX_ATTR = "sliceindex"

    def __init__(self, sequence):
        self._data = sequence

    def __getitem__(self, i):
        if isinstance(i, str) and i.startswith(self._INDEX_PREFIX):
            i = int(i[len(self._INDEX_PREFIX) :])
        return self._data[i]

    def __eq__(self, other):
        return self.to_list() == other.to_list()

    def __len__(self):
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def to_list(self):
        """Returns a list object with the exact same content."""
        return list(self._data)

    @staticmethod
    def _sloppy_lookup(item, k):
        """Look for a key *k* in the *item* dictionary and returns it.

        :note: A special treatment is made for the 'role' key (the role factory is used
        and the 'alternate' attribute may also be looked for).

        :note: A special case is made for the attribute 'kind' of the section which can be
        accessed via the 'section_kind' attribute (the attribute 'kind' is used for the resource attribute).

        :note: if *k* is not found at the top level of the dictionary, the
        'resource', 'provider' and 'container' parts of the 'rh'sub-dictionary
        are also looked for.
        """
        if k == "role":
            return item[k] or item["alternate"]
        elif k == "kind" and k in item.get("rh", dict()).get(
            "resource", dict()
        ):
            return item["rh"]["resource"][k]
        elif k == "section_kind" and "kind" in item:
            return item["kind"]
        elif k in item:
            return item[k]
        elif k in item.get("rh", dict()).get("resource", dict()):
            return item["rh"]["resource"][k]
        elif k in item.get("rh", dict()).get("provider", dict()):
            return item["rh"]["provider"][k]
        elif k in item.get("rh", dict()).get("container", dict()):
            return item["rh"]["container"][k]
        else:
            raise KeyError(
                "'{:s}' wasn't found in the designated dictionary".format(k)
            )

    @staticmethod
    def _sloppy_compare(json_v, v):
        """Try a very very permissive check."""
        if callable(v):
            try:
                return v(json_v)
            except (ValueError, TypeError):
                return False
        else:
            try:
                return type(v)(json_v) == v
            except (ValueError, TypeError):
                try:
                    return json_v == v
                except (ValueError, TypeError):
                    return False

    def _sloppy_ckeck(self, item, k, v, extras):
        """Perform a _sloppy_lookup and check the result against *v*."""
        if k in ("role", "alternate"):
            v = setrole(v)
        try:
            if k == "baseterm":
                found = self._sloppy_lookup(item, "term")
                foundbis = self._sloppy_lookup(item, "date")
            else:
                found = self._sloppy_lookup(item, k)
        except KeyError:
            return False
        if not isinstance(v, (list, tuple, set)):
            v = [
                v,
            ]
        if k == "baseterm" and extras.get("basedate", None):
            delta = Date(extras["basedate"]) - Date(foundbis)
            found = Time(found) - delta
        return any([self._sloppy_compare(found, a_v) for a_v in v])

    def filter(self, **kwargs):
        """Create a new :class:`SectionsSlice` object that will be filtered using *kwargs*.

        :example: To retrieve sections with ``role=='Guess'`` and ``rh.provider.member==1``::

            >>> self.filter(role='Guess', member=1)
        """
        extras = dict()
        extras["basedate"] = kwargs.pop("basedate", None)
        newslice = [
            s
            for s in self
            if all(
                [
                    self._sloppy_ckeck(s, k, v, extras)
                    for k, v in kwargs.items()
                ]
            )
        ]
        return self.__class__(newslice)

    def uniquefilter(self, **kwargs):
        """Like :meth:`filter` but checks that only one element matches."""
        newslice = self.filter(**kwargs)
        if len(newslice) == 0:
            raise ValueError("No section was found")
        elif len(newslice) > 1:
            raise ValueError("Multiple sections were found")
        else:
            return newslice

    @property
    def indexes(self):
        """Returns an index list of all the element contained if the present object."""
        return [
            self._INDEX_PREFIX + "{:d}".format(i) for i in range(len(self))
        ]

    def __deepcopy__(self, memo):
        newslice = self.__class__(self._data)
        memo[id(self)] = newslice
        return newslice

    def __getattr__(self, attr):
        """Provides an easy access to content's data with footprint's mechanisms.*

        If the present :class:`SectionsSlice` only contains one element, a
        :meth:`_sloppy_lookup` is performed on this unique element and returned.
        For exemple ``self.vapp`` will be equivalent to
        ``self[0]['rh']['provider']['vapp']``.

        If the present :class:`SectionsSlice` contains several elements, it's more
        complex : a callback function is returned. Such a callback can be used
        in conjunction with footprint's replacement mechanism. Provided that a
        ``{idx_attr:s}`` attribute exists in the footprint description and
        can be used as an index in the present object (such a list of indexes can
        be generated using the :meth:`indexes` property), the corresponding element
        will be searched using :meth:`_sloppy_lookup`.
        """.format(idx_attr=self._INDEX_ATTR)
        if attr.startswith("__"):
            raise AttributeError(attr)
        if len(self) == 1:
            try:
                return self._sloppy_lookup(self[0], attr)
            except KeyError:
                raise AttributeError(
                    "'{:s}' wasn't found in the unique dictionary".format(attr)
                )
        elif len(self) == 0:
            raise AttributeError(
                "The current SectionsSlice is empty. No attribute lookup allowed !"
            )
        else:

            def _attr_lookup(g, x):
                if len(self) > 1 and (
                    self._INDEX_ATTR in g or self._INDEX_ATTR in x
                ):
                    idx = g.get(self._INDEX_ATTR, x.get(self._INDEX_ATTR))
                    try:
                        return self._sloppy_lookup(self[idx], attr)
                    except KeyError:
                        raise AttributeError(
                            "'{:s}' wasn't found in the {!s}-th dictionary".format(
                                attr, idx
                            )
                        )
                else:
                    raise AttributeError(
                        "A '{:s}' attribute must be there !".format(
                            self._INDEX_ATTR
                        )
                    )

            return _attr_lookup


class SectionsJsonListContent(DataContent):
    """Load/Dump a JSON file that contains a list of Sections.

    The conents of the JSON file is then stored in a query-able
    :class:`SectionsSlice` object.
    """

    def slurp(self, container):
        """Get data from the ``container``."""
        t = sessions.current()
        with container.preferred_decoding(byte=False):
            container.rewind()
            self._data = SectionsSlice(t.sh.json_load(container.iotarget()))
        self._size = len(self._data)

    def rewrite(self, container):
        """Write the data in the specified container."""
        t = sessions.current()
        container.close()
        with container.iod_context():
            with container.preferred_decoding(byte=False):
                with container.preferred_write():
                    iod = container.iodesc()
                    t.sh.json_dump(self.data.to_list(), iod, indent=4)
        container.updfill(True)


@use_flow_logs_stack
@namebuilding_insert("src", lambda s: s.task.split("/").pop())
class SectionsList(FlowResource):
    """Class to handle a resource that contains a list of Sections in JSON format.

    Such a resource can be generated using the :class:`FunctionStore` with the
    :func:`vortex.util.storefunctions.dumpinputs` function.
    """

    _footprint = dict(
        info="A Sections List",
        attr=dict(
            kind=dict(
                values=[
                    "sectionslist",
                ],
            ),
            task=dict(optional=True, default="anonymous"),
            clscontents=dict(
                default=SectionsJsonListContent,
            ),
            nativefmt=dict(
                values=[
                    "json",
                ],
                default="json",
            ),
        ),
    )

    @property
    def realkind(self):
        return "sectionslist"
