"""
Module that deals with part of the Arpege/IFS listings related to the
tests of the Tangent Linear and Adjoint models.
"""

import re
import math

from .util import (read_listing,
                   diverging_digit,
                   number_of_different_digits,
                   PARSING_ERROR_CODE,
                   re_for_fortran_scientific_format,
                   set_figax)

#: Automatic export
__all__ = []


class ADTest:
    """
    Handle results of the test of the adjoint from a listing.

    The resulting attribute *score* is close to a "number of different digits"
    in the comparison of :literal:`< F(X) , Y >` and :literal:`< X , F*(Y) >`, so the
    closest to 0 is the best.
    It is actually computed as the :literal:`log10(|< F(X) , Y >-< X , F*(Y) >|/epsilon)`
    where epsilon is the zero of the machine.
    """

    signature = 'TEST OF THE ADJOINT'
    p_fxy = '< F(X) , Y >'
    p_xfy = '< X , F*(Y) >'
    p_zero = r'THE DIFFERENCE IS\s*((?P<n_times_zero>(\d*\.\d+)|(\**))\s+)+TIMES THE ZERO OF THE MACHINE$'
    zero_overflow = 21

    def __init__(self, source):
        """:param source: may be either a filename or a list of lines."""
        self.diverging_digit = 999
        self.number_of_different_digits = -1
        self.diff_is_n_times_zero = -1
        self.score = -1
        self._parse_listing(source)

    def _parse_listing(self, source):
        """
        Parse a listing (either given as its filename or already read as a
        list of lines) looking for adjoint test.
        """
        lines = read_listing(source)
        for i in range(len(lines)):
            if self.signature in lines[i]:
                if self.p_fxy in lines[i + 2] and self.p_xfy in lines[i + 3]:
                    self.fxy = lines[i + 2].split('=')[1].strip()
                    self.xfy = lines[i + 3].split('=')[1].strip()
                    self.diverging_digit = min(self.diverging_digit,
                                               diverging_digit(self.fxy,
                                                               self.xfy))
                    self.number_of_different_digits = max(self.number_of_different_digits,
                                                          number_of_different_digits(self.fxy, self.xfy))
                    re_n_zero = re.match(self.p_zero, lines[i + 4].strip())
                    if re_n_zero is not None:
                        if '*' in re_n_zero.group('n_times_zero'):
                            self.diff_is_n_times_zero = 10 ^ self.zero_overflow
                            self.score = self.zero_overflow
                        else:
                            self.diff_is_n_times_zero = max(self.diff_is_n_times_zero,
                                                            float(re_n_zero.group('n_times_zero')))
                            score = math.log(max(1., self.diff_is_n_times_zero), 10)
                            self.score = max(self.score, score)

        if self.score == -1:
            self.score = PARSING_ERROR_CODE

    def format(self):
        """Format for printing."""
        s = ' '.join(['|', self.p_fxy, '-', self.p_xfy, '|',
                      'is', str(self.diff_is_n_times_zero),
                      'times the zero of the machine.'])
        s += '\n'
        d = int(math.ceil(self.score))
        s += ' '.join(['~', str(d),
                       'different significative digit' + 's' * int(bool(d - 1))])
        return s


