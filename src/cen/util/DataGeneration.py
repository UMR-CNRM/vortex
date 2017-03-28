#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import os

import footprints
logger = footprints.loggers.getLogger(__name__)

from StringIO import StringIO

from vortex.tools.date import Date

_domain_map = dict(alp='_al', pyr='_py', cor='_co')


def DirextGeneration(options):
    """Generate DIREXT file for the BDAP extraction of P files (Arpege fields used by Safran).
    
    This function is designed to be used with a function store.
    """
    
    outstr = ''
    rhdict = options.get('rhandler', None)
    t = options.get('ticket', None)
    if rhdict:
        outstr += "{}\n".format(rhdict.get('options', {}).get('term', '')) # echeance
        outstr += "{}\n".format( _domain_map["{:s}".format(rhdict.get('provider', {}).get('vconf', None))]) # domain
        outstr += '734\n' #nompt
        #--------------------------------------------------------------------------------------------------------------------
        # nompt est le numéro de routage vers la BDPE des fichiers P produits par l'extraction de la BDAP,  
        # sa valeur est à 11962 (resp 11963 et 11964) pour la chaine déterministe (produits existants sur le portail soprano)
        # l'orgine de la valeur 734 est inconnue, il n'y a pas de produit associé sur le portail soprano...
        #-------------------------------------------------------------------------------------------------------------------- 
        outstr += '2\n' #ioptfic
        #--------------------------------------------------------------------------------------------------------------------
        # ioptfic=3 pour créer fichier P et p, ioptfic=2 pour créer seulement les P et ioptfic=1 pour seulement les p
        #--------------------------------------------------------------------------------------------------------------------
        member  = t.env.getvar("OP_MEMBER")
        mod     = rhdict.get('options', {}).get('mod', 'PEARP0') + member
        outstr += "{}\n".format(mod)
        outstr += "{}\n".format(member)
    else:
        raise HandlerError('Expected informations on the resource missing')  

    # NB: The result have to be a file like object !
    return StringIO(outstr) 


def SapdatGeneration(options):
    """Generate the 'sapdat' file for the safran execution.
  
    This function is designed to be used with a function store.
    """

    outstr = ''
#    rhdict = options.get('rhandler', None)
#    t = options.get('ticket', None)
#    if rhdict:
#        date  = Date(rhdict.get('options', {}).get('date', ''))
#        year  = date.strftime('%y')
#        month = date.strftime('%m')
#        day   = date.strftime('%d')
#        hour  = date.hh 
#        outstr += "{} {} {} {}\n".format(year, month, day, hour)
#    else:
#        raise HandlerError('Expected informations on the resource missing')

    outstr += '17,01,27,06\n'
    outstr += '0,0,0\n'
    outstr += '3,1,1,3\n'
    outstr += '0\n'
    outstr += '1,1,1,1\n'

    return StringIO(outstr)

def SapfichGeneration(options):

    outstr = 'SAPLUI5'
    return StringIO(outstr)


def OPfileGeneration(options):
    """Generate the 'OPxxxxx' files containing links for the safran execution.
  
    This function is designed to be used with a function store.
    """

    outstr = os.getcwd() + '@'
    return StringIO(outstr) 
