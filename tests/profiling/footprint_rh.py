
from cProfile import Profile
#from meliae import scanner
import gc
import pstats
import os
import datetime

pr = Profile()
pr.enable()

import footprints as fp

import vortex  # @UnusedImport
import olive  # @UnusedImport
import gco  # @UnusedImport
from vortex import toolbox

fp.collectors.get(tag='resource').fasttrack = ('kind',)

n_loads = 10000

fp.setup.fastmode = True
fp.setup.fastkeys = ('kind', 'namespace')

fp.setup.defaults = dict(model='arpege',
                         date='2016010100',
                         cutoff='assim',
                         geometry='global798')

for n in range(n_loads):

    rh = toolbox.rh(
            kind='gridpoint',
            format='grib',
            nativefmt='[format]',
            origin='hst',
            term=3,
            local='toto',
            namespace='vortex.multi.fr',
            experiment='0007',
            block='forecast',
        )

pr.disable()
ps = pstats.Stats(pr).sort_stats('cumulative')

# Save to file
radix = (os.environ['HOME'] + '/footprint_rh_' +
         datetime.datetime.utcnow().isoformat())
ps.dump_stats(radix + '.prof')

#scanner.dump_all_objects(radix + '.mem')
