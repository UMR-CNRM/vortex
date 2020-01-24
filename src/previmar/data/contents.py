#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import re

from bronx.fancies import loggers
from vortex.data.contents import AlmostListContent

logger = loggers.getLogger(__name__)

#: No automatic export
__all__ = []


class SurgeTemplate(AlmostListContent):
    """Multi-lines data which fits to a surge template (blkdat format)."""

    def substitute(self, dictkeyvalue):
        """Actually substitute item present in a container like blkdat."""
        config_line = self._data
        self._data = list()
        for line in config_line:
            m = re.match(r"^(?P<value>[\-\w.]+)\s*'(?P<key>[\w ]+)'(\s*=\s*)?(?P<info>.*)", line)
            if m:
                dico_in = m.groupdict()
                if dico_in['key'] in dictkeyvalue.keys():
                    line = "{0:11s}'{1:6s}' = {2:s}\n".format(dictkeyvalue[dico_in['key']], dico_in['key'], dico_in['info'])
            self._data.append(line)


class AltidataContent(AlmostListContent):
    """Multi-columns files with altimetric measurement by positions."""

    def sort(self, ** sort_opts):
        """Sort the current object."""
        lines = {tuple(line.strip().split(' ')[4:]): line
                 for line in self.data}
        self._data = list(sorted(lines.values()))
