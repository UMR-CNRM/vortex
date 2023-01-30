"""
TNT - The Namelist Tool - Compose: a namelist composer merging parts of others.
"""

import argparse
import os

import thenamelisttool as tnt


def main():
    """Start the tntcompose CLI."""
    _tmpl = 'tmpl_compose-recipe.tnt'

    parser = argparse.ArgumentParser(description='TNT - The Namelist Tool - Compose: ' +
                                     'a namelist composer merging parts of others.',
                                     epilog='End of help for: %(prog)s')
    parser.add_argument('recipes',
                        type=str,
                        nargs='*',
                        help='YAML recipe file(s) of namelists to be composed.')
    parser.add_argument('-R',
                        dest='generate_recipe_template',
                        action='store_true',
                        help="generates a recipe template '{}.yaml'.".format(_tmpl))
    parser.add_argument('-d',
                        dest='sourcenam_directory',
                        default=None,
                        help="specify the directory in which to find the source namelists mentioned in recipes")
    parser.add_argument('-x',
                        dest='suffix',
                        default='.nam',
                        help='suffix to be used in output namelist filename, in replacement of .yaml')
    parser.add_argument('--squeeze',
                        dest='squeeze',
                        action='store_true',
                        help='squeeze the namelist: remove empty blocks.',
                        default=False)
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
    parser.add_argument('-v',
                        action='store_true',
                        dest='verbose',
                        help='verbose mode.',
                        default=False)
    args = parser.parse_args()

    if args.generate_recipe_template:
        tnt.config.write_directives_template(_tmpl + '.yaml',
                                             tplname='tntcompose-recipe.tpl.yaml')
        print("Template of directives written in: " +
              os.path.abspath(_tmpl + '.yaml'))
    else:
        assert len(args.recipes) > 0, "no namelists provided to process."
        if args.firstorder_sorting:
            sorting = tnt.namadapter.FIRST_ORDER_SORTING
        elif args.secondorder_sorting:
            sorting = tnt.namadapter.SECOND_ORDER_SORTING
        else:
            sorting = tnt.namadapter.NO_SORTING
        for recipe in args.recipes:
            with tnt.util.set_verbose(args.verbose, recipe):
                tnt.util.compose_namelist(recipe,
                                          sourcenam_directory=args.sourcenam_directory,
                                          suffix=args.suffix,
                                          sorting=sorting,
                                          squeeze=args.squeeze)
