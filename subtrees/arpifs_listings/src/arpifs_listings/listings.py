"""
Module that deal with any Arpege/IFS listing.
"""

import sys

from .util import PARSING_ERROR_CODE, FOUND_NAN_ERROR_CODE
from .norms import NormsSet, compare_normsets
from .jo_tables import JoTables, DEFAULT_N_THRESHOLD, DEFAULT_JO_THRESHOLD
from .cost_functions import CostFunctions
from .TLAD import ADTest, TLTest

#: No automatic export
__all__ = []


class OutputListing:
    """Handling of a model configuration output listing."""

    patterns = {'end_is_reached': ['*** END CNT0 ***',
                                   '| PGD ENDS CORRECTLY |'],
                }

    def __init__(self, filename, pattern_type):
        """

        :param filename: name of the file to read in
        :param pattern_type: type of pattern to compare, among
                             ('norms', 'Jo-tables', 'costs', 'AD-test', 'TL-test')

        The :meth:`parse_patterns` needs to be called before accessing the data.
        Once this necessary step is completed, parsed data can be accessed using
        the :attr:`normset`, :attr:`jo_tables`, :attr:`costs`, :attr:`AD-test`
        or :attr:`TL-test` attributes (according to the **pattern_type** value).
        """
        assert pattern_type in ('norms', 'Jo-tables', 'costs', 'AD-test', 'TL-test'), \
            "unknown pattern: " + pattern_type

        # init
        self.filename = filename
        self.pattern_type = pattern_type
        self.end_is_reached = False

        self.normset = None
        self.jo_tables = None
        self.costs = None
        self.ad_test = None
        self.tl_test = None

        # read listing in file
        with open(self.filename) as f:
            self.lines = [line.rstrip("\n") for line in f]  # to remove trailing '\n'

    def __len__(self):
        return len(self.lines)

    def look_for_end(self):
        """Is the end reached in listing ?"""
        for line in self.lines:
            if any([p in line for p in self.patterns['end_is_reached']]):
                self.end_is_reached = True
                break
        return self.end_is_reached

    @property
    def patterns_count(self):
        if self.pattern_type == 'norms':
            n = len(self.normset)
        elif self.pattern_type == 'Jo-tables':
            n = len(self.jo_tables)
        elif self.pattern_type == 'costs':
            n = len(self.costs)
        elif self.pattern_type == 'AD-test':
            n = 1
        elif self.pattern_type == 'TL-test':
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
        elif self.pattern_type == 'costs':
            self.parse_costs(flush_after_reading=flush_after_reading)
        elif self.pattern_type == 'AD-test':
            self.parse_AD_test(flush_after_reading=flush_after_reading)
        elif self.pattern_type == 'TL-test':
            self.parse_TL_test(flush_after_reading=flush_after_reading)

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
        self.jo_tables = JoTables(self.filename, self.lines)
        if flush_after_reading:
            self.flush_listing()

    # Jo-tables
    def parse_costs(self, flush_after_reading=False):
        """
        Look for and read each cost function information

        If **flush_after_reading**, get rid of listing after reading data.
        """
        self.costs = CostFunctions(self.filename, self.lines)
        if flush_after_reading:
            self.flush_listing()

    # Test of the Adjoint
    def parse_AD_test(self, flush_after_reading=False):
        """
        Look for and read test of the adjoint.

        If **flush_after_reading**, get rid of listing after reading the test.
        """
        self.ad_test = ADTest(self.lines)
        if flush_after_reading:
            self.flush_listing()

    # Test of the tangent linear
    def parse_TL_test(self, flush_after_reading=False):
        """
        Look for and read test of the tangent linear.

        If **flush_after_reading**, get rid of listing after reading the test.
        """
        self.tl_test = TLTest(self.lines)
        if flush_after_reading:
            self.flush_listing()


#############
# FUNCTIONS #
#############
def compare(test, ref, **kwargs):
    """Compare two :class:`OutputListing` objects."""
    assert test.pattern_type == ref.pattern_type
    result = None
    if test.pattern_type == 'norms':
        result = compare_norms(test, ref, **kwargs)
    elif test.pattern_type == 'Jo-tables':
        compare_jo_tables(test, ref, **kwargs)
    elif test.pattern_type == 'AD-test':
        result = compare_AD_tests(test, ref, **kwargs)
    elif test.pattern_type == 'TL-test':
        result = compare_TL_tests(test, ref, **kwargs)
    return result


def compare_norms(test, ref,
                  mode,
                  which='first_and_last_spectral',
                  out=sys.stdout,
                  onlymaxdiff=False,
                  **_):
    """Compare two 'norms' pattern-type :class:`OutputListing` objects.

    :param which: either 'all' to compare norms for all steps found in listings,
                  or 'first_and_last_spectral' (default) for the first and last
                  spectral norms only.
    :param out: output open file or stdout
    :param onlymaxdiff: only max difference is printed for each step.
    :param mode: - if 'text', prints the comparison to file;
                 - if 'get_worst_by_step', get worst (among fields) digits
                   comparison for each step;
                 - if 'get_worst' get worst of worst (among fields) digits
                   comparison.
                 - if 'plot', plot a graph of differences
    """
    assert ref.look_for_end()
    assert test.look_for_end()
    assert ref.pattern_type == 'norms'
    assert test.pattern_type == 'norms'
    if not hasattr(ref, 'normset'):
        ref.parse_norms()
    if not hasattr(test, 'normset'):
        test.parse_norms()
    assert len(ref.normset) > 0
    assert len(test.normset) > 0
    assert mode in ('text', 'get_worst', 'get_worst_by_step', 'plot')
    assert which in ('first_and_last_spectral', 'all')

    return compare_normsets(test.normset, ref.normset, mode,
                            which=which,
                            out=out,
                            onlymaxdiff=onlymaxdiff)


