#!/usr/bin/env python3

"""
TNTdiffpack - The Namelist Tool: a namelist pack comparator.
"""

import os
import sys

# Automatically set the python path
sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'src')
)

from thenamelisttool.entrypoints import tntdiffpack as tnt_cli


if __name__ == '__main__':
    tnt_cli.main()
