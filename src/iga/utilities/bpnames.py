#!/bin/env python
# -*- coding:Utf-8 -*-

r"""
Functions and tools to handle resources names or other kind of names.
"""

#: No automatic export
__all__ = []

import sys
import logging


def faNames(cutoff, reseau, model, filling=None):
    if cutoff == 'assim':
        map_suffix = dict(
             zip(
                 zip(
                     (cutoff,)*4,
                     (0, 6, 12, 18)
                 ),
                 ('r00', 'r06', 'r12','r18')
             )
         )
    else:
        map_suffix = dict(
            zip(
                zip(
                    (cutoff,)*4,
                    (0, 6, 12, 18)
                ),
                ('rAM', 'rSX' , 'rPM', 'rDH')
            )
        )
    #suffix choice
    suffix = map_suffix[(cutoff, reseau)]
    if model == 'arpege':
        if filling == 'surf':
            model_info = 'ANAL'
        else:
            model_info = 'ARPE'
    elif model == 'arome':
        model_info = 'AROM'
    elif model == 'aladin':
        model_info = 'ALAD'
    return model_info, suffix
    
def gribNames(cutoff, reseau, model, run=None):
    logging.debug('model %s run %s', model, run)
    if model == 'arome':
        map_suffix = dict(
            zip(
                range(0, 24, 3),
                map('r'.__add__, ('CM','TR','SX','NF','PM','QZ','DH','VU'))
            )
        )
        prefix = 'GRID'
        suffix = map_suffix[reseau]
    elif model == 'arpege' and run:
        map_suffix = dict(
            zip(
                (6, 18),
                ('SX', 'DH')
            )
        )
        prefix = 'fc'
        suffix = map_suffix[reseau]
    elif model == 'arpege' and not run:
        logging.debug('cutoff %s', cutoff)
        if cutoff == 'assim':
            map_suffix = dict(
                 zip(
                     zip(
                         (cutoff,)*4,
                         (0, 6, 12, 18)
                     ),
                     ('00', '06', '12','18')
                 )
             )
        elif cutoff == 'production':
            map_suffix = dict(
                zip(
                    zip(
                        (cutoff,)*4,
                        (0, 6, 12, 18)
                    ),
                    ('rAM', 'rSX' , 'rPM', 'rDH')
                )
            )       
        prefix = 'PE'
        suffix = map_suffix[(cutoff, reseau)]
    else:
        return None
    return prefix, suffix


def global_pnames(provider, resource):
    """
    Return a dictionary whose content is the paired (key, values) so as to
    resolved the path using the config parser.
    Must defined:
        -suite,
        -geometry,
        -fmt
    """
    info = getattr(resource, provider.realkind() + '_pathinfo',
                   resource.vortex_pathinfo)()
    for mnd in ("suite", "igakey", "fmt"):
        if mnd not in info:
            info[mnd] = getattr(provider, mnd, None)
    return info

def clim_bdap_bnames(resource):
    """docstring for clim_bdap_bnames"""
    if 'arome' in resource.model:
        localname = 'BDAP_frangp_isba' + str(resource.month)
    elif resource.model == 'aladin':
        if "08" in resource.geometry.resolution:
            #clim_dap.caled01.m01
            resolution = "01"
        else:
            resolution = "025"
        if "caled" in resource.geometry.area:
            igadomain = "caled"
        localname = 'clim_dap' + "." + igadomain + resolution + '.m' +\
str(resource.month)
    else:
        localname = 'const.clim.' + resource.geometry.area + '_m' + str(resource.month)
    return localname

