#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, division

"""
Extract all files provided by the genv command for one or several cycles,
and/or remove the files needed only by a specific cyle.

e.g.:
   $ cd /chaine/mxpt001/vortex/cycles'
   $ ggetall.py -nvc cy41t1_op1.33.genv -f cycles.txt
will freeze cycle cy41t1_op1.33 and all cycle names from cycles.txt.

   $ ggetall.py -vr cy41t1_op1.33 -f cycles.txt
will freeze all cycle names found in cycle.txt, then remove the files
of cy41t1_op1.33 that are not needed by any other cycle described in
genv/*.genv (which includes those freshly added from cycles.txt).

Description files for option -f may include comments (introduced by '#')
and  blank lines. The usual separators are allowed (space, tab, newline).
"""

import argparse
import os
import sys

# Automatically set the python path
vortexbase = os.path.dirname(os.path.abspath(__file__)).rstrip('/bin')
sys.path.insert(0, os.path.join(vortexbase, 'site'))
sys.path.insert(0, os.path.join(vortexbase, 'src'))


def parse_command_line():
    description = "Create or remove frozen copies of gco resources in gco/ and genv/."
    parser = argparse.ArgumentParser(description=description)

    group = parser.add_argument_group(title='at least one of -c, -f or -r is mandatory')
    group.add_argument('-c', '--cycles', nargs='+', help='name(s) of cycle(s) to freeze')
    group.add_argument('-f', '--file', nargs='+', help='file(s) containing a list of cycles to freeze')
    group.add_argument('-r', '--remove', help='name of the cycle to remove')

    parser.add_argument('-l', '--list', help='only list cycles to handle, and exit', action='store_true')
    parser.add_argument('-n', '--noerror', help="don't stop on errors", action='store_true')
    parser.add_argument('-s', '--simulate', help="simulate removal without doing it", action='store_true')
    parser.add_argument('-v', '--verbose', dest='verbose', help='verbose mode', action='store_true')
    parser.add_argument('-q', '--noverbose', dest='verbose', help='quiet (non-verbose) mode, the default',
                        action='store_false')

    args = parser.parse_args()
    if not (args.cycles or args.file or args.remove):
        parser.error('\nNo action requested.\nUse at least one of: -c, -f or -r\n')

    # add cycles from -f arguments
    args.cycles = args.cycles or list()
    files = args.file or list()
    for filename in files:
        with open(filename) as fp:
            for line in fp.readlines():
                args.cycles.extend(line.partition('#')[0].strip().split())

    # remove ".genv" extensions (to ease copy-paste)
    args.cycles = {c.strip('.genv') for c in args.cycles}
    if args.remove:
        args.remove = args.remove.strip('.genv')

    # check consistency
    if args.remove in args.cycles:
        print('\nCannot both freeze *and* remove cycle {}\n'.format(args.remove))
        sys.exit(1)

    return args


def list_cycles(args):
    sep = '\n    '
    if args.cycles:
        print('cycles to freeze:' + sep + sep.join(args.cycles))
    if args.remove:
        print('cycle  to remove:' + sep + args.remove)


def freeze(args):
    import vortex
    from iga.util import swissknife
    t = vortex.sessions.current()
    for cycle in args.cycles:
        t.sh.title('Freezing cycle : ' + cycle)
        increase, details = swissknife.freeze_cycle(
            vortex.ticket(),
            cycle=cycle,
            force=args.noerror,
            verbose=args.verbose,
            logpath='ggetall.log'
        )
        print("Summary for freezing cycle", cycle)
        for k, v in list(details.items()):
            print('\t{:12s}:{:4d}'.format(k, len(v)))
        print('\tlocal store increase:', increase // (1024 * 1024), 'Mb')


def unfreeze(args):
    import vortex
    from iga.util import swissknife
    t = vortex.sessions.current()
    if args.simulate:
        t.sh.title('Simulating removal of cycle : ' + args.remove)
    else:
        t.sh.title('Removing cycle : ' + args.remove)
    decrease, details = swissknife.unfreeze_cycle(
        vortex.ticket(),
        delcycle=args.remove,
        fake=args.simulate,
        verbose=args.verbose,
        logpath='ggetall.log'
    )
    print("Summary for unfreezing cycle", args.remove)
    for k, v in list(details.items()):
        print('\t{:12s}:{:4d}'.format(k, len(v)))
    print('\tlocal store decrease:', decrease // (1024 * 1024), 'Mb')


if __name__ == "__main__":
    args = parse_command_line()
    if args.list:
        list_cycles(args)
    else:
        if args.cycles:
            freeze(args)
        if args.remove:
            unfreeze(args)
