#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Promethee standard attributes.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import footprints
from bronx.stdtypes.date import Time
from vortex.syntax.stddeco import namebuilding_append

#: Export a set of attributes
__all__ = [
    'a_promid',
    'a_version',
    'a_param',
    'a_step',
    'a_task'
]

#: Usual definition for the ``promid`` (*i.e.* promethee production identifier).
a_promid = dict(
    info="The identifier of the Promethee production (e.g. report name, mask id, zone id, etc.)",
    type=str,
    optional=False,
)

promid = footprints.Footprint(info='Abstract Promethee identifier', attr=dict(promid=a_promid))

promid_deco = footprints.DecorativeFootprint(
    promid,
    decorator=[namebuilding_append('src', lambda self: {'promid': self.promid})]
)

#: Usual definition for the ``version`` (*e.g.* config version, promethee mask version).
a_version = dict(
    info="The resource version (i.e. production version).",
    type=str,
    optional=True,
    default=""
)

version = footprints.Footprint(info='Abstract resource version', attr=dict(version=a_version))

version_deco = footprints.DecorativeFootprint(
    version,
    decorator=[namebuilding_append('src', lambda self: {'version': self.version})]
)


#: Usual definition for the ``param`` (*i.e.* parameter name).
a_param = dict(
    info="The weather parameter or field name.",
    type=str,
    optional=False,
)

param = footprints.Footprint(info='Abstract parameter or field name', attr=dict(param=a_param))

param_deco = footprints.DecorativeFootprint(
    param,
    decorator=[namebuilding_append('src', lambda self: {'param': self.param})]
)

#: Usual definition for the ``task`` (*i.e.* promethee task name among "conf_task",
#: "data_task", "mask_task", "prod_task" and "version" for which the resource is
#: dedicated)
a_task = dict(
    info="The task name for which the resource is dedicated.",
    type=str,
    optional=False,
    values=["conf_task", "data_task", "mask_task", "prod_task", "version"]
)

task = footprints.Footprint(info='Abstract task name', attr=dict(task=a_task))

task_deco = footprints.DecorativeFootprint(
    task,
    decorator=[namebuilding_append('src', lambda self: {"task": self.task})]
)

#: Usual definition for the ``step`` (*i.e.* step (in hours) between two
#: consecutive terms in the resource)
a_step = dict(
    info="The step (in hours) between two consecutive terms in the resource.",
    type=Time,
    optional=False,
    values=[1, 3, 6, 12, 24]
)

step = footprints.Footprint(info='Abstract step', attr=dict(step=a_step))

step_deco = footprints.DecorativeFootprint(
    step,
    decorator=[namebuilding_append('period', lambda self: {"step": self.step})]
)
