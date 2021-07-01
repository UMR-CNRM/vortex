#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Typical ressources for promethee use.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

from vortex.data.resources import Resource
from vortex.data.contents import JsonDictContent
from promethee.syntax.stdattrs import version_deco, task_deco
from vortex.syntax.stdattrs import model_deco, cutoff_deco

#: No automatic export
__all__ = []


class PrometheeNoDateBdpeResource(Resource):
    """Undated BDPE resource bound to a model and a cutoff."""

    _footprint = [
        model_deco,
        cutoff_deco,
        task_deco,
        version_deco,
        dict(
            info = "Undated BDPE resource for Promethee usage. It is a resource that has version, model, and cutoff tags and is related to a specific task.",
            attr = dict(
            kind = dict(
                values = ["bdpe"]
            ),
            model = dict(
                values = ['promethee', ]
            ),
            nativefmt = dict(
                values = ["tgz"],
                default = "tgz"
            ),
        ),
    )
    ]

    @property
    def realkind(self):
        return self.kind
