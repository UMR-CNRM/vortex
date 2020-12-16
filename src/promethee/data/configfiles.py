#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Various configuration files (Namelists excepted).
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from common.data.configfiles import JsonConfig
from vortex.data.outflow import StaticResource
from vortex.syntax.stddeco import namebuilding_append, namebuilding_insert
from vortex.syntax.stdattrs import date_deco
from promethee.syntax.stdattrs import version_deco, promid_deco

#: No automatic export
__all__ = []

@namebuilding_append('src', lambda s : {'scope' : s.scope})
class PrometheeConfig(JsonConfig):
    """Class to access Promethee configuration files."""
    _footprint = [
        version_deco,
        date_deco,
        dict(
            info = 'JSON Configuration file',
            attr = dict(
                kind    = dict(
                    optional    = False,
                    values      = ["promethee_config"]
                ),
                scope = dict(
                    values      = ['global', 'mask', 'data', 'prod', 'version']
                ),
                source = dict(
                    optional    = True,
                    default     = ""
                ),
                nativefmt = dict(
                    optional    = True,
                    values      = ['json', ],
                    default     = 'json'
                )
            )
        )
    ]


@namebuilding_append('src', lambda s : {'scope' : s.scope})
class PrometheeLog(JsonConfig):
    """Class to access Promethee log files."""
    _footprint = [
        version_deco,
        date_deco,
        dict(
            info = 'JSON Log file',
            attr = dict(
                kind    = dict(
                    optional    = False,
                    values      = ["promethee_log"]
                ),
                scope = dict(
                    values      = ['config', 'mask', 'data', 'prod']
                ),
                source = dict(
                    optional    = True,
                    default     = ""
                ),
                nativefmt = dict(
                    optional    = True,
                    values      = ['json', ],
                    default     = 'json'
                )
            )
        )
    ]
    
    @property
    def realkind(self):
        return 'log'



class PrometheeOutput(JsonConfig):
    """Class to access Promethee output file."""
    _footprint = [
        promid_deco,
        version_deco,
        date_deco,
        dict(
            info = 'JSON Output file',
            attr = dict(
                kind    = dict(
                    optional    = False,
                    values      = ["promethee_output"]
                ),
                scope = dict(
                    optional    = True,
                    default     = ""
                ),
                source = dict(
                    optional    = True,
                    default     = ""
                ),
                nativefmt = dict(
                    optional    = True,
                    values      = ['json', ],
                    default     = 'json'
                )
            )
        )
    ]

    @property
    def realkind(self):
        return 'output'


@namebuilding_insert('radical', lambda s: s.realkind)
@namebuilding_append('src', lambda s : {'scope' : s.scope})
class PrometheeArchive(StaticResource):
    """Class to access a promethee archive (input or output)"""
    _footprint = [
        version_deco,
        date_deco,
        dict(
            info = 'Archive file (tar)',
            attr = dict(
                kind    = dict(
                    optional    = False,
                    values      = ["promethee_archive"]
                ),
                scope = dict(
                    optional    = True,
                    values      = ["config", "output"],
                    default     = ""
                ),
                nativefmt = dict(
                    optional    = True,
                    values      = ['tgz', 'tar.gz', 'tar'],
                    default     = 'tgz'
                )
            )
        )
    ]

    @property
    def realkind(self):
        return 'archive'
