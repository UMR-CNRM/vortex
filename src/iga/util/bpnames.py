#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Functions and tools to handle resources names or other kind of names.
"""

#: No automatic export
__all__ = []

import sys

import footprints
logger = footprints.loggers.getLogger(__name__)


_arpcourt_vconf = ('courtfr', 'frcourt', 'court')
_arome_vconf    = ('3dvarfr',)

def faNames(cutoff, reseau, model, filling=None, vapp=None, vconf=None):
    if cutoff == 'assim' and vconf not in _arpcourt_vconf:
        if vconf in _arome_vconf:
            map_suffix = dict(
                zip(
                    zip(
                        (cutoff,) * 2,
                        (9, 21)
                    ),
                    ('r09', 'r21')
                )
            ) 
        else:
            map_suffix = dict(
                zip(
                    zip(
                        (cutoff,) * 4,
                        (0, 6, 12, 18)
                    ),
                    ('r00', 'r06', 'r12', 'r18')
                )
            )
    elif cutoff == 'production' and vconf not in _arpcourt_vconf:
        suffix_r0 = 'rAM' if model == 'arpege' else 'rCM'
        map_suffix = dict(
            zip(
                zip(
                    (cutoff,) * 8,
                    range(0, 24, 3)
                ),
                (suffix_r0, 'rTR', 'rSX', 'rNF', 'rPM', 'rQZ', 'rDH', 'rVU')
            )
        )
    elif vconf in _arpcourt_vconf:
        map_suffix = {(cutoff, 0): 'rCM'}
    else:
        logger.warning(
            "The cutoff attribute of the ressource %s is incorrect",
            cutoff
        )
        return None
    # suffix choice
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
    elif model == 'surfex':
        model_info = vapp[:4].upper()
    elif model == 'hycom':
        model_info = 'HYCOM'
    else:
        logger.critical('Unknown model <%s> for op names fabrik', model)
        raise ValueError('Unknown model')
    return model_info, suffix


def gribNames(cutoff, reseau, model, run=None, vapp=None, vconf=None,
              force_courtfr=False):
    logger.debug('model %s run %s', model, run)
    if model == 'arome':
        map_suffix = dict(
            zip(
                range(0, 24, 3),
                map('r'.__add__, ('AM', 'TR', 'SX', 'NF', 'PM', 'QZ', 'DH', 'VU'))
            )
        )
        prefix = 'GRID'
        suffix = map_suffix[reseau]
        if force_courtfr:
            suffix = 'rCM'
    elif model == 'arpege' and run is not None:
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
        if cutoff == 'assim' and vconf not in _arpcourt_vconf:
            map_suffix = dict(
                zip(
                    zip(
                        (cutoff,) * 4,
                        (0, 6, 12, 18)
                    ),
                    ('00', '06', '12', '18')
                )
            )
        elif cutoff == 'production' and vconf not in _arpcourt_vconf:
            map_suffix = dict(
                zip(
                    zip(
                        (cutoff,) * 4,
                        (0, 6, 12, 18)
                    ),
                    ('rAM', 'rSX', 'rPM', 'rDH')
                )
            )
        elif vconf in _arpcourt_vconf:
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

        * suite,
        * geometry,
        * fmt
    """
    suite_map = dict(dble='dbl', mirr='oper')
    info = getattr(resource, provider.realkind + '_pathinfo',
                   resource.vortex_pathinfo)()
    for mnd in ('suite', 'igakey', 'fmt'):
        if mnd not in info:
            info[mnd] = getattr(provider, mnd, None)
    # patch: if model is not in info we must provide it through the
    # provider's attributes: model or vapp
    if 'model' not in info:
        info['model'] = getattr(provider, 'model', getattr(provider, 'vapp'))
    # In the inline cache, Hycom data are stored in the "vagues" directory
    info['model'] = dict(hycom='vagues').get(info['model'], info['model'])
    # The suite may not e consistent between the vortex cache and the inline cache
    info['suite'] = suite_map.get(info['suite'], info['suite'])
    return info


