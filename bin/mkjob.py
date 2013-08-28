#!/bin/env python
# -*- coding: utf-8 -*-

import vortex
from iga.utilities import swissknife

t = vortex.ticket()

opts = t.sh.rawopts(
    defaults = dict(
        verbose  = 'on',
        name     = None,
    )
)

t.sh.header(' '.join(('Vortex', vortex.__version__, 'job builder')))
for k, v in opts.iteritems():
    print ' >', k.ljust(16), ':', v

if not opts['name']:
    vortex.logger.error('A job name sould be provided.')
    exit(1)

opts['wrap'] = False
corejob, tplconf = swissknife.mkjob(t, **opts)

t.sh.header('Template configuration')
for k, v in sorted(tplconf.iteritems()):
    print ' >', k.ljust(16), ':', v

with open(tplconf['file'], 'w') as job:
    job.write(corejob)

t.sh.header('Job creation completed')
