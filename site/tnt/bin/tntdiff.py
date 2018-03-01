#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import print_function, absolute_import, unicode_literals, division

import io
import os
import re
import six
import sys

# Automatically set the python path
sitepath = re.sub('{0:}tnt{0:}bin$'.format(os.path.sep), '',
                  os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, sitepath)

from bronx.stdtypes.tracking import Tracker, MappingTracker
import tnt

_outfilename = 'tntdiff.out.py'


def _string_encode(valueslist):
    return [("'{:s}'".format(v) if isinstance(v, six.string_types)
             else "{}".format(v))
            for v in valueslist]


def main(before_filename, after_filename, outfilename=_outfilename):
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
    keys_to_remove = set([(b, k) for b, k in keys_diff.deleted if b in after_namelist])

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
        with io.open(outfilename, 'w', encoding='utf_8') as outfh:
            outfh.write(outstr)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(
        description='TNTdiff - The Namelist Tool: a namelist comparator. ' +
                    'Compares two namelists and writes the TNT directives to ' +
                    'go from one (before/-b) to the other (after/-a).',
        epilog='End of help for: %(prog)s')
    parser.add_argument('-b', '--before',
                        required=True,
                        help="source namelist.")
    parser.add_argument('-a', '--after',
                        required=True,
                        help="target namelist.")
    parser.add_argument('-o',
                        dest='outputfilename',
                        default=_outfilename,
                        help="directives (.py) output filename. Defaults to " +
                             _outfilename)
    args = parser.parse_args()
    print("Diff directives written in: " + os.path.abspath(_outfilename))
    main(args.before, args.after, args.outputfilename)
