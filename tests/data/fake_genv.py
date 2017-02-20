#!/usr/bin/env python

import os
import sys

cycle = '{:s}.genv'.format(sys.argv[1])
where = os.path.dirname(__file__)

with open(os.path.join(where, cycle)) as fh:
    print fh.read()
