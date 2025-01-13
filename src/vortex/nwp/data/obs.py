"""
Resources to handle observations files in various formats.
"""

import re
from collections import namedtuple


import footprints
from bronx.datagrip.varbcheaders import VarbcHeadersFile
from bronx.fancies import loggers
from bronx.syntax.decorators import nicedeco

from vortex.data.flow import GeoFlowResource, FlowResource
from vortex.data.contents import TextContent, AlmostListContent
from vortex.syntax import stdattrs, stddeco

from ..syntax.stdattrs import gvar, GenvKey

#: Automatic export of Observations class
__all__ = [
    "Observations",
]

logger = loggers.getLogger(__name__)


@stddeco.namebuilding_insert("style", lambda s: "obs")
@stddeco.namebuilding_insert("stage", lambda s: s.stage)
@stddeco.namebuilding_insert("part", lambda s: s.part)
class Observations(GeoFlowResource):
    """
    Abstract observation resource.
    """

    _abstract = True
    _footprint = dict(
        info="Observations file",
        attr=dict(
            kind=dict(
                values=["observations", "obs"],
                remap=dict(obs="observations"),
            ),
            part=dict(info="The name of this subset of observations."),
            nativefmt=dict(
                alias=("format",),
            ),
            stage=dict(
                info="The processing stage for this subset of observations."
            ),
        ),
    )

    @property
    def realkind(self):
        return "observations"


class ObsProcessed(Observations):
    """Pre-Processed or Processed observations."""

    _footprint = dict(
        info="Pre-Processed observations.",
        attr=dict(
            nativefmt=dict(
                values=["ascii", "netcdf", "hdf5"],
            ),
            stage=dict(
                values=[
                    "preprocessing",
                ],
            ),
        ),
    )


@stddeco.namebuilding_insert("layout", lambda s: s.layout)
class ObsODB(Observations):
    """Observations in ODB format associated to a given stage."""

    _footprint = dict(
        info="Packed observations (ODB, CCMA, etc.)",
        attr=dict(
            nativefmt=dict(
                values=["odb", "odb/split", "odb/compressed"],
                remap={"odb/split": "odb", "odb/compressed": "odb"},
            ),
            layout=dict(
                info="The layout of the ODB database.",
                optional=True,
                default="ecma",
                values=[
                    "ccma",
                    "ecma",
                    "ecmascr",
                    "CCMA",
                    "ECMA",
                    "ECMASCR",
                    "rstbias",
                    "countryrstrhbias",
                    "sondetyperstrhbias",
                    "RSTBIAS",
                    "COUNTRYRSTRHBIAS",
                    "SONDETYPERSTRHBIAS",
                ],
                remap=dict(
                    CCMA="ccma",
                    ECMA="ecma",
                    ECMASCR="ecmascr",
                    RSTBIAS="rstbias",
                    COUNTRYRSTRHBIAS="countryrstrhbias",
                    SONDETYPERSTRHBIAS="sondetyperstrhbias",
                ),
            ),
            stage=dict(
                values=[
                    "void",
                    "avg",
                    "average",
                    "screen",
                    "screening",
                    "split",
                    "build",
                    "traj",
                    "min",
                    "minim",
                    "complete",
                    "matchup",
                    "canari",
                    "cans",
                ],
                remap=dict(
                    avg="average",
                    min="minim",
                    cans="canari",
                    split="build",
                    screen="screening",
                ),
            ),
        ),
    )

    def olive_basename(self):
        """OLIVE specific naming convention."""
        stage_map = dict(
            screening="screen", build="split", minim="min", canari="cans"
        )
        mystage = stage_map.get(self.stage, self.stage)
        return "_".join((self.layout, mystage, self.part)) + ".tar"

    @property
    def _archive_mapping(self):
        re_fullmix = re.compile(r"^(?:altitude|mix|full)$")
        ecma_map = dict(
            void="ecmascr.tar",
            screening="odb_screen.tar",
            matchup="odb_cpl.tar",
            complete="odb_cpl.tar",
        )
        ecma_prefix = {
            ("matchup", "arpege"): "BASE/",
            ("complete", "arpege"): "BASE/",
            ("matchup", "arome"): "BASE/",
            ("complete", "arome"): "BASE/",
            ("screening", "arome"): "./",
        }
        if self.stage in ecma_map and self.layout == "ecma":
            if re_fullmix.match(self.part):
                return (ecma_map[self.stage], "extract=all&format=unknown")
            elif self.part == "virtual":
                return (
                    ecma_map[self.stage],
                    "extract={:s}ECMA&format=unknown".format(
                        ecma_prefix.get((self.stage, self.model), "")
                    ),
                )
            else:
                return (
                    ecma_map[self.stage],
                    "extract={:s}ECMA.{:s}&format=unknown".format(
                        ecma_prefix.get((self.stage, self.model), ""),
                        self.part,
                    ),
                )
        elif self.stage == "screening" and self.layout == "ccma":
            return ("odb_ccma_screen.tar", "")
        elif re_fullmix.match(self.part) and self.stage == "traj":
            return ("odb_traj.tar", "")
        elif (
            re_fullmix.match(self.part)
            and self.stage == "minim"
            and self.model == "aladin"
        ):
            return ("odb_cpl.tar", "")
        elif re_fullmix.match(self.part) and self.stage == "minim":
            return ("odb_min.tar", "")
        elif self.part in ("ground", "surf") and self.stage in (
            "canari",
            "surfan",
        ):
            return ("odb_canari.tar", "")
        else:
            logger.error(
                "No archive basename defined for such observations (format=%s, part=%s, stage=%s)",
                self.nativefmt,
                self.part,
                self.stage,
            )
            return (None, None)

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return self._archive_mapping[0]

    def archive_urlquery(self):
        """OP ARCHIVE special query for odb case."""
        return self._archive_mapping[1]


