#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MeteoFrance ressources
"""

from vortex.syntax.stddeco import namebuilding_insert
from common.data.gridfiles import GridPoint

class MeteoFranceFiles(GridPoint):
    """MeteoFrance Forecast and Analyse run files"""

    _footprint = [
        dict(
            info="MeteoFrance Forecast and Analyse run files",
            attr=dict(
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
        return "gridpoint"