def clim_bdap_bnames(resource, provider):
    """docstring for clim_bdap_bnames"""
    if 'arome' in resource.model:
        localname = 'BDAP_frangp_isba' + str(resource.month)
    elif resource.model == 'aladin':
        if "08" in resource.geometry.rnice:
            #clim_dap.caled01.m01
            resolution = "01"
        else:
            resolution = "025"
        if "caled" in resource.geometry.area:
            igadomain = "caled"
        else:
            raise ValueError('Could not evaluate <igadomain> in {!r}'.format(resource.geometry))
        localname = 'clim_dap' + "." + igadomain + resolution + '.m' + str(resource.month)
    else:
        localname = 'const.clim.' + resource.geometry.area + '_m' + str(resource.month)
    return localname


def clim_model_bnames(resource, provider):
    """docstring for clim_model_bnames"""
    if resource.model == 'arome' or resource.model == 'aladin':
        localname = 'clim_' + resource.geometry.area + '_isba' + str(resource.month)
    elif resource.model == 'arpege':
        localname = 'clim_t' + str(resource.truncation) + '_isba' + str(resource.month)
    else:
        raise ValueError('Unknown model {:s} in clim_model_bnames'.format(resource.model))
    return localname


def rawfields_bnames(resource, provider):
    """docstring for rawfileds_bnames"""
    if resource.origin == 'nesdis':
        return resource.fields + '.' + resource.origin + '.' + 'bdap'
    elif resource.origin == 'ostia':
        return resource.fields + '.' + resource.origin
    elif resource.fields == 'seaice':
        return 'ice_concent'
    else:
        return None


def geofields_bnames(resource, provider):
    """docstring for geofields_bnames"""
    return 'ICMSHANAL' + resource.fields.upper()


def analysis_bnames(resource, provider):
    """docstring for analysis_bnames"""
    model_info, suffix = faNames(
        resource.cutoff, resource.date.hour, resource.model, resource.filling,
        vapp=provider.vapp, vconf=provider.vconf,
    )
    #patch for the different kind of analysis (surface and atmospheric)
    if ( resource.model == 'arome' and resource.filling == 'surf' ) or resource.model == 'surfex':
        return 'INIT_SURF.fa.' + suffix
    elif resource.model == 'hycom' and resource.filling == 'surf':
        if provider.vconf[:3] == 'atl':
            DOM = ""
        elif provider.vconf[:3] == 'med':
            DOM = "MED_"
        anabase = 's_init_sort'
        return anabase + '_' + provider.vconf[-3:] + '_' + DOM + 'ana' + '.' + resource.date.ymdh
    else:
        anabase = 'ICMSH' + model_info + 'INIT'
        if resource.filling == 'surf':
            anabase += '_SURF'
        return  anabase + '.' + suffix


def historic_bnames(resource, provider):
    """docstring for historic_bnames"""
    if resource.model == 'surfex':
        return histsurf_bnames(resource, provider)
    model_info, suffix = faNames(resource.cutoff, resource.date.hour, resource.model,
                                 vapp=provider.vapp, vconf=provider.vconf)
    if provider.vconf == 'pearp':
        return 'ICMSHPREV' + '+' + resource.term.fmthour + '.' + suffix
    else:
        return 'ICMSH' + model_info + '+' + resource.term.fmthour + '.' + suffix

def histsurf_bnames(resource, provider):
    """docstring for histsurf"""
    model_info, suffix = faNames(resource.cutoff, resource.date.hour, resource.model,
                                 vapp=provider.vapp, vconf=provider.vconf)
    reseau = resource.date.hour
    map_suffix = dict(
        zip(
            range(0, 24, 3),
            map('r'.__add__, ('CM', 'TR', 'SX', 'NF', 'PM', 'QZ', 'DH', 'VU'))
        )
    )
    suffix = map_suffix[reseau]
    return 'ICMSH' + model_info + '+' + resource.term.fmthour + '.sfx.' + suffix