class ObsRaw(Observations):
    """
    TODO.
    """

    _footprint = dict(
        info="Raw observations set",
        attr=dict(
            nativefmt=dict(
                values=["obsoul", "grib", "bufr", "ascii", "netcdf", "hdf5"],
                remap=dict(
                    OBSOUL="obsoul",
                    GRIB="grib",
                    BUFR="bufr",
                    ASCII="ascii",
                    NETCDF="netcdf",
                    HDF5="hdf5",
                ),
            ),
            stage=dict(values=["void", "extract", "raw", "std"]),
            olivefmt=dict(
                info="The mapping between Vortex and Olive formats names.",
                type=footprints.FPDict,
                optional=True,
                default=footprints.FPDict(
                    ascii="ascii",
                    obsoul="obsoul",
                    grib="obsgrib",
                    bufr="obsbufr",
                    netcdf="netcdf",
                    hdf5="hdf5",
                ),
                doc_visibility=footprints.doc.visibility.GURU,
            ),
        ),
    )

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return "_".join(
            (
                self.olivefmt.get(self.nativefmt, "obsfoo"),
                self.stage,
                self.part,
            )
        )

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        if (
            re.match(r"^(?:bufr|obsoul|grib|netcdf|hdf5)$", self.nativefmt)
            and self.part != "full"
            and self.stage == "void"
        ):
            return ".".join((self.nativefmt, self.part))
        elif (
            re.match(r"^obsoul$", self.nativefmt)
            and self.part == "full"
            and self.stage == "void"
        ):
            return "obsoul"
        else:
            logger.error(
                "No archive basename defined for such observations (format=%s, part=%s, stage=%s)",
                self.nativefmt,
                self.part,
                self.stage,
            )


@stddeco.namebuilding_insert("radical", lambda s: s.kind)
@stddeco.namebuilding_insert(
    "src",
    lambda s: [
        s.part,
    ],
)
class ObsFlags(FlowResource):
    """Class for observations flags."""

    _footprint = dict(
        info="Observations flags",
        attr=dict(
            kind=dict(
                values=["obsflag"],
            ),
            nativefmt=dict(
                values=["ascii", "txt"],
                default="txt",
                remap=dict(ascii="txt"),
            ),
            part=dict(),
        ),
    )

    @property
    def realkind(self):
        return "obsflags"

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return "BDM_CQ"


@nicedeco
def needs_slurp(mtd):
    """Call _actual_slurp before anything happens."""

    def new_stuff(self):
        if self._do_delayed_slurp is not None:
            with self._do_delayed_slurp.iod_context():
                self._actual_slurp(self._do_delayed_slurp)
        return mtd(self)

    return new_stuff


