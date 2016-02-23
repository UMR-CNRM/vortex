#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Extract all files provided by the genv command for one or several cycles.

e.g.:
   $ cd /chaine/mxpt001/vortex/cycles'
   $ ggetall.py -nvc cy41t1_op1.33.genv -f cycles.txt
will freeze cycle cy41t1_op1.33 and all cycle names from cycles.txt.

Description files for option -f may include comments (introduced by '#')
and  blank lines. The usual separators are allowed (space, tab, newline).
"""

import argparse

import vortex
from iga.util import swissknife


def parse_command_line():
    description = "Creates a frozen copy of gco resources (in gco/ and genv/)."

    parser = argparse.ArgumentParser(description=description)

    group = parser.add_argument_group(title='at least one of -c and -f is mandatory')
    group.add_argument('-c', '--cycle', nargs='+', help='cycle name(s) (e.g. cy38t1_op2.13)')
    group.add_argument('-f', '--file', nargs='+', help='file(s) containing a list of cycles')

    parser.add_argument('-l', '--list', help='only list cycles to freeze, and exit', action='store_true')
    parser.add_argument('-n', '--noerror', help="don't stop on errors", action='store_true')
    parser.add_argument('-v', '--verbose', dest='verbose', help='verbose mode', action='store_true')
    parser.add_argument('-q', '--noverbose', dest='verbose', help='quiet (non-verbose) mode, the default',
                        action='store_false')

    args = parser.parse_args()
    if not (args.cycle or args.file):
        parser.error('\nNo action requested: use -c or -f (or both)\n')
    return args


args = parse_command_line()
cycles = args.cycle or list()
files = args.file or list()
for filename in files:
    with open(filename) as fp:
        for line in fp.readlines():
            cycles.extend(line.partition('#')[0].strip().split())
cycles = {c.strip('.genv') for c in cycles}

if args.list:
    print 'cycles to freeze:'
    for cycle in cycles:
        print "    {}".format(cycle)
else:
    t = vortex.sessions.current()
    for cycle in cycles:
        t.sh.title('Freezing cycle : ' + cycle)
        increase, details = swissknife.freeze_cycle(
            vortex.ticket(),
            cycle=cycle,
            force=args.noerror,
            verbose=args.verbose,
            logpath='genv/ggetall.log'
        )
        print "Summary for cycle", cycle
        for k, v in details.items():
            print '\t{:10s}:{:3d}'.format(k, len(v))
        print '\tlocal store increase:', increase / (1024 * 1024), 'Mb'
