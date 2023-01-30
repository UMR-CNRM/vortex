"""
TNTdiff - The Namelist Tool: a namelist comparator.

Compares two namelists and produce the following outputs:

* (default)   a TNT directives file to go from one (before/-b) to the other
              (after/-a);
* (-H option) a HTML file that displays the differences in a table
* (-V or -v)  a summary of the differences on the standard output
* (-e option) a visualisation of the differences in an external tool

Beware that TNTdiff (purposely) DO NOT take into account:

* Differences in the order of appearance of namelists blocks or keys
* Differences in the formatting of namelist values (e.g 1.0 and 1.0000 are
  considered the same)

With the -H, -V, -v or -e options, the displayed namelists DO NOT necessarily
correspond to the original files since, prior to be displayed, blocks/keys are
ordered alphabetically and values are formatted in a "standard" way.

"""

import argparse
import difflib
import os
import subprocess
import tempfile

from bronx.stdtypes.tracking import Tracker, MappingTracker
import thenamelisttool as tnt

_outfilename = 'tntdiff.out'


def _string_encode(valueslist):
    return [("'{:s}'".format(v) if isinstance(v, str)
             else "{}".format(v))
            for v in valueslist]


def visualdiff(before_filename, after_filename, bw=False):
    """Print a nicely formated text representation of the differences."""
    namtxtB = tnt.util.namelist_read_and_sort(before_filename).split('\n')
    namtxtA = tnt.util.namelist_read_and_sort(after_filename).split('\n')

    diff = difflib.ndiff(namtxtB, namtxtA)
    if not bw and diff:
        diff = tnt.util.colorise_diff(diff)

    print('\n'.join(diff))


def htmldiff_view(before_filename, after_filename, outfilename):
    """Create an HTML representation of the differences and open a web browser."""
    namtxtB = tnt.util.namelist_read_and_sort(before_filename).split('\n')
    namtxtA = tnt.util.namelist_read_and_sort(after_filename).split('\n')

    htmldiff = difflib.HtmlDiff()
    htmlout = htmldiff.make_file(namtxtB, namtxtA, before_filename, after_filename)
    with open(outfilename, "w") as fh_ht:
        fh_ht.writelines(htmlout)
    import webbrowser
    webbrowser.open(outfilename)


def extdiff(before_filename, after_filename, tool):
    """Visualise the differences with an external tool such as ``vim`` or ``meld``."""
    with tempfile.NamedTemporaryFile(mode='w', prefix='tntdiff_BEFORE.', delete=True) as fhB:
        with tempfile.NamedTemporaryFile(mode='w', prefix='tntdiff_AFTER.', delete=True) as fhA:
            fhB.write(tnt.util.namelist_read_and_sort(before_filename))
            fhA.write(tnt.util.namelist_read_and_sort(after_filename))
            fhB.flush()
            fhA.flush()
            if tool == 'meld':
                subprocess.check_call(['meld', '--diff', fhB.name, fhA.name])
            elif tool == 'vim':
                subprocess.check_call(['vim', '-d', fhB.name, fhA.name])
            else:
                raise ValueError("Unknown diff tool.")


def actual_main(before_filename, after_filename, outfilename):
    """
    Compare two namelists and return directives to go from one (before) to the
    other (after).

    :param outfilename: output file in which to store directives (.py).
                        Or None if not required.
    """
    # Read namelists
    before_namelist = tnt.namadapter.BronxNamelistAdapter(before_filename)
    after_namelist = tnt.namadapter.BronxNamelistAdapter(after_filename)

    blocks_diff = Tracker(before=before_namelist.keys(), after=after_namelist.keys())
    keys_diff = MappingTracker(before={(b, k): v for b, bl in before_namelist.items() for k, v in bl.items()},
                               after={(b, k): v for b, bl in after_namelist.items() for k, v in bl.items()},)

    # Compare:
    # 7. macros
    # 6. blocks to remove
    blocks_to_remove = blocks_diff.deleted

    # 5. Keys to be set with a value (new or modified).
    keys_to_set = {(b, k): after_namelist[b][k] for b, k in keys_diff.created}

    # 4. Keys to be removed.
    keys_to_remove = {(b, k) for b, k in keys_diff.deleted if b in after_namelist}

    # 3. Keys to be moved. No way to discriminate from set/remove => treated this way
    # 2. Blocks to be moved. No way to discriminate from new/remove => treated this way
    # 1. Blocks to be added.
    new_blocks = blocks_diff.created

    # 0. Modified values
    modified_values = {}
    for b, k in keys_diff.updated:
        keys_to_set[(b, k)] = after_namelist[b][k]
        modified_values[(b, k)] = (getattr(before_namelist[b], 'dumps_values', str)(k),
                                   getattr(after_namelist[b], 'dumps_values', str)(k))

    # Prepare the output directives
    tplsep = ',\n' + ' ' * 4

    outtpl = tnt.config.get_template('tnt-diff-outputdir.tpl', encoding='utf_8')
    outstr = outtpl.substitute(dict(
        TPL_NEWBLOCKS=tplsep.join(_string_encode(new_blocks)),
        TPL_RMKEYS=tplsep.join(_string_encode(keys_to_remove)),
        TPL_NEWKEYS=tplsep.join(['{}: {}'.format(k, v)
                                 for k, v in zip(* map(_string_encode,
                                                       zip(* sorted(keys_to_set.items()))))]),
        TPL_MODIFIED=('#None' if not modified_values
                      else '\n'.join(["# {}: {} => {}".format(k, *v)
                                      for k, v in sorted(modified_values.items())])),
        TPL_RMBLOCKS=tplsep.join(_string_encode(blocks_to_remove)),
    ))

    # Write to file
    if outfilename is not None:
        with open(outfilename, 'w', encoding='utf_8') as outfh:
            outfh.write(outstr)


def main():
    """Start the tntdiff CLI."""
    program_desc = '%(prog)s -- ' + __import__('__main__').__doc__.lstrip('\n')
    parser = argparse.ArgumentParser(description=program_desc, epilog='End of help for: %(prog)s',
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('-b', '--before',
                        required=True,
                        help="source namelist.")
    parser.add_argument('-a', '--after',
                        required=True,
                        help="target namelist.")
    parser.add_argument('-o',
                        default=_outfilename,
                        dest='outputfilename',
                        help="output filename (without any extension). Defaults to %(default)s.")
    visual = parser.add_mutually_exclusive_group()
    visual.add_argument('-H',
                        action='store_true',
                        dest='html',
                        help="Create a HTML file and display it in a webbrowser.")
    visual.add_argument('-V',
                        action='store_true',
                        dest='visual',
                        help="Visualise the diff result on the standard output.")
    visual.add_argument('-v',
                        action='store_true',
                        dest='visualbw',
                        help="Visualise the diff result on the standard output (in black & white).")
    visual.add_argument('-e',
                        choices=('meld', 'vim'),
                        dest='external',
                        help="Use an external tool to compute and display the diff.")
    args = parser.parse_args()
    if args.html:
        print("HTML diff file written in: " + os.path.abspath(args.outputfilename + '.html'))
        htmldiff_view(args.before, args.after, args.outputfilename + '.html')
    elif args.visual or args.visualbw:
        visualdiff(args.before, args.after, bw=args.visualbw)
    elif args.external:
        extdiff(args.before, args.after, args.external)
    else:
        print("Diff directives written in: " + os.path.abspath(args.outputfilename + '.py'))
        actual_main(args.before, args.after, args.outputfilename + '.py')