def gridpoint_bnames(resource, provider):
    """docstring for gridpoint_bnames"""
    cutoff, reseau, model = resource.cutoff, resource.date.hour, resource.model
    logger.debug('gridpoint_bnames: cutoff %s reseau %s model %s',
                 cutoff, reseau, model)
    logger.debug('gridpoint_bnames: member %s', provider.member)
    if resource.nativefmt == 'fa':
        model_info, suffix = faNames(resource.cutoff, resource.date.hour, resource.model,
                                     vapp=provider.vapp, vconf=provider.vconf)
        localname = 'PF' + model_info + resource.geometry.area + '+' \
            + resource.term.fmthour + '.' + suffix
    elif resource.nativefmt == 'grib':
        if resource.model == 'arpege':
            prefix, suffix = gribNames(cutoff, reseau, model, provider.member,
                                       vapp=provider.vapp, vconf=provider.vconf)
            nw_term = "{0:03d}".format(resource.term.hour)
            if provider.member is not None:
                localname = prefix + '_' + suffix + '_' + str(provider.member) + '_' \
                    + resource.geometry.area + '_' + resource.term.fmthour
            else:
                localname = prefix + suffix + nw_term + resource.geometry.area
        elif resource.model == 'arome':
            prefix, suffix = gribNames(cutoff, reseau, model, provider.member,
                                       vapp=provider.vapp, vconf=provider.vconf)
            localname = prefix + resource.geometry.area + suffix + resource.term.fmthour
        else:
            return None
    else:
        return None
    return localname


def varbc_bnames(resource, provider):
    """docstring for varbc_bnames"""
    reseau, model, stage  = resource.date.hour, resource.model, resource.stage
    if model in ['reunion', 'aladin', 'caledonie', 'antiguy', 'polynesie']:
        suffix = '_alad'
    elif model == "arpege":
        suffix = ''
    elif model == "arome":
        suffix = '_aro'
    else:
        raise ValueError('Unknown model {:s} in varbc_bnames'.format(model))
    if stage == 'merge':
        localname = 'VARBC.merge.' + str(reseau)
    else:
        localname = 'VARBC.cycle' + suffix + '.r' + str(reseau)
    return localname


def boundary_bnames(resource, provider):
    """docstring for boundary_bnames"""
    cutoff, reseau, model, term = resource.cutoff, resource.date.hour, resource.model, resource.term
    if 'arome' in model:
        if hasattr(resource, 'source_conf'):
            is_court = resource.source_conf in ('court', 'courtfr', 'frcourt')
        else:
            is_court = resource.date.hour == 0
        _, suffix = gribNames(cutoff, reseau, model, force_courtfr=is_court)
        nw_term = "{0:03d}".format(term.hour)
        localname = 'ELSCFAROMALBC' + nw_term + '.' + suffix
    else:
        _, suffix = faNames(cutoff, reseau, model)
        nw_term = "{0:03d}".format(resource.term.hour)
        localname = 'ELSCFALADALBC' + nw_term + '.' + suffix
    return localname


def refdata_bnames(resource, provider):
    """docstring for refdata_bnames."""
    cutoff, reseau, model = resource.cutoff, resource.date.hour, resource.model
    logger.debug('cutoff %s reseau %s model %s', cutoff, reseau, model)
    u_prefix, suffix = gribNames(cutoff, reseau, model)
    localname = 'refdata' + '.' + suffix
    return localname


def bgstderr_bnames(resource, provider):
    if provider.igakey == 'france':
        #errgrib_scr type
        return 'errgrib_scr.r' + str(resource.date.hour)
    else:
        #I have to calculate a new date so as to get the correct run
        prefix = 'errgrib'
        if resource.term.hour in [3, 9]:
            delta = 'PT' + str(resource.term.hour + 3) + 'H'
            suffix = resource.date + delta
            stdname = resource.cutoff
        elif resource.term == 12:
            delta = 'PT' + str(resource.term.hour) + 'H'
            suffix = resource.date + delta
            stdname = 'production_' + 'dsbscr'
        return prefix + '_' + stdname + '.' + suffix.compact()


