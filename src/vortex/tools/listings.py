"""Utility classes to read and compare IFS/Arpege listings."""

import copy
import re
from collections import OrderedDict, defaultdict, deque

import footprints
from arpifs_listings import cost_functions, jo_tables, listings, norms
from bronx.stdtypes.date import Date
from vortex.data.contents import FormatAdapterAbstractImplementation

from . import addons

#: No automatic export
__all__ = []


def use_in_shell(sh, **kw):
    """Extend current shell with the arpifs_listings interface defined by optional arguments."""
    kw["shell"] = sh
    return footprints.proxy.addon(**kw)


class ArpIfsListingDiff_Result:
    """Holds the detailed results of a listing comparison."""

    def __init__(self, norms_eq, jos_eq, jos_diff):
        self._norms_eq = norms_eq
        self._jos_eq = jos_eq
        self._jos_diff = jos_diff

    def __str__(self):
        return "{:s} | NormsOk={:b} JoTablesOk={:b}>".format(
            repr(self).rstrip(">"),
            all(self._norms_eq.values()),
            all(self._jos_eq.values()),
        )

    def differences(self):
        """Print a summary of the listing comparison."""
        # print()  # activation breaks test_arpifs_listings_integration.py
        if self._norms_eq:
            if all(self._norms_eq.values()):
                print("Norms   check succeeded for all steps.")
            else:
                print(
                    "Norms   check succeeded for steps:\n  {:s}".format(
                        "\n  ".join(
                            [str(k) for k, v in self._norms_eq.items() if v]
                        )
                    )
                )
                print(
                    "Norms   check FAILED    for steps:\n  {:s}".format(
                        "\n  ".join(
                            [
                                str(k)
                                for k, v in self._norms_eq.items()
                                if not v
                            ]
                        )
                    )
                )
        else:
            print("No norms found in the new listing or no matching norms.")
        # print()  # activation breaks test_arpifs_listings_integration.py
        if self._jos_eq:
            diffprinted = False
            for k, v in self._jos_eq.items():
                if v:
                    print("JoTable check succeeded for: {:s}".format(k))
                else:
                    print("JoTable check FAILED    for: {:s}".format(k))
                    if not diffprinted:
                        todo = self._jos_diff[k]
                        for otype_k, otype_v in todo.items():
                            for sensor_k, sensor_v in otype_v.items():
                                for var_k, var_v in sensor_v.items():
                                    if var_k == "GLOBAL":
                                        continue
                                    print(
                                        "  > {:s} > {:s} > {:4s} : d_n={:<9d}  d_jo={:f}".format(
                                            otype_k,
                                            sensor_k,
                                            var_k,
                                            var_v["n"]["diff"],
                                            var_v["jo"]["diff"],
                                        )
                                    )
                        diffprinted = True
        else:
            print(
                "No Jo-Tables were found or the number of Jo-Tables do not match."
            )


class ArpIfsListingDiff_Status:
    """Holds the status of a listing comparison."""

    def __init__(self, norms_eq, jos_eq, jos_diff):
        self._norms_ok = all(norms_eq.values())
        self._jos_ok = all(jos_eq.values())
        self._result = ArpIfsListingDiff_Result(norms_eq, jos_eq, jos_diff)

    def __str__(self):
        return "{:s} | rc={:b}>".format(repr(self).rstrip(">"), bool(self))

    @property
    def result(self):
        """Return the detailed results of the comparison."""
        return self._result

    def __bool__(self):
        return bool(self._norms_ok and self._jos_ok)


