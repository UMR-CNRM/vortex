#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
TNTdiffpack - The Namelist Tool: a namelist pack comparator.

Compares two namelists packs and produces a summary on the standard output
and in a separate file.

Beware that TNTdiffpack (purposely) DO NOT take into account:

* Differences in the order of appearance of namelists blocks or keys
* Differences in the formatting of namelist values (e.g 1.0 and 1.0000 are
  considered the same)

The displayed namelists DO NOT necessarily correspond to the original files since,
prior to be displayed, blocks/keys are ordered alphabetically and values are
formatted in a "standard" way.

"""

from __future__ import print_function, absolute_import, unicode_literals, division

import argparse
import difflib
import io
import os
import re
import sys


# Automatically set the python path
sitepath = re.sub('{0:}tnt{0:}bin$'.format(os.path.sep), '',
                  os.path.dirname(os.path.realpath(__file__)))
sys.path.insert(0, sitepath)

from bronx.fancies.display import printstatus
from bronx.stdtypes.tracking import MappingTracker
import tnt

_outfilename = 'tntdiffpack.out'


def _compute_diffs(nambefore, namafter, modified):
    diffs = dict()
    for k in modified:
        txtB = nambefore[k].split('\n')
        txtA = namafter[k].split('\n')
        diffs[k] = difflib.ndiff(txtB, txtA)
    return diffs


if __name__ == '__main__':
    program_desc = '%(prog)s -- ' + __import__('__main__').__doc__.lstrip('\n')
    parser = argparse.ArgumentParser(description=program_desc, epilog='End of help for: %(prog)s',
                                     formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-b', '--before',
                        required=True,
                        help="source namelist pack.")
    parser.add_argument('-a', '--after',
                        required=True,
                        help="target namelist pack.")
    parser.add_argument('-o',
                        default=_outfilename,
                        dest='outputfilename',
                        help="output filename (without any extension). Defaults to %(default)s.")
    args = parser.parse_args()

    ko = set()
    nambefore = dict()
    namafter = dict()
    listbefore = [f for f in os.listdir(args.before)
                  if os.path.isfile(os.path.join(args.before, f))]
    listafter = [f for f in os.listdir(args.after)
                 if os.path.isfile(os.path.join(args.after, f))]
    listcommon = set(listbefore) & set(listafter)

    for (targetdict, listdir, inputdir) in ((nambefore, listbefore, args.before),
                                            (namafter, listafter, args.after)):
        sys.stdout.write('Processing files in {:s}: '.format(inputdir))
        for i, f in enumerate(listdir):
            printstatus(i + 1, len(listdir))
            if f in listcommon:
                try:
                    nparsed = tnt.util.namelist_read_and_sort(os.path.join(inputdir, f))
                except ValueError:
                    ko.add(f)
                else:
                    targetdict[f] = nparsed
            else:
                targetdict[f] = ''

    tracker = MappingTracker(nambefore, namafter)
    computediffs = _compute_diffs(nambefore, namafter, tracker.updated)
    # Expand the generator objects into lists
    print('Creating diff outputs. It may take a while (depending on the amount of changes).')
    for i, n in enumerate(tracker.updated):
        computediffs[n] = [l for l in computediffs[n]]

    outtpl = tnt.config.get_template('tnt-diffpack-output.tpl', encoding='utf_8')

    with io.open(args.outputfilename, "w") as fhout:
        fhout.write(outtpl.substitute(ref=args.before, new=args.after,
                                      ko='\n'.join(['{:s}'.format(n) for n in sorted(ko)]),
                                      untouched='\n'.join(['{:s}'.format(n) for n in sorted(tracker.unchanged)]),
                                      created='\n'.join(['{:s}'.format(n) for n in sorted(tracker.created)]),
                                      deleted='\n'.join(['{:s}'.format(n) for n in sorted(tracker.deleted)]),
                                      modified='\n'.join(['{:s}'.format(n) for n in sorted(tracker.updated)]),
                                      computediffs='\n'.join(['============ {:s} ============\n\n{:s}\n'.
                                                              format(n, '\n'.join(computediffs[n]))
                                                              for n in tracker.updated])
                                      ))
