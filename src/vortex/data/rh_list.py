#!/usr/bin/env python
# -*- coding:Utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

from .flow import FlowResource
from .contents import JsonDictContent


class RhJsonList(JsonDictContent):
    """New class to handle the search in json files containing a list of sequences"""

    def find_rh(self, **kwargs):
        """Find ResourceHandlers in the list according to some criteria"""
        outlist = list()
        for info in self.data:
            test = True
            for k in kwargs:
                if info[k] != kwargs[k]:
                    test = False
            if test:
                outlist.append(info['rh'])
        return outlist


class ResourceHandlers_list(FlowResource):
    """Class to handle the files which contains a list of ResourceHandlers in a json format."""
    _footprint = dict(
        info = 'A Population List',
        attr = dict(
            kind=dict(
                values=['rhlist', ],
            ),
            clscontents = dict(
                default = RhJsonList,
            ),
            nativefmt   = dict(
                values  = ['json',],
                default = 'json',
            )
        )
    )

    def basename_info(self):
        """Generic information for names fabric."""
        return dict(
            radical = self.realkind,
            fmt     = self.nativefmt,
        )

    @property
    def realkind(self):
        return "rhlist"
