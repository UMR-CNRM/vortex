#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Functions and tools to handle resources names or other kind of names.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import six
import re
import sys

from bronx.fancies import loggers
from bronx.stdtypes.date import Time, Date

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)

_arpcourt_vconf = ('courtfr', 'frcourt', 'court')
_arome_vconf = ('3dvarfr',)
_arpege_vconf = ('4dvarfr',)


def _reseau_suffix(cutoff, reseau, vconf=None, vapp=None, suffix_r=False):
    _reseau = '{:02d}'.format(int(reseau))
    if vconf in _arpcourt_vconf:
        reseau_suff = 'CM'
    elif cutoff == 'assim':
        reseau_suff = _reseau
    elif cutoff == 'production' and vconf == '4dvarfr':
        reseau_prod = {'00': 'AM', '01': '01', '02': '02', '03': 'TR', '04': '04',
                       '05': '05', '06': 'SX', '07': '07', '08': '08', '09': 'NF',
                       '10': '10', '11': '11', '12': 'PM', '13': '13', '14': '14',
                       '15': 'QZ', '16': '16', '17': '17', '18': 'DH', '19': '19',
                       '20': '20', '21': 'VU', '22': '22', '23': '23'}
        reseau_suff = reseau_prod[_reseau]
    elif cutoff == 'production' and vconf == 'pifrance' or vapp == 'pprod':
        reseau_prod = {'00': '00', '01': '01', '02': '02', '03': '03', '04': '04',
                       '05': '05', '06': '06', '07': '07', '08': '08', '09': '09',
                       '10': '10', '11': '11', '12': '12', '13': '13', '14': '14',
                       '15': '15', '16': '16', '17': '17', '18': '18', '19': '19',
                       '20': '20', '21': '21', '22': '22', '23': '23'}
        reseau_suff = reseau_prod[_reseau]
    elif vconf in ('angola0025', 'assmp1', 'assms1', 'assms2', 'atourxarp01', 'caledaro01',
                   'euratarpc01', 'frangparo0025', 'frangparoifs0025', 'globalarp02',
                   'globalarpc02', 'globalcep01', 'polyaro01',
                   'reuaro01', 'ctbto'):
        reseau_suff = _reseau
    else:
        logger.warning(
            "The attributes are incorrect : %s, %s, %s",
            cutoff, reseau, vconf
        )
    logger.info("Attributes : cutoff:%s, reseau:%s, vconf:%s, suffix_r:%s, reseau_suff:%s",
                cutoff, reseau, vconf, suffix_r, reseau_suff)
    if suffix_r:
        _suffix_r = 'r'
    else:
        _suffix_r = ''
    return '{}{}'.format(_suffix_r, reseau_suff)


def faNames(cutoff, reseau, model, filling=None, vapp=None, vconf=None):
    if cutoff == 'assim' and vconf not in _arpcourt_vconf:
        if vconf in _arome_vconf:
            assim_cutoffs = range(0, 24, 1)
        else:
            assim_cutoffs = range(0, 24, 3)
        if (vconf in _arome_vconf) and (model == 'surfex'):
            map_suffix = {(cutoff, h): 'r{:d}'.format(h) for h in assim_cutoffs}
        else:
            map_suffix = {(cutoff, h): 'r{:02d}'.format(h) for h in assim_cutoffs}
    elif cutoff == 'production' and vconf not in _arpcourt_vconf:
        suffix_r0 = 'rAM' if model == 'arpege' or model == 'surfex' else 'rCM'
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
    elif model == 'mocage':
        model_info = ''
    elif model == 'mfwam':
        model_info = 'MFWAM'
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
            map_suffix = {(cutoff, h): '{:02d}'.format(h) for h in (0, 6, 12, 18)}
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
        if cutoff == 'production' and vconf in _arpege_vconf:
            suffix = suffix[1:]
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
                   resource.generic_pathinfo)()
    # patch pearp : the arpege surface analysis from surfex is in 'autres', not in 'fic_day'
    if hasattr(resource, 'model'):
        if resource.model == 'surfex' and provider.vapp == 'arpege':
            info['fmt'] = 'autres'
        if provider.vapp == 'mocage' and provider.vconf == 'camsfcst':

            info['model'] = 'macc'
            info['igakey'] = 'france'

    for mnd in ('suite', 'igakey', 'fmt'):
        if mnd not in info:
            info[mnd] = getattr(provider, mnd, None)

    # patch: if model is not in info we must provide it through the
    # provider's attributes: model or vapp
    if 'model' not in info:
        info['model'] = getattr(provider, 'model', getattr(provider, 'vapp'))
    # In the inline cache, Hycom data are stored in the "vagues" directory
    info['model'] = dict(hycom='vagues', mfwam='vagues').get(info['model'], info['model'])
    # The suite may not e consistent between the vortex cache and the inline cache
    info['suite'] = suite_map.get(info['suite'], info['suite'])
    return info


