#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Leave it to Jeeves
A basic lauching interface to Jeeves' services !
"""

import sys, time

from jeeves.butlers import Jeeves

if __name__ == "__main__":

    if len(sys.argv) < 2:
        print "usage: %s start|stop|restart [tagname]" % sys.argv[0]
        sys.exit(2)
    else:
        if len(sys.argv) == 3:
            tagname = sys.argv[1]
        else:
            tagname = 'test'
        j = Jeeves(tag=tagname)
        if 'start' == sys.argv[1]:
            j.start(mkdaemon=True)
        elif 'stop' == sys.argv[1]:
            j.stop()
        elif 'restart' == sys.argv[1]:
            j.restart()
        else:
            print 'Unknown command'
            sys.exit(2)
        sys.exit(0)
