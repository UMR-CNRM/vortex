

__all__ = [ 'os', 'logging', 'TestCase', 'TestLoader', 'TextTestRunner',
            'common', 'iga', 'toolbox', 'sessions',
            'resources', 'SpectralGeometry', 'GridGeometry',
            'today', 'Date', 'vortex', 't', 'get_default_provider',
            'get_spec_provider', 'IgaHelperSelect'
        ]

import os
import logging
from unittest import TestCase, TestLoader, TextTestRunner

import common.data
import iga.data
from iga.utilities.helpers import IgaHelperSelect

import vortex
from vortex import toolbox, sessions
from vortex.tools import env
from vortex.data import resources
from vortex.data.geometries import SpectralGeometry, GridGeometry
from vortex.tools.date import today, Date

#main variables definition for unittest
__version__ = '0.5.4'
fpg = dict(tag='oper', user='mxpt001', profile='oper')
operenv = env.Environment(active=True)
operenv.glove = sessions.glove(**fpg)
t = sessions.ticket(
    tag=fpg['tag'],
    glove=operenv.glove, 
    topenv=operenv,
    prompt='Vortex_oper' + __version__+':'
)

sessions.switch('oper')

def get_default_provider():
    return dict(
        username = 'mxpt001',
        suite = 'oper',
        igakey = 'france'
    )

def get_spec_provider(**kw):
    tmp_dict = get_default_provider()
    tmp_dict.update(kw)
    return tmp_dict
