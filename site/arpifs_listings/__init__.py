#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import argparse
import sys

from . import util, norms, jo_tables, listings

__version__ = '1.0.2'


def compare_files(file_test, file_ref,
                  out=sys.stdout,
                  pattern='norms',
                  # 'norms' arguments:
                  mode='standalone',
                  onlymaxdiff=False,
                  which='first_and_last',
                  # 'Jo-tables' arguments:
                  nthres=jo_tables.DEFAULT_N_THRESHOLD,
                  jothres=jo_tables.DEFAULT_JO_THRESHOLD,
                  bw=False):
    """Compare the output listings of two files.

    :param pattern: the pattern to be compared, among ('norms', 'Jo-tables')

    'norms' arguments:
        :param onlymaxdiff: only max difference is printed for each step.
        :param which: either 'all' to compare norms for all steps found in listings,
                      or 'first_and_last' (default) for the first and last only.
        :param mode: if 'standalone', prints the comparison to file;
                     if 'get_worst', return the worst digits comparison.

    'Jo-tables' arguments:
        :param nthres: Alert threshold on the ObsCount
        :param jothres: Alert threshold on the Jo
        :param bw: Black & White flag

    """

    test = listings.OutputListing(file_test, pattern_type=pattern)
    if test.look_for_end():
        test.parse_patterns()
    else:
        out.write('*test* (' + test.filename + ') crashed before end !' + '\n')

    ref = listings.OutputListing(file_ref, pattern_type=pattern)
    if ref.look_for_end():
        ref.parse_patterns()
    else:
        out.write('*ref* (' + ref.filename + ') crashed before end !' + '\n')

    if test.end_is_reached and ref.end_is_reached:
        if test.patterns_count > 0 and ref.patterns_count > 0:
            comp_out = listings.compare(test, ref,
                                        mode=mode,
                                        out=out,
                                        which=which,
                                        onlymaxdiff=onlymaxdiff,
                                        nthres=nthres,
                                        jothres=jothres,
                                        bw=bw)
        else:
            out.write(' '.join(['No', pattern, 'found in output.\n']))
            comp_out = None
    return comp_out