def clim_bdap_bnames(resource, provider):
    if 'arome' in resource.model:
        localname = 'BDAP_frangp_isba' + six.text_type(resource.month)
    elif resource.model == 'aladin':
        if "08" in resource.geometry.rnice:
            # clim_dap.caled01.m01
            resolution = "01"
        else:
            resolution = "025"
        if "caled" in resource.geometry.area:
            igadomain = "caled"
        else:
            raise ValueError('Could not evaluate <igadomain> in {!r}'.format(resource.geometry))
        localname = 'clim_dap' + "." + igadomain + resolution + '.m' + six.text_type(resource.month)
    else:
        localname = 'const.clim.' + resource.geometry.area + '_m' + six.text_type(resource.month)
    return localname


def clim_model_bnames(resource, provider):
    if resource.model == 'arome' or resource.model == 'aladin':
        localname = 'clim_' + resource.geometry.area + '_isba' + six.text_type(resource.month)
    elif resource.model == 'arpege':
        localname = 'clim_t' + six.text_type(resource.truncation) + '_isba' + six.text_type(resource.month)
    else:
        raise ValueError('Unknown model {:s} in clim_model_bnames'.format(resource.model))
    return localname


def rawfields_bnames(resource, provider):
    if resource.origin == 'nesdis':
        return resource.fields + '.' + resource.origin + '.' + 'bdap'
    elif resource.origin == 'ostia':
        return resource.fields + '.' + resource.origin
    elif resource.fields == 'seaice':
        return 'ice_concent'
    else:
        return None


def obsfire_bnames(resource, provider):
    return 'GFASfires_H_fcst_' + resource.date.ymd + '.tar.gz'


def chemical_bc_bnames(resource, provider):
    return 'bc22_{0.ymdh:s}.nc'.format(resource.date + resource.term)


def geofields_bnames(resource, provider):
    return 'ICMSHANAL' + resource.fields.upper()


def analysis_bnames(resource, provider):
    model_info, suffix = faNames(
        resource.cutoff, resource.date.hour, resource.model, resource.filling,
        vapp=provider.vapp, vconf=provider.vconf,
    )
    # patch for the different kind of analysis (surface and atmospheric)
    if (resource.model == 'arome' and resource.filling == 'surf') or resource.model == 'surfex':
        if provider.vconf in _arome_vconf:
            return 'INIT_SURF.fa.' + suffix
        else:
            return 'ICMSHARPEINIT.' + suffix + '.sfx'
    elif resource.model == 'hycom' and resource.filling == 'surf':
        region_map = dict(atl='', med='_MED', oin='_OIN')
        mode_map = dict(fc='pre', an='ana')
        region = region_map.get(provider.vconf[:3], provider.vconf[:3])
        mode = mode_map.get(provider.vconf[4:][:2], None)

        config = provider.vconf[-3:] + region + '_' + mode
        if mode == 'ana':
            suffix = resource.date.ymdh
        # s_init_sort_cep_OIN_ana.2017070900     (T0)
        return 's_init_sort_' + config + '.' + six.text_type(suffix)
    elif resource.model == 'mfwam' and resource.filling == 'surf':
        suffix = resource.date.ymdhms
        suffix2 = resource.term.fmtraw2
        return 'LAW' + str(suffix) + '_' + str(suffix2)
    else:
        anabase = 'ICMSH' + model_info + 'INIT'
        if resource.filling == 'surf':
            anabase += '_SURF'
        return anabase + '.' + suffix


