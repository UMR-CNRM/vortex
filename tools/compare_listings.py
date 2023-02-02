#!/usr/bin/env python3

"""
A command line tool that compares two Arpege/IFS listings.
"""

import os
import sys

# Automatically set the python path
sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.realpath(__file__)), '..', 'src')
)

from arpifs_listings.entrypoints import compare_listings as cmp_cli


if __name__ == '__main__':
    cmp_cli.main()
