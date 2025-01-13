"""
Generic Resources and Contents to work with namelists.
"""

import re

from bronx.fancies import loggers
from bronx.stdtypes.date import Time, Date
from bronx.datagrip.namelist import NO_SORTING, NamelistSet, NamelistParser
from footprints.stdtypes import FPList
from vortex import sessions
from vortex.data.outflow import ModelResource, StaticResource
from vortex.data.outflow import ModelGeoResource
from vortex.data.contents import AlmostDictContent, IndexedTable
from vortex.syntax.stdattrs import binaries, term, cutoff
from vortex.syntax.stddeco import namebuilding_insert
from vortex.tools import env
from ..syntax.stdattrs import gvar

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)

KNOWN_NAMELIST_MACROS = {
    "NPROC",
    "NBPROC",
    "NBPROC_IO",
    "NCPROC",
    "NDPROC",
    "NBPROCIN",
    "NBPROCOUT",
    "IDAT",
    "CEXP",
    "TIMESTEP",
    "FCSTOP",
    "NMODVAL",
    "NBE",
    "SEED",
    "MEMBER",
    "NUMOD",
    "OUTPUTID",
    "NRESX",
    "PERTURB",
    "JOUR",
    "RES",
    "LLADAJ",
    "LLADMON",
    "LLFLAG",
    "LLARO",
    "LLVRP",
    "LLCAN",
}


