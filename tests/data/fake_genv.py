#!/usr/bin/env python

from __future__ import print_function, absolute_import, unicode_literals, division

import os
import sys

cycle = '{:s}.genv'.format(sys.argv[1])
where = os.path.dirname(__file__)

with open(os.path.join(where, cycle)) as fh:
    print(fh.read())