class TLTest:
    """
    Handle results of the test of the tangent linear from a listing.

    The resulting score is close to a "best number of digits towards 1.0" in
    the lambda-variating test.
    The retained overall score is the worst of these scores among different
    fields.
    Then, the largest the score, the best the test is .

    Scores are actually computed as :literal:`-log10(|1.0-RAT|)`
    where RAT is the ratio computed in the TL test, :literal:`RAT = (M(x+dx)-M(x))/M'(dx)`.
    """

    signature = 'TEST OF THE TANGENT LINEAR'
    p_lambda = r'LAMBDA\s*=\s*(?P<lambda>-?\d{1,2})$'
    p_lambda = re.compile(p_lambda)
    p_ratio = r'(?P<fld>\w+\.?)\s*I =\s*(?P<gridpoint>\d+)\s+' + \
              r'RAT = (?P<ratio>' + re_for_fortran_scientific_format.pattern + r')\s+.*'
    p_ratio = re.compile(p_ratio)

    def __init__(self, source):
        """
        :param source: may be either a filename or a list of lines.
        """
        self.ratios = {la: {} for la in range(-10, 1)}
        self.ratios_per_id = {}
        self.scores_per_id = {}
        self.best_score_per_id = {}
        self.score = PARSING_ERROR_CODE
        self._parse_listing(source)

    def _parse_listing(self, source):
        """
        Parse a listing (either given as its filename or already read as a
        list of lines) looking for TL test.
        """
        lines = read_listing(source)
        for i in range(len(lines)):
            if self.signature in lines[i]:
                lambdas = []
                ratios = {}
                la = int(self.p_lambda.match(lines[i + 1].strip()).group('lambda'))
                lambdas.append(la)
                j = 2
                while True:
                    if i + j >= len(lines):  # security
                        break
                    _re_ok = self.p_ratio.match(lines[i + j].strip())
                    if _re_ok:
                        fld = _re_ok.group('fld')
                        gridpoint = int(_re_ok.group('gridpoint'))
                        ratio = _re_ok.group('ratio')
                        if fld in ratios.keys():
                            ratios[fld][gridpoint] = ratio
                        else:
                            ratios[fld] = {gridpoint: ratio}
                        j += 1
                    else:  # end of ratios prints
                        break
                self.ratios[la] = ratios
        # compute best digits
        # a) sort
        lambdas = sorted(self.ratios.keys())
        flds = self.ratios[lambdas[0]].keys()
        gridpoints = {f: [] for f in flds}
        for f in flds:
            gridpoints[f] = self.ratios[lambdas[0]][f].keys()
        ids = []
        for f in flds:
            for g in gridpoints[f]:
                ids.append((f, g))
        self.ratios_per_id = {i: {} for i in ids}
        for i in ids:
            for la in lambdas:
                self.ratios_per_id[i][la] = self.ratios[la][i[0]][i[1]]

        # b) compute scores
        def score(x):
            if x == '-.5555555555000000E+10':
                s = None
            else:
                s = max(0., -math.log(abs(1. - float(x)), 10))
            return s
        self.scores_per_id = {i: {la: score(self.ratios_per_id[i][la])
                                  for la in lambdas}
                              for i in ids}

        self.best_score_per_id = {i: max(self.scores_per_id[i].values())
                                  for i in ids}
        self.score = min(self.score,
                         min([s for s in self.best_score_per_id.values()
                              if s is not None]))

    def plot(self, over=(None, None), title="TL test"):
        """Show a graphical interpretation of the test."""
        fig, ax = set_figax(*over)
        # colors and linestyles
        colors = ['red', 'blue', 'green', 'orange', 'magenta', 'darkolivegreen',
                  'yellow', 'salmon', 'black']
        variables = sorted({i[0] for i in self.scores_per_id.keys()})
        cmap = {v: colors[i] for i, v in enumerate(variables)}
        gridpoints = {v: [i[1] for i in self.scores_per_id.keys() if i[0] == v]
                      for v in variables}
        labels = [(k, v[0]) for k, v in gridpoints.items()]
        M = 0
        for i in sorted(self.scores_per_id.keys()):
            x = sorted(self.scores_per_id[i].keys())
            y = [self.scores_per_id[i][line]for line in x]
            M = int(math.ceil(max(M, max(y))))
            plot_kwargs = {'color': cmap[i[0]]}
            if i in labels:
                plot_kwargs['label'] = i[0]
            ax.plot(x, y, **plot_kwargs)
        ax.set_ylim(bottom=-1, top=M + 2)
        ax.set_ylabel(r"$-log_{10}(1.-\frac{M(x+\delta x)-M(x)}{\mathbf{M}(\delta x)}) \equiv$ Digit towards 1.0")
        ax.set_xlabel("Lambda")
        ax.set_xticks(range(-10, 1))
        ax.set_yticks(range(M + 2))
        ax.legend()
        ax.grid(True)
        ax.set_title(title)
        return fig, ax