def historic_bnames(resource, provider):
    if resource.model == 'surfex':
        return histsurf_bnames(resource, provider)
    model_info, suffix = faNames(resource.cutoff, resource.date.hour, resource.model,
                                 vapp=provider.vapp, vconf=provider.vconf)

    if resource.model == 'hycom':
        region_map = dict(atl='', med='_MED', oin='_OIN')
        mode_map = dict(fc='pre', an='ana')
        region = region_map.get(provider.vconf[:3], provider.vconf[:3])
        mode = mode_map.get(provider.vconf[4:][:2], None)

        if mode is None:
            term0 = resource.term.hour
            delta = 'PT' + six.text_type(term0) + 'H'
            date_val = (resource.date + delta).ymdh
            config = provider.vconf[4:] + region
        else:
            date_val = (resource.date + resource.term).ymdh
            config = provider.vconf[-3:] + region + '_' + mode

        prefix = 's_init'
        if resource.term == 6 or (resource.term == 24 and mode is None):
            prefix = 's_init_sort'
            suffix = ''
        else:
            if mode is None:
                deltatime = Time(72)
                suffix = '.{0:03d}'.format((resource.term + deltatime).hour)
            else:
                suffix = '.{0:03d}'.format(resource.term.hour)
        return '{0:s}_{1:s}.{2:s}{3:s}'.format(prefix, config, date_val, suffix)

    if resource.model == 'mfwam':
        if hasattr(resource, 'fields'):
            prefix = resource.fields.upper()
            return prefix + resource.date.ymdhms + '_' + resource.term.fmtraw2
        else:
            return resource.date.ymdhms + '_' + resource.term.fmtraw2

    if provider.vconf == 'camsfcst':
        return 'HM' + resource.geometry.area + '+' + resource.term

    if provider.vconf == 'pearp':
        return 'ICMSHPREV' + '+' + resource.term.fmthour + '.' + suffix
    else:
        return 'ICMSH' + model_info + '+' + resource.term.fmthour + '.' + suffix


def pts_bnames(resource, provider):
    if resource.model == 'hycom':
        # s_ddpts_aro_OIN_pre
        # s_ddpts_cep_OIN_ana
        region_map = dict(atl='_', med='_MED_', oin='_OIN_')
        mode_map = dict(fc='pre', an='ana')
        region = region_map.get(provider.vconf[:3], provider.vconf[:3])
        mode = mode_map.get(provider.vconf[4:][:2], None)
        if mode is None:
            # 'restart'
            config = provider.vconf[4:]
        else:
            config = provider.vconf[-3:] + region + mode

        if resource.fields == '_huv.txt':
            return '_huv_{0:s}.txt'.format(config)
        else:
            return resource.fields + '_' + config


def bufr_bnames(resource, provider):
    if resource.model == 'hycom':
        region_map = dict(atl='', med='_MED', oin='_OIN')
        mode_map = dict(fc='prv', an='ana')
        region = region_map.get(provider.vconf[:3], provider.vconf[:3])
        mode = mode_map.get(provider.vconf[4:][:2], None)
        return '{0:s}_{1:03d}_{2:s}_{3:d}{4:s}.bfr'.format(mode, resource.timeslot.hour, provider.vconf[-3:],
                                                           int(resource.date.hh), region)


def SurgesResultNative_bnames(resource, provider):
    if resource.model == 'hycom':
        region_map = dict(atl='_', med='_MED_')
        mode_map = dict(fc='pre', an='ana')
        region = region_map.get(provider.vconf[:3], provider.vconf[:3])
        mode = mode_map.get(provider.vconf[4:][:2], None)
        config = provider.vconf[-3:] + region + mode
        prefix = re.sub(".nc", "", resource.fields)
        return prefix + '_' + config + '.nc.gz'


def SurgesWw3coupling_bnames(resource, provider):
    if resource.model == 'hycom':
        region_map = dict(atl='_', med='_MED_')
        mode_map = dict(fc='pre', an='ana')
        region = region_map.get(provider.vconf[:3], provider.vconf[:3])
        mode = mode_map.get(provider.vconf[4:][:2], None)
        config = provider.vconf[-3:] + region + mode

        config_new = config
        if re.match(r'level', resource.fields):
            config_new = '.' + config
        return resource.fields + config_new + '.gz'


def AltidataWave_bnames(resource, provider):
    if resource.model == 'mfwam':
        return 'altidata_{0:s}'.format(resource.date.ymdhm)


