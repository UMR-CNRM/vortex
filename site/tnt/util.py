"""
Utility methods widely used in the various TNT utilities.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import io
import six

import footprints

from tnt.namadapter import BronxNamelistAdapter, NO_SORTING

tntlog = footprints.loggers.getLogger('tntlog')


def set_verbose(verbose, filename):
    if verbose:
        print("==> ", filename)
        tntlog.setLevel('INFO')
    else:
        tntlog.setLevel('WARNING')


def process_namelist(filename,
                     new_blocks=None,
                     blocks_to_move=None,
                     keys_to_move=None,
                     keys_to_remove=None,
                     keys_to_set=None,
                     blocks_to_remove=None,
                     macros=None,
                     # options
                     sorting=NO_SORTING,
                     blocks_ref=None,
                     in_place=False,
                     outfilename=None,
                     doctor=False,
                     keep_index=False):
    """
    For the syntax of keys & blocks arguments, please refer to the according
    functions.

    The order of processing is that of the arguments. As movings are done first,
    check consistency.

    If **macros** is not None, it can contain the macros a.k.a. values to be
    replaced, e.g.: {'NPROC':8, 'substrA':None} will replace all NPROC values
    by 8 and will let substrA untouched.

    Other options:
    :param in_place: if True, the namelist is written back in the same file;
                     else (default), the target namelist is suffixed with '.tnt'
                     if not given as **outfilename**.
    :param outfilename: target file for out namelist
    :param sorting: Sorting option (from bronx.datagrip.namelist):
                    NO_SORTING;
                    FIRST_ORDER_SORTING => sort all keys within blocks;
                    SECOND_ORDER_SORTING => sort only within indexes or
                    attributes of the same key, within blocks.
    :param blocks_ref: if not None, defines the path for a reference namelist to
                       which the set of blocks is asserted to be equal.
    :param doctor: if True, try to convert value to DOCTOR norm according type
                   for moved keys
    :param keep_index: if True, moved keys in identical block keep the original
                       index of key in block (except a sorting is requested
                       later on.
    """

    # The initial namelist
    initial_nam = BronxNamelistAdapter(filename)

    # Target namelist file
    if not in_place:
        target_namfile = outfilename or filename + '.tnt'
    else:
        target_namfile = filename
        if outfilename is not None:
            raise ValueError("Incompatibility between arguments *outfilename* and *in_place*.")

    # process (in the right order !)
    if new_blocks is not None:
        initial_nam.add_blocks(new_blocks)
    if blocks_to_move is not None:
        initial_nam.move_blocks(blocks_to_move)
    if keys_to_move is not None:
        initial_nam.move_keys(keys_to_move, doctor=doctor, keep_index=keep_index)
    if keys_to_remove is not None:
        initial_nam.remove_keys(keys_to_remove)
    if keys_to_set is not None:
        initial_nam.add_keys(keys_to_set)
    if blocks_to_remove is not None:
        initial_nam.remove_blocks(blocks_to_remove)
    if blocks_ref is not None:
        cb = initial_nam.check_blocks(blocks_ref, macros)
        if len(cb) != 0:
            tntlog.warning('Set of blocks is different from reference: ' + blocks_ref)
            tntlog.warning('diff: ' + str(cb))

    with io.open(target_namfile, 'w', encoding='ascii') as fh_namout:
        fh_namout.write(six.u(initial_nam.dumps(sorting=sorting)))
