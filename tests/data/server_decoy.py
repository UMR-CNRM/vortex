# -*- coding: utf-8 -*-

from __future__ import print_function

import argparse
import os
import subprocess
import sys
import time

sync_py = './decoy_sync.py'


def server(sleep, crash, verb):
    stop_request = False
    i = 0
    while not stop_request:
        if verb:
            print('Starting the {} script.'.format(sync_py))
        retcode = subprocess.call([sys.executable, sync_py])
        if verb:
            print('{} retcode is: {:d}.'.format(sync_py, retcode))
        if retcode == 1:  # This should not happened
            print('Oh my god !')
            sys.exit(1)
        elif retcode == 0:  # Everything is fine
            if os.path.exists(sync_py):
                if crash:  # Simulate a crash
                    if verb:
                        print('I will simulate a crash')
                    sys.exit(1)
                else:
                    if verb:
                        print('Fake processing. Sleeping {:g} seconds'.format(sleep))
                    time.sleep(sleep)
                    i += 1
                    fd = open('server_decoy_processing_{:d}'.format(i), 'w')
                    fd.write('Blop')
                    fd.close()
            else:
                stop_request = True
        else:
            print('Killed by a signal. retcode={:d}'.format(retcode))
            sys.exit(retcode)

    sys.exit(0)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Fake server to test the abstract AlgoComponent.")
    parser.add_argument("-v", "--verbose", dest="verbose", action="count",
                        help="set verbosity level [default: %(default)s]")
    parser.add_argument("--sleep", dest="sleep", action="store", default=5., type=float,
                        help="Duration of the fake processing in seconds [default: %(default)s]")
    parser.add_argument("--crash", dest="crash", action="store_true",
                        help="Quit abruptly")
    args = parser.parse_args()

    server(sleep=args.sleep, crash=args.crash, verb=args.verbose)