def histsurf_bnames(resource, provider):
    model_info, suffix = faNames(resource.cutoff, resource.date.hour, resource.model,
                                 vapp=provider.vapp, vconf=provider.vconf)
    reseau = resource.date.hour
    if resource.cutoff == 'production':
        if reseau in range(0, 24, 3):
            map_suffix = dict(
                zip(
                    range(0, 24, 3),
                    map('r'.__add__, ('CM', 'TR', 'SX', 'NF', 'PM', 'QZ', 'DH', 'VU'))
                )
            )
            suffix = map_suffix[reseau]
            if resource.model == 'arpege' and reseau == '00':
                suffix = 'rAM'
            bname = 'ICMSH' + model_info + '+' + resource.term.fmthour + '.sfx.' + suffix

    elif resource.cutoff == 'assim':
        bname = 'PREP.fa_' + '{:02d}'.format(reseau) + '.{:02d}'.format(resource.term.hour)

    return bname


def gridpoint_bnames(resource, provider):
    cutoff, reseau, model = resource.cutoff, resource.date.hour, resource.model
    logger.debug('gridpoint_bnames: cutoff %s reseau %s model %s',
                 cutoff, reseau, model)
    logger.debug('gridpoint_bnames: member %s', provider.member)
    if resource.nativefmt == 'fa':
        if resource.model == 'mocage':
            if resource.kind == 'gridpoint':
                model_info, suffix = faNames(resource.cutoff, resource.date.hour, resource.model,
                                             vapp=provider.vapp, vconf=provider.vconf)
                localname = 'RUN1_HM' + resource.geometry.area + '+' \
                    + Date(resource.date.ymdh + '/-PT12H').ymdh
            else:
                pass
        else:
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
                localname = prefix + '_' + suffix + '_' + six.text_type(provider.member) + '_' \
                    + resource.geometry.area + '_' + resource.term.fmthour
            else:
                if resource.term.fmthour == '0108' and prefix == 'PE':
                    suffix = 'PM'
                localname = prefix + suffix + nw_term + resource.geometry.area
        elif resource.model == 'arome':
            prefix, suffix = gribNames(cutoff, reseau, model, provider.member,
                                       vapp=provider.vapp, vconf=provider.vconf)
            localname = prefix + resource.geometry.area + suffix + resource.term.fmthour
        elif resource.model == 'hycom':
            region_map = dict(atl='', med='_MED', oin='_OIN')
            mode_map = dict(fc='prv', an='ana')
            region = region_map.get(provider.vconf[:3], provider.vconf[:3])
            mode = mode_map.get(provider.vconf[4:][:2], None)
            localname = '{0:s}_{1:s}_{2:02d}{3:s}.{4:03d}.grb'.format(
                mode,
                provider.vconf[-3:],
                int(resource.date.hh),
                region,
                resource.term.hour
            )
            return localname
        elif resource.model == 'mfwam':
            logger.info("resourceterm %s", resource.term.hour)
            if provider.vconf == 'globalcep01':
                if six.text_type(resource.deltabegin.hour) == '0':
                    return 'windandice{0:s}_{1:s}'.format('2', resource.date.ymdhm)
                else:
                    return 'windandice{0:s}_{1:s}'.format('3', resource.date.ymdhm)
            else:
                return 'windandice_{0:s}'.format(resource.date.ymdhm)
        else:
            return None
    else:
        return None
    return localname


def varbc_bnames(resource, provider):
    reseau, model, stage = resource.date.hour, resource.model, resource.stage
    if model in ['reunion', 'aladin', 'caledonie', 'antiguy', 'polynesie']:
        suffix = '_alad'
    elif model == "arpege":
        suffix = ''
    elif model == "arome":
        suffix = '_aro'
    else:
        raise ValueError('Unknown model {:s} in varbc_bnames'.format(model))
    if stage == 'merge':
        localname = 'VARBC.merge.{!s}'.format(reseau)
    else:
        if model == "arome":
            localname = 'VARBC.cycle' + suffix + '. ' + six.text_type(resource.date.ymdhms)
        elif model == "arpege":
            localname = 'VARBC.cycle.r{!s}'.format(reseau)

    return localname


