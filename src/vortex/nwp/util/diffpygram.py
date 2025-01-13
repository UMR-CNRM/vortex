"""
Usage of the EPyGrAM package to compute diffs.
"""

import collections
import copy
import functools
import hashlib
import io
import json
import operator
import pprint

import footprints
from vortex import sessions
from . import usepygram


class HGeoDesc:
    """Holds Epygram's horizontal geometry data."""

    def __init__(self, epyfield):
        """
        :param epyfied: An epygram fild object.
        """
        geo = epyfield.geometry
        self.grid = geo.grid
        self.dimensions = geo.dimensions
        self.name = geo.name
        self.projection = (
            None if not geo.projected_geometry else geo.projection
        )
        sio = io.StringIO()
        geo.what(out=sio, vertical_geometry=False)
        sio.seek(0)
        self._what = sio.readlines()[3:]

    def __eq__(self, other):
        return (
            (self.grid == other.grid)
            and (self.dimensions == other.dimensions)
            and (self.name == other.name)
            and (self.projection == other.projection)
        )

    def __str__(self):
        return "".join(self._what)


class DataDesc:
    """Holds information about an Epygram's field data (basic stats + checksum)."""

    def __init__(self, epyfield):
        """
        :param epyfied: An epygram fild object.
        """
        self.stats = epyfield.stats()
        self.stats.pop("quadmean", None)  # We do not want quadmean
        s256 = hashlib.sha256()
        s256.update(epyfield.data.tobytes())
        self.checksum = s256.digest()

    def __eq__(self, other):
        return self.checksum == other.checksum

    def __str__(self):
        return ", ".join(
            ["{:s}={!s}".format(k, v) for k, v in self.stats.items()]
        )


class HGeoLibrary:
    """A collection/library of :class:`HGeoDesc` objects."""

    def __init__(self):
        self._geolist = list()

    def register(self, hgeo_desc):
        """Check if an :class:`HGeoDesc` object is already in the library.

        If the *hgeo_desc* object is not already in the library it is inserted.
        In any case, the index of the *hgeo_desc* geometry within the library is
        returned.
        """
        found = (None, None)
        for i, g in enumerate(self._geolist):
            if hgeo_desc == g:
                found = (i, g)
                break
        if found == (None, None):
            found = (len(self._geolist), hgeo_desc)
            self._geolist.append(hgeo_desc)
        return found[0]

    def __str__(self):
        outstr = ""
        for i, g in enumerate(self._geolist):
            outstr += "HORIZONTAL GEOMETRY #{:d}\n\n".format(i)
            outstr += str(g)
            outstr += "\n"
        return outstr


class FieldDesc:
    """Holds various information about an Epygram field."""

    def __init__(self, hgeoid, vgeo, datadesc, fid, valid):
        self.hgeoid = hgeoid
        self.vgeo = vgeo
        self.datadesc = datadesc
        self.fid = fid
        self.valid = valid

    def ranking(self, other):
        """
        Compute the comparison score of the present field with respect to a
        reference one (*other*).
        """
        fidscore = functools.reduce(
            operator.add,
            [
                int(self.fid[k] == other.fid[k])
                for k in self.fid.keys()
                if k in other.fid
            ],
        )
        fidscore = (
            5.0 * float(fidscore) / float(max(len(self.fid), len(other.fid)))
        )
        return (
            int(self.valid != other.valid) * -5.0
            + int(self.hgeoid != other.hgeoid) * -5.0
            + int(self.vgeo != other.vgeo) * -4.0
            + int(self.datadesc == other.datadesc) * 5.0
            + fidscore
        )

    def ranking_summary(self, other):
        """Returns detailed comparison information (including the ranking)."""
        return (
            self.datadesc == other.datadesc,
            self.valid == other.valid,
            self.hgeoid == other.hgeoid and self.vgeo == other.vgeo,
            self.ranking(other),
        )

    def __str__(self):
        out = "HGeo=#{:d} ; Validity={!s} ; metadata are:\n".format(
            self.hgeoid, self.valid
        )
        out += pprint.pformat(self.fid) + "\n"
        out += "Data: {!s}".format(self.datadesc)
        return out

    def prefixed_str(self, prefix):
        """A representation of this object prefixed with the *prefix* string."""
        return "\n".join([prefix + l for l in str(self).split("\n")])


