#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Exemple du wiki
http://sicompas/vortex/doku.php/documentation:faq:rhandler

Ok 20180801 - GR
"""
from __future__ import print_function, absolute_import, unicode_literals, division

import common.data
import olive.data
import vortex
from vortex.data.geometries import Geometry
from bronx.stdtypes import date

assert any([common.data, olive.data])


# Initialize environment for examples
t = vortex.ticket()
sh = t.sh
e = t.env


# Change the work directory
workdirectory = '/'.join([e.HOME, "tmp", "Vortex"])
if not sh.path.isdir(workdirectory):
    sh.mkdir(workdirectory)
sh.chdir(workdirectory)

# Define the run date
rundate = date.today() + date.Period('PT00H')


# Define the resource
rh = vortex.toolbox.rh(
    cutoff         = 'production',
    date           = rundate,
    format         = 'fa',
    kind           = 'historic',
    local          = 'CPLINIT+[term::fmthm]',
    model          = 'arpege',
    namespace      = '[suite].archive.fr',
    suite          = 'oper',
    term           =  8,
    vapp           = '[model]',
    vconf          = '4dvarfr',
    geometry       = Geometry(tag='globalsp2'),
)

print('container  : {}\n'.format(rh.container))
print('provider   : {}\n'.format(rh.provider))
print('resource   : {}\n'.format(rh.resource))
print('idcard()   :')
print(rh.idcard())
print('\ncomplete   : {}\n'.format(rh.complete))
print('location() : {}\n'.format(rh.location()))
#print('get()      : {}\n'.format(rh.get()))
print('check()    : {}\n'.format(rh.check()))
print('locate()   : {}\n'.format(rh.locate()))
