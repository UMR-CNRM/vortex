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

class PrometheeInputs(FlowResource):
    """Tar with gribs extracted from the BDAP database"""

    _footprint = dict(
        info = "Tar from soprano. Specific to promethee.",
        attr = dict(
            kind = dict(
                values = ["promethee_inputs"]
            ),
            model = dict(
                values = ['promethee', ]
            ),
            nativefmt = dict(
                values = ["tar"],
                default = "tar"
            ),
        ),
    )

    @property
    def realkind(self):
        return self.kind


class PrometheeFlowResource(FlowResource):
    """PrometheeFlowResource : Abstract Class to access all kind of flow resources
    for promethee. A PrometheeFlowResource is a quite common flow resource with a
    version tag and is related to a specific Promethee task.

    It designates all the resources used in the Promethee flow, such as:
        - config files,
        - log files,
        - archive files (containing configs or output productions).

    Inheritance:
        vortex.data.flow.FlowResource

    Attrs:
        kind        (str) : Resource's kind.
        date (bronx.stdtypes.date.Datetime) : The generating process run date.
        cutoff      (str) : The cutoff type of the generating process.
        model       (str) : The model name (from a source code perspective).
        nativefmt   (str) : The resource's storage format.
        task        (str) : The task name for which the resource is designed. Among
        "conf_task", "data_task", "mask_task", "prod_task" and "version".
        version     (str) : The resource version.
    """

    _abstract = True
    _footprint = [
        task_deco,
        version_deco,
        dict(
            info = "Abstract FlowResource for a Promethee usage. It is a flow resource"
            " that has a version tag and is related to a specific task.",
        )
    ]

    @property
    def realkind(self):
        return self.kind


class PrometheeJson(PrometheeFlowResource):
    """PrometheeJson : Specific PrometheeFlowResource designed for Json files.
    It concerns the Promethee config and log files.

    Inheritance:
        PrometheeFlowResource

    Attrs:
        kind (str) : The resource kind. Among 'config' and 'log'.
        nativefmt (str) : The resource's storage format. Must be 'json'.
        clscontents (type) : Must be JsonDictContent.
        * and all the other PrometheeFlowResource attributes.
    """

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
    """PrometheeArchive : specific PrometheeFlowResource designed archive files.
    It concerns the Promethee input containing all the configurations files, and
    the Promethee output containing all the production files.

    Inheritance:
        PrometheeFlowResource

    Attrs:
        kind (str) : The resource kind. Must be 'archive'.
        nativefmt (str) : The resource's storage format. Among 'tgz' or 'tar'.
        * and all the other PrometheeFlowResource attributes.
    """

    _footprint = dict(
        info = 'Archive files (tar) identified as task related, versioned, flow resources. Specific to Promethee.',
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
