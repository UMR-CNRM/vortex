#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Dec  2 13:27:17 2020

@author: lmmorvan
"""

from vortex.data.flow import FlowResource

class CmemsRivers(FlowResource):
    """Rivers file from cmems in 'tar' format"""

    _footprint = [
        dict(
            info='Rivers tar file from cmems',
            attr=dict(
                kind=dict(
                    values=["rivers"]
                ),
                nativefmt=dict(
                    values=['tar']
                ),
                model=dict(
                    values=['cmems']
                ),
            ),
        ),
    ]

    @property
    def realkind(self):
        return 'rivers'