def boundary_bnames(resource, provider):
    cutoff, reseau, model, term = resource.cutoff, resource.date.hour, resource.model, resource.term
    if 'arome' in model:
        if hasattr(resource, 'source_conf'):
            is_court = resource.source_conf in ('court', 'courtfr', 'frcourt')
        else:
            is_court = resource.date.hour == 0
        _, suffix = gribNames(cutoff, reseau, model, force_courtfr=is_court)
        nw_term = "{0:03d}".format(term.hour)
        localname = 'ELSCFAROMALBC' + nw_term + '.' + suffix
    elif resource.model == 'mocage':
        localname = 'RUN1_SM' + resource.geometry.area + '+' \
                    + resource.date.ymd
    elif resource.model == 'mfwam':
        if (resource.term < 0):
            nw_date = (resource.date + resource.term).ymdh
            nw_term = "0000"
        else:
            nw_date = resource.date.ymdh
            nw_term = "{0:04d}".format(resource.term.hour)
        localname = 'FBI' + nw_date + nw_term
    else:
        _, suffix = faNames(cutoff, reseau, model)
        nw_term = "{0:03d}".format(resource.term.hour)
        localname = 'ELSCFALADALBC' + nw_term + '.' + suffix
    return localname


def refdata_bnames(resource, provider):
    cutoff, reseau, model = resource.cutoff, resource.date.hour, resource.model
    logger.debug('cutoff %s reseau %s model %s', cutoff, reseau, model)
    u_prefix, suffix = gribNames(cutoff, reseau, model)  # @UnusedVariable
    localname = 'refdata' + '.' + suffix
    return localname


def bgstderr_bnames(resource, provider):
    if provider.igakey == 'france':
        # errgrib_scr type
        return 'errgrib_scr.r{!s}'.format(resource.date.hour)
    else:
        # I have to calculate a new date so as to get the correct run
        prefix = 'errgrib'
        if resource.term.hour in [3, 9]:
            delta = 'PT{!s}H'.format(resource.term.hour + 3)
            suffix = resource.date + delta
            stdname = resource.cutoff
        elif resource.term == 12:
            delta = 'PT{!s}H'.format(resource.term.hour)
            suffix = resource.date + delta
            stdname = 'production_' + 'dsbscr'
        return prefix + '_' + stdname + '.' + suffix.compact()


def observations_bnames(resource, provider):
    fmt, part = resource.nativefmt, resource.part
    cutoff, reseau, model = resource.cutoff, resource.date.hour, resource.model
    day = six.text_type(resource.date.day)
    u_prefix, suffix = gribNames(cutoff, reseau, model)  # @UnusedVariable
    dico_names = {
        'obsoul': 'obsoul' + '.' + part + '.' + suffix,
        'ecma': {
            'surf': 'ECMA.surf' + '.' + six.text_type(int(reseau)) + '.' + six.text_type(reseau) + '.tar',
            'conv': 'ECMA.conv' + '.' + day + '.' + six.text_type(reseau) + '.tar',
            'prof': 'ECMA.prof' + '.' + day + '.' + six.text_type(reseau) + '.tar',
        }

    }
    localname = dico_names[fmt][0] + '.' + part + '.'
    logger.debug('localname %s', localname)
    if dico_names[fmt][1]:
        localname += six.text_type(day) + '.' + suffix + dico_names[fmt][1]
    else:
        localname += suffix
    return localname


