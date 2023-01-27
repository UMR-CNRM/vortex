#!/usr/bin/env python3

"""
Example of BDPE extraction.

The 'extract' function tries to extract a product for several dates, both with
and without permission to access the archive version of the database. The result
should be similar to what is produced by the shell version bdpe_extract_cdp.sh.
"""

# prefer the vortex version this file is in
import os
import sys

vortexbase = os.path.realpath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(vortexbase, 'site'))
sys.path.insert(0, os.path.join(vortexbase, 'src'))

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


def vortex_path():
    """Base path of the vortex currently running."""
    p = vortex.__file__
    for _ in range(3):
        p = sh.path.dirname(p)
    return p


def extract(days, **special):
    """Loop on some attributes values, just for testing."""

    # computes dates so that days = [1, 2] is an easy way to express [J-1, J-2] at 18h
    list_of_dates = [date.today() + date.Period(days=-day, hours=+18) for day in days]

    # @formatter: off
    tb = toolbox.input(
        date             = list_of_dates,
        term             = 0,
        local            = '[bdpeid]_[date:ymdh]_P[preferred_target]_F[forbidden_target]'
                           '_D[soprano_domain]_[allow_archive]',
        namespace        = 'bdpe.archive.fr',
        preferred_target = ['oper',],
        forbidden_target = ['int',],
        soprano_domain   = ['dev',],
        allow_archive    = [False, True],
        bdpe_timeout     = 5,
        bdpe_retries     = 1,

        **special
    )
    # @formatter: on

    for (i, rh) in enumerate(tb):
        sh.title('rh #{}/{}:'.format(i + 1, len(tb)))
        print(tb[i].idcard())
        tb[i].get()


# run in a dedicated directory
base = sh.path.join(e.get('TMPDIR', e.get('WORKDIR', sh.path.join(e.HOME, 'tmp'))))
rundir = sh.path.join(base, 'rundir', date.now().strftime('%Y%m%d-%H%M%S'))
sh.subtitle('rundir is ' + rundir)

print('vortex version:', vortex.__version__, 'from', vortex_path())

with sh.cdcontext(rundir, create=True):
    # cdph
    # 3 days with archive access, only 1 day w/o
    # @formatter: off
    extract(
        days        = [4, 5, 6],
        bdpeid      = 7885,
        cutoff      = 'production',
        model       = 'aladin',
        unknownflow = True,
    )
    # @formatter: on

    # antilles coupling files from ecmwf
    # 3 days only, be it with or w/o archive access
    # @formatter: off
    extract(
        days        = [3, 4],
        bdpeid      = 14351,
        kind        = 'boundary',
        source_app  = 'ifs',
        source_conf = 'determ',
        geometry    = 'antilles8km',
        cutoff      = 'production',
        model       = 'aladin',
    )
    # @formatter: on

    sh.ls('-l', output=False)

print("That's all, Folks!")
