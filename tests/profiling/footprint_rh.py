from __future__ import print_function, division, absolute_import, unicode_literals

from cProfile import Profile
# from meliae import scanner
import pstats
import os
import datetime

do_cprofiles = True

if do_cprofiles:
    pr = Profile()
    pr.enable()

t0 = datetime.datetime.utcnow()

import bronx.stdtypes.date
import footprints as fp

import vortex  # @UnusedImport
import olive  # @UnusedImport
import gco  # @UnusedImport
from vortex import toolbox

n_loads = 10000

fp.setup.defaults = dict(model='arpege',
                         date=bronx.stdtypes.date.Date('2016010100'),
                         cutoff='assim',
                         geometry=vortex.data.geometries.get(tag='global798'), )

for n in range(n_loads):

    rh = toolbox.rh(kind='gridpoint',
                    format='grib',
                    nativefmt='[format]',
                    origin='hst',
                    term=3,
                    local='toto',
                    namespace='vortex.multi.fr',
                    experiment='0007',
                    block='forecast',
                    )

t1 = datetime.datetime.utcnow()
print('Real time spent (nloads: {:d}): {:f} seconds.'.format(n_loads,
                                                             (t1 - t0).total_seconds()))

if do_cprofiles:
    pr.disable()
    ps = pstats.Stats(pr).sort_stats('cumulative')

    # Save to file
    radix = (os.environ['HOME'] + '/footprint_rh_' +
             datetime.datetime.utcnow().isoformat())
    ps.dump_stats(radix + '.prof')

    # scanner.dump_all_objects(radix + '.mem')
