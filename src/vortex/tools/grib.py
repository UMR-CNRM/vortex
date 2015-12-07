#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from . import addons


def use_in_shell(sh, **kw):
    """Extend current shell with the LFI interface defined by optional arguments."""
    kw['shell'] = sh
    return footprints.proxy.addon(**kw)


class GRIBAPI_Tool(addons.Addon):
    """
    Interface to gribapi commands (designed as a shell Addon).
    """

    _footprint = dict(
        info = 'Default GRIBAPI system interface',
        attr = dict(
            kind = dict(
                values   = ['gribapi'],
            ),
        )
    )

    def __init__(self, *args, **kw):
        """Addon initialisation."""
        super(GRIBAPI_Tool, self).__init__(*args, **kw)
        # Additionaly, check for the GRIB_API_ROOTDIR key in the config file
        if self.path is None and self.cfginfo is not None:
            tg = self.sh.target()
            addon_rootdir = tg.get(self.cfginfo + ':grib_api_rootdir', None)
            if addon_rootdir is not None:
                self.path = addon_rootdir

    def _spawn_wrap(self, cmd, **kw):
        """Internal method calling standard shell spawn."""
        cmd[0] = 'bin' + self.sh.path.sep + cmd[0]
        return super(GRIBAPI_Tool, self)._spawn_wrap(cmd, **kw)

    def grib_diff(self, grib1, grib2, skipkeys=('generatingProcessIdentifier',), **kw):
        """
        Difference between two grib-file (using the GRIB-API

        Mandatory args are:
          * grib1 : first file to compare
          * grib2 : second file to compare

        Options are:
          * skipkeys : List of GRIB keys that will be ignored.

        GRIB messages may not be in the same order in both files.
        """
        cmd = [ 'grib_compare', '-r', '-b', ','.join(skipkeys), grib1, grib2 ]

        kw['fatal'] = False
        kw['output'] = False
        return self._spawn_wrap(cmd, **kw)
