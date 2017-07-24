#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Utility classes to read and compare IFS/Arpege listings."""

from __future__ import print_function, absolute_import, unicode_literals, division

from collections import OrderedDict

from arpifs_listings import norms, jo_tables, listings
import footprints

from . import addons
from __builtin__ import property

#: No automatic export
__all__ = []


def use_in_shell(sh, **kw):
    """Extend current shell with the arpifs_listings interface defined by optional arguments."""
    kw['shell'] = sh
    return footprints.proxy.addon(**kw)


class ArpIfsListingDiff_Result(object):
    """Holds the detailed results of a listing comparison."""

    def __init__(self, norms_eq, jos_eq, jos_diff):
        self._norms_eq = norms_eq
        self._jos_eq = jos_eq
        self._jos_diff = jos_diff

    def __str__(self):
        return '{0:s} | NormsOk={1:b} JoTablesOk={2:b}>'.format(
            repr(self).rstrip('>'),
            self._norms_eq and all(self._norms_eq.values()),
            self._jos_eq and all(self._jos_eq.values())
        )

    def differences(self):
        """Print a summary of the listing comparison."""
        print
        if self._norms_eq:
            if all(self._norms_eq.values()):
                print("Norms   check succeeded for all steps.")
            else:
                print("Norms   check succeeded for steps:\n  {:s}".format(
                    "\n  ".join([str(k) for k, v in self._norms_eq.items() if v])))
                print("Norms   check FAILED    for steps:\n  {:s}".format(
                    "\n  ".join([str(k) for k, v in self._norms_eq.items() if not v])))
        else:
            print("Norms steps do not match. The check FAILED.")
        print
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
                                    print("  > {:s} > {:s} > {:4s} : d_n={:<9d}  d_jo={:f}".format(
                                        otype_k, sensor_k, var_k,
                                        var_v['n']['diff'], var_v['jo']['diff']))
                        diffprinted = True
        else:
            print("The number of Jo-Tables do not match. The check FAILED.")


class ArpIfsListingDiff_Status(object):
    """Holds the status of a listing comparison."""

    def __init__(self, norms_eq, jos_eq, jos_diff):
        self._norms_ok = norms_eq and all(norms_eq.values())
        self._jos_ok = jos_eq and all(jos_eq.values())
        self._result = ArpIfsListingDiff_Result(norms_eq, jos_eq, jos_diff)

    def __str__(self):
        return '{0:s} | rc={1:b}>'.format(repr(self).rstrip('>'), bool(self))

    @property
    def result(self):
        """Return the detailed results of the comparison."""
        return self._result

    def __nonzero__(self):
        return bool(self._norms_ok and self._jos_ok)


class ArpIfsListingsTool(addons.Addon):
    """Interface to arpifs_listings (designed as a shell Addon)."""

    _footprint = dict(
        info='Default arpifs_listings interface',
        attr=dict(
            kind=dict(
                values=['arpifs_listings'],
            ),
        )
    )

    def arpifslist_diff(self, listing1, listing2):
        """Difference between two Arpege/IFS listing files.

        Only Spectral/Gridpoint norms and JO-tables are compared.

        :param listing1: first file to compare
        :param listing2: second file to compare
        :rtype: :class:`ArpIfsListingDiff_Status`
        """

        with open(listing1, 'r') as fh1:
            l1_slurp = [l.rstrip("\n") for l in fh1]
        with open(listing2, 'r') as fh2:
            l2_slurp = [l.rstrip("\n") for l in fh2]
        l1_normset = norms.NormsSet(l1_slurp)
        l2_normset = norms.NormsSet(l2_slurp)
        l1_jos = jo_tables.JoTables(listing1, l1_slurp)
        l2_jos = jo_tables.JoTables(listing2, l2_slurp)

        # The reference listing may contain more norms compared to the second one
        norms_eq = OrderedDict()
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
        if not l1_jos == l2_jos:
            # If the JoTables list is not consistent: do nothing
            if list(l1_jos.keys()) == list(l2_jos.keys()):
                for table1, table2 in zip(l1_jos.values(), l2_jos.values()):
                    jos_eq[table1.name] = table1 == table2
                    if not jos_eq[table1.name]:
                        jos_diff[table1.name] = OrderedDict()
                        # We only save differences when deltaN or deltaJo != 0
                        for otype_k, otype_v in table2.compute_diff(table1).items():
                            otype_tmp = OrderedDict()
                            for sensor_k, sensor_v in otype_v.items():
                                sensor_tmp = OrderedDict()
                                for k, v in sensor_v.items():
                                    if v['n']['diff'] != 0 or v['jo']['diff'] != 0:
                                        sensor_tmp[k] = v
                                if len(sensor_tmp):
                                    otype_tmp[sensor_k] = sensor_tmp
                            if len(otype_tmp):
                                jos_diff[table1.name][otype_k] = otype_tmp
        else:
            for k in l1_jos.keys():
                jos_eq[k] = True

        return ArpIfsListingDiff_Status(norms_eq, jos_eq, jos_diff)


class ArpifsListingsFormatAdapter(footprints.FootprintBase):

    _collector = ('dataformat',)
    _footprint = dict(
        attr=dict(
            filename=dict(
                info="Path to the Arpege/IFSlisting file.",
            ),
            openmode=dict(
                info="File open-mode.",
                values=['r', ],
                default='r',
                optional=True,
            ),
            fmtdelayedopen=dict(
                info="Delay the opening of the listing file.",
                type=bool,
                default=True,
                optional=True,
            ),
            format=dict(
                values=['ARPIFSLIST', ],
            ),
        )
    )

    def __init__(self, *kargs, **kwargs):
        super(ArpifsListingsFormatAdapter, self).__init__(*kargs, **kwargs)
        self._lines = None
        self._normset = None
        self._jotables = None
        self._end_is_reached = None
        if not self.fmtdelayedopen:
            self.normset
            self.jotables

    @property
    def lines(self):
        """Return an array populated with the listing file lines."""
        if self._lines is None:
            with open(self.filename, self.openmode) as f:
                self._lines = [l.rstrip("\n") for l in f]  # to remove trailing '\n'
        return self._lines

    @property
    def end_is_reached(self):
        """Return whether the end of CNT0 was reached."""
        if self._end_is_reached is None:
            self._end_is_reached = False
            for line in self.lines:
                if any([p in line for p in listings.OutputListing.patterns['end_is_reached']]):
                    self._end_is_reached = True
                    break
        return self._end_is_reached

    @property
    def normset(self):
        """Return a :class:`arpifs_listings.norms.NormsSet` object."""
        if self._normset is None:
            self._normset = norms.NormsSet(self.lines)
        return self._normset

    @property
    def jotables(self):
        """Return a :class:`arpifs_listings.jo_tables.JoTables` object."""
        if self._jotables is None:
            self._jotables = jo_tables.JoTables(self.filename, self.lines)
        return self._jotables

    def __len__(self):
        """The number of lines in the listing."""
        return len(self.lines)
