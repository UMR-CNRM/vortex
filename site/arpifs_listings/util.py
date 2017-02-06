#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import six

#: No automatic export
__all__ = []


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
    Get the index of the first diverging digit between two floats
    **t** (test) and **r** (ref), given as scientific format strings !

    **t** and **r** syntax example: '0.256351366366780E+03'

    If both are identical, return *None*.
    If comparison is not possible (due to formatting reason), return '?'.
    """

    ts = t.split('E')
    rs = r.split('E')
    exponents_are_OK = (len(ts) == len(rs) == 2)
    if t == r:
        digit = None
    else:
        if exponents_are_OK:
            [t_digits, t_exp] = ts[:]
            [r_digits, r_exp] = rs[:]
            if t_exp == r_exp:
                # identical exponents
                for i in range(len(r_digits[2:])):
                    if r_digits[2:][i] != t_digits[2:][i]:
                        digit = i
                        break
            else:
                # exponents differ
                exponent = int(r_exp)
                d = float(t) - float(r)
                d = d * (10 ** -exponent)
                diff = str(d)
                for i in range(len(diff)):
                    if diff[2:][i] != '0':  # look for non-0
                        digit = i
                        break
        else:
            digit = '?'
    return digit


def get_maxint(a_dict, infinity=99):
    """
    Get the max value of a dict, assuming its values are int.
    None values are ignored, str values come out as max.
    """

    assert isinstance(a_dict, dict)
    digit = infinity
    for d in a_dict.values():
        if isinstance(d, int):
            digit = min(digit, d)
        elif isinstance(d, six.string_types):
            digit = d
            break
        elif d is None:
            continue
    if digit == infinity:
        digit = None
    return digit
