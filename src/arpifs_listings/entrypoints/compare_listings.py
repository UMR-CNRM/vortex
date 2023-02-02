"""
A command line tool that compares two Arpege/IFS listings.
"""

import argparse
import sys

import arpifs_listings


def main():
    """Start the CLI."""
    parser = argparse.ArgumentParser(description='Tool designed to compare the output listings (norms '
                                                 'or Jo-tables) of an IFS/ARPEGE/ALADIN/AROME experiment.')
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
                        default='first_and_last_spectral',
                        help=("(for 'norms' comparison only, 'text' mode): either 'all' to compare " +
                              "norms for all steps found in listings, or 'first_and_last_spectral' " +
                              "(default) for the first and last spectral norms only."))
    parser.add_argument('-m',
                        dest='mode',
                        default='text',
                        help=("(for 'norms' comparison only): " +
                              "either 'text' (default) or 'plot': " +
                              "how the norm comparison is shown."))
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
                        help=("(for 'norms' comparison only, 'text' mode): " +
                              "only max difference is printed for each step."))
    args = parser.parse_args()

    if args.out is None:
        out = sys.stdout
    else:
        out = open(args.out, 'w', encoding='utf-8')
    # TODO: add TL/AD comparisons
    arpifs_listings.compare_files(args.listings[0], args.listings[1],
                                  mode=args.mode,
                                  out=out,
                                  pattern=args.pattern,
                                  which=args.which,
                                  onlymaxdiff=args.onlymaxdiff,
                                  nthres=args.nthres,
                                  jothres=args.jothres,
                                  bw=args.bw)