class ArpIfsListingsTool(addons.Addon):
    """Interface to arpifs_listings (designed as a shell Addon)."""

    _footprint = dict(
        info="Default arpifs_listings interface",
        attr=dict(
            kind=dict(
                values=["arpifs_listings"],
            ),
        ),
    )

    def arpifslist_diff(self, listing1, listing2):
        """Difference between two Arpege/IFS listing files.

        Only Spectral/Gridpoint norms and JO-tables are compared.

        :param listing1: first file to compare
        :param listing2: second file to compare
        :rtype: :class:`ArpIfsListingDiff_Status`
        """

        with open(listing1) as fh1:
            l1_slurp = [l.rstrip("\n") for l in fh1]
        with open(listing2) as fh2:
            l2_slurp = [l.rstrip("\n") for l in fh2]
        l1_normset = norms.NormsSet(l1_slurp)
        l2_normset = norms.NormsSet(l2_slurp)
        l1_jos = jo_tables.JoTables(listing1, l1_slurp)
        l2_jos = jo_tables.JoTables(listing2, l2_slurp)

        # The reference listing may contain more norms compared to the second one
        norms_eq = OrderedDict()
        if len(l2_normset):
            if not l2_normset.steps_equal(l1_normset):
                l1_tdict = OrderedDict()
                for n in l1_normset:
                    l1_tdict[n.format_step()] = n
                l2_tdict = OrderedDict()
                for n in l2_normset:
                    l2_tdict[n.format_step()] = n
                ikeys = set(l1_tdict.keys()) & set(l2_tdict.keys())
                for k in ikeys:
                    norms_eq[k] = l1_tdict[k] == l2_tdict[k]
            else:
                for i, n in enumerate(l2_normset):
                    k = n.format_step()
                    norms_eq[k] = n == l1_normset[i]

        jos_eq = OrderedDict()
        jos_diff = OrderedDict()
        if len(l2_jos):
            if not l1_jos == l2_jos:
                # If the JoTables list is not consistent: do nothing
                if list(l1_jos.keys()) == list(l2_jos.keys()):
                    for table1, table2 in zip(
                        l1_jos.values(), l2_jos.values()
                    ):
                        jos_eq[table1.name] = table1 == table2
                        if not jos_eq[table1.name]:
                            jos_diff[table1.name] = OrderedDict()
                            # We only save differences when deltaN or deltaJo != 0
                            for otype_k, otype_v in table2.compute_diff(
                                table1
                            ).items():
                                otype_tmp = OrderedDict()
                                for sensor_k, sensor_v in otype_v.items():
                                    sensor_tmp = OrderedDict()
                                    for k, v in sensor_v.items():
                                        if (
                                            v["n"]["diff"] != 0
                                            or v["jo"]["diff"] != 0
                                        ):
                                            sensor_tmp[k] = v
                                    if len(sensor_tmp):
                                        otype_tmp[sensor_k] = sensor_tmp
                                if len(otype_tmp):
                                    jos_diff[table1.name][otype_k] = otype_tmp
            else:
                for k in l1_jos.keys():
                    jos_eq[k] = True

        return ArpIfsListingDiff_Status(norms_eq, jos_eq, jos_diff)


