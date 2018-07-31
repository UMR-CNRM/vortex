#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Exemple du wiki
http://sicompas/vortex/doku.php/documentation:faq:rhandler
"""

from __future__ import division, print_function, absolute_import

import os
import sys

import common.data
import footprints
import gco.data
import iga.data
import olive.data
import vortex.data
from bronx.stdtypes import date
from gco.tools import genv
from iga.tools import services
from vortex.data.geometries import Geometry
from vortex.tools import lfi, odb, grib, ddhpack, rawfiles
from vortex.tools.actions import actiond as ad

# ### would be removed by auto-import... ###
assert any((common.data, gco.data, iga.data, olive.data, vortex.data))
assert any((lfi, odb, grib, ddhpack, rawfiles))
assert any((date, ad, services))
assert any((os, sys))

# ### Standard vortex init
fpx = footprints.proxy
t = vortex.ticket()
sh = t.sh
sh.trace = True
sh.verbose = True
e = t.env
e.verbose(True, sh)

# ### Load add-ons ###
addons = ['lfi', 'odb', 'gribapi', 'grib', 'ddhpack', 'rawfiles']
loaded = list()

if not (sys.platform == 'darwin' or 'alose' in sh.hostname):
    fpx.targets.discard_onflag('is_anonymous', verbose=False)
    for addon in addons:
        try:
            if fpx.addon(shell=sh, kind=addon):
                loaded.append(addon)
        except AttributeError:
            print('{}: not loaded'.format(addon))
    print('- Addons loaded: {}'.format(' '.join(loaded)))
    del addons
    del loaded


def essai_1():
    # try a folder
    # print(sh.rawfiles_ftput)
    dico = dict(
        source      = os.path.expanduser('~/.tkdiffrc'),
        destination = 'test_rawfiles',
        fmt         = 'rawfiles',
        hostname    = 'hendrix',
        logname     = 'lamboleyp',
    )
    sh.ftput(**dico)


def essai_2():
    rh = vortex.toolbox.rh(
        # ## role
        format     = 'fa',
        local      = 'ICMSHFCST+[term::fmthm]',
        # rsrc
        kind       = 'historic',
        model      = 'arome',
        term       = [0, 1, 6],
        # ## provider
        block      = 'forecast',
        experiment = 'oper',
        namespace  = 'vortex.multi.fr',
        # ## defaults
        cutoff     = 'production',
        geometry   = Geometry(tag='franmgsp25'),
        date       = '2017-02-06T00:00:00Z',
        cycle      = 'al42_arome@ifs-op2.01',
        gnamespace = 'gco.multi.fr',
        # model = 'arome',
        # namespace = 'vortex.multi.fr',
        # ## other
        suite      = 'oper',
        vapp       = '[model]',
        vconf      = '4dvarfr',
        checkrole  = '*.grib',
    )
    test_magic = False
    if test_magic:
        p = fpx.provider(magic='function:///common.util.ens.safedrawingfunction')
        print(p)
        rh.provider = p
    print('container :', rh.container)
    print('provider  :', rh.provider)
    print('resource  :', rh.resource)
    print('idcard()  :', rh.idcard())
    print('complete  :', rh.complete)
    print('location():', rh.location())
    print('get()     :', rh.get())
    print('check()   :', rh.check())
    print('locate()  :', rh.locate())


def essai_3():
    # /home/mf/dp/marp/verolive/SAVE/public/mtool-2.2.5/include/python) cat env.gco.beaufix
    # e.GGET_PATH   = '[this:public]/gco-tools/std/bin'
    # e.GGET_TAMPON = '[this:public]/gco-tools/std/tampon'
    # vortex.toolbox.defaults(gnamespace='gco.multi.fr')
    the_cycle = 'al42_arome@ifs-op2.03'
    defs = genv.autofill(the_cycle)
    print('{} definitions in genv for cycle {}'.format(len(defs), the_cycle))
    rh = vortex.toolbox.rh(
        # ## role
        # intent='inout',
        # role="Namelist",
        # rsrc
        format     = 'ascii',
        kind       = 'namelist',
        source     = 'namel_prep',
        # ## provider
        genv       = the_cycle,
        # gnamespace='gco.multi.fr',
        gnamespace = 'opgco.cache.fr',
        # ## file
        local      = 'OPTIONS.nam',
        # ## defaults
        cutoff     = 'production',
        geometry   = Geometry(tag='franmgsp25'),
        date       = '2017-02-06T00:00:00Z',
        cycle      = the_cycle,
        model      = 'arome',
        namespace  = 'vortex.multi.fr',
        # ## other
        # suite='oper',
        # vapp='[model]',
        # vconf='4dvarfr',
        # checkrole='*.grib',
    )
    # IgaGcoCacheStore initiates rootdir from this:
    e.op_gcocache = '/tmp/vortex/cycles'
    print('container :', rh.container)
    print('provider  :', rh.provider)
    print('resource  :', rh.resource)
    print('idcard()  :', rh.idcard())
    print('complete  :', rh.complete)
    print('location():', rh.location())
    print('get()     :', rh.get())
    print('check()   :', rh.check())
    print('locate()  :', rh.locate())


if __name__ == '__main__':
    essai_3()
    print("That's all, Folks!")
