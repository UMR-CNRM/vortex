#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Typical flow ressources for promethee use.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.data.flow import FlowResource
from vortex.data.contents import JsonDictContent
from promethee.syntax.stdattrs import version_deco, task_deco

#: No automatic export
__all__ = []

class PrometheeFlowResource(FlowResource):
    """Abstract Class to access all kind of flow resources for promethee."""
    _abstract = True
    _footprint = [
        task_deco,
        version_deco,
        dict(
            info = 'Abstract FlowResource for Promethee uses. It is a flow resource that has a version tag and is related to a specific task',
        )
    ]

    @property
    def realkind(self):
        return self.kind


class PrometheeJson(PrometheeFlowResource):
    """Promethee json files"""
    _footprint = dict(
        info = 'Json files identified as task related, versioned, flow resources. Specific to Promethee.',
        attr = dict(
            kind = dict(
                optional    = False,
                values      = ['config', 'log']
            ),
            nativefmt = dict(
                optional    = True,
                values      = ['json'],
                default     = 'json'
            ),
            clscontents = dict(
                default     = JsonDictContent
            )
        )
    )

class PrometheeArchive(PrometheeFlowResource):
    """Promethee archive files"""
    _footprint = dict(
        info = 'Tar files identified as task related, versioned, flow resources. Specific to Promethee.',
        attr = dict(
            kind = dict(
                optional    = False,
                values      = ['archive']
            ),
            nativefmt = dict(
                optional    = True,
                values      = ['tgz', 'tar'],
                default     = 'tgz'
            )
        )
    )

