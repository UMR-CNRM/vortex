"""
Various utility functions used when parsinf ArpIFS listings.
"""

import re

#: No automatic export
__all__ = []

# regular expressions tools
_sign = r'(\-|0)'
_dot = r'\.'
_digits = r'\d+'
_exp = r'E?(\+|\-)\d{2,3}'
re_for_fortran_scientific_format = re.compile(_sign + _dot + _digits + _exp)

_sign = r'(?P<sign>' + _sign + ')'
_digits = r'(?P<digits>' + _digits + ')'
_exp = r'E?(?P<exp>(\+|\-)\d{2,3})'

# useful patterns
re_for_fortran_scientific_format_groups = re.compile(_sign + _dot + _digits + _exp + '$')
re_for_nan = re.compile(r'\s*N|nA|aN|n\s*')
# useful error codes
PARSING_ERROR_CODE = 999
CRASHED_JOB_ERROR_CODE = -1
MISSING_OUTPUT_ERROR_CODE = -2
FOUND_NAN_ERROR_CODE = -3


def find_line_containing(pattern, lines):
    """
    Find the first line containing a given **pattern**
    within a list of **lines**.

    Returns (index, line).
    """
    index = None
    line = ''
    for i, in_line in enumerate(lines):
        if pattern in in_line:
            line = in_line
            index = i
            break
    return (index, line)


def diverging_digit(t, r):
    """
    Get the index (starting from 0) of the first diverging digit between two
    floats **t** (test) and **r** (ref), given as scientific format strings !

    **t** and **r** syntax examples:
    '0.256351366366780E-03'
    '-.256351366366780E+03'
    '0.256351366366780-305' (misformatted E-305)

    If comparison is not possible (due to formatting reason),
    raises ParsingError.
    """
    if t == r:
        digit = None
    else:
        digit = number_of_different_digits(t, r)
        if digit == 0:
            digit = None
        elif digit < 0:
            pass
        else:
            r_re = re_for_fortran_scientific_format_groups.match(r)
            digits_len = len(r_re.group('digits'))
            digit = digits_len - digit
    return digit


class ParsingError(ValueError):
    """Error class while parsing a float in scientific format."""
    pass


def number_of_different_digits(t, r):
    """
    Get the number of different digits between two floats
    **t** (test) and **r** (ref), given as scientific format strings !

    **t** and **r** syntax examples:
    '0.256351366366780E-03'
    '-.256351366366780E+03'
    '0.256351366366780-305' (misformatted E-305)

    If comparison is not possible (due to formatting reason),
    raises ParsingError.
    """
    if t == r:
        digit = 0
    else:
        t_re = re_for_fortran_scientific_format_groups.match(t)
        r_re = re_for_fortran_scientific_format_groups.match(r)
        if t_re and r_re:
            t_sign = t_re.group('sign')
            r_sign = r_re.group('sign')
            t_digits = t_re.group('digits')
            r_digits = r_re.group('digits')
            t_exp = t_re.group('exp')
            r_exp = r_re.group('exp')
            digits_len = len(r_digits)
            digit = digits_len
            if t_exp == r_exp:
                # identical exponents
                if t_sign != r_sign:
                    # different signs: find the first non-zero digit
                    for i in range(digits_len):
                        if r_digits[i] != '0' or t_digits[i] != '0':
                            digit = i
                            break
                else:
                    # identical signs
                    for i in range(digits_len):
                        if r_digits[i] != t_digits[i]:
                            digit = i
                            break
            else:
                # exponents differ
                exponent = int(r_exp)
                t = float(t_sign + '.' + t_digits + 'E' + t_exp)
                r = float(r_sign + '.' + r_digits + 'E' + r_exp)
                d = float(t) - float(r)
                d = d * (10 ** -exponent)
                diff = '{:+.{nd}F}'.format(d, nd=digits_len)
                # diff has format '+n.nnnnnnnnnnnnnnnn'
                for i in range(len(diff) - 3):
                    if diff[1] != '0':
                        digit = 0
                        break
                    if diff[3:][i] != '0':  # look for non-0
                        digit = i
                        break
            digit = digits_len - digit
        else:
            if re_for_nan.match(t) or re_for_nan.match(r):
                digit = FOUND_NAN_ERROR_CODE
            else:
                if not t_re:
                    raise ParsingError('unable to parse test float: ' + t)
                if not r_re:
                    raise ParsingError('unable to parse ref float: ' + r)
    return digit


def get_maxint(container, infinity=-999):
    """
    Get the max value of a dict or a list, assuming its values are int.
    None values are ignored, str values come out as max.
    """
    assert (isinstance(container, dict) or
            isinstance(container, list) or
            isinstance(container, tuple))
    digit = infinity
    if isinstance(container, dict):
        container = list(container.values())
    for d in container:
        if isinstance(d, int):
            digit = max(digit, d)
        elif isinstance(d, str):
            digit = d
            break
        elif d is None:
            continue
    if digit == infinity:
        digit = None
    return digit


def get_worst(a_list):
    """
    Get the worst, i.e. max or FOUND_NAN_ERROR_CODE, value of a list.
    """
    if FOUND_NAN_ERROR_CODE in a_list:
        worst = FOUND_NAN_ERROR_CODE
    elif len(a_list) == 0:
        worst = 0
    else:
        worst = max(a_list)
    return worst


def read_listing(source):
    """
    Read a listing, given its (either given as its filename or already read as a
    list of lines).
    """
    if isinstance(source, list):
        lines = source
    elif isinstance(source, str):
        with open(source) as listfh:
            lines = [line.rstrip("\n") for line in listfh]
    return lines


def set_figax(figure, ax, figsize=(12, 8)):
    """
    Given existing matplotlib *figure* and an *ax* (or None),
    check consistency or generate a consistent (figure, ax) duet.
    """
    import matplotlib.pyplot as plt

    if ax is not None and figure is None:
        figure = ax.figure
    elif ax is None and figure is not None:
        if len(figure.axes) > 0:
            ax = figure.axes[0]
        else:
            ax = figure.gca()
    elif ax is not None and figure is not None:
        assert ax in figure.axes, '*over*: inconsistency between given fig and ax'
    elif figure is ax is None:
        figure, ax = plt.subplots(1, 1, figsize=figsize)

    return (figure, ax)
