#!/usr/bin/env python2.7
# encoding: utf-8
"""
Generate and put fake promises (for test purposes).
"""

from multiprocessing import Event

from utils import promises_generator as pgen

if __name__ == "__main__":
    args = pgen.promises_argparse()
    pgen.auto_promises(args, Event())