def clim_model_bnames(resource):
    """docstring for clim_model_bnames"""
    if resource.model == 'arome' or resource.model == 'aladin':
        #if "08" in resource.geometry.resolution:
        #    #clim_dap.caled01.m01
        #    resolution = "01"
        #else:
        #    resolution = "025"
        #if "caledonie" in resource.geometry.area:
        #    igadomain = "caledonie"
        #localname = 'clim_' + igadomain + resolution + '.' + str(resource.month)
        localname = 'clim_' + resource.geometry.area + '_isba' + str(resource.month)
    elif resource.model == 'arpege':
        localname = 'clim_t' + str(resource.truncation) + '_isba' + str(resource.month)
    return localname

def rawfields_bnames(resource):
    """docstring for rawfileds_bnames"""
    if resource.origin == 'nesdis':
        return resource.fields + '.' + resource.origin + '.' + 'bdap'
    elif resource.origin == 'ostia':
        return resource.fields + '.' + resource.origin
    elif resource.fields == 'seaice':
        return 'ice_concent'
    else:
        return None

def geofields_bnames(resource):
    """docstring for geofields_bnames"""
    return 'ICMSHANAL' + resource.fields.upper()

def analysis_bnames(resource):
    """docstring for analysis_bnames"""
    model_info, suffix = faNames(
        resource.cutoff, resource.date.hour, resource.model, resource.filling)
    #patch for the different kind of analysis (surface and atmospheric)
    if resource.filling == 'surf':
        return 'ICMSH' + model_info + 'INIT_SURF.' + suffix
    else:
        return 'ICMSH' + model_info + 'INIT.' + suffix

def historic_bnames(resource):
    """docstring for historic_bnames"""
    model_info, suffix = faNames(resource.cutoff, resource.date.hour, resource.model)
    return 'ICMSH' + model_info + '+' + str(resource.term) + '.' + suffix

#def gridpoint_bnames(resource):
#    """docstring for gridpoint_bnames"""
#    cutoff, reseau, model = resource.cutoff, resource.date.hour, resource.model
#    run = getattr(resource, 'run', None)
#    if resource.nativefmt == 'fa':
#        model_info, suffix = faNames(resource.cutoff, resource.date.hour, resource.model)
#        localname = 'PF' + model_info + resource.geometry.area + '+'\
#+ str(resource.term) + '.' + suffix
#    elif resource.nativefmt == 'grib':
#        if resource.model == 'arpege':
#            prefix, suffix = gribNames(cutoff, reseau, model, run)
#            nw_term = "{0:03d}".format(resource.term)
#            if run:
#                localname = prefix + '_' + suffix + '_' + str(run) + '_' +\
#resource.geometry.area + '_' + str(resource.term)
#            else:
#                localname = prefix + suffix + nw_term + resource.geometry.area
#        elif resource.model == 'arome':
#            prefix, suffix = gribNames(cutoff, reseau, model, run)
#            localname = prefix + resource.geometry.area + suffix +\
#str(resource.term)
#        else:
#            return None
#    return localname

def gridpoint_bnames(resource, member=None):
    """docstring for gridpoint_bnames"""
    cutoff, reseau, model = resource.cutoff, resource.date.hour, resource.model
    logging.debug('gridpoint_bnames: cutoff %s reseau %s model %s',
                  cutoff, reseau, model)
    logging.debug('gridpoint_bnames: member %s', member)
    if resource.nativefmt == 'fa':
        model_info, suffix = faNames(resource.cutoff, resource.date.hour, resource.model)
        localname = 'PF' + model_info + resource.geometry.area + '+'\
+ str(resource.term) + '.' + suffix
    elif resource.nativefmt == 'grib':
        if resource.model == 'arpege':
            prefix, suffix = gribNames(cutoff, reseau, model, member)
            nw_term = "{0:03d}".format(resource.term)
            if member:
                localname = prefix + '_' + suffix + '_' + str(member) + '_' +\
resource.geometry.area + '_' + str(resource.term)
            else:
                localname = prefix + suffix + nw_term + resource.geometry.area
        elif resource.model == 'arome':
            prefix, suffix = gribNames(cutoff, reseau, model, member)
            localname = prefix + resource.geometry.area + suffix +\