class ArpifsListingsFormatAdapter(FormatAdapterAbstractImplementation):
    _footprint = dict(
        attr=dict(
            format=dict(
                values=[
                    "ARPIFSLIST",
                ],
            ),
        )
    )

    def __init__(self, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self._lines = None
        self._normset = None
        self._jotables = None
        self._costs = None
        self._end_is_reached = None
        if not self.fmtdelayedopen:
            self.normset
            self.jotables
            self.costs
            self.flush_lines()

    @property
    def lines(self):
        """Return an array populated with the listing file lines."""
        if self._lines is None:
            with open(
                self.filename,
                self.openmode,
                encoding="utf-8",
                errors="replace",
            ) as f:
                self._lines = [
                    l.rstrip("\n") for l in f
                ]  # to remove trailing '\n'
        return self._lines

    def flush_lines(self):
        """By defaults, listing lines are cached (that consumes memory). This method clear the cache."""
        self._lines = None

    @property
    def end_is_reached(self):
        """Return whether the end of CNT0 was reached."""
        if self._end_is_reached is None:
            self._end_is_reached = False
            for line in self.lines:
                if any(
                    [
                        p in line
                        for p in listings.OutputListing.patterns[
                            "end_is_reached"
                        ]
                    ]
                ):
                    self._end_is_reached = True
                    break
        return self._end_is_reached

    @property
    def normset(self):
        """Return a :class:`arpifs_listings.norms.NormsSet` object."""
        if self._normset is None:
            self._normset = norms.NormsSet(self.lines)
            if not self.fmtdelayedopen:
                self.flush_lines()
        return self._normset

    @property
    def jotables(self):
        """Return a :class:`arpifs_listings.jo_tables.JoTables` object."""
        if self._jotables is None:
            self._jotables = jo_tables.JoTables(self.filename, self.lines)
            if not self.fmtdelayedopen:
                self.flush_lines()
        return self._jotables

    @property
    def cost_functions(self):
        """Return a :class:`arpifs_listings.jo_tables.JoTables` object."""
        if self._costs is None:
            self._costs = cost_functions.CostFunctions(
                self.filename, self.lines
            )
            if not self.fmtdelayedopen:
                self.flush_lines()
        return self._costs

    def __len__(self):
        """The number of lines in the listing."""
        return len(self.lines)


class ListBasedCutoffDispenser:
    """
    From a dictionary of cutoff times (probably read from an extraction listing,
    see :class:`BdmBufrListingsFormatAdapter`), for a given *obstype*, find the
    best suited cutoff time.

    The __call__ method takes a unique *obstype* argument. It will return the
    best suited cutoff time for this particular *obstype*. N.B: If no exact
    match is found, the latest cutoff time will be used.
    """

    def __init__(self, cutoffs, fuse_per_obstype=False):
        self._cutoffs = cutoffs
        f_cutoffs = {}
        for k, dates in cutoffs.items():
            f_dates = [d for d in dates if d is not None]
            if f_dates:
                f_cutoffs[k] = f_dates
        if f_cutoffs:
            self._max_cutoff = max(
                [max(dates) for dates in f_cutoffs.values()]
            )
        else:
            self._max_cutoff = None
        self._default_cutoffs = defaultdict(lambda: self._max_cutoff)
        self._default_cutoffs.update(
            {k: max(dates) for k, dates in f_cutoffs.items()}
        )
        self._fuse_per_obstype = fuse_per_obstype

    @property
    def max_cutoff(self):
        """The latest cutoff time(accoss any available obstypes)."""
        return self._max_cutoff

    @property
    def default_cutoffs(self):
        """A dictionary of the latest cutoff time for each of the obstypes."""
        return self._default_cutoffs

    def __call__(self, obstype):
        """Find the best suited cutoff time for *obstype*."""
        obstype = obstype.lower()
        if self._cutoffs.get(obstype, None) and not self._fuse_per_obstype:
            item = self._cutoffs[obstype].popleft()
            return item or self.default_cutoffs[obstype]
        else:
            return self.default_cutoffs[obstype]


class BdmBufrListingsFormatAdapter(FormatAdapterAbstractImplementation):
    """Read the content of a BDM extraction output listing."""

    _footprint = dict(
        attr=dict(
            format=dict(
                values=[
                    "BDMBUFR_LISTING",
                ],
            ),
        )
    )

    _RE_OBSTYPE_GRP = re.compile(
        r"^.*tentative\s+(?:d')?extraction\s+pour\s+'?(?P<obstype>\w+)'?\b",
        re.IGNORECASE,
    )
    _RE_OBSTYPE_CUT = re.compile(
        r"^.*cutoff\s+pour\s+'?(?P<obstype>\w+)'?\s*:\s*(?P<datetime>\d+)\b",
        re.IGNORECASE,
    )

    def __init__(self, *kargs, **kwargs):
        super().__init__(*kargs, **kwargs)
        self._lines = None
        self._cutoffs = defaultdict(deque)
        if not self.fmtdelayedopen:
            self.lines

    @property
    def lines(self):
        """Return an array populated with the listing file lines."""
        if self._lines is None:
            with open(
                self.filename,
                self.openmode,
                encoding="utf-8",
                errors="replace",
            ) as f:
                self._lines = [
                    l.rstrip("\n") for l in f
                ]  # to remove trailing '\n'
        return self._lines

    @property
    def cutoffs(self):
        """
        A dictionary of cutoff times for all of the obstypes available in the
        listing.
        """
        if not self._cutoffs:
            cur_obstype = None
            for line in self.lines:
                l_match = self._RE_OBSTYPE_GRP.match(line)
                if l_match:
                    if cur_obstype is not None:
                        self._cutoffs[cur_obstype].append(None)
                    cur_obstype = l_match.group("obstype").lower()
                if cur_obstype:
                    l_match = self._RE_OBSTYPE_CUT.match(line)
                    if (
                        l_match
                        and l_match.group("obstype").lower() == cur_obstype
                    ):
                        self._cutoffs[cur_obstype].append(
                            Date(l_match.group("datetime"))
                        )
                        cur_obstype = None
            if cur_obstype is not None:
                self._cutoffs[cur_obstype].append(None)
        return self._cutoffs

    def cutoffs_dispenser(self, fuse_per_obstype=False):
        """Return a new :class:`CutoffDispenser` object."""
        return ListBasedCutoffDispenser(
            copy.deepcopy(self.cutoffs), fuse_per_obstype=fuse_per_obstype
        )