class NamelistPack(ModelResource):
    """
    Class for all kinds of namelists
    """

    _footprint = [
        gvar,
        dict(
            info="A whole Namelist pack",
            attr=dict(
                kind=dict(values=["namelistpack"]),
                gvar=dict(
                    values=["NAMELIST_" + x.upper() for x in binaries],
                    default="namelist_[binary]",
                ),
                model=dict(
                    optional=True,
                ),
                binary=dict(
                    optional=True,
                    values=binaries,
                    default="[model]",
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "namelistpack"

    def gget_urlquery(self):
        """GGET specific query : ``dir_extract``."""
        return "dir_extract=1"


class NamelistContentError(ValueError):
    pass


class NamelistContent(AlmostDictContent):
    """Fortran namelist including namelist blocks."""

    def __init__(self, **kw):
        """
        Initialize default namelist content with optional parameters:
          * macros : pre-defined macros for all namelist blocks
          * remove : elements to remove from the contents
          * parser : a namelist parser object (a default one will be built otherwise)
        """
        kw.setdefault("macros", {k: None for k in KNOWN_NAMELIST_MACROS})
        kw.setdefault("remove", set())
        kw.setdefault("parser", None)
        kw.setdefault("data", NamelistSet())
        super().__init__(**kw)
        self._declaredmacros = set(self._macros.keys())

    def toremove(self, bname):
        """Add an entry to the list of blocks to be removed."""
        self._remove.add(bname)

    def rmblocks(self):
        """Returns the list of blocks to get rid off."""
        return self._remove

    def macros(self):
        """Returns the dictionary of macros already registered."""
        return self._macros.copy()

    def setmacro(self, item, value):
        """Set macro value for further substitution."""
        self._data.setmacro(item, value)
        self._macros[item] = value

    @property
    def dumps_needs_update(self):
        """Tells wether something as changed in the namelist's dump."""
        return self._data.dumps_needs_update

    def dumps(self, sorting=NO_SORTING):
        """
        Returns the namelist contents as a string.
        Sorting option **sorting** (from bronx.datagrip.namelist):

            * NO_SORTING;
            * FIRST_ORDER_SORTING => sort all keys within blocks;
            * SECOND_ORDER_SORTING => sort only within indexes or attributes of the same key.

        """
        return self._data.dumps(sorting=sorting)

    def merge(self, delta, rmkeys=None, rmblocks=None, clblocks=None):
        """Merge of the current namelist content with the set of namelist blocks provided."""
        if isinstance(delta, NamelistContent):
            if rmblocks is None and hasattr(delta, "rmblocks"):
                rmblocks = delta.rmblocks()
            actualdelta = delta.data
        else:
            actualdelta = delta
        self._data.merge(
            actualdelta, rmkeys=rmkeys, rmblocks=rmblocks, clblocks=clblocks
        )

    def slurp(self, container):
        """Get data from the ``container`` namelist."""
        if not self._parser:
            self._parser = NamelistParser(macros=self._declaredmacros)
        with container.preferred_decoding(byte=False):
            container.rewind()
            try:
                namset = self._parser.parse(container.read())
            except (ValueError, OSError) as e:
                raise NamelistContentError(
                    "Could not parse container contents: {!s}".format(e)
                )
        self._data = namset
        for macro, value in self._macros.items():
            self._data.setmacro(macro, value)

    def rewrite(self, container, sorting=NO_SORTING):
        """
        Write the namelist contents in the specified container.
        Sorting option **sorting** (from bronx.datagrip.namelist):

            * NO_SORTING;
            * FIRST_ORDER_SORTING => sort all keys within blocks;
            * SECOND_ORDER_SORTING => sort only within indexes or attributes of the same key.

        """
        container.close()
        with container.iod_context():
            with container.preferred_decoding(byte=False):
                container.write(self.dumps(sorting=sorting))


class Namelist(ModelResource):
    """
    Class for all kinds of namelists
    """

    _footprint = [
        gvar,
        dict(
            info="Namelist from binary pack",
            attr=dict(
                kind=dict(values=["namelist"]),
                clscontents=dict(default=NamelistContent),
                gvar=dict(
                    values=["NAMELIST_" + x.upper() for x in binaries],
                    default="namelist_[binary]",
                ),
                source=dict(
                    info="The namelist name within the namelist pack.",
                    optional=True,
                    default="namel_[binary]",
                    doc_zorder=50,
                ),
                model=dict(
                    optional=True,
                ),
                binary=dict(
                    optional=True,
                    values=binaries,
                    default="[model]",
                ),
                date=dict(
                    type=Date,
                    optional=True,
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "namelist"

    def _find_source(self):
        sources = self.source.split("|")
        if len(sources) == 1:
            source = sources[0].split(":")[0]
        else:
            # Check that the date argument was provided.:
            if self.date is None:
                raise AttributeError(
                    "The date argument should be provided when dealing "
                    + "with time based namelist sources."
                )
            datedSource = {}
            for s in sources:
                dateNsource = s.split(":")
                if dateNsource[0]:
                    if len(dateNsource) == 2:
                        date = Date(dateNsource[1], year=self.date.year)
                    else:
                        date = Date(self.date.year, 1, 1)
                    if date not in datedSource.keys():
                        datedSource[date] = dateNsource[0]
                    else:
                        logger.warning(
                            "%s already begins the %s, %s is ignored.",
                            datedSource[date],
                            date.strftime("%d of %b."),
                            dateNsource[0],
                        )
            datedSource = sorted(datedSource.items(), reverse=True)
            source = datedSource[0][1]
            for dateNsource in datedSource:
                if self.date >= dateNsource[0]:
                    source = dateNsource[1]
                    break
            logger.info("The consistent source is %s", source)

        return source

    def gget_urlquery(self):
        """GGET specific query : ``extract``."""
        return "extract=" + self._find_source()


class NamelistDelta(Namelist):
    """
    Class for namelist deltas (i.e. small bits of namelists).
    """

    _footprint = dict(
        attr=dict(
            kind=dict(
                values=[
                    "namdelta",
                    "deltanam",
                ]
            ),
            source=dict(
                default="deltanam.[binary]",
            ),
        )
    )

    @property
    def realkind(self):
        return "namdelta"


class NamelistUtil(Namelist):
    """
    Class for namelists utilities
    """

    _footprint = dict(
        info="Namelist from utilities pack",
        attr=dict(
            kind=dict(
                values=["namelist_util", "namutil"],
                remap=dict(autoremap="first"),
            ),
            gvar=dict(
                values=["NAMELIST_UTILITIES"], default="namelist_utilities"
            ),
            binary=dict(
                values=["batodb", "utilities", "odbtools"],
                default="utilities",
                optional=True,
            ),
        ),
    )


class NamelistTerm(Namelist):
    """
    Class for all the terms dependent namelists
    """

    _footprint = [
        term,
        dict(
            info="Terms dependent namelist",
            attr=dict(kind=dict(values=["namterm"])),
        ),
    ]

    def incoming_xxt_fixup(self, attr, key=None, prefix=None):
        """Fix as best as possible the ``xxt.def`` file."""

        regex = re.compile(r",(.*)$")
        myenv = env.current()
        suffix = regex.search(myenv.VORTEX_XXT_DEF)
        if suffix:
            fp = suffix.group(1)
        else:
            fp = None

        try:
            with open("xxt.def") as f:
                lines = f.readlines()
        except OSError:
            logger.error("Could not open file xxt.def")
            raise

        select = lines[self.term.hour].split()[2]

        if not re.match(r"undef", select):
            if fp:
                rgx = re.compile(key + r"(.*)$")
                sfx = rgx.search(select)
                if sfx:
                    s = sfx.group(1)
                else:
                    s = ""
                return "".join((key, "_", fp, s))
            else:
                return select
        else:
            logger.error(
                "Fullpos namelist id not defined for term %s", self.term
            )

    def incoming_namelist_fixup(self, attr, key=None):
        """Fix as best as possible the namelist term extensions."""

        val = getattr(self, attr)
        r1 = re.compile(r"^(.*\/)?(" + key + r".*_fp|cpl)$")
        r2 = re.compile(r"^(.*\/)?(" + key + r".*_fp)(\..*)$")
        r3 = re.compile(r"^(.*\/)?(" + key + r".*_p)$")

        fixed = 0

        for r in (r1, r2, r3):
            s = r.search(val)
            if s:
                fixed = 1
                (dirpath, base) = (s.group(1), s.group(2))
                if dirpath is None:
                    dirpath = ""
                ext = ""
                if r == r3:
                    if self.term.hour == 0:
                        p = "0"
                    elif self.term.hour % 6 == 0:
                        p = "6"
                    elif self.term.hour % 3 == 0:
                        p = "3"
                    else:
                        p = "1"
                else:
                    if self.term.hour == 0:
                        p = "0"
                    else:
                        p = ""
                    if r == r2:
                        ext = s.group(3)
                        if ext is None:
                            ext = ""

        if fixed:
            return dirpath + base + p + ext
        else:
            return val


class NamelistSelect(NamelistTerm):
    """
    Class for the select namelists
    """

    _footprint = [
        dict(
            info="Select namelist for fullpos ",
            attr=dict(
                kind=dict(
                    values=[
                        "namselect",
                    ]
                )
            ),
        )
    ]

    @property
    def realkind(self):
        return "namselect"

    def gget_urlquery(self):
        """GGET specific query : ``extract``."""
        myenv = env.current()
        if myenv.true("VORTEX_XXT_DEF"):
            return "extract=" + self.incoming_xxt_fixup("source", "select")
        else:
            return "extract={:s}".format(self.source)


class NamelistFullPos(NamelistTerm):
    """
    Class for the fullpos term dependent namelists
    """

    _footprint = [
        dict(
            info="Namelist for offline fullpos ",
            attr=dict(
                kind=dict(
                    values=[
                        "namelistfp",
                    ]
                )
            ),
        )
    ]

    @property
    def realkind(self):
        return "namelistfp"

    def gget_urlquery(self):
        """GGET specific query : ``extract``."""
        return "extract=" + self.incoming_namelist_fixup("source", "namel")


class NamelistFpServerObject(Namelist):
    """Class for a fullpos server object's namelists."""

    _footprint = dict(
        info="Namelist for a fullpos server object",
        attr=dict(
            kind=dict(
                values=[
                    "namelist_fpobject",
                ]
            ),
            fp_conf=dict(
                info="The FPCONF setting associated with this object.",
                type=int,
                optional=True,
            ),
            fp_cmodel=dict(
                info="The CMODEL setting associated with this object.",
                optional=True,
            ),
            fp_lextern=dict(
                info="The LEXTERN setting associated with this object.",
                type=bool,
                optional=True,
            ),
            fp_terms=dict(
                info=(
                    "Apply this object only on a subset of the input "
                    "data (based on term)"
                ),
                type=FPList,
                optional=True,
            ),
        ),
    )

    @property
    def realkind(self):
        return "namelist_fpobject"


class XXTContent(IndexedTable):
    """Indexed table of selection namelist used by inlined fullpos forecasts."""

    def __init__(self, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self._cachedomains = None
        self._cachedomains_term = None

    def fmtkey(self, key):
        """Reshape entry keys of the internal dictionary as a :class:`~bronx.stdtypes.date.Time` value."""
        key = Time(key)
        return key.fmthm

    def xxtpos(self, n, g, x):
        """
        Return value in position ``n`` for the ``term`` occurence defined in ``g`` or ``x``.
          * ``g`` stands for a guess dictionary.
          * ``x`` stands for an extra dictionary.

        These naming convention refer to the footprints resolve mechanism.
        """
        t = g.get("term", x.get("term", None))
        if t is None:
            return None
        else:
            value = None
            try:
                t = Time(t)
            except (ValueError, TypeError):
                return None
            tkey = self.get(t.fmthm, self.get(str(t.hour), None))
            if tkey is None:
                logger.warning(
                    "No entry found in the XXT file for term = %s.", t.fmthm
                )
            else:
                try:
                    value = tkey[n]
                except IndexError:
                    return None
            return value

    def xxtnam(self, g, x):
        """Return local namelist filename according to first column."""
        return self.xxtpos(0, g, x)

    def xxtsrc(self, g, x):
        """Return local namelist source in gco set according to second column."""
        return self.xxtpos(1, g, x)

    def mapdomains(self, maxterm=None, where=None):
        """Return a map of domains associated for each term in selection namelists."""
        mapdom = dict()
        allterms = sorted([Time(x) for x in self.keys()])
        if maxterm is None:
            if allterms:
                maxterm = allterms[-1]
            else:
                maxterm = -1
        maxterm = Time(maxterm)

        if (self._cachedomains is None) or (
            self._cachedomains_term != maxterm
        ):
            select_seen = dict()
            for a_term in [x for x in allterms if x <= maxterm]:
                tvalue = self.get(
                    a_term.fmthm, self.get(str(a_term.hour), None)
                )
                sh = sessions.system()
                if tvalue[0] is not None:
                    local_guesses = [tvalue[0], "fpselect_" + a_term.fmthm]
                    if where:
                        local_guesses = [
                            sh.path.join(where, g) for g in local_guesses
                        ]
                    local_guesses = [
                        g for g in local_guesses if sh.path.exists(g)
                    ]
                    if local_guesses:
                        # Do not waste time on duplicated selects...
                        if tvalue[1] not in select_seen:
                            fortp = NamelistParser()
                            with open(local_guesses[0]) as fd:
                                xx = fortp.parse(fd.read())
                            domains = set()
                            for nb in xx.values():
                                for domlist in [
                                    y
                                    for x, y in nb.items()
                                    if x.startswith("CLD")
                                ]:
                                    domains = domains | set(
                                        domlist.pop().split(":")
                                    )
                            select_seen[tvalue[1]] = domains
                        else:
                            domains = select_seen[tvalue[1]]
                        mapdom[a_term.fmthm] = list(domains)
                        if a_term.minute == 0:
                            mapdom[str(a_term.hour)] = list(domains)

            self._cachedomains_term = maxterm
            self._cachedomains = mapdom

        else:
            mapdom = self._cachedomains

        return dict(term=mapdom)


class NamelistSelectDef(StaticResource):
    """Utility, so-called xxt file."""

    _footprint = [
        cutoff,
        gvar,
        dict(
            info="xxt.def file from namelist pack",
            attr=dict(
                gvar=dict(
                    values=["NAMELIST_" + x.upper() for x in binaries],
                    default="namelist_[binary]",
                ),
                source=dict(
                    optional=True,
                ),
                binary=dict(
                    optional=True,
                    values=binaries,
                    default="[model]",
                ),
                kind=dict(values=["xxtdef", "namselectdef"]),
                clscontents=dict(default=XXTContent),
            ),
            bind=["gvar", "source"],
        ),
    ]

    _source_map = dict(
        assim="xxt.def.assim",
    )

    @property
    def realkind(self):
        return "namselectdef"

    def gget_urlquery(self):
        """GGET specific query : ``extract``."""
        if self.source is None:
            thesource = self._source_map.get(self.cutoff, "xxt.def")
        else:
            thesource = self.source
        return "extract=" + thesource


@namebuilding_insert("src", lambda s: s.target)
class GeoBlocks(ModelGeoResource):
    """Extract of a namelist containing Geometry blocks."""

    _footprint = dict(
        attr=dict(
            kind=dict(
                info="Geometry blocks of namelist.", values=["geoblocks"]
            ),
            clscontents=dict(
                default=NamelistContent,
            ),
            target=dict(
                info="Scope that should use these blocks.",
            ),
            nativefmt=dict(
                optional=True,
                values=["nam"],
                default="nam",
            ),
        )
    )

    @property
    def realkind(self):
        return "geoblocks"
