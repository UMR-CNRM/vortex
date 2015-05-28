#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Leave it to Jeeves
A basic launching interface to Jeeves' services !
"""

import os, sys
import argparse

rootpath = os.path.dirname(os.path.dirname(os.path.realpath(sys.argv[0])))
incvortex = [ os.path.realpath(x) for x in sys.path if 'vortex' in x ]
for thispath in [ os.path.join(rootpath, x) for x in ('site', 'src') ]:
    if thispath not in incvortex:
        print 'ADD to sys.path', thispath
        sys.path.append(thispath)

from jeeves.butlers import Jeeves


def get_options():
    default_tag = 'test'
    description = "Leave it to Jeeves - A basic launching interface to Jeeves' services !"
    parser = argparse.ArgumentParser(description=description)
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

    j = Jeeves(tag=opts.tagname)

    if opts.action == 'start':
        j.start(mkdaemon=True)

    elif opts.action == 'stop':
        j.stop()

    elif opts.action == 'restart':
        j.restart()

    else:
        print 'Unknown command'
        sys.exit(2)

    sys.exit(0)
