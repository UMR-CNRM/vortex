#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import division, print_function, absolute_import

"""
In a Terminal: ~/.vortex should point to the right vortex/
open $(python -m site --user-site)/vortex.pth
open $(python3 -m site --user-site)/vortex.pth

Version Guillaume sur prolix:

    /scratch/work/morvang/vortex/dev/mfwam_DEV@morvang
"""

import sys
import os

version = '/scratch/work/morvang/vortex/dev/mfwam_DEV@morvang/vortex'
sys.path.insert(0, os.path.expanduser(version + '/src'))
sys.path.insert(0, os.path.expanduser(version + '/site'))

import logging

import common.data
import footprints
import gco
import iga
import olive
import previmar.data
import vortex
from bronx.stdtypes import date
from vortex import toolbox

assert any((common, previmar, gco, olive, iga))

logger = logging.getLogger("footprints")
# logger.setLevel(logging.DEBUG)

t = vortex.ticket()
e = t.env
sh = t.sh

sh.trace = True
e.verbose(True, sh)
fpx = footprints.proxy

# run in a dedicated directory
rundir = e.get('RUNDIR', e.WORKDIR + '/rundir/' + date.today().ymd)
sh.cd(rundir, create=True)
sh.subtitle('Vortex is ' + vortex.__file__)
sh.subtitle('Rundir is ' + rundir)


def get_1():
    tb_uget = toolbox.input(
        role     = 'InflationFactor',
        format   = 'ascii',
        genv     = 'uenv:al42_arome@aefrance-op2.01@meunierlf',
        geometry = 'franmgsp38',
        insitu   = False,
        kind     = 'infl_factor',
        local    = 'inflation_factor',
        term     = 3,
        cutoff   = 'assim',
        date     = '2017-10-11T21:00:00Z',
        model    = 'arome',
    )
    print(footprints.proxy.resources.report_whynot('common.data.obs.Obsmap'))
    t = tb_uget[0]
    print(t)
    print(tb_uget)
    tb_uget[0].get()


def get_2():
    tb_obsmap = toolbox.input(
        role    = 'Obsmap',
        kind    = 'obsmap',
        local   = 'bator_map',
        remote  = '/home/mf/dp/marp/civiatem/batormap_sans_atms',
        cutoff  = 'production',
        date    = date.now(),
        model   = 'arome',
        discard = ('atms',)
    )
    print(footprints.proxy.resources.report_whynot('common.data.obs.Obsmap'))
    t = tb_obsmap[0]
    print(t)
    print(tb_obsmap)
    tb_obsmap[0].get()


def get_3():
    tb_errgribvor = toolbox.input(
        role       = '---',
        kind       = 'bgstderr',
        local      = 'errgribvor.tmp',
        cutoff     = 'assim',
        geometry   = 'globalupd399',
        date       = date.now(),
        model      = 'aearp',
        stage      = 'unbal',
        experiment = 'OPER',
        block      = 'the_block',
    )
    print(footprints.proxy.resources.report_whynot('common.data.assim.BackgroundStdError'))
    t = tb_errgribvor[0]
    print(t)
    print(tb_errgribvor)
    tb_errgribvor[0].get()


def get_4():
    # 20180717 Guillaume Morvan (insitu=False)
    # (version de vortex "morvan" incluant cette resource)
    sh.remove('currents.ascii')
    # l'un ou l'autre suffit
    toolbox.defaults(rootdir='/chaine/mxpt001')
    e.DATADIR = '/chaine/mxpt001'
    # ne devrait pas marcher avec True: caches seulement
    # et oper.inline n'est pas un cache, au sens Vortex.
    toolbox.active_incache = True
    tb = toolbox.input(
        date      = '2018-07-11T00:00:00Z',
        role      = 'Current',
        cutoff    = 'production',
        format    = 'ascii',
        geometry  = 'globalirr01',
        kind      = 'WaveCurrent',
        local     = 'currents.ascii',
        namespace = '[suite].inline.fr',
        suite     = 'oper',
        term      = '0',
        model     = 'mfwam',
        vapp      = 'mfwam',
        vconf     = 'global@cep01',
        # igakey = dict[vapp][vconf] remappé en fin de ./common/tools/igastuff.py
        # igakey='mfwamglocep01',
        # insitu=False,
        # loglevel='DEBUG',
        # verbose=True,
    )
    print(footprints.proxy.resources.report_whynot('previmar.data.resources.WaveCurrent'))
    s = '/chaine/mxpt001/vagues/mfwamglocep01/oper/data/fic_day/currents_201807110000'
    sh.ls('-l', s, output=False)
    print(tb)
    print(tb[0])
    tb[0].get()
    print(toolbox.active_incache)


if __name__ == '__main__':
    get_1()
    get_2()
    get_3()
    get_4()
