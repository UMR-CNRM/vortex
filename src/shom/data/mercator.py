#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mercator forecast ressources
"""
from vortex.data.flow import Resource
from vortex.data.geometries import hgeometry_deco
from vortex.syntax.stdattrs import model_deco, date_deco, term_deco

# from vortex.syntax.stddeco import namebuilding_append


class MercatorSingleFileDailyForecast(Resource):

    _footprint = [
        model_deco,
        date_deco,
        hgeometry_deco,
        dict(
            info="Mercator daily forecast run",
            attr=dict(
                kind=dict(values=["mercator_single_file_daily_forecast"]),
                nativefmt=dict(values=["netcdf", "nc"], default="nc"),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "mercator_single_file_daily_forecast"


class MercatorDailyForecast(MercatorSingleFileDailyForecast):

    _footprint = [
        term_deco,
        dict(
            info="Mercator daily forecast run",
            attr=dict(
                kind=dict(values=["mercator_daily_forecast"]),
                nativefmt=dict(values=["netcdf", "nc"], default="nc"),
            ),
        ),
    ]

    @property
    def realkind(self):
        return "mercator_daily_forecast"
