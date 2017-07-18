#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division
import six

import sys
from collections import OrderedDict

from .norms import NormsSet, NormsComparison
from . import jo_tables

#: No automatic export
__all__ = []

CRASHED_JOB_ERROR_CODE = -1


class OutputListing(object):
    """Handling of a model configuration output listing."""

    patterns = {'end_is_reached': '*** END CNT0 ***', }

    def __init__(self, filename, pattern_type):
        """

        :param filename: name of the file to read in
        :param pattern_type: type of pattern to compare, among ('norms', 'Jo-tables')
        """
        assert pattern_type in ('norms', 'Jo-tables', ), \
            "unknown pattern: " + pattern_type

        # init
        self.filename = filename
        self.pattern_type = pattern_type
        self.end_is_reached = False
        self.normset = None
        self.jo_tables = None

        # read listing in file
        with open(self.filename, 'r') as f:
            self.lines = [six.u(l).rstrip("\n") for l in f]  # to remove trailing '\n'

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
            n = len(self.normset)
        elif self.pattern_type == 'Jo-tables':
            n = len(self.jo_tables)
        elif self.pattern_type == 'adjoint-test':
            n = 1
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

        If **flush_after_reading**, get rid of listing after reading norms.
        """
        self.normset = NormsSet(self.lines)
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
                  mode,
                  which='first_and_last_spectral',
                  out=sys.stdout,
                  onlymaxdiff=False,
                  **ignored_kwargs):
    """Compare two 'norms' pattern-type output listings.

    :param which: either 'all' to compare norms for all steps found in listings,
                  or 'first_and_last_spectral' (default) for the first and last
                  spectral norms only.

    :param onlymaxdiff: only max difference is printed for each step.
    :param mode: - if 'text', prints the comparison to file;
                 - if 'get_worst_by_step', get worst (among fields) digits
                   comparison for each step;
                 - if 'get_worst' get worst of worst (among fields) digits
                   comparison.
                 - if 'plot', plot a graph of differences (spectral norms only)
    """

    assert ref.end_is_reached
    assert test.end_is_reached
    assert len(ref.normset) > 0
    assert len(test.normset) > 0
    assert mode in ('text', 'get_worst', 'get_worst_by_step', 'plot')
    assert which in ('first_and_last_spectral', 'all')

    if not test.normset.steps_equal(ref.normset):
        st = set([n.format_step() for n in test.normset])
        sr = set([n.format_step() for n in ref.normset])
        stepset = st.intersection(sr)
        test_rm = [i for i in range(len(test.normset))
                   if test.normset[i].format_step() not in stepset]
        for off, i in enumerate(test_rm):
            test.normset.pop(i - off)
        ref_rm = [i for i in range(len(ref.normset))
                  if ref.normset[i].format_step() not in stepset]
        for off, i in enumerate(ref_rm):
            ref.normset.pop(i - off)
        assert test.normset.steps_equal(ref.normset)
    if which == 'first_and_last_spectral':
        for i in range(len(test.normset)):
            if len(test.normset[i].spnorms) > 0:
                steps = (i, None)
                break
        for i in sorted(range(len(test.normset)), reverse=True):
            if len(test.normset[i].spnorms) > 0:
                steps = (steps[0], i)
                break
        if steps[0] == steps[1]:
            steps = (steps[0],)
    elif which == 'all':
        steps = list(range(len(test.normset)))

    if 'get_worst' in mode:
        worstdigits = []
    elif mode == 'plot':
        normsout = OrderedDict()
    for i in steps:
        norm_comp = NormsComparison(test.normset[i],
                                    ref.normset[i])
        if mode == 'text':
            out.write(test.normset.norms_at_each_step[i].format_step() + '\n')
            norm_comp.write(out, onlymaxdiff)
            out.write('-' * 80 + '\n')
        elif 'get_worst' in mode:
            assert onlymaxdiff is True
            worstdigits.append(norm_comp.get_worst('both'))
        elif mode == 'plot':
            norm_comp = NormsComparison(test.normset.norms_at_each_step[i],
                                        ref.normset.norms_at_each_step[i],
                                        only='spectral')
            if len(norm_comp.sp_comp) > 0:
                normsout[test.normset[i].format_step()] = norm_comp.sp_comp
    if mode == 'plot':
        import matplotlib.pyplot as plt
        fldset = []
        for n in normsout.values():
            fldset.extend(n.keys())
        fldset = sorted(set(fldset))
        tab_f = {f: [n.get(f, None) for n in normsout.values()] for f in fldset}
        xlabels = [(i, f) for i, f in enumerate(normsout.keys())]
        xlen = len(xlabels)
        tn = 5
        if xlen > tn:
            xstep = xlen // tn
            xlast = xlabels[-1]
            xlabels = xlabels[::xstep]
            if (xlast[0] - xlabels[-1][0]) < xstep / 2:
                xlabels[-1] = xlast
            else:
                xlabels.append(xlast)
        fig, axes = plt.subplots(len(fldset), 1, figsize=(12, 8))
        for j, f in enumerate(fldset):
            axes[j].plot(tab_f[f], color='DarkMagenta')
            axes[j].scatter(0, tab_f[f][0], c='DarkMagenta', s=50, marker='o')
            axes[j].set_xlim(0, xlen)
            axes[j].scatter(xlen, tab_f[f][xlen - 1], c='DarkMagenta', s=20, marker='o', edgecolors='face')
            axes[j].set_xticks([x[0] for x in xlabels])
            axes[j].set_xticklabels([])
            axes[j].set_ylim(0, 15)
            axes[j].set_yticks([0, 5, 10, 15])
            axes[j].set_yticklabels([0, 5, 10, 15])
            axes[j].set_ylabel(f, rotation=45., horizontalalignment='right')
            axes[j].grid()
        xlabels = [x[1].split() for x in xlabels]
        for x in xlabels:
            if len(x) > 2:
                x.insert(2, '\n')
        axes[-1].set_xticklabels([''.join(x) for x in xlabels],
                                 rotation=45., horizontalalignment='right')
        axes[0].set_title('Norms: number of # digits')
        pngname = 'norms_diff.png'
        print('=> Output in: ' + pngname)
        fig.savefig(pngname, bbox_inches='tight', dpi=300)

    if mode == 'get_worst':
        return max(worstdigits)
    elif mode == 'get_worst_by_step':
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
