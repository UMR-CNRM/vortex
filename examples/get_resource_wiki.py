# -*- coding: utf-8 -*-

"""
Various ways to retrieve informations on a resource handler and it's components.

Ok 20180801 - GR
"""

from __future__ import absolute_import, division, print_function, unicode_literals


# load the packages used in this example
import common.data
import olive.data
import vortex
from bronx.stdtypes import date
from vortex.data.geometries import Geometry

# prevent IDEs from removing seemingly unused imports
assert any([common, olive])


# set up the Vortex environment
t = vortex.ticket()
sh = t.sh
e = t.env

# change the working directory
working_directory = sh.path.join(e.HOME, "tmp", "vortex_examples_tmpdir")
sh.cd(working_directory, create=True)

# define the run date
rundate = date.today() + date.Period('PT00H')

# define the resource
rh = vortex.toolbox.rh(
    cutoff     = 'production',
    date       = rundate,
    format     = 'fa',
    kind       = 'historic',
    local      = 'CPLINIT+[term::fmthm]',
    model      = 'arpege',
    namespace  = '[suite].archive.fr',
    suite      = 'oper',
    term       = 8,
    vapp       = '[model]',
    vconf      = '4dvarfr',
    geometry   = Geometry(tag='globalsp2'),
)

print('container  : {}\n'.format(rh.container))
print('provider   : {}\n'.format(rh.provider))
print('resource   : {}\n'.format(rh.resource))
print('idcard()   :')
print(rh.idcard())
print('\ncomplete : {}\n'.format(rh.complete))
print('location() : {}\n'.format(rh.location()))
# print('get()      : {}\n'.format(rh.get()))
print('check()    : {}\n'.format(rh.check()))
print('locate()   : {}\n'.format(rh.locate()))
