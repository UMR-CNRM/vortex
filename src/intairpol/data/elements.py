#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re
import footprints

from vortex.util.config  import IniConf, ExtendedReadOnlyConfigParser

logger = footprints.loggers.getLogger(__name__)


class Site(footprints.FootprintBase):
    """
    Site or location where some pollution may occur.
    """
    _collector = ('element',)
    _footprint = dict(
        info = 'Sites for sources of pollution (radiologic, chemical, volcanic, etc.)',
        attr = dict(
            name = dict(),
            family = dict(
                values = ['radiologic', 'chemical', 'volcanic'],
            ),
            latitude = dict(
                type = float
            ),
            longitude = dict(
                type = float
            ),
            location = dict(
                optional = True,
                default  = '[name]',
            ),
        )
    )

    @property
    def realkind(self):
        return 'site'


class Element(footprints.FootprintBase):
    """
    Element of any kind (radiologic, chemical, volcanic.)
    """
    _collector = ('element',)
    _footprint = dict(
        info = 'Generic element (radiologic, chemical, volcanic, etc.)',
        attr = dict(
            symbol = dict(),
            family = dict(
                values = ['radiologic', 'chemical', 'volcanic'],
            ),
            name = dict(
                optional = True,
                default  = '[symbol]',
            ),
            description = dict(
                optional = True,
                default  = '[family]',
            ),
            size = dict(
                optional = True,
                type     = float,
                default  = None,
            ),
            size_unit = dict(
                optional = True,
                default  = 'microns',
            ),
            speed = dict(
                optional = True,
                type     = float,
                default  = None,
            ),
            speed_unit = dict(
                optional = True,
                default  = 'm.s-1',
            ),
            mass = dict(
                optional = True,
                type     = float,
                default  = None,
            ),
            mass_unit = dict(
                optional = True,
                default  = 'g',
            ),
            density = dict(
                optional = True,
                type     = float,
                default  = None,
            ),
            density_unit = dict(
                optional = True,
                default  = 'kg.m-3',
            ),
            halflife = dict(
                optional = True,
                type     = float,
                default  = None,
            ),
            halflife_unit = dict(
                optional = True,
                default  = 's',
            ),
            leaching = dict(
                optional = True,
                type     = float,
                default  = None,
            ),
            khenry1 = dict(
                optional = True,
                type     = float,
                default  = None,
            ),
            khenry2 = dict(
                optional = True,
                type     = float,
                default  = None,
            ),
            translator = dict(
                optional = True,
                type     = footprints.FPDict,
                default  = None,
            ),
        )
    )

    @property
    def realkind(self):
        return 'element'

    def nice_print(self, mkshort=True):
        """Produces a nice ordered output of the element specification."""
        if self.translator:
            for k in self.translator.get('ordered_dump', '').split(','):
                if not mkshort or self.footprint_getattr(k) is not None:
                    print '{0:24s} : {1:s}'.format(
                        self.translator.get(
                            k, k.replace('_', ' ').title()),
                            str(self.footprint_getattr(k))
                        )
        else:
            logger.warning('Could not produce a nice dump without translator')


class PollutantsTable(IniConf):
    """
    Configuration file with description of pollutants elements.
    """
    _abstract  = True
    _footprint = dict(
        info = 'Pollutants table configuration files',
        attr = dict(
            kind = dict(),
            family = dict(
                values   = ['pollutants', 'pollution'],
                remap    = dict(pollution = 'pollutants'),
            ),
            version = dict(
                optional = True,
                default  = 'std',
            ),
            searchkeys = dict(
                type     = footprints.FPTuple,
                optional = True,
                default  = footprints.FPTuple(),
            ),
            groupname = dict(
                optional = True,
                default  = 'family',
            ),
            inifile = dict(
                optional = True,
                default  = '@[family]-[kind]-[version].ini',
            ),
            clsconfig = dict(
                default  = ExtendedReadOnlyConfigParser,
            ),
            language = dict(
                optional = True,
                default  = 'en',
            ),
        )
    )

    @property
    def realkind(self):
        return 'pollutants-table'

    def groups(self):
        """Actual list of items groups described in the current iniconf."""
        return [ x for x in self.config.parser.sections()
                    if ':' not in x and not x.startswith('lang_') ]

    def keys(self):
        """Actual list of different items in the current iniconf."""
        return [ x for x in self.config.sections()
                    if x not in self.groups() and not x.startswith('lang_') ]

    @property
    def translator(self):
        """The special section of the iniconf dedicated to tranlastion, as a dict."""
        if not hasattr(self, '_translator'):
            if self.config.has_section('lang_' + self.language):
                self._translator = self.config.as_dict()['lang_'+self.language]
            else:
                self._translator = None
        return self._translator

    @property
    def tablelist(self):
        """List of unique instances of items described in the current iniconf."""
        if not hasattr(self, '_tablelist'):
            self._tablelist = list()
            d = self.config.as_dict()
            for item, group in [ x.split(':') for x in self.config.parser.sections() if ':' in x ]:
                try:
                    for k, v in d[item].items():
                        if re.match('none$', v, re.IGNORECASE):
                            d[item][k] = None
                        if re.search('[a-z]_[a-z]', v, re.IGNORECASE):
                            d[item][k] = v.replace('_', "'")
                    d[item][self.searchkeys[0]] = item
                    d[item][self.groupname]     = group
                    d[item]['translator']       = self.translator
                    self._tablelist.append(footprints.proxy.element(**d[item]))
                except Exception as trouble:
                   logger.warning('Some item description could not match ' + item + '/' + group)
                   logger.warning(trouble)
        return self._tablelist

    def get(self, item):
        """Return the item with main key exactly matching the given argument."""
        candidates = [ x for x in self.tablelist if x.footprint_getattr(self.searchkeys[0]) == item ]
        if candidates:
            return candidates[0]
        else:
            return None

    def match(self, item):
        """Return the item with main key matching the given argument without case consideration."""
        candidates = [ x for x in self.tablelist
                      if x.footprint_getattr(self.searchkeys[0]).lower().startswith(item.lower()) ]
        if candidates:
            return candidates[0]
        else:
            return None

    def grep(self, item):
        """Return a list of items with main key loosely matching the given argument."""
        return [ x for x in self.tablelist
                if re.search(item, x.footprint_getattr(self.searchkeys[0]), re.IGNORECASE) ]

    def find(self, item):
        """Return a list of items with main key or name loosely matching the given argument."""
        return [ x for x in self.tablelist if any([
                    re.search(item, x.footprint_getattr(thiskey), re.IGNORECASE)
                        for thiskey in self.searchkeys ]) ]


class PollutantsElementsTable(PollutantsTable):
    """
    """

    _footprint = dict(
        info = 'Pollutants elements table',
        attr = dict(
            kind = dict(
                values   = ['elements'],
            ),
            version = dict(
                values   = ['std', 'nist', 'si'],
                remap    = dict(si='nist'),
            ),
            searchkeys = dict(
                default  = footprints.FPTuple(('symbol', 'name'),)
            ),
        )
    )

    @property
    def elements(self):
        return self.tablelist


class PollutantsSitesTable(PollutantsTable):
    """
    """

    _footprint = dict(
        info = 'Pollutants sites table',
        attr = dict(
            kind = dict(
                values   = ['sites'],
            ),
            searchkeys = dict(
                default  = footprints.FPTuple(('name', 'location'),)
            ),
        )
    )

    @property
    def sites(self):
        return self.tablelist
