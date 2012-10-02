#!/bin/env python
# -*- coding:Utf-8 -*-

import re

#: No automatic export
__all__ = []

#: Default values for suite ids.
suites = [ 'oper', 'dbl', 'dble', 'test' ]

#: Specific tricks for base naming in iga fuzzy namespace.
fuzzystr = dict(
    histfix = dict(
        historic = dict( pearp = 'prev', arome = 'AROM', arpege = 'arpe', aladin = 'ALAD' ),
    ),
    prefix = dict(
        gridpoint = dict( oper = 'PE', dbl = 'PA' ),
    ),
    suffix = dict(
        bgerrstd = dict( input = 'in', output = 'out' )
    ),
    term0003 = dict(
        bgerrstd = dict( input = '', output = '_assim' ),
    ),
    term0009 = dict(
        bgerrstd = dict( input = '_production', output = '_production' ),
    ),
    term0012 = dict(
        bgerrstd = dict( input = '_production_dsbscr', output = '_production_dsbscr' ),
    ),
    varbcarpege = dict(
        varbc = dict( input = '.cycle_arp', output = '.cycle' ),
    ),
    varbcaladin = dict(
        varbc = dict( input = '.cycle_alad', output = '.cycle' ),
    ),
    varbcarome = dict(
        varbc = dict( input = '.cycle_aro', output = '.cycle' ),
    ),
    surf0000 = dict(
        histsurf = dict( input = 'INIT_SURF', output = 'INIT_SURF' ),
    ),
    surf0003 = dict(
        histsurf = dict( input = 'PREP', output = 'AROMOUT_.0003' ),
    ),
    surf0006 = dict(
        histsurf = dict( input = 'PREP', output = 'AROMOUT_.0006' ),
    ),
)


def fuzzyname(entry, realkind, key):
    """Returns any non-standard naming convention in the operational namespace."""
    return fuzzystr[entry][realkind][key]


def hliteral2int(hliteral):
    l2i = dict(
        AM = 0, CM = 0,
        TR = 3, SX = 6, NF = 9, PM = 12, QZ = 15, DH = 18, VU = 21
    )
    return l2i[hliteral]

def archivesuffix(model, cutoff, date):
    """Returns the suffix for iga filenames according to specified ``model``, ``cutoff`` and ``date`` hour."""

    hh = range(0,21,3)
    hrange = []
    for h in hh:
        hrange.append("%02d" %h)

    if cutoff == 'assim':

        rr = dict(
            zip(
                zip(
                    (cutoff,)*len(hrange),
                    hh
                ),
                hrange
            )
        )
    else:
        if re.search('court|arome', model):
            rr = dict(
                zip(
                    zip(
                        (cutoff,)*len(hrange),
                        hh
                    ),
                    ('CM', 'TR', 'SX', 'NF', 'PM', 'QZ', 'DH', 'VU')
                )
            )
        else:
            rr = dict(
                zip(
                    zip(
                        (cutoff,)*len(hrange),
                        hh
                    ),
                    ('AM', 'TR', 'SX' , 'NF', 'PM', 'QZ', 'DH', 'VU')
                )
            )     

    return str(rr[(cutoff, date.hour)])