def global_bnames(resource, provider):
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
    """Global names for soprano provider"""
    bname = None
    vapp = getattr(provider, 'vapp', None)
    vconf = getattr(provider, 'vconf', None)
    suff = _reseau_suffix(resource.cutoff, resource.date.hh, vconf, vapp)
    if vconf == 'aefrance' or vconf == 'pifrance':
        my_model = '_' + resource.model.upper()
    else:
        my_model = ''

    if resource.realkind == 'rawfields':
        if resource.origin == 'ostia' and resource.fields == 'sst':
            bname = 'sst.ostia'
        if resource.origin == 'bdm' and resource.fields == 'seaice':
            bname = 'SSMI.AM'

    elif resource.realkind == 'gridpoint':
        if resource.model == 'ifs':
            # Alpha
            if vapp == 'pprod':
                if vconf == 'ecmwf2mf@determ':
                    bname = 'cep_ifs_' + str(resource.date) + '_' + resource.geometry.area + '_ECH{0:04d}'.format(
                        resource.term.hour) + '.X.grb'
                elif vconf == 'ecmwf2mf@eps':
                    bname = 'cep_eps_' + str(resource.date) + '_MB{0:02d}_'.format(
                        provider.member) + resource.geometry.area + '_ECH{0:04d}'.format(resource.term.hour) + '.X.grb'
            # Others
            else:
                # For MACC forecast (camsfcst)
                if resource.cutoff == 'production':
                    bname = 'MET' + resource.date.ymd + '.' + resource.geometry.area + '.grb'
                # For MACC assim
                else:
                    bname = 'MET0utc' + resource.date.ymd + '.' + resource.geometry.area + '.grb'
        # For ALPHA production : Statistic Adaptations from BDAP/Soprano
        elif vconf in ['pg1@pa', 'pg1@pagrex', 'pg1@parome', 'pg1@multimod']:
            bname = ('pg1_' + re.split('@', vconf)[1] + '_' + str(resource.date) +
                     '_' + resource.geometry.area +
                     '_ECH{0:04d}'.format(resource.term.hour) + '.X.grb')

    elif resource.realkind == 'chemical_bc':
        if resource.model == 'mocage':
            if resource.cutoff == 'production':
                bname = '12utc_bc22_' + Date(resource.date.ymdh + '/+P1D').ymdh + '.nc'
            else:
                bname = '00utc_bc22_' + Date(resource.date.ymdh + '/+P1D').ymdh + '.nc'

    elif resource.realkind in ['AltidataWave', 'SARdataWave']:
        if resource.satellite == 'allsat' and resource.realkind == 'AltidataWave':
            bname = 'altidata_' + '{:02d}'.format(int(resource.date.hh))
        else:
            bname = dict(sentinel1='SENT1').get(resource.satellite, resource.satellite)

    elif resource.realkind == 'forcing' and resource.model in ('mfwam', 'ww3'):
        if resource.filling == 'wind':

            if hasattr(resource, 'term'):
                bname = 'vent_{:s}{:s}'.format('ana' if resource.term in (0, None) else 'prv', resource.date.hh)
            elif hasattr(resource, 'endtime'):
                bname = 'vent_{:s}{:s}'.format('ana' if resource.endtime == 0 else 'prv', resource.date.hh)

        elif resource.filling == 'currents':
            bname = 'courant_{:s}'.format(resource.date.hh)
        else:
            bname = 'allsop'

    elif resource.realkind == 'observations':
        if resource.nativefmt == 'grib':
            if resource.part == 'sev':
                bname = 'SEVIRI' + '.' + suff + '.grb'
        elif resource.nativefmt == 'obsoul':
            if resource.part == 'conv':
                bname = 'OBSOUL1F' + my_model + '.' + suff
            elif resource.part == 'prof':
                bname = 'OBSOUL2F' + my_model + '.' + suff
            elif resource.part == 'surf':
                bname = 'OBSOUL_SURFAN' + my_model + '.' + suff
        elif resource.nativefmt == 'bufr':
            bname = resource.nativefmt.upper() + '.' + resource.part + my_model + '.' + suff
        elif resource.nativefmt == 'netcdf':
            bname = resource.nativefmt.upper() + '.' + resource.part + my_model + '.' + suff
        elif resource.nativefmt == 'hdf5':
            bname = resource.nativefmt.upper() + '.' + resource.part + my_model + '.' + suff

    elif resource.realkind == 'refdata':
        if resource.part == 'prof':
            bname = 'RD_2' + my_model + '.' + suff
        elif resource.part == 'conv':
            bname = 'RD_1' + my_model + '.' + suff
        elif resource.part == 'surf':
            bname = 'RD_SURFAN' + my_model + '.' + suff
        else:
            bname = 'rd_' + resource.part + my_model + '.' + suff

    elif resource.realkind == 'historic':
        bname = 'toto'

    elif resource.realkind == 'obsmap':
        if resource.scope.startswith('surf'):
            scope = resource.scope[:4].lower()
        else:
            scope = resource.scope
        bname = 'bm' + my_model + '_' + scope + '.' + suff + '.' + resource.date.ymd

    elif resource.realkind == 'listing_ouloutput':
        if resource.scope == 'surf':
            bname = 'OULOUTPUT_SURFAN' + my_model + '.' + suff
        elif resource.scope == 'oulan':
            bname = 'OULOUTPUT' + my_model + '.' + suff
        else:
            bname = 'OULOUTPUT_BUFR' + '_' + resource.scope + my_model + '.' + suff

    elif resource.realkind == 'mocacc_emis_and_nwp_inputs':
        bname = 'ctbto_in.tar'

    return bname
