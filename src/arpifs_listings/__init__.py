"""
Processing and comparison of various data from Arpege/IFS listings.
"""

import sys

from . import util, norms, jo_tables, listings

assert util
assert norms


def compare_files(file_test, file_ref,
                  out=sys.stdout,
                  pattern='norms',
                  # 'norms' arguments:
                  mode='text',
                  onlymaxdiff=False,
                  which='first_and_last_spectral',
                  # 'Jo-tables' arguments:
                  nthres=jo_tables.DEFAULT_N_THRESHOLD,
                  jothres=jo_tables.DEFAULT_JO_THRESHOLD,
                  bw=False):
    """Compare the output listings of two files.

    :param pattern: the pattern to be compared, among
                    ('norms', 'Jo-tables', 'AD-test', 'TL-test')

    Optional arguments when *pattern* is 'norms':

    :param onlymaxdiff: only max difference is printed for each step.
    :param which: either 'all' to compare norms for all steps found in listings,
                  or 'first_and_last_spectral' (default) for the first and last only.
    :param mode: if 'text', prints the comparison to file;
                 if 'plot', plots the comparison (pattern='norms');
                 if 'get_worst', return the worst digits comparison.

    Optional arguments when *pattern* is 'Jo-tables':

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


def show_TL_test(filename, outputname='TL-test.png'):
    """Show a graphical interpretation of the TL-test."""
    listing = listings.OutputListing(filename, pattern_type='TL-test')
    listing.parse_TL_test()
    fig, _ = listing.tl_test.plot()
    if outputname is None:
        fig.show()
    else:
        fig.savefig(outputname)
