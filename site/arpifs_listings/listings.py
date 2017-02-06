#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import sys

from .norms import Norms, NormComparison
from . import jo_tables

#: No automatic export
__all__ = []


class OutputListing(object):
    """Handling of a model configuration output listing."""

    patterns = {'end_is_reached': '*** END CNT0 ***', }

    def __init__(self, filename, pattern_type):
        """

        :param filename: name of the file to read in
        :param pattern_type: type of pattern to compare, among ('norms', 'Jo-tables')
        """
        assert pattern_type in ('norms', 'Jo-tables')

        # init
        self.filename = filename
        self.pattern_type = pattern_type
        self.end_is_reached = False
        self.norms = None
        self.jo_tables = None

        # read listing in file
        with open(self.filename, 'r') as f:
            self.lines = [l.rstrip("\n") for l in f]  # to remove trailing '\n'

    def __len__(self):
        return len(self.lines)

    def look_for_end(self):
        """Is the end reached in listing ?"""
        for line in self.lines:
            if self.patterns['end_is_reached'] in line:
                self.end_is_reached = True
                break
        return self.end_is_reached

    @property
    def patterns_count(self):
        if self.pattern_type == 'norms':
            n = len(self.norms)
        elif self.pattern_type == 'Jo-tables':
            n = len(self.jo_tables)
        return n

    def parse_patterns(self, flush_after_reading=False):
        """
        Look for and read each pattern instance.

        If **flush_after_reading**, get rid of listing after reading patterns.
        """
        if self.pattern_type == 'norms':
            self.parse_norms(flush_after_reading=flush_after_reading)
        elif self.pattern_type == 'Jo-tables':
            self.parse_jo_tables(flush_after_reading=flush_after_reading)

    def flush_listing(self):
        """Get rid of the text listing that may consume some memory."""
        self.lines = ['', ] * len(self)

    # norms
    def parse_norms(self, flush_after_reading=False):
        """
        Look for and read each norms instance.
        The recognition of Norms patterns and parsing of their values is the
        most tricky part of this class.
        The most subject to maintenance too...

        If **flush_after_reading**, get rid of listing after reading norms.
        """
        self.norms = Norms(self.lines)
        if flush_after_reading:
            self.flush_listing()

    # Jo-tables
    def parse_jo_tables(self, flush_after_reading=False):
        """
        Look for and read each Jo-tables instance.
        The recognition of Jo-tables patterns and parsing of their values is the
        most tricky part of this class.
        The most subject to maintenance too...

        If **flush_after_reading**, get rid of listing after reading Jo-tables.
        """
        self.jo_tables = jo_tables.JoTables(self.filename, self.lines)
        if flush_after_reading:
            self.flush_listing()


#############
# FUNCTIONS #
#############
def compare(test, ref, **kwargs):
    """Compare two output listings."""
    assert test.pattern_type == ref.pattern_type
    result = None
    if test.pattern_type == 'norms':
        result = compare_norms(test, ref, **kwargs)
    elif test.pattern_type == 'Jo-tables':
        compare_jo_tables(test, ref, **kwargs)
    return result


def compare_norms(test, ref,
                  mode='first_and_last',
                  out=sys.stdout,
                  onlymaxdiff=False,
                  printmode='standalone',
                  **ignored_kwargs):
    """Compare two 'norms' pattern-type output listings.

    :param mode: either 'all' to compare norms for all steps found in listings,
                 or 'first_and_last' (default) for the first and last only.

    :param onlymaxdiff: only max difference is printed for each step.
    :param printmode: if 'standalone', prints the comparison to file;
                      if 'jobs_manager', return the worst digits comparison.
    """

    assert ref.end_is_reached
    assert test.end_is_reached
    assert len(ref.norms) > 0
    assert len(test.norms) > 0

    if mode == 'first_and_last':
        ref_set = ref.norms.get_first_and_last_norms_indexes()
        test_set = test.norms.get_first_and_last_norms_indexes()
    elif mode == 'all':
        ref_set = [(nstep, sorted(ref.norms[nstep].keys(), reverse=True))
                   for nstep in sorted(ref.norms.steps())]
        test_set = [(nstep, sorted(test.norms[nstep].keys(), reverse=True))
                    for nstep in sorted(test.norms.steps())]
    assert ref_set == test_set, "set of norms differ between ref and test."

    if printmode == 'jobs_manager':
        worstdigits = []
    for (nstep, subsets) in ref_set:
        for subset in subsets:
            norm_comp = NormComparison(test.norms[nstep][subset],
                                       ref.norms[nstep][subset])
            if printmode == 'standalone':
                nstepline = 'NSTEP = ' + str(nstep)
                if subset is not None:
                    nstepline += ' (' + subset + ')'
                out.write(nstepline + '\n')
                norm_comp.write(out, onlymaxdiff)
                out.write('-' * 80 + '\n')
            elif printmode == 'jobs_manager':
                assert mode == 'first_and_last'
                assert onlymaxdiff is True
                worstdigits.append(norm_comp.get_worst('both'))
    if printmode == 'jobs_manager':
        return worstdigits
    else:
        return None


def compare_jo_tables(test, ref,
                      out=sys.stdout,
                      nthres=jo_tables.DEFAULT_N_THRESHOLD,
                      jothres=jo_tables.DEFAULT_JO_THRESHOLD,
                      bw=False,
                      onlymaxdiff=False,
                      **ignored_kwargs):
    """Compare two 'Jo-tables' pattern-type output listings.

    :param test: Test listing object (to be compared)
    :param ref: Reference listing object (to be compared to)
    :param nthres: Alert threshold on the ObsCount
    :param jothres: Alert threshold on the Jo
    :param bw: Black & White flag
    :param onlymaxdiff: Only max difference is printed for each table
    """

    assert ref.end_is_reached
    assert test.end_is_reached
    assert len(ref.jo_tables) > 0
    assert len(test.jo_tables) > 0

    test.jo_tables.print_diff(ref.jo_tables,
                              out=out,
                              nthres=nthres,
                              jothres=jothres,
                              bw=bw,
                              onlymaxdiff=onlymaxdiff)
