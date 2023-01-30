#!/usr/bin/env python3

"""
TNT Stack - A namelist's pack updater.
"""

import os
import sys

# Automatically set the python path
sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'src')
)

from thenamelisttool.entrypoints import tntstack as tnt_cli


if __name__ == '__main__':
    tnt_cli.main()
