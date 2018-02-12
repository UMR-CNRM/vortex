#!/usr/bin/env python
# -*- coding: utf-8 -*-

import six
import os
import vortex  # @UnusedImport
import common
import footprints

_outfilename = 'tntdiff.out.py'


def main(before_filename, after_filename,
         outfilename=_outfilename):
    """
    Compare two namelists and return directives to go from one (before) to the
    other (after).

    :param outfilename: output file in which to store directives (.py).
                        Or None if not required.
    """
    # Read namelists
    before_container = footprints.proxy.container(filename=before_filename)
    before_namelist = common.data.namelists.NamelistContent()
    before_namelist.slurp(before_container)
    after_container = footprints.proxy.container(filename=after_filename)
    after_namelist = common.data.namelists.NamelistContent()
    after_namelist.slurp(after_container)

    # Compare:
    # 7. macros
    # 6. blocks to remove
    blocks_to_remove = []
    for b in before_namelist:
        if b not in after_namelist:
            blocks_to_remove.append(b)
    # 5. Keys to be set with a value (new or modified).
    keys_to_set = {}
    for b in after_namelist:
        for k in after_namelist[b]:
            if b not in before_namelist or k not in before_namelist[b]:
                v = after_namelist[b][k]
                keys_to_set[(b, k)] = v
    # 4. Keys to be removed.
    keys_to_remove = []
    for b in before_namelist:
        for k in before_namelist[b]:
            if b in after_namelist:
                if k not in after_namelist[b]:
                    keys_to_remove.append((b, k))
    # 3. Keys to be moved. No way to discriminate from set/remove => treated this way
    # 2. Blocks to be moved. No way to discriminate from new/remove => treated this way
    # 1. Blocks to be added.
    new_blocks = []
    for b in after_namelist:
        if b not in before_namelist:
            new_blocks.append(b)

    # 0. Modified values
    modified_values = {}
    for b in after_namelist:
        for k in after_namelist[b]:
            if b in before_namelist:
                if k in before_namelist[b]:
                    if after_namelist[b][k] != before_namelist[b][k]:
                        keys_to_set[(b, k)] = after_namelist[b][k]
                        modified_values[(b, k)] = (before_namelist[b].dumps_values(k),
                                                   after_namelist[b].dumps_values(k))

    # Write directives
    tab = ' ' * 4
    dirs = ('#!/usr/bin/env python\n' +
            '# -*- coding: utf-8 -*\n')
    # 1. new blocks
    dirs += 'new_blocks = set([\n'
    for b in new_blocks:
        dirs += tab + "'{}',\n".format(b)
    dirs += tab + '])' + '\n' * 2
    # 4. keys to remove
    dirs += 'keys_to_remove = set([\n'
    for k in keys_to_remove:
        dirs += tab + "{},\n".format(k)
    dirs += tab + '])' + '\n' * 2
    # 5. keys to set
    dirs += 'keys_to_set = {\n'
    for k, v in sorted(keys_to_set.items()):
        if isinstance(v, six.string_types):
            v = "'{}'".format(v)
        dirs += tab + "{}:{},\n".format(k, v)
    dirs += tab + '}' + '\n'
    if len(modified_values) > 0:
        dirs += "# of which modified values:\n"
        for k, v in sorted(modified_values.items()):
            dirs += "# {}: {} => {}\n".format(k, *v)
    dirs += '\n'
    # 6. blocks to remove
    dirs += 'blocks_to_remove = set([\n'
    for b in blocks_to_remove:
        dirs += tab + "'{}',\n".format(b)
    dirs += tab + '])' + '\n' * 2

    # Write to file
    if outfilename is not None:
        with open(outfilename, 'w') as o:
            o.write(dirs)


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
    main(args.before, args.after,
         args.outputfilename)