class VarBCContent(AlmostListContent):
    # The VarBC file is too big: revert to the good old diff
    _diffable = False

    def __init__(self, **kw):
        super().__init__(**kw)
        self._parsed_data = None
        self._do_delayed_slurp = None

    @property
    @needs_slurp
    def data(self):
        """The internal data encapsulated."""
        return self._data

    @property
    @needs_slurp
    def size(self):
        """The internal data size."""
        return self._size

    @property
    def parsed_data(self):
        """The data as a :class:`VarbcFile` object."""
        if self._parsed_data is None:
            # May fail if Numpy is not installed...
            from bronx.datagrip.varbc import VarbcFile

            self._parsed_data = VarbcFile(self.data)
        return self._parsed_data

    def _actual_slurp(self, container):
        with container.preferred_decoding(byte=False):
            self._size = container.totalsize
            self._data.extend(container.readlines())
        self._do_delayed_slurp = None

    def slurp(self, container):
        """Get data from the ``container``."""
        self._do_delayed_slurp = container
        with container.preferred_decoding(byte=False):
            container.rewind()
            self._metadata = VarbcHeadersFile(
                [container.readline() for _ in range(3)]
            )


@stddeco.namebuilding_append(
    "src",
    lambda s: [
        s.stage,
    ],
)
class VarBC(FlowResource):
    """
    VarBC file resource. Contains all the coefficients for the VarBC bias correction scheme.
    """

    _footprint = dict(
        info="Varbc file (coefficients for the bias correction of observations).",
        attr=dict(
            kind=dict(values=["varbc"]),
            clscontents=dict(
                default=VarBCContent,
            ),
            nativefmt=dict(
                values=["ascii", "txt"],
                default="txt",
                remap=dict(ascii="txt"),
            ),
            stage=dict(
                optional=True,
                values=[
                    "void",
                    "merge",
                    "screen",
                    "screening",
                    "minim",
                    "traj",
                ],
                remap=dict(screen="screening"),
                default="void",
            ),
            mixmodel=dict(
                optional=True,
                default=None,
                values=stdattrs.models,
            ),
        ),
    )

    @property
    def realkind(self):
        return "varbc"

    def olive_basename(self):
        """OLIVE specific naming convention."""
        olivestage_map = {
            "screening": "screen",
        }
        return (
            self.realkind.upper()
            + "."
            + olivestage_map.get(self.stage, self.stage)
        )

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        if self.stage in ("void", "traj"):
            bname = "VARBC.cycle"
            if self.mixmodel is not None:
                bname += "_"
                if self.mixmodel.startswith("alad"):
                    bname = bname + self.mixmodel[:4]
                else:
                    bname = bname + self.mixmodel[:3]
        else:
            bname = "VARBC." + self.stage
        return bname


