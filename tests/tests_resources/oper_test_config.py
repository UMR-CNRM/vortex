# -*- coding: utf-8 -*-

__all__ = [
    # logging and std test
    'logging', 'TestCase', 'TestLoader', 'TextTestRunner',
    # vortex packages
    'common', 'iga', 'toolbox', 'sessions', 'resources',
    # vortex classes
    'SpectralGeometry', 'GridGeometry', 'IgaHelperSelect',
    # local test functions
    'get_default_provider', 'get_spec_provider', 
    # some default env values
    'sh', 'datadir', 'homedir', 'rundate', 'rundate_bis'
]

import os  # @UnusedImport
import logging  # @UnusedImport
from unittest import TestCase, TestLoader, TextTestRunner  # @UnusedImport

import vortex
from vortex import toolbox, sessions
from vortex.tools import env
from vortex.data import resources  # @UnusedImport
from vortex.data.geometries import SpectralGeometry, GridGeometry  # @UnusedImport
from vortex.tools import date

from iga.util.helpers import IgaHelperSelect  # @UnusedImport

import common.data
import iga.data
u_fill_fp_catalogs = common.data, iga.data

# A nice synoptic time for date value
rundate = date.yesterday() + date.Period('PT18H')
rundate_bis = date.today()



# main variables definition for unittest
fpg = dict(tag='oper', user='mxpt001', profile='oper')
operenv = env.Environment(active=True)
operenv.glove = sessions.getglove(**fpg)
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

sh = t.sh

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