class FieldBundle:
    """A collection of FieldDesc objects."""

    def __init__(self, hgeolib):
        self._hgeolib = hgeolib
        self._fields = list()

    @property
    def fields(self):
        """The list of fields in the present collection."""
        return self._fields

    def _common_processing(self, fld, fid):
        hgeo = HGeoDesc(fld)
        vgeo = fld.geometry.vcoordinate
        valid = fld.validity.get()
        ddesc = DataDesc(fld)
        hgeo_id = self._hgeolib.register(hgeo)
        fid = copy.copy(fid)
        fid["datebasis"] = fld.validity.getbasis()
        fid["term"] = fld.validity.term()
        fid["cumulativeduration"] = fld.validity.cumulativeduration()
        return FieldDesc(hgeo_id, vgeo, ddesc, fid, valid)

    @usepygram.epygram_checker.disabled_if_unavailable(version="1.0.0")
    def read_grib(self, filename):
        """Read in a GRIB file."""
        with usepygram.epy_env_prepare(sessions.current()):
            gribdata = footprints.proxy.dataformat(
                filename=filename, openmode="r", format="GRIB"
            )
            fld = gribdata.iter_fields(
                get_info_as_json=("centre", "subCentre")
            )
            while fld:
                fid = fld.fid.get("GRIB2", fld.fid.get("GRIB1"))
                fid.update(json.loads(fld.comment))
                self._fields.append(self._common_processing(fld, fid))
                fld = gribdata.iter_fields(
                    get_info_as_json=("centre", "subCentre")
                )


class FieldBundles:
    """A collection of :class:`FieldBundle` objects."""

    def __init__(self):
        self._hgeolib = HGeoLibrary()
        self._bundles = dict()

    @property
    def hgeo_library(self):
        """The :class:`HGeoLibrary` onject being used in this collection."""
        return self._hgeolib

    def new_bundle(self, name):
        """Create a new :class:`FieldBundle` object in this collection."""
        fbd = FieldBundle(self._hgeolib)
        self._bundles[name] = fbd
        return fbd

    @property
    def bundles(self):
        """The dictionary of bundles in the present collection."""
        return self._bundles


