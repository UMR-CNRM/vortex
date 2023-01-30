"""
TNT Stack - A namelist's pack updater.
"""

import argparse
import os
import yaml

import thenamelisttool as tnt
from thenamelisttool.namadapter import NO_SORTING, FIRST_ORDER_SORTING, SECOND_ORDER_SORTING

_tmpl = 'tmpl_directives.tntstack.yaml'


def main():
    """Run the tntstack CLI."""
    parser = argparse.ArgumentParser(description="TNT Stack - A namelist's pack updater.",
                                     epilog='End of help for: %(prog)s')

    parser.add_argument('-v',
                        action='store_true',
                        dest='verbose',
                        help='verbose mode.',
                        default=False)
    sorting = parser.add_mutually_exclusive_group()
    sorting.add_argument('-S',
                         action='store_const', const=FIRST_ORDER_SORTING + 1,
                         dest='first_order_sorting',
                         help='first order sorting: sort all keys within blocks.')
    sorting.add_argument('-0',
                         action='store_const', const=NO_SORTING + 1,
                         dest='no_sorting',
                         help='no sorting at all (the default is second_order_sorting, \
                               i.e. sort only within indexes or attributes of the \
                               same key within blocks).')
    directive = parser.add_mutually_exclusive_group(required=True)
    directive.add_argument('-d',
                           dest='directive',
                           type=str,
                           help='the file in which update directives are stored. \
                                 Activate option -D instead of -d to generate a template.')
    directive.add_argument('-D',
                           dest='generate_directive_template',
                           action='store_true',
                           help="generates a directive template written in '{}'.".format(_tmpl))
    args = parser.parse_args()

    if args.generate_directive_template:
        tnt.config.write_directives_template(_tmpl, tplname='tntstack-directive.tpl.yaml')
        print("Template of directives written in: " + os.path.abspath(_tmpl))
    else:
        # Find the basedir
        dirpath = os.path.realpath(args.directive)
        basedir = os.path.dirname(dirpath)

        with open(args.directive) as fhyaml:
            directive = tnt.config.TntStackDirective(basedir, ** yaml.load(fhyaml))

        with tnt.util.set_verbose(args.verbose, args.directive):
            tnt.util.process_tnt_stack(directive,
                                       sorting=(args.first_order_sorting or args.no_sorting or
                                                SECOND_ORDER_SORTING + 1) - 1)
