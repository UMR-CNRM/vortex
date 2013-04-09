#!/bin/env python
# -*- coding: utf-8 -*-

r"""
Functions and tools to handle resources names or other kind of names.
"""

#: No automatic export
__all__ = []

import sys
from vortex.autolog import logdefault as logger
from vortex.tools.date import Date


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
    elif cutoff == 'short':
        map_suffix = {(cutoff, 0): 'rCM'}
    else:
        logger.warning(
            "The cutoff attribute of the ressource %s is incorrect",
            cutoff
        )
        return None
    #suffix choice
    # TODO: not safe in case the time is not defined
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
    logger.debug('model %s run %s', model, run)
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
        logger.debug('cutoff %s', cutoff)
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
        elif cutoff == 'short':
            map_suffix = {(cutoff, 0): 'rCM'}
        else:
            logger.warning(
                "The cutoff attribute of the ressource %s is incorrect",
                cutoff
            )
            return None
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
    #patch: if model is not in info we must provide it through the
    #provider's attributes: model or vapp
    if "model" not in info:
        info['model'] = getattr(provider, 'model', getattr(provider, 'vapp'))
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
        if resource.nativefmt != 'lfi':
            return 'ICMSH' + model_info + 'INIT_SURF.' + suffix
        else:
            return 'INIT_SURF.' + suffix
    else:
        return 'ICMSH' + model_info + 'INIT.' + suffix

def historic_bnames(resource):
    """docstring for historic_bnames"""
    model_info, suffix = faNames(resource.cutoff, resource.date.hour, resource.model)
    return 'ICMSH' + model_info + '+' + str(resource.term) + '.' + suffix

def histsurf_bnames(resource):
    """docstring for histsurf"""
    reseau = resource.date.hour
    map_suffix = dict(
        zip(
            range(0, 24, 3),
            map('r'.__add__, ('CM','TR','SX','NF','PM','QZ','DH','VU'))
        )
    )
    suffix = map_suffix[reseau]
    return 'PREP.lfi.' + suffix

def gridpoint_bnames(resource, member=None):
    """docstring for gridpoint_bnames"""
    cutoff, reseau, model = resource.cutoff, resource.date.hour, resource.model
    logger.debug('gridpoint_bnames: cutoff %s reseau %s model %s',
                  cutoff, reseau, model)
    logger.debug('gridpoint_bnames: member %s', member)
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
        u_prefix, suffix = gribNames(cutoff, reseau, model)
        nw_term = "{0:03d}".format(term)
        localname = 'ELSCFAROMALBC' + nw_term + '.' + suffix
    else:
        u_model_info, suffix = faNames(cutoff, reseau, model)
        nw_term = "{0:03d}".format(resource.term)
        localname = 'ELSCFALADALBC' + nw_term + '.' + suffix
    return localname

def refdata_bnames(resource):
    """docstring for refdata_bnames."""
    cutoff, reseau, model = resource.cutoff, resource.date.hour, resource.model
    logger.debug('cutoff %s reseau %s model %s', cutoff, reseau, model)
    u_prefix, suffix = gribNames(cutoff, reseau, model)
    localname = 'refdata' + '.' + suffix
    return localname

def bgerrstd_bnames(resource, ens=None):
    cutoff, term, ens, date = resource.cutoff, resource.term, ens, resource.date
    prefix = 'errgribvor'
    if ens == 'france':
        #errgrib_scr type
        delta = "P" + str(term) + "H"
        target_date = Date(date.add_delta(delta, fmt="yyyymmddhh"))
        new_run = int(target_date.get_date(fmt="hh"))
        stdname = "errgrib_scr.r"
        suffix = str(new_run)
        return stdname + suffix

    else:
        #I have to calculate a new date so as to get the correct run
        if term in [3, 9]:
            delta = "P" + str(term + 3) + "H"
            suffix = resource.date.add_delta(delta, fmt = "yyyymmddhhmnss")
            stdname = cutoff
        elif term == 12:
            delta = "P" + str(term) + "H"
            suffix = resource.date.add_delta(delta, fmt = "yyyymmddhhmnss")
            stdname = 'production_' + 'dsbscr'
        return prefix + '_' + stdname + '.' + suffix

