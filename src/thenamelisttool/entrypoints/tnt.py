"""
TNT - The Namelist Tool: a namelist updater.
"""

import argparse
import os

import thenamelisttool as tnt


def main():
    """Start the tnt CLI."""
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
                            help="generates a directives template '{}.(py|yaml)'.".format(_tmpl))
    directives.add_argument('-n',
                            dest='namdelta',
                            type=str,
                            help='path to a file that contains a namelist delta.')
    directives.add_argument('-c',
                            dest='check_namelist',
                            action='store_true',
                            help='check that the namelist is ok and do a first order sorting. \
                                  This option is equivalent to. \
                                  "tnt.py -d void.py -S NAMELIST" with an empty void.py directive file.',
                            default=False)
    directives.add_argument('--squeeze',
                            dest='squeeze',
                            action='store_true',
                            help='squeeze the namelist: remove empty blocks.',
                            default=False)
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

    if args.firstorder_sorting or args.check_namelist:
        sorting = tnt.namadapter.FIRST_ORDER_SORTING
    elif args.secondorder_sorting:
        sorting = tnt.namadapter.SECOND_ORDER_SORTING
    else:
        sorting = tnt.namadapter.NO_SORTING

    if len(args.namelists) > 1 and args.outfilename is not None:
        raise ValueError('Arg -o should not be used applied to several namelists')

    if args.generate_directives_template:
        tnt.config.write_directives_template(_tmpl + '.py', tplname='tnt-directive.tpl.py')
        print("Template of directives written in: " + os.path.abspath(_tmpl + '.py'))
        tnt.config.write_directives_template(_tmpl + '.yaml', tplname='tnt-directive.tpl.yaml')
        print("Template of directives written in: " + os.path.abspath(_tmpl + '.yaml'))
    else:
        assert len(args.namelists) > 0, "no namelists provided to process."
        if args.directives:
            directives = tnt.config.read_directives(args.directives)
        else:
            if args.check_namelist or args.squeeze:
                directives = tnt.config.TntDirective()
            else:
                with open(args.namdelta) as fhnam:
                    directives = tnt.config.TntDirective(namdelta=fhnam.read())
        for nam in args.namelists:
            with tnt.util.set_verbose(args.verbose, nam):
                tnt.util.process_namelist(nam, directives,
                                          sorting=sorting,
                                          in_place=args.in_place,
                                          outfilename=args.outfilename,
                                          blocks_ref=args.blocks_ref,
                                          doctor=args.doctor,
                                          keep_index=args.keep_index,
                                          squeeze=args.squeeze)
