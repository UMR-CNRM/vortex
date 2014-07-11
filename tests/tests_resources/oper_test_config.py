# -*- coding: utf-8 -*-

__all__ = [
    'os', 'logging', 'TestCase', 'TestLoader', 'TextTestRunner', 'common',
    'iga', 'toolbox', 'sessions', 'resources', 'SpectralGeometry', 'GridGeometry',
    'today', 'Date', 'Period', 'vortex', 't', 'get_default_provider',
    'get_spec_provider', 'IgaHelperSelect', 'datadir', 'homedir'
]

import os  # @UnusedImport
import logging  # @UnusedImport
from unittest import TestCase, TestLoader, TextTestRunner  # @UnusedImport

import vortex
from vortex import toolbox, sessions
from vortex.tools import env
from vortex.data import resources  # @UnusedImport
from vortex.data.geometries import SpectralGeometry, GridGeometry  # @UnusedImport
from vortex.tools.date import today, Date, Period  # @UnusedImport

from iga.utilities.helpers import IgaHelperSelect  # @UnusedImport

import common.data
import iga.data
u_fill_fp_catalogs = common.data, iga.data

# main variables definition for unittest
fpg = dict(tag='oper', user='mxpt001', profile='oper')
operenv = env.Environment(active=True)
operenv.glove = sessions.glove(**fpg)
t = sessions.ticket(
    tag=fpg['tag'],
    glove=operenv.glove,
    topenv=operenv,
    prompt='Vortex_oper' + vortex.__version__+':'
)

tg = t.sh.target()
datadir = tg.get('op:datadir')
homedir = tg.get('op:homedir')

toolbox.defaults(namespace='[suite].inline.fr')
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
