#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Arpege ressources
"""

from vortex.syntax.stddeco import namebuilding_insert
from common.data.gridfiles import GridPoint


@namebuilding_insert("src", lambda self: self.origin)
class ArpegeFiles(GridPoint):

    _footprint = [
        dict(
            info="Arpege hourly PAA and PA run",
            attr=dict(
                kind=dict(
                    values=["arpege_paa_pa"],
                ),
                origin=dict(
                    values=["ana","fcst"]
                ),
                cumul=dict(
                    values=["cumul","insta"]
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "arpege_paa_pa"
