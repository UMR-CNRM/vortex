# -*- coding: utf-8 -*-


__all__ = [ 'os', 'logging', 'TestCase', 'TestLoader', 'TextTestRunner',
            'common', 'iga', 'toolbox', 'sessions',
            'resources', 'SpectralGeometry', 'GridGeometry',
            'today', 'Date', 'Period', 'vortex', 't', 'get_default_provider',
            'get_spec_provider', 'IgaHelperSelect', 'datadir', 'homedir'
        ]
import os
import logging
from unittest import TestCase, TestLoader, TextTestRunner

import vortex
from vortex import toolbox, sessions
from vortex.tools import env
from vortex.data import resources
from vortex.data.geometries import SpectralGeometry, GridGeometry
from vortex.tools.date import today, Date, Period


import common.data
import iga.data
from iga.utilities.helpers import IgaHelperSelect

#main variables definition for unittest
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
