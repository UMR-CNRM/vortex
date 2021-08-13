#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Leave it to Jeeves.

A basic launching interface to Jeeves' services !
"""

from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import os
import re
import shlex
import sys

vortexbase = re.sub(os.path.sep + 'bin$', '',
                    os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(vortexbase, 'site'))
sys.path.insert(0, os.path.join(vortexbase, 'src'))

from jeeves.butlers import Jeeves
from jeeves import bertie


def get_options():
    default_tag = 'test'
    default_level = 'INFO'
    description = "Leave it to Jeeves - A basic launching interface to Jeeves' services !"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        '-f',
        '--foreground',
        help="run in the foreground (don't daemonize)",
        action='store_true',
    )
    parser.add_argument(
        '-l',
        '--loglevel',
        help='log level of the logger (defaults to {})'.format(default_level),
        default=default_level,
        choices=['DEBUG', 'INFO', 'WARNING'],
    )
    parser.add_argument(
        'action',
        help='desired action',
        choices=['start', 'stop', 'restart', 'reload', 'status', 'debug', 'info'],
    )
    parser.add_argument(
        'tagname',
        nargs='?',
        help='name of the tag (defaults to {})'.format(default_tag),
        default=default_tag,
    )
    return parser.parse_args()


def add_args(s):
    """Add args to the command line, expressed like in a shell"""
    sys.argv.extend([os.path.expanduser(u) for u in shlex.split(s)])


def check_running_and_depot(j):
    """Check that the daemon run and that the depot directory exists."""
    if j.pidfile.is_running():
        j.pidfile.unlock()
    else:
        print('Apparently the Jeeves daemon is not running.')
        return False
    if not os.path.isdir('depot'):
        print('The daemon is running but there is no "depot" directory.')
        return False
    return True


if __name__ == "__main__":

    # add options for debugging
    # add_args('start test')

    opts = get_options()

    myname = os.path.basename(__file__)
    j = Jeeves(tag=opts.tagname, procname=myname, loglevel=opts.loglevel)

    if opts.action == 'start':
        j.start(mkdaemon=not opts.foreground)

    elif opts.action == 'stop':
        j.stop()

    elif opts.action == 'restart':
        j.restart()

    elif opts.action == 'reload':
        if check_running_and_depot(j):
            bertie.ask_reload()
            print('The Jeeves Daemon was asked to reload its configuration. Check the logs.')

    elif opts.action == 'status':
        if check_running_and_depot(j):
            print('Everything is fine, the Jeeves daemon is running')

    elif opts.action == 'debug':
        if check_running_and_depot(j):
            bertie.ask_debug()
            print('The Jeeves Daemon was asked to switch its default verbosity to DEBUG.')

    elif opts.action == 'info':
        if check_running_and_depot(j):
            bertie.ask_info()
            print('The Jeeves Daemon was asked to switch its default verbosity to INFO.')

    else:
        print('Unknown command:', opts.action)
        sys.exit(2)

    sys.exit(0)