def observations_bnames(resource):
    """docstring for observations_bnames"""
    fmt, part = resource.nativefmt, resource.part
    cutoff, reseau, model = resource.cutoff, resource.date.hour, resource.model
    day = str(resource.date.day)
    u_prefix, suffix = gribNames(cutoff, reseau, model)
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
    logger.debug('localname %s', localname)
    if dico_names[fmt][1]:
        localname += str(day) + '.' + suffix + dico_names[fmt][1]
    else:
        localname += suffix
    #localname = fmt + '.' + part + '.' + suffix
    return localname

def global_bnames(resource, provider):
    """Return the basename of the resource."""
    #itself = sys.modules.get(__name__)
    for elmt in list(sys.modules):
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
        if 'bgerrstd' in searched_func:
            return getattr(itself, searched_func)(resource, ens=provider.igakey)
        else:
            return getattr(itself, searched_func)(resource)
    else:
        if resource.realkind() == 'rtcoef':
            return resource.realkind() + '.tar'
        if resource.realkind() == 'matfilter':
            return 'matrix.fil.' + resource.scopedomain.area
        if resource.realkind() == 'namelist':
            return resource.source
        if resource.realkind() == 'namselect':
            return resource.source
        if resource.realkind() == 'blacklist':
            if 'loc' in resource.scope:
                return 'LISTE_LOC'
            else:
                return 'LISTE_NOIRE_LOC'
        if resource.realkind() == 'bcor':
            return 'bcor_' + resource.satbias + '.dat'
        if resource.realkind() == 'obsmap':
            return 'BATOR_MAP_' + resource.cutoff

def global_snames(resource):
    """global names for soprano provider"""
    cutoff = resource.cutoff
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
               ('AM', 'SX' , 'PM', 'DH')
           )
       )
    elif cutoff == 'short':
        map_suffix = {(cutoff, 0): 'rCM'}
    else:
        logger.warning(
            "The cutoff attribute of the ressource %s is incorrect",
            cutoff
        )
        return None

    bname = None
    if resource.realkind() == 'rawfields':
        if resource.origin == 'ostia' and resource.fields == 'sst':
            bname = 'sst.ostia'
        if resource.origin == 'bdm' and resource.fields == 'seaice':
            bname = 'SSMI.AM'
    if resource.realkind() == 'observations':
        suff = map_suffix[(cutoff, resource.date.hour)]
        if resource.nativefmt == 'obsoul' and resource.part == 'conv':
            bname = 'OBSOUL1F.' + suff
        if resource.nativefmt == 'obsoul' and resource.part == 'prof':
            bname = 'OBSOUL2F.' + suff
        if resource.nativefmt == 'obsoul' and resource.part == 'surf':
            bname = 'OBSOUL_SURFAN.' + suff
        if resource.nativefmt == 'bufr':
            bname = 'BUFR.' + resource.part + '.' + suff
        logger.debug("global_snames cutoff %s suffixe %s", cutoff, suff)
    if resource.realkind() == 'refdata':
        suff = map_suffix[(cutoff, resource.date.hour)]
        if resource.nativefmt == 'obsoul' and resource.part == 'conv':
            bname = 'RD_1.' + suff
        if resource.nativefmt == 'obsoul' and resource.part == 'prof':
            bname = 'RD_2.' + suff
        if resource.nativefmt == 'bufr':
            bname = 'rd_' + resource.part + '.' + suff
        if resource.part == 'surf':
            bname = 'RD_SURFAN' + '.' + suff
        logger.debug("global_snames cutoff %s suffixe %s", cutoff, suff)
    return bname

