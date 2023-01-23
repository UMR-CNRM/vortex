"""
TODO: Module documentation
"""

import footprints

from vortex.util.config import ConfigurationTable, TableItem

#: No automatic export
__all__ = []


class Site(TableItem):
    """
    Site or location where some pollution may occur.
    """
    _RST_NAME = 'name'
    _RST_HOTKEYS = ['family', 'location']

    _footprint = dict(
        info = 'Sites for sources of pollution (radiologic, chemical, volcanic, etc.)',
        attr = dict(
            name = dict(
                type   = str,
            ),
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
                type     = str,
                optional = True,
                default  = '[name]',
            ),
        )
    )

    @property
    def realkind(self):
        return 'site'


class Element(TableItem):
    """
    Element of any kind (radiologic, chemical, volcanic.)
    """
    _RST_NAME = 'symbol'
    _RST_HOTKEYS = ['name', 'family']

    _footprint = dict(
        info = 'Generic element (radiologic, chemical, volcanic, etc.)',
        attr = dict(
            symbol = dict(),
            family = dict(
                values = ['radiologic', 'chemical', 'volcanic'],
            ),
            name = dict(
                type     = str,
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
            deposit = dict(
                optional = True,
                type     = float,
                default  = None,
            ),
            deposit_unit = dict(
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
            scavenging = dict(
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
        )
    )

    @property
    def realkind(self):
        return 'element'


class PollutantsTable(ConfigurationTable):
    """
    Configuration file with description of pollutants elements or sites.
    """
    _abstract = True
    _footprint = dict(
        info = 'Pollutants table configuration files',
        attr = dict(
            kind = dict(),
            family = dict(
                values   = ['pollutants', 'pollution'],
                remap    = dict(pollution = 'pollutants'),
            ),
        )
    )

    @property
    def realkind(self):
        return 'pollutants-table'


class PollutantsElementsTable(PollutantsTable):
    """
    Configuration file with description of pollutants elements.
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
    Configuration file with description of pollutants sites
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
