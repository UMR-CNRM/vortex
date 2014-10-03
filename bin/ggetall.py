#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse

description = "Creates a frozen copy of gco resources (in gco/ and genv/)."

parser = argparse.ArgumentParser(description=description)
parser.add_argument('-c', '--cycle',     required=True,  help='cycle name (e.g. cy38t1_op2.13)')
parser.add_argument('-f', '--force',                     help='ignore errors',    action='store_true')
parser.add_argument(      '--noverbose', dest='verbose', help='non-verbose mode', action='store_false')
parser.add_argument('-v', '--verbose',   dest='verbose', help='verbose mode',     action='store_true')

args = parser.parse_args()

import vortex
from iga.util import swissknife

increase, details = swissknife.freeze_cycle(
    vortex.ticket(),
    cycle   = args.cycle,
    force   = args.force,
    verbose = args.verbose,
    logpath = 'genv/ggetall.log'
)

print 'Local store increase =', increase / ( 1024 * 1024 ), 'Mb'
for k, v in details.items():
    print 'Number of items', k.ljust(10), '=', len(v)
