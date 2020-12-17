#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Promethee standard attributes.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import footprints
from vortex.syntax.stddeco import namebuilding_append, namebuilding_insert, generic_pathname_insert

#: Export a set of attributes
__all__ = [
    'a_promid',
    'a_version',
    'a_param'
]

#: Usual definition for the ``promid`` (*e.g.* promethee identifier).
a_promid = dict(
    info="[Deprecated] The promethee identifier (name of the file)",
    type=str,
    optional=False,
)

promid = footprints.Footprint(info='Abstract promethee identifier (name of the file)',
                            attr=dict(promid=a_promid))


promid_deco = footprints.DecorativeFootprint(
    promid,
    decorator=[namebuilding_append('src', lambda self: {'promid': self.promid})]
)

#: Usual definition for the ``version`` (*e.g.* original configuration hashcode).
a_version = dict(
    info="The original config version (MD5 checksum)",
    type=str,
    optional=True,
    default=""
)

version = footprints.Footprint(info='Abstract original config version (MD5 checksum)',
                            attr=dict(version=a_version))


version_deco = footprints.DecorativeFootprint(
    version,
    decorator=[namebuilding_append('src', lambda self: {'version': self.version})]
)


#: Usual definition for the ``param`` (*e.g.* field).
a_param = dict(
    info="Parameter or field name",
    type=str,
    optional=False,
)

param = footprints.Footprint(info='Abstract parameter or field name',
                            attr=dict(param=a_param))


param_deco = footprints.DecorativeFootprint(
    param,
    decorator=[namebuilding_append('src', lambda self: {'param': self.param})]
)


#: Usual definition for the ``task`` (*e.g.* task name for/from which the resource exists)
tasks = ["conf_task", "data_task", "mask_task", "prod_task", "version"]

a_task = dict(
    info='Task name',
    type=str,
    optional=False,
    values=tasks
)

task = footprints.Footprint(info='Abstract task name',
                            attr=dict(task=a_task))

task_deco = footprints.DecorativeFootprint(
    task,
    decorator=[namebuilding_append('src', lambda self: {"task": self.task})]
)
 
