#!/usr/bin/env python2.7
# encoding: utf-8
"""
Generate and put fake promises (for test purposes).
"""

from __future__ import print_function, absolute_import

from argparse import ArgumentParser
from argparse import RawDescriptionHelpFormatter
import collections
from multiprocessing import Event
import os
import sys
import random
import tempfile
import time

import footprints as fp

import vortex  # @UnusedImport
import common  # @UnusedImport
from vortex import toolbox

S_CACHEROOT = '/tmp/vortex_manual_test'

R_DATE = '2016010100'
R_CUTOFF = 'production'
R_MODEL = 'arpege'
R_ROLE = 'PickMeUp'

RH_DICT = dict(date=R_DATE, cutoff=R_CUTOFF, model=R_MODEL, kind='gridpoint',
               origin='hst', format='grib', nativefmt='[format]',
               experiment='0007', namespace="vortex.cache.fr",
               block='forecast', storetrack = False,
               local = 'scrontch_[term]_[member]_[geometry::area]')

MISC_INIDELAY = 5

TodoEntry = collections.namedtuple('TodoEntry', ('t', 'rh', 'fail'))

vlogger = fp.loggers.getLogger('vortex')
vlogger.setLevel('WARNING')
logger = fp.loggers.getLogger(__name__)
logger.setLevel('INFO')


def ini_expected(args):
    """Create the expected resources."""

    t = vortex.ticket()
    env = t.env
    sh = t.sh

    # Setup the cache root
    sh.mkdir(args.cacheroot)
    env.MTOOLDIR = args.cacheroot

    # Jump into the cacheroot dir and create a tmp directory
    wkdir = tempfile.mkdtemp('', 'test_wkdir', env.MTOOLDIR)
    sh.cd(wkdir)

    # Create the promises
    toolbox.active_now = True
    toolbox.active_insitu = True
    tbex = toolbox.input(geometry=args.domains, member=range(args.nmembers),
                         term=fp.util.rangex(args.terms), expected=True,
                         role=R_ROLE, **RH_DICT)

    return t, wkdir, tbex


def auto_promises(args, ready_event):
    """Make promises and eventually honour them."""

    t = vortex.ticket()
    env = t.env
    sh = t.sh

    # Setup the cache root
    sh.mkdir(args.cacheroot)
    env.MTOOLDIR = args.cacheroot

    # Jump into the cacheroot dir and create a tmp directory
    wkdir = tempfile.mkdtemp('', 'test_wkdir', env.MTOOLDIR)

    try:
        sh.cd(wkdir)

        # Create the promises
        toolbox.active_now = True
        tbpr = toolbox.promise(geometry=args.domains, member=range(args.nmembers),
                               term=fp.util.rangex(args.terms), **RH_DICT)

        # Determine the output time of each resource + generate files
        todolist = list()
        for pr in tbpr:
            # Calculate the time on which the promise will be honoured
            lastmember = pr.provider.member == args.nmembers - 1
            delay = max(pr.resource.term.hour * args.stepdelay +
                        random.uniform(- args.randomdelay, args.randomdelay) +
                        MISC_INIDELAY +
                        (args.lastdelay if lastmember else 0),
                        0)
            # Is the member failing ?
            fail = lastmember and args.lastfails >= 0 and delay >= args.lastfails
            if fail:
                delay = args.lastfails
            # Lets dal with this entry
            todolist.append(TodoEntry(delay, pr, fail))
            with file(pr.container.localpath(), 'w') as fh:
                fh.write('This is a great test file !\n')
        # Sort the entries by time
        todolist.sort(lambda a, b: cmp(a.t, b.t))
        todolist = collections.deque(todolist)

        ready_event.set()
        t0 = time.time()

        sh.header("Ok: All the promised are placed. Now starting the waiting loop.")

        # Waiting loop
        popped = todolist.popleft() if todolist else None
        while popped is not None:
            t = time.time() - t0
            while popped is not None and popped.t < t:
                if popped.fail:
                    logger.info("At t=%12f, fail %s.",
                                popped.t, popped.rh.container.filename)
                    popped.rh.delete()
                else:
                    logger.info("At t=%12f, put  %s.",
                                popped.t, popped.rh.container.filename)
                    popped.rh.put()
                popped = todolist.popleft() if todolist else None
            time.sleep(0.1)

    finally:

        # Clean after this
        sh.cd(env.HOME)
        sh.rm(wkdir)


def promises_argparse():
    """Return the dictionnary of commandline arguments."""

    program_name = os.path.basename(sys.argv[0])
    program_desc = program_name + ' -- ' + __import__('__main__').__doc__.lstrip("\n")

    # Setup argument parser
    parser = ArgumentParser(description=program_desc,
                            formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("-v", "--verbose", dest="verbose", action="count",
                        help="set verbosity level [default: %(default)s]")
    parser.add_argument("-c", "--cacheroot", default=S_CACHEROOT,
                        help="The Vortex cache rootdir [default: %(default)s]")
    parser.add_argument("-n", "--nmembers", type=int, default=2,
                        help="The number of members to create [default: %(default)s]")
    parser.add_argument("-d", "--domains", default='glob05,glob15',
                        help="The list of domains (footprint style) [default: %(default)s]")
    parser.add_argument("-t", "--terms", default='0-6-3',
                        help="The list of terms (footprint style) [default: %(default)s]")
    parser.add_argument("-s", "--stepdelay", type=int, default=5,
                        help="Duration of a one hour forecast (in sec.) [default: %(default)s]")
    parser.add_argument("-r", "--randomdelay", type=int, default=4,
                        help="The random delay added to the step delay (in sec.) " +
                        "[default: %(default)s]")
    parser.add_argument("--lastfails", type=int, default=-1,
                        help="The last member will fail at t=N (in sec.)" +
                        "[default: %(default)s]")
    parser.add_argument("--lastdelay", type=int, default=0,
                        help="The last member will start N sec. late" +
                        "[default: %(default)s]")
    args = parser.parse_args()

    return args


if __name__ == "__main__":
    args = promises_argparse()
    auto_promises(args, Event())
