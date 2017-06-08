#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import argparse
import os
import re
import sys

# Automatically set the python path
sitepath = re.sub('{0:}arpifs_listings{0:}bin$'.format(os.path.sep), '',
                  os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, sitepath)

import arpifs_listings


if __name__ == '__main__':

    parser = argparse.ArgumentParser(description='Tool designed to compare the output listings (norms or Jo-tables) of an IFS/ARPEGE/ALADIN/AROME experiment.')
    parser.add_argument('listings',
                        nargs=2,
                        help="Names of the output listings.")
    parser.add_argument('-o',
                        dest='out',
                        default=None,
                        help="Store the comparison in the given file name instead of standard output")
    pattern = parser.add_mutually_exclusive_group(required=True)
    pattern.add_argument('-n',
                         dest='pattern',
                         action='store_const',
                         const='norms',
                         help='Compare norms')
    pattern.add_argument('-j',
                         dest='pattern',
                         action='store_const',
                         const='Jo-tables',
                         help='Compare Jo-Tables')
    parser.add_argument('-w',
                        dest='which',
                        default='first_and_last',
                        help=("(for 'norms' comparison only): either 'all' to " +
                              "compare norms for all steps found in listings, " +
                              "or 'first_and_last' (default) for the first and last only."))
    parser.add_argument('--n-threshold', '--nt',
                        dest='nthres',
                        action='store',
                        type=int,
                        default=arpifs_listings.jo_tables.DEFAULT_N_THRESHOLD,
                        help='Alert threshold for the ObsCount [default: %(default)s]')
    parser.add_argument('--jo-threshold', '--jot',
                        dest='jothres',
                        action='store',
                        type=float,
                        default=arpifs_listings.jo_tables.DEFAULT_JO_THRESHOLD,
                        help='Alert threshold for the Jo [default: %(default)s]')
    parser.add_argument('--bw',
                        action='store_true',
                        help='Produce a black & white output (no red color)')
    parser.add_argument('-x',
                        dest='onlymaxdiff',
                        action='store_true',
                        default=False,
                        help="Only max difference (for pattern 'norms') is printed for each step.")
    args = parser.parse_args()

    if args.out is None:
        out = sys.stdout
    else:
        out = open(args.out, 'w')

    arpifs_listings.compare_files(args.listings[0], args.listings[1],
                                  mode='standalone',
                                  out=out,
                                  pattern=args.pattern,
                                  which=args.which,
                                  onlymaxdiff=args.onlymaxdiff,
                                  nthres=args.nthres,
                                  jothres=args.jothres,
                                  bw=args.bw)