@stddeco.namebuilding_insert("src", lambda s: s.scope)
class BlackList(FlowResource):
    """
    TODO.
    """

    _footprint = [
        gvar,
        dict(
            info="Blacklist file for observations",
            attr=dict(
                kind=dict(
                    values=["blacklist"],
                ),
                gvar=dict(
                    default="blacklist_[scope]",
                    values=[
                        "BLACKLIST_LOC",
                        "BLACKLIST_DIAP",
                        "BLACKLIST_LOCAL",
                        "BLACKLIST_GLOBAL",
                    ],
                    remap=dict(
                        BLACKLIST_LOCAL="BLACKLIST_LOC",
                        BLACKLIST_GLOBAL="BLACKLIST_DIAP",
                        blacklist_local="BLACKLIST_LOC",
                        blacklist_global="BLACKLIST_DIAP",
                    ),
                ),
                clscontents=dict(
                    default=TextContent,
                ),
                nativefmt=dict(values=["txt"], default="txt"),
                scope=dict(
                    values=[
                        "loc",
                        "local",
                        "site",
                        "global",
                        "diap",
                        "diapason",
                    ],
                    remap=dict(
                        loc="local",
                        site="local",
                        diap="global",
                        diapason="global",
                    ),
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "blacklist"

    def iga_pathinfo(self):
        """Standard path information for IGA inline cache."""
        return dict(model=self.model)

    def archive_map(self):
        """OP ARCHIVE specific naming convention."""
        return {
            "local": "LISTE_LOC",
            "global": "LISTE_NOIRE_DIAP",
        }

    def archive_basename(self):
        """OP ARCHIVE local basename."""
        mapd = self.archive_map()
        return mapd.get(self.scope, "LISTE_NOIRE_X")


#: A namedtuple of the internal fields of an ObsRef file
ObsRefItem = namedtuple("ObsRefItem", ("data", "fmt", "instr", "date", "time"))


class ObsRefContent(TextContent):
    """Content class for refdata resources."""

    def append(self, item):
        """Append the specified ``item`` to internal data contents."""
        self.data.append(ObsRefItem(*item))

    def slurp(self, container):
        with container.preferred_decoding(byte=False):
            self._data.extend(
                [
                    ObsRefItem(*x.split()[:5])
                    for x in container
                    if not x.startswith("#")
                ]
            )
            self._size = container.totalsize

    @classmethod
    def formatted_data(self, item):
        """Return a formatted string."""
        return "{:8s} {:8s} {:16s} {:s} {!s}".format(
            item.data, item.fmt, item.instr, str(item.date), item.time
        )


@stddeco.namebuilding_append(
    "src",
    lambda s: [
        s.part,
    ],
)
class Refdata(FlowResource):
    """
    TODO.
    """

    _footprint = dict(
        info="Refdata file",
        attr=dict(
            kind=dict(values=["refdata"]),
            clscontents=dict(
                default=ObsRefContent,
            ),
            nativefmt=dict(
                values=["ascii", "txt"], default="txt", remap=dict(ascii="txt")
            ),
            part=dict(optional=True, default="all"),
        ),
    )

    @property
    def realkind(self):
        return "refdata"

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return self.realkind + "." + self.part

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return self.realkind


#: A namedtuple of the internal fields of an ObsMap file
ObsMapItem = namedtuple("ObsMapItem", ("odb", "data", "fmt", "instr"))


class ObsMapContent(TextContent):
    """Content class for the *ObsMap* resources.

    The :class:`ObsMap` resource provides its *discard* and *only* attributes.
    This attribute is a :class:`footprints.stdtypes.FPSet` object thats holds
    *odb:data* pairs that will be used to filter/discard some of the lines of
    the local resource. The matching is done using regular expressions (however
    when *:data* is omitted, ':' is automatically added at the end of the regular
    expression).

    The *only* attribute is evaluated first (if *only* is not provided or equals
    *None*, all ObsMap lines are retained).

    Here are some examples:

    * ``discard=FPSet(('sev',))`` -> The *sev* ODB database will be discarded
      (but the *seviri* database is kept).
    * ``discard=FPSet(('radar', 'radar1'))`` -> Both the *radar* and *radar1*
      ODB databases will be discarded.
    * ``discard=FPSet(('radar1?', ))`` -> Same result as above.
    * ``discard=FPSet(('conv:temp', ))`` -> Discard the *temp* data file that
      would usualy be inserted in the *conv* database.
    * ``discard=FPSet(('conv:temp', ))`` -> Discard the *temp* data file that
      would usualy be inserted in the *conv* database.
    * ``discard=FPSet(('conv:t[ea]', ))`` -> Discard the data file starting
      with *te* or *ta* that would usualy be inserted in the *conv* database.
    * ``only=FPSet(('conv',))`` -> Only *conv* ODB database will be used.
    """

    def __init__(self, **kw):
        kw.setdefault("discarded", set())
        kw.setdefault("only", None)
        super().__init__(**kw)

    @property
    def discarded(self):
        """Set of *odb:data* pairs that will be discarded."""
        return self._discarded

    @property
    def only(self):
        """Set of *odb:data* pairs that will be kept (*None* means "keep everything")."""
        return self._only

    def append(self, item):
        """Append the specified ``item`` to internal data contents."""
        self._data.append(ObsMapItem(*item))

    def slurp(self, container):
        """Get data from the ``container``."""
        if self.only is not None:
            ofilters = [
                re.compile(d if ":" in d else d + ":") for d in self.only
            ]
        else:
            ofilters = None
        dfilters = [
            re.compile(d if ":" in d else d + ":") for d in self.discarded
        ]

        def item_filter(omline):
            om = ":".join([omline.odb, omline.data])
            return (
                ofilters is None or any([f.match(om) for f in ofilters])
            ) and not any([f.match(om) for f in dfilters])

        with container.preferred_decoding(byte=False):
            container.rewind()
            self.extend(
                filter(
                    item_filter,
                    [
                        ObsMapItem(*x.split())
                        for x in [line.strip() for line in container]
                        if x and not x.startswith("#")
                    ],
                )
            )
            self._size = container.totalsize

    @classmethod
    def formatted_data(self, item):
        """Return a formatted string."""
        return "{:12s} {:12s} {:12s} {:s}".format(
            item.odb, item.data, item.fmt, item.instr
        )

    def odbset(self):
        """Return set of odb values."""
        return {x.odb for x in self}

    def dataset(self):
        """Return set of data values."""
        return {x.data for x in self}

    def fmtset(self):
        """Return set of format values."""
        return {x.fmt for x in self}

    def instrset(self):
        """Return set of instrument values."""
        return {x.instr for x in self}

    def datafmt(self, data):
        """Return format associated to specified ``data``."""
        dfmt = [x.fmt for x in self if x.data == data]
        try:
            return dfmt[0]
        except IndexError:
            logger.warning('Data "%s" not found in ObsMap contents', data)

    def getfmt(self, g, x):
        """
        Return format ``part`` of data defined in ``g`` or ``x``.
          * ``g`` stands for a guess dictionary.
          * ``x`` stands for an extra dictionary.

        These naming convention refer to the footprints resolve mechanism.
        """
        part = g.get("part", x.get("part", None))
        if part is None:
            return None
        else:
            return self.datafmt(part)


@stddeco.namebuilding_insert("style", lambda s: "obsmap")
@stddeco.namebuilding_insert("stage", lambda s: [s.scope, s.stage])
class ObsMap(FlowResource):
    """Observation mapping.

    Simple ascii table for the description of the mapping of
    observations set to ODB bases. The native format is :
    odb / data / fmt / instr.

    The *discard* attribute is passed directly to the :class:`ObsMapContent`
    object in charge of accessing this resource: It is used to discard some
    of the lines of the *ObsMap* file (for more details see the
    :class:`ObsMapContent` class documentation)
    """

    _footprint = [
        gvar,
        dict(
            info="Bator mapping file",
            attr=dict(
                kind=dict(
                    values=["obsmap"],
                ),
                clscontents=dict(
                    default=ObsMapContent,
                ),
                nativefmt=dict(
                    values=["ascii", "txt"],
                    default="txt",
                    remap=dict(ascii="txt"),
                ),
                stage=dict(optional=True, default="void"),
                scope=dict(
                    optional=True,
                    default="full",
                    remap=dict(surf="surface"),
                ),
                discard=dict(
                    info="Discard some lines of the mapping (see the class documentation).",
                    type=footprints.FPSet,
                    optional=True,
                    default=footprints.FPSet(),
                ),
                only=dict(
                    info="Only retain some lines of the mapping (see the class documentation).",
                    type=footprints.FPSet,
                    optional=True,
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "obsmap"

    def contents_args(self):
        """Returns default arguments value to class content constructor."""
        return dict(discarded=set(self.discard), only=self.only)

    def olive_basename(self):
        """OLIVE specific naming convention."""
        return "OBSMAP_" + self.stage

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        if self.scope.startswith("surf"):
            return "BATOR_MAP_" + self.scope[:4].lower()
        else:
            return "BATOR_MAP"

    def genv_basename(self):
        """Genv key naming convention."""
        cutoff_map = {"production": "prod"}
        if self.gvar is None:
            if self.scope == "surface":
                gkey = "bator_map_surf"
            else:
                gkey = "bator_map_" + cutoff_map.get(self.cutoff, self.cutoff)
            return GenvKey(gkey)
        else:
            return self.gvar


@stddeco.namebuilding_insert("src", lambda s: s.satbias)
class Bcor(FlowResource):
    """Bias correction parameters."""

    _footprint = dict(
        info="Bias correction parameters",
        attr=dict(
            kind=dict(
                values=["bcor"],
            ),
            nativefmt=dict(
                values=["ascii", "txt"], default="txt", remap=dict(ascii="txt")
            ),
            satbias=dict(
                values=["mtop", "metop", "noaa", "ssmi"],
                remap=dict(metop="mtop"),
            ),
        ),
    )

    @property
    def realkind(self):
        return "bcor"

    def archive_basename(self):
        """OP ARCHIVE specific naming convention."""
        return "bcor_" + self.satbias + ".dat"
