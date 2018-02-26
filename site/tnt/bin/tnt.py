#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import os
import re
import sys

# Automatically set the python path
sitepath = re.sub('{0:}tnt{0:}bin$'.format(os.path.sep), '',
                  os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, sitepath)

import tnt


if __name__ == '__main__':

    _tmpl = 'tmpl_directives.tnt'

    parser = argparse.ArgumentParser(description='TNT - The Namelist Tool: a namelist updater.',
                                     epilog='End of help for: %(prog)s')
    parser.add_argument('namelists',
                        type=str,
                        nargs='*',
                        help='namelist(s) file(s) to be processed.')
    directives = parser.add_mutually_exclusive_group(required=True)
    directives.add_argument('-d',
                            dest='directives',
                            type=str,
                            help='the file in which update directives are stored. \
                                  Activate option -D instead of -d to generate a template.')
    directives.add_argument('-D',
                            dest='generate_directives_template',
                            action='store_true',
                            help="generates a directives template '{}'.".format(_tmpl))
    parser.add_argument('-i',
                        action='store_true',
                        dest='in_place',
                        help='modifies the namelist(s) in place. \
                              Else, modified namelists are suffixed with .tnt \
                              if not given as arg -o.',
                        default=False)
    parser.add_argument('-o',
                        dest='outfilename',
                        default=None,
                        help="directives (.py) output filename.")
    sorting = parser.add_mutually_exclusive_group()
    sorting.add_argument('-S',
                         action='store_true',
                         dest='firstorder_sorting',
                         help='First order sorting: sort all keys within blocks.',
                         default=False)
    sorting.add_argument('-s',
                         action='store_true',
                         dest='secondorder_sorting',
                         help='Second order sorting: sort only within indexes \
                               or attributes of the same key within blocks.',
                         default=False)
    parser.add_argument('--doctor',
                        action='store_true',
                        dest='doctor',
                        help='try to convert value to DOCTOR norm according \
                              type for moved keys',
                        default=False)
    parser.add_argument('--keep_index',
                        action='store_true',
                        dest='keep_index',
                        help='moved keys in identical block keep the original \
                              index of key in block (except a sorting is \
                              requested)',
                        default=False)
    parser.add_argument('-r',
                        dest='blocks_ref',
                        type=str,
                        help='a (possibly empty) reference namelist, to which the \
                              set of blocks is asserted to be equal.',
                        default=None)
    parser.add_argument('-v',
                        action='store_true',
                        dest='verbose',
                        help='verbose mode.',
                        default=False)
    args = parser.parse_args()

    if args.firstorder_sorting:
        sorting = tnt.namadapter.FIRST_ORDER_SORTING
    elif args.secondorder_sorting:
        sorting = tnt.namadapter.SECOND_ORDER_SORTING
    else:
        sorting = tnt.namadapter.NO_SORTING

    if len(args.namelists) > 1 and args.outfilename is not None:
        raise ValueError('Arg -o should not be used applied to several namelists')

    if args.generate_directives_template:
        tnt.config.write_directives_template(_tmpl)
        print("Template of directives written in: " + os.path.abspath(_tmpl))
    else:

        assert len(args.namelists) > 0, "no namelists provided to process."
        directives = tnt.config.read_directives(args.directives)
        for nam in args.namelists:
            tnt.util.set_verbose(args.verbose, nam)
            tnt.util.process_namelist(nam,
                                      sorting=sorting,
                                      in_place=args.in_place,
                                      outfilename=args.outfilename,
                                      blocks_ref=args.blocks_ref,
                                      doctor=args.doctor,
                                      keep_index=args.keep_index,
                                      **directives)
