#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import sys

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
    parser.add_argument('-p',
                        dest='pattern',
                        default='norms',
                        help="Pattern: either 'norms' or 'Jo-tables'.")
    parser.add_argument('-m',
                        dest='mode',
                        default='first_and_last',
                        help="Mode (for pattern 'norms'): either 'all' to" \
                             + "compare norms for all steps found in listings," \
                             + "or 'first_and_last' (default) for the first and last only.")
    parser.add_argument('--thres-n', '-n',
                        dest='nthres',
                        action='store',
                        type=int,
                        default=arpifs_listings.jo_tables.DEFAULT_N_THRESHOLD,
                        help='Alert threshold for the ObsCount')
    parser.add_argument('--thres-jo', '-j',
                        dest='jothres',
                        action='store',
                        type=float,
                        default=arpifs_listings.jo_tables.DEFAULT_JO_THRESHOLD,
                        help='Alert threshold for the Jo')
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
                                  out=out,
                                  pattern=args.pattern,
                                  mode=args.mode,
                                  onlymaxdiff=args.onlymaxdiff,
                                  nthres=args.nthres,
                                  jothres=args.jothres,
                                  bw=args.bw)
