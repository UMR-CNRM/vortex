#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from StringIO import StringIO

from vortex.tools.date import Date


def EchoData(options):
    """Generate data configuration for surges model.

    This function is designed to be used with a function store.
    """
    outstr = ''
    rhdict = options.get('rhandler', None)
    if rhdict:

        date = "{}".format(rhdict.get('resource', {}).get('date', ''))
        run = Date(date).hh
        term = "{}".format(rhdict.get('options', {}).get('term', ''))
        forcage = "{}".format(rhdict.get('provider', {}).get('vconf', '')).upper()[-3:]
        forcage_mode = "{}".format(rhdict.get('provider', {}).get('vconf', '')).upper()[-5:-3]

        mod = "{:s}".format(rhdict.get('resource', {}).get('mod', ''))

        outstr += forcage[-3:] + "\n"

        if forcage in {'ARP', 'ARO', 'CEP'}:
            outstr += "NON\n"

        outstr += str(term) + "\n"

        if forcage in {'ARP', 'ARO'}:
            outstr += "06 06\n"
        elif forcage in 'CEP':
            outstr += "12 12\n"
        else:
            outstr += "{} {}\n".format(run, run)

        # PR (Prevision) ou AA (Analyse)
        outstr += mod + "\n"

        outstr += Date(date).ymdh + "\n"

        if mod in 'PR':
            outstr += "0 {}\n".format(term)
        elif mod in 'AA':
            if forcage in {'ARP', 'ARO'}:
                outstr += "0 5\n"
            elif forcage in 'CEP':
                outstr += "0 11\n"

        if forcage_mode in 'PE':
            outstr += "180\n"
        elif forcage_mode in 'FC':
            if forcage in {'ARP', 'ARO'}:
                outstr += "60\n"
            elif forcage in 'CEP':
                outstr += "180\n"

        outstr += "60\n"
        outstr += "{}\n".format(run)
        outstr += "O\nN\nN"

    # NB: The result have to be a file like object !
    return StringIO(outstr)


def RulesGribFunction(options):
    """Generate a simple rules file for grib_filter (UV 10m, Pmer) grib_api tools.

    This function is designed to be used with a function store.
    """
    outstr = ''

    outstr += "if( ( level == 10 ) && (indicatorOfParameter==33) ){\n write;\n}\n"
    outstr += "if( ( level == 10 ) && (indicatorOfParameter==34) ){\n write;\n}\n"
    outstr += "if( (indicatorOfParameter==2) ){\n write;\n}"

    # NB: The result have to be a file like object !
    return StringIO(outstr)
