#!/usr/bin/env python
# -*- coding:Utf-8 -*-

import re

#: No automatic export
__all__ = []

#: Specific tricks for base naming in iga fuzzy namespace.
fuzzystr = dict(
    histfix = dict(
        historic = dict(
            pearp = 'prev', arome = 'AROM', arpege = 'arpe', arp_court = 'arpe',
            aladin = 'ALAD', surfex = 'SURF'
        ),
    ),
    prefix = dict(
        gridpoint = dict( oper = 'PE', dble = 'PA', mirr='PE' ),
    ),
    suffix = dict(
        bgstderr = dict( input = 'in', output = 'out' )
    ),
    term0003 = dict(
        bgstderr = dict( input = '', output = '_assim' ),
    ),
    term0009 = dict(
        bgstderr = dict( input = '', output = '_production' ),
    ),
    term0012 = dict(
        bgstderr = dict( input = '_production_dsbscr', output = '_production_dsbscr' ),
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
        historic = dict( input = 'INIT_SURF', output = 'INIT_SURF' ),
    ),
    surf0003 = dict(
        histsurf = dict( input = 'PREP', output = 'AROMOUT_.0003' ),
        historic = dict( input = 'PREP', output = 'AROMOUT_.0003' ),
    ),
    surf0006 = dict(
        histsurf = dict( input = 'PREP', output = 'AROMOUT_.0006' ),
        historic = dict( input = 'PREP', output = 'AROMOUT_.0006' ),
    ),
)

arpcourt_vconf = ('courtfr', 'frcourt', 'court')


def fuzzyname(entry, realkind, key):
    """Returns any non-standard naming convention in the operational namespace."""
    return fuzzystr[entry][realkind][key]


def archive_suffix(model, cutoff, date, vconf=None):
    """Returns the suffix for iga filenames according to specified ``model``, ``cutoff`` and ``date`` hour."""

    hh = range(0, 21, 3)
    hrange = []
    for h in hh:
        hrange.append("%02d" % h)

    if cutoff == 'assim':
        rr = dict(
            zip(
                zip(
                    (cutoff,) * len(hrange),
                    hh
                ),
                hrange
            )
        )
    else:
        if (re.search('court|arome', model) or (vconf in arpcourt_vconf)):
            rr = dict(
                zip(
                    zip(
                        (cutoff,) * len(hrange),
                        hh
                    ),
                    ('CM', 'TR', 'SX', 'NF', 'PM', 'QZ', 'DH', 'VU')
                )
            )
        else:
            rr = dict(
                zip(
                    zip(
                        (cutoff,) * len(hrange),
                        hh
                    ),
                    ('AM', 'TR', 'SX', 'NF', 'PM', 'QZ', 'DH', 'VU')
                )
            )

    return str(rr[(cutoff, date.hour)])


class _BaseIgakeyFactory(str):
    """
    Given the vapp/vconf, returns a default value for the igakey attribute.

    Needs to be subclassed !
    """

    _re_appconf = re.compile('^(\w+)/([\w@]+)$')

    def __new__(cls, value):
        """
        If the input string is something like "vapp/vconf", use a mapping
        between vapp/vconf pairs and the igakey (see _keymap).
        If no mapping is found, it returns vapp.
        """
        val_split = cls._re_appconf.match(value)
        if val_split:
            value = cls._keymap.get(val_split.group(1),
                                    {}).get(val_split.group(2),
                                            val_split.group(1))
        return str.__new__(cls, value)


class IgakeyFactoryArchive(_BaseIgakeyFactory):
    """
    Given the vapp/vconf, returns a default value for the igakey attribute
    """

    _keymap = {'arpege': {'4dvarfr': 'arpege',
                          '4dvar': 'arpege',
                          'pearp': 'pearp',
                          'aearp': 'aearp',
                          'courtfr': 'arpege',
                          'frcourt': 'arpege',
                          'court': 'arpege', },
               'arome': {'3dvarfr': 'arome',
                         'france': 'arome',
                         'pegase': 'pegase', },
               'aladin': {'antiguy': 'antiguy',
                          'caledonie': 'caledonie',
                          'nc': 'caledonie',
                          'polynesie': 'polynesie',
                          'reunion': 'reunion', },
               }


class IgakeyFactoryInline(_BaseIgakeyFactory):
    """
    Given the vapp/vconf, returns a default value for the igakey attribute
    """

    _keymap = {'arpege': {'4dvarfr': 'france',
                          '4dvar': 'france',
                          'pearp': 'pearp',
                          'aearp': 'aearp',
                          'courtfr': 'frcourt',
                          'frcourt': 'frcourt',
                          'court': 'frcourt', },
               'arome': {'3dvarfr': 'france',
                         'france': 'france',
                         'pegase': 'pegase', },
               'aladin': {'antiguy': 'antiguy',
                          'caledonie': 'caledonie',
                          'nc': 'caledonie',
                          'polynesie': 'polynesie',
                          'reunion': 'reunion', },
               'hycom':  {'atl@anarp': 'surcotes',
                          'med@anarp': 'surcotes',
                          'atl@fcarp': 'surcotes',
                          'med@fcarp': 'surcotes', },
               }
