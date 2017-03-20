#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

"""
Leave it to Jeeves
A basic launching interface to Jeeves' services !
"""

import os
import re
import sys
import argparse

vortexbase = re.sub(os.path.sep + 'bin$', '',
                    os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, os.path.join(vortexbase, 'site'))
sys.path.insert(0, os.path.join(vortexbase, 'src'))

from jeeves.butlers import Jeeves


def get_options():
    default_tag = 'test'
    default_level = 'INFO'
    description = "Leave it to Jeeves - A basic launching interface to Jeeves' services !"
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument(
        '-f',
        '--foreground',
        help="run in the foreground( don't daemonize)",
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
        choices=['start', 'stop', 'restart'],
    )
    parser.add_argument(
        'tagname',
        nargs='?',
        help='name of the tag (defaults to {})'.format(default_tag),
        default=default_tag,
    )
    return parser.parse_args()


if __name__ == "__main__":

    opts = get_options()

    j = Jeeves(tag=opts.tagname, loglevel=opts.loglevel)

    if opts.action == 'start':
        j.start(mkdaemon=not opts.foreground)

    elif opts.action == 'stop':
        j.stop()

    elif opts.action == 'restart':
        j.restart()

    else:
        print 'Unknown command'
        sys.exit(2)

    sys.exit(0)