class EpyGribDiff(FieldBundles):
    """A specialised version of :class:`FieldBundles` that deals with GRIB files."""

    _FMT_COUNTER = "[{:04d}] "
    _HEAD_COUNTER = " " * len(_FMT_COUNTER.format(0))

    _FMT_SHORT = (
        "#{n:>4d} id={id:16s} l={level:<6d} c={centre:<3d},{scentre:3d}"
    )
    _HEAD_SHORT = "Mess. ParamId/ShortN      Level    Centre,S "

    _FMT_MIDDLE = " | {0:1s} {1:1s} {2:1s} {3:6s} | "
    _HEAD_MIDDLE = " | {:1s} {:1s} {:1s}  {:5s} | "
    _ELTS_MIDDLE = ("data", "valid", "geo", "score")

    _SPACER = (
        _HEAD_COUNTER
        + "REF "
        + "-" * (len(_HEAD_SHORT) - 4)
        + " | -----  ----- | "
        + "NEW "
        + "-" * (len(_HEAD_SHORT) - 4)
    )

    _DETAILED_SUMARY = "Data: {0:1s} ; Validity Date: {1:1s} ; HGeometry: {2:s} ; Score: {3:6s}"

    def __init__(self, ref, new):
        """
        :param str ref: Path to the reference GRIB file
        :param str new: Path to the new GRIB file
        """
        super().__init__()
        self._new = self.new_bundle("New")
        self._new.read_grib(new)
        self._ref = self.new_bundle("Ref")
        self._ref.read_grib(ref)

    def _compute_diff(self):
        """Explore all possible field combinations and find the closest match.

        :return: tuple (newfield_id, list of matching reffield_ids, rankingscore,
                        list of ranking_summaries)
        """
        found = set()
        couples = list()
        for i, field in enumerate(self._new.fields):
            rscore = collections.defaultdict(list)
            rsummary = collections.defaultdict(list)
            for j, rfield in enumerate(self._ref.fields):
                tsummary = field.ranking_summary(rfield)
                rscore[tsummary[-1]].append(j)
                rsummary[tsummary[-1]].append(tsummary)
            highest = max(rscore.keys())
            # If the score is >= 3 the fields are paired...
            # Note: Their might be several field combinations with the same
            # ranking score
            if highest >= 3.0:
                refs = rscore[highest]
                couples.append((i, refs, highest, rsummary[highest]))
                found.update(refs)
            else:
                couples.append((i, (), None, None))
        missings = set(range(len(self._ref.fields))) - found
        if missings:
            couples.append((None, list(missings), None, None))
        return couples

    @classmethod
    def _str_header(cls):
        """Returns the comparison table header."""
        out = cls._SPACER + "\n"
        e_len = max([len(e) for e in cls._ELTS_MIDDLE])
        e_new = [
            ("{:>" + str(e_len) + "s}").format(e.upper())
            for e in cls._ELTS_MIDDLE
        ]
        if e_len > 1:
            for i in range(e_len - 1):
                out += (
                    cls._HEAD_COUNTER
                    + " " * len(cls._HEAD_SHORT)
                    + cls._HEAD_MIDDLE.format(*[e[i] for e in e_new])
                    + " " * len(cls._HEAD_SHORT)
                    + "\n"
                )
        out += (
            (
                cls._HEAD_COUNTER
                + cls._HEAD_SHORT
                + cls._HEAD_MIDDLE.format(*[e[-1] for e in e_new])
                + cls._HEAD_SHORT
                + "\n"
            )
            + cls._SPACER
            + "\n"
        )
        return out

    @classmethod
    def _str_field_summary(cls, n, field):
        """Returns a string that summarise a field properties."""
        if "paramId" in field.fid:
            # GRIB1
            sid = str(field.fid["paramId"]) + "/" + field.fid["shortName"]
        else:
            # GRIB2
            sid = (
                str(field.fid["parameterCategory"])
                + "-"
                + str(field.fid["parameterNumber"])
                + "/"
                + field.fid["shortName"]
            )
        if len(sid) > 16:  # Truncate if the string is too long
            sid = sid[:15] + "*"
        return cls._FMT_SHORT.format(
            n=n,
            id=sid,
            level=field.fid.get("level", -99),
            centre=field.fid["centre"],
            scentre=field.fid.get("subCentre", -99),
        )

    @classmethod
    def _str_rsummary_format(cls, rsum, fmt):
        """Format the ranking_summary output."""
        dmap = {True: "=", False: "!"}
        return fmt.format(
            dmap[rsum[0]],
            dmap[rsum[1]],
            dmap[rsum[2]],
            "======" if rsum[3] == 10 else "{:6.2f}".format(rsum[3]),
        )

    @staticmethod
    def _embedded_counter(c):
        """Return the formatted comparison counter."""
        return "[{:04d}] ".format(c)

    def format_diff(self, detailed=True):
        """Return a string that contains the comparison results.

        :param bool detailed: If False, just returns the comparison table.
        """
        out = ""
        counter = 0
        for couple in self._compute_diff():
            if couple[0] is None:
                for n in couple[1]:
                    counter += 1
                    out += self._embedded_counter(counter)
                    if detailed:
                        out += "Unmatched reference field\n"
                        out += (
                            self.bundles["Ref"]
                            .fields[n]
                            .prefixed_str("  REF| ")
                            + "\n"
                        )
                    else:
                        out += self._str_field_summary(
                            n, self.bundles["Ref"].fields[n]
                        )
                        out += (
                            self._FMT_MIDDLE.format("?", "?", "?", "     ?")
                            + "\n"
                        )
            else:
                new = self.bundles["New"].fields[couple[0]]
                if len(couple[1]):
                    for i, n in enumerate(couple[1]):
                        counter += 1
                        ref = self.bundles["Ref"].fields[n]
                        out += self._embedded_counter(counter)
                        if detailed:
                            out += (
                                self._str_rsummary_format(
                                    couple[3][i], self._DETAILED_SUMARY
                                )
                                + "\n"
                            )
                            out += (
                                ref.prefixed_str("  REF| ")
                                + "\n  vs\n"
                                + new.prefixed_str("  NEW| ")
                                + "\n"
                            )
                        else:
                            out += self._str_field_summary(n, ref)
                            out += self._str_rsummary_format(
                                couple[3][i], self._FMT_MIDDLE
                            )
                            out += (
                                self._str_field_summary(couple[0], new)
                                if i == 0
                                else "  idem."
                            )
                            out += "\n"
                else:
                    counter += 1
                    out += self._embedded_counter(counter)
                    if detailed:
                        out += "Unmatched new field \n"
                        out += (
                            self.bundles["New"]
                            .fields[couple[0]]
                            .prefixed_str("  NEW| ")
                            + "\n"
                        )
                    else:
                        out += " " * len(self._HEAD_SHORT)
                        out += self._FMT_MIDDLE.format("?", "?", "?", "     ?")
                        out += self._str_field_summary(couple[0], new) + "\n"
            out += "\n" if detailed else ""
        if detailed:
            out += "LIST OF HORIZONTAL GEOMETRIES:\n\n"
            out += str(self.hgeo_library)
        return out

    def __str__(self):
        return self._str_header() + self.format_diff(detailed=False)
