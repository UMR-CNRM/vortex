#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import six

from bronx.fancies import loggers
from bronx.stdtypes.date import Date, Time

#: No automatic export
__all__ = []
logger = loggers.getLogger(__name__)


def EchoData(options):
    """Generate data configuration for surges model.
    """
    outstr = ''
    rhdict = options.get('rhandler', None)
    if rhdict:

        # recuperation date, reseau
        date = "{}".format(rhdict.get('resource', {}).get('date', ''))
        run = Date(date).hh
        term = "{}".format(Time(rhdict.get('options', {}).get('term', '')))
        term_hh = six.text_type(term)[:-3]
        chaine = "{}".format(rhdict.get('options', {}).get('chaine_utilise', '')).upper()[:1]

        # recuperation info conf
        forcage = "{}".format(rhdict.get('provider', {}).get('vconf', '')).upper()[-3:]
        forcage_mode = "{}".format(rhdict.get('provider', {}).get('vconf', '')).upper()

        if forcage_mode[-3:] in 'RED':
            forcage_mode = forcage_mode[-3:]
        else:
            forcage_mode = forcage_mode[-5:-3]

        Initial_w = "{}".format(rhdict.get('options', {}).get('initial_w', ''))
        Bufr_48h = "{}".format(rhdict.get('options', {}).get('maintien_bufr', ''))
        write_wind_txt = "{}".format(rhdict.get('options', {}).get('reecriture_vent', ''))
        freq_grib = "{}".format(rhdict.get('options', {}).get('freq_grib', ''))
        freq_forcage = "{}".format(rhdict.get('options', {}).get('freq_forcage', ''))

        deb_res   = 0
        mod = 'PR'
        if forcage_mode in 'AN':
            mod = 'AA'
            fin_res   = int(term_hh) - 1

        if forcage_mode in {'FC', 'PE'}:
            mod = 'PR'
            fin_res   = int(term_hh)

        Initial   = Initial_w
        if forcage in {'ARP', 'ARO', 'CEP', 'AOC'}:
            red_maree = 'NON'
            Initial   = Initial_w
        elif forcage in 'RED':
            red_maree = 'OUI'
            Initial   = 0
            deb_res   = -1
            fin_res   = deb_res

        # Nom du modele
        outstr += forcage + "\n"

        # Chaine redemarrage maree seule ==> OUI
        outstr += red_maree + "\n"

        # Echeance simulation
        outstr += term_hh + "\n"

        # initial initial_w : Echeance pour Generation des fichiers guess (h). En general initial_w et initial sont identiques;
        outstr += six.text_type(Initial) + "  " + six.text_type(Initial_w) + "\n"

        # PR (Prevision) ou AA (Analyse)
        outstr += mod + "\n"

        # Date (mais date du fichier guess prioritaire)
        #   outstr += Date(date).ymdhm + "\n"
        outstr += "200402090000\n"

        # Echeance resultat debut et fin (h)
        outstr += six.text_type(deb_res) + "  " + six.text_type(fin_res) + "\n"

        # frequence forcage (min)
        outstr += freq_forcage + "\n"

        # frequence resultat (min) sortie grib
        outstr += freq_grib + "\n"

        # Reseau
        outstr += "{}\n".format(run)

        # Chaine utilisee (Oper ou Double) !! si D alors change le code_modele ASURWARPD par ex
        outstr += chaine + "\n"

        # Chaine maintien BUFR sur 48hmax
        outstr += Bufr_48h + "\n"

        # Reecriture vent
        outstr += write_wind_txt

    # NB: The result have to be a file like object !
    return six.StringIO(outstr)


def RulesGribFunction(options):
    """Generate a simple rules file for grib_filter (UV 10m, Pmer) grib_api tools.

    This function is designed to be used with a function store.
    """
    outstr = ''
    outstr += "if( (table2Version==1) ){\n"
    outstr += "if( (indicatorOfParameter==2) && (indicatorOfTypeOfLevel==102) ){\n write;\n}\n"
    outstr += "if( ( level == 10 ) && (indicatorOfParameter==33) ){\n write;\n}\n"
    outstr += "if( ( level == 10 ) && (indicatorOfParameter==34) ){\n write;\n}"
    outstr += "}"

    # NB: The result have to be a file like object !
    return six.StringIO(outstr)