def compare_jo_tables(test, ref,
                      out=sys.stdout,
                      nthres=DEFAULT_N_THRESHOLD,
                      jothres=DEFAULT_JO_THRESHOLD,
                      bw=False,
                      onlymaxdiff=False,
                      **_):
    """
    Compare two 'Jo-tables' pattern-type :class:`OutputListing` objects.

    :param test: Test listing object (to be compared)
    :param ref: Reference listing object (to be compared to)
    :param nthres: Alert threshold on the ObsCount
    :param jothres: Alert threshold on the Jo
    :param bw: Black & White flag
    :param onlymaxdiff: Only max difference is printed for each table
    """
    assert ref.look_for_end()
    assert test.look_for_end()
    assert ref.pattern_type == 'Jo-tables'
    assert test.pattern_type == 'Jo-tables'
    if not hasattr(ref, 'jo_tables'):
        ref.parse_jo_tables()
    if not hasattr(test, 'jo_tables'):
        test.parse_jo_tables()
    assert len(ref.jo_tables) > 0
    assert len(test.jo_tables) > 0

    test.jo_tables.print_diff(ref.jo_tables,
                              out=out,
                              nthres=nthres,
                              jothres=jothres,
                              bw=bw,
                              onlymaxdiff=onlymaxdiff)


def compare_AD_tests(test, ref,
                     mode='text',
                     out=sys.stdout,
                     **_):
    """
    Compare two adjoint pattern-type :class:`OutputListing` objects.

    :param test: Test listing object (to be compared)
    :param ref: Reference listing object (to be compared to)
    :param mode: - if 'text', prints the comparison to out;
                 - if 'get_worst' get worst of worst (among fields) digits
                   comparison.
    :param out: output open file or stdout
    :return: The absolute difference of both scores (only if *mode* is
             'get_worst').
    """
    assert ref.look_for_end()
    assert test.look_for_end()
    assert ref.pattern_type == 'AD-test'
    assert test.pattern_type == 'AD-test'
    if not hasattr(ref, 'ad_test'):
        ref.parse_AD_test()
    if not hasattr(test, 'ad_test'):
        test.parse_AD_test()

    if mode == 'get_worst':
        if PARSING_ERROR_CODE in (test.ad_test.score, ref.ad_test.score):
            comp = PARSING_ERROR_CODE
        elif FOUND_NAN_ERROR_CODE in (test.ad_test.score, ref.ad_test.score):
            comp = FOUND_NAN_ERROR_CODE
        elif test.ad_test.zero_overflow in (test.ad_test.score, ref.ad_test.score):
            comp = test.ad_test.zero_overflow
        else:
            comp = abs(test.ad_test.score - ref.ad_test.score)
        return comp
    elif mode == 'text':
        out.write(test.filename + ':\n')
        out.write(test.ad_test.format() + '\n')
        out.write(ref.filename + ':\n')
        out.write(ref.ad_test.format() + '\n')


def compare_TL_tests(test, ref,
                     mode='plot',
                     out='TL-tests.png',
                     **_):
    """
    Compare two tangent linear pattern-type :class:`OutputListing` objects.

    :param test: Test listing object (to be compared)
    :param ref: Reference listing object (to be compared to)
    :param mode: - if 'get_worst' get worst of worst (among fields) digits
                   comparison.
                 - if 'plot', plot a graph of differences
    :param out: (mode=='plot' only) output filename (.png) or None for
                interactive display
    :return: The absolute difference of both scores (only if *mode* is
             'get_worst')..
    """
    assert ref.look_for_end()
    assert test.look_for_end()
    assert ref.pattern_type == 'TL-test'
    assert test.pattern_type == 'TL-test'
    if not hasattr(ref, 'tl_test'):
        ref.parse_AD_test()
    if not hasattr(test, 'tl_test'):
        test.parse_AD_test()

    if mode == 'get_worst':
        if PARSING_ERROR_CODE in (test.tl_test.score, ref.tl_test.score):
            comp = PARSING_ERROR_CODE
        elif FOUND_NAN_ERROR_CODE in (test.tl_test.score, ref.tl_test.score):
            comp = FOUND_NAN_ERROR_CODE
        else:
            comp = abs(test.tl_test.score - ref.tl_test.score)
        return comp
    elif mode == 'plot':
        import matplotlib.pyplot as plt
        fig, axes = plt.subplots(2, 1, figsize=(12, 16))
        fig, _ = test.tl_test.plot(over=(fig, axes[0]), title='\n'.join(["TL-test",
                                                                         test.filename]))
        fig, _ = ref.tl_test.plot(over=(fig, axes[1]), title='\n'.join(["TL-test",
                                                                        ref.filename]))
        if out is None:
            fig.show()
        else:
            fig.savefig(out, bbox_inches='tight')