str(resource.term)
        else:
            return None
    return localname


def varbc_bnames(resource):
    """docstring for varbc_bnames"""
    reseau, model = resource.date.hour, resource.model
    if model in ['reunion', 'aladin', 'caledonie', 'antiguy', 'polynesie']:
        suffix = '_alad'
    elif model == "arpege":
        suffix = ''
    elif model == "arome":
        suffix = '_aro'
    localname = 'VARBC.cycle' + suffix + '.r' + str(reseau)
    return localname

def elscf_bnames(resource):
    """docstring for elscf_bnames"""
    cutoff, reseau, model, term = resource.cutoff, resource.date.hour, resource.model, resource.term
    if 'arome' in model:
        prefix, suffix = gribNames(cutoff, reseau, model)
        nw_term = "{0:03d}".format(term)
        localname = 'ELSCFAROMALBC' + nw_term + '.' + suffix
    else:
        model_info, suffix = faNames(cutoff, reseau, model)
        nw_term = "{0:03d}".format(resource.term)
        localname = 'ELSCFALADALBC' + nw_term + '.' + suffix
    return localname

def refdata_bnames(resource):
    """docstring for refdata_bnames."""
    cutoff, reseau, model = resource.cutoff, resource.date.hour, resource.model
    logging.debug('cutoff %s reseau %s model %s', cutoff, reseau, model)
    prefix, suffix = gribNames(cutoff, reseau, model)
    localname = 'refdata' + '.' + suffix
    return localname

def observations_bnames(resource):
    """docstring for observations_bnames"""
    fmt, part = resource.nativefmt, resource.part
    cutoff, reseau, model = resource.cutoff, resource.date.hour, resource.model
    day = str(resource.date.day)
    prefix, suffix = gribNames(cutoff, reseau, model)
    logging.debug('fmt %s part %s cutoff %s reseau %s model %s day %s suffix %s',
                  fmt, part, cutoff, reseau, model, day, suffix)
    dico_names = {
        'obsoul' : 'obsoul' + '.' + part + '.' + suffix,
        'ecma' : {
            'surf': 'ECMA.surf' + '.' + str(int(reseau)) + '.' + str(reseau) +
'.tar',
            'conv': 'ECMA.conv' + '.' + day + '.' + str(reseau) + '.tar',
            'prof': 'ECMA.prof' + '.' + day + '.' + str(reseau) + '.tar',
        }

    }
    localname = dico_names[fmt][0] + '.' + part + '.'
    logging.debug('localname %s', localname)
    if dico_names[fmt][1]:
        localname += str(day) + '.' + suffix + dico_names[fmt][1]
    else:
        localname += suffix
    #localname = fmt + '.' + part + '.' + suffix
    return localname

def global_bnames(resource, provider):
    """Return the basename of the resource."""
    #itself = sys.modules.get(__name__)
    for elmt in sys.modules:
        if sys.modules[elmt]:
            try:
                current_file = sys.modules[elmt].__file__
            except AttributeError:
                current_file = None
            if current_file == __file__:
                itself = sys.modules[elmt]
    searched_func = resource.realkind() + '_bnames'
    attr = hasattr(itself, searched_func)
    member = getattr(provider, 'member', None)
    if member and attr:
        return getattr(itself, searched_func)(resource, member)
    elif attr:
        return getattr(itself, searched_func)(resource)
    else:
        if resource.realkind() == 'rtcoef':
            return resource.realkind() + '.tar'
        if resource.realkind() == 'matfilter':
            return 'matrix.fil.' + resource.scopedomain.area
        if resource.realkind() == 'namelist':
            return resource.source
        if resource.realkind() == 'namelselect':
            return resource.realkind()

def global_snames(resource):
    """docstring for global_snames"""
    bname = None
    if resource.fields == 'seaice':
        bname = 'SSMI.AM'
    return bname

