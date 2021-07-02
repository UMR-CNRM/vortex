#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Example of BDPE extraction.

The 'extract' function tries to extract a product for several dates, both with
and without permission to access the archive version of the database. The result
should be similar to what is produced by the shell version bdpe_extract_cdp.sh.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

# load the packages used in this example
import common.data
import vortex
from bronx.stdtypes import date
from vortex import toolbox

# prevent IDEs from removing seemingly unused imports
assert common.data

t = vortex.ticket()
sh = t.sh
sh.trace = True
e = t.env
e.verbose(True, sh)


def extract(ndays=3, **special):
    tb = toolbox.input(
        # last ndays days at 18h, including today unless 18h is in the future
        date=list(date.daterange(
            date.today() + date.Period(days=-ndays, hours=+18),
            date.today()
        )),
        term=0,
        cutoff='production',
        model='aladin',

        local='[bdpeid]_[date:ymdhms]_[allow_archive]',

        namespace='bdpe.archive.fr',
        preferred_target='OPER',
        forbidden_target='INT',

        allow_archive=[False, True],

        **special
    )
    for (i, rh) in enumerate(tb):
        sh.title('rh #{}/{}:'.format(i + 1, len(tb)))
        # print(tb[i].idcard())
        tb[i].get()


# run in a dedicated directory
base = e.get(
    'RUNDIR',
    sh.path.join(
        e.get('TMPDIR', e.get('WORKDIR', sh.path.join(e.HOME, 'tmp'))),
        'rundir'
    )
)
sdate = date.now().ymdhms
rundir = sh.path.join(base, sdate[:8] + '-' + sdate[8:])
sh.subtitle('rundir is ' + rundir)

with sh.cdcontext(rundir, create=True):

    testing = 'cdph'
    # testing = 'antig'

    if testing == 'cdph':
        # 3 days ok with archive access, only 1 day w/o
        extract(
            ndays=3,
            bdpeid=7885,
            unknownflow=True,
        )

    if testing == 'antig':
        # 3 days only, be it with or w/o archive access
        extract(
            ndays=4,
            bdpeid=8097,
            format='fa',
            geometry='antigsp16km',
            kind='boundary',
            source_app='ifs',
            source_conf='determ',
        )

    sh.ls('-l', output=False)

print("That's all, Folks!")