def observations_bnames(resource, provider):
    """docstring for observations_bnames"""
    fmt, part = resource.nativefmt, resource.part
    cutoff, reseau, model = resource.cutoff, resource.date.hour, resource.model
    day = str(resource.date.day)
    u_prefix, suffix = gribNames(cutoff, reseau, model)
    dico_names = {
        'obsoul': 'obsoul' + '.' + part + '.' + suffix,
        'ecma': {
            'surf': 'ECMA.surf' + '.' + str(int(reseau)) + '.' + str(reseau) + '.tar',
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
    searched_func = resource.realkind + '_bnames'
    if hasattr(itself, searched_func):
        return getattr(itself, searched_func)(resource, provider)
    else:
        if resource.realkind == 'rtcoef':
            return resource.realkind + '.tar'
        if resource.realkind == 'matfilter':
            return 'matrix.fil.' + resource.scope.area
        if resource.realkind == 'namelist':
            return resource.source
        if resource.realkind == 'namselect':
            return resource.source
        if resource.realkind == 'blacklist':
            if 'loc' in resource.scope:
                return 'LISTE_LOC'
            else:
                return 'LISTE_NOIRE_LOC'
        if resource.realkind == 'bcor':
            return 'bcor_' + resource.satbias + '.dat'
        if resource.realkind == 'obsmap':
            return 'BATOR_MAP_' + resource.cutoff


def global_snames(resource, provider):
    """global names for soprano provider"""
    cutoff = resource.cutoff
    if cutoff == 'assim':
        map_suffix = dict(
            zip(
                zip(
                    (cutoff,)*4,
                    (0, 6, 12, 18)
                ),
                ('00', '06', '12', '18')
            )
        )
    elif cutoff == 'production':
        map_suffix = dict(
           zip(
               zip(
                   (cutoff,)*24,
                   (0, 1, 2, 3, 4, 5,6 ,7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23)
               ),
               ('00', '01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12', '13', '14', '15', '16', '17', '18', '19', '20', '21', '22', '23')
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
    vapp = getattr(provider, 'vapp', None)
    if resource.realkind == 'rawfields':
        if resource.origin == 'ostia' and resource.fields == 'sst':
            bname = 'sst.ostia'
        if resource.origin == 'bdm' and resource.fields == 'seaice':
            bname = 'SSMI.AM'
    if resource.realkind == 'observations':
        suff = map_suffix[(cutoff, resource.date.hour)]
        if vapp == 'arpege':
            modsuff = ''
        else:
            modsuff = '_' + vapp.upper()
        if resource.nativefmt == 'grib':
            if resource.part == 'sev':
                bname = 'SEVIRI' + modsuff + '.' + suff + '.grb'
        elif resource.nativefmt == 'obsoul':
            if resource.part == 'conv':
                bname = 'OBSOUL1F' + modsuff + '.' + suff
            elif resource.part == 'prof':
                bname = 'OBSOUL2F' + modsuff + '.'+ suff
            elif resource.part == 'surf':
                bname = 'OBSOUL_SURFAN' + modsuff + '.' + suff
        elif resource.nativefmt == 'bufr':
            bname = resource.nativefmt.upper() + '.' + resource.part + modsuff + '.' + suff
        elif resource.nativefmt == 'netcdf':
            if resource.part == 'sev000':
                bname = resource.nativefmt.upper() + '.' + resource.part + modsuff + '.' + suff
        logger.debug("global_snames cutoff %s suffixe %s", cutoff, suff)
    if resource.realkind == 'refdata':
        suff = map_suffix[(cutoff, resource.date.hour)]
        if vapp == 'arpege':
            modsuff = ''
        else:
            modsuff = '_' + vapp.upper()
        if resource.part == 'prof':
            bname = 'RD_2' + modsuff + '.' + suff
        elif resource.part == 'conv':
            bname = 'RD_1' + modsuff + '.' + suff
        elif resource.part == 'surf':
            bname = 'RD_SURFAN' + modsuff + '.' + suff
        else:
            bname = 'rd_' + resource.part + modsuff + '.' + suff
        print 'bname = ', bname
        logger.debug("global_snames cutoff %s suffixe %s", cutoff, suff)
    if resource.realkind == 'historic':
        bname = 'toto'
    return bname

