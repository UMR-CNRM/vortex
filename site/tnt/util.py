"""
Utility methods widely used in the various TNT utilities.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import glob
import io
import os
import shutil
import six

import footprints

from bronx.fancies.colors import termcolors
from tnt.namadapter import BronxNamelistAdapter, NO_SORTING, FIRST_ORDER_SORTING, SECOND_ORDER_SORTING

tntlog = footprints.loggers.getLogger('tntlog')
tntstacklog = footprints.loggers.getLogger('tntstacklog')


def set_verbose(verbose, filename):
    """Set or reset the verbosity level."""
    tntstacklog.setLevel('INFO')
    if verbose:
        print("==> ", filename)
        tntlog.setLevel('INFO')
    else:
        tntlog.setLevel('WARNING')


def process_namelist(filename, directives,
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

    if not isinstance(directives, (list, tuple)):
        directives = [directives, ]

    # The initial namelist
    initial_nam = BronxNamelistAdapter(filename, macros=directives[0].macros)

    # Target namelist file
    if not in_place:
        target_namfile = outfilename or filename + '.tnt'
    else:
        target_namfile = filename
        if outfilename is not None:
            raise ValueError("Incompatibility between arguments *outfilename* and *in_place*.")

    for d in directives:
        # process (in the appropriate order !)
        if d.new_blocks is not None:
            initial_nam.add_blocks(d.new_blocks)
        if d.blocks_to_move is not None:
            initial_nam.move_blocks(d.blocks_to_move)
        if d.keys_to_move is not None:
            initial_nam.move_keys(d.keys_to_move,
                                  doctor=doctor, keep_index=keep_index)
        if d.keys_to_remove is not None:
            initial_nam.remove_keys(d.keys_to_remove)
        if d.keys_to_set is not None:
            initial_nam.add_keys(d.keys_to_set)
        if d.blocks_to_remove is not None:
            initial_nam.remove_blocks(d.blocks_to_remove)
        if d.namdelta is not None:
            try:
                ndelta = BronxNamelistAdapter(d.namdelta, macros=d.macros)
            except ValueError:
                tntlog.error("Error while parsing the following namelist's delta:\n%s",
                             d.namdelta)
                raise
            initial_nam.merge(ndelta)

    if blocks_ref is not None:
        cb = initial_nam.check_blocks(blocks_ref, directives[0].macros)
        if len(cb) != 0:
            tntlog.warning('Set of blocks is different from reference: ' + blocks_ref)
            tntlog.warning('diff: ' + str(cb))

    with io.open(target_namfile, 'w', encoding='ascii') as fh_namout:
        fh_namout.write(six.u(initial_nam.dumps(sorting=sorting)))


def process_tnt_stack(directive, sorting=SECOND_ORDER_SORTING):
    """Apply *directive* to the current working directory.

    :param TntStackDirective directive: The tntstack directive to apply
    :param sorting: Sorting option (from bronx.datagrip.namelist):
                    NO_SORTING;
                    FIRST_ORDER_SORTING => sort all keys within blocks;
                    SECOND_ORDER_SORTING => sort only within indexes or
                    attributes of the same key, within blocks.
    """
    # Record the list of file contained in the directory
    initial_files = set()
    initial_subdirectories = set()
    for root, directories, files in os.walk('.'):
        for f in files:
            initial_files.add(os.path.normpath(os.path.join(root, f)))
        for d in directories:
            initial_subdirectories.add(os.path.normpath(os.path.join(root, d)))

    # Process the todolist
    for todo in directive.todolist:
        action = todo['action']

        if action == 'tnt':
            for nam in todo['namelist']:
                for realnam in glob.glob(nam):
                    tntstacklog.info("Namelist '%s': applying the following directives: %s",
                                     realnam, ",".join(todo['directive']))
                    process_namelist(realnam,
                                     [directive.directives[name] for name in todo['directive']],
                                     in_place=True, sorting=sorting)
                    initial_files.discard(os.path.normpath(realnam))

        elif action == 'create':
            if 'external' in todo:
                tntstacklog.info("Creating namelist '%s' from external file '%s'", todo['target'], todo['external'])
                shutil.copy(todo['external'], todo['target'])
            elif 'copy' in todo:
                tntstacklog.info("Creating namelist '%s' from file '%s'", todo['target'], todo['copy'])
                shutil.copy(todo['copy'], todo['target'])
            else:
                tntstacklog.info("Creating namelist '%s' from namelist '%s' by applying the following directives: %s",
                                 todo['target'], todo['namelist'], ",".join(todo['directive']))
                process_namelist(todo['namelist'],
                                 [directive.directives[name] for name in todo['directive']],
                                 outfilename=todo['target'], sorting=sorting)
            initial_files.discard(os.path.normpath(todo['target']))

        elif action in ('delete', 'touch'):
            for nam in todo['namelist']:
                for realnam in glob.glob(nam):
                    if action == 'delete':
                        tntstacklog.info("Deleting namelist '%s'", realnam)
                        os.unlink(realnam)
                    elif action == 'touch':
                        tntstacklog.info("Marking file '%s' as touched'", realnam)
                    initial_files.discard(os.path.normpath(realnam))

        elif action == 'link':
            tntstacklog.info("Linking '%s' -> '%s'", todo['target'], todo['namelist'])
            os.symlink(todo['namelist'], todo['target'])
            initial_files.discard(os.path.normpath(todo['namelist']))

        elif action == 'move':
            tntstacklog.info("Moving '%s' to '%s'", todo['namelist'], todo['target'])
            shutil.move(todo['namelist'], todo['target'])
            initial_files.discard(os.path.normpath(todo['namelist']))
            initial_files.discard(os.path.normpath(todo['target']))

        elif action == 'clean_untouched':
            for f in initial_files:
                tntstacklog.info("Deleting file '%s'", f)
                os.unlink(f)
            for d in [d for d in initial_subdirectories if not os.listdir(d)]:
                # Remove empty directories
                tntstacklog.info("Deleting empty directory '%s'", d)
                os.rmdir(d)


def namelist_read_and_sort(namfile):
    try:
        namp = BronxNamelistAdapter(namfile)
    except (ValueError, IOError):
        tntlog.error("Something went wrong will reading: %s", namfile)
        raise
    if not len(namp):
        raise ValueError('Nothing to read in "{:s}": Is it a namelist ?'.format(namfile))
    return namp.dumps(sorting=FIRST_ORDER_SORTING)


def _check_diffline(line, expected):
    return line and len(line) >= 2 and line[0] == expected and line[1] == ' '


def _color_diffline(prevline, line=''):
    """Colorise an individual line of a difflib output."""
    if _check_diffline(prevline, '-') and _check_diffline(line, '?'):
        return termcolors.error(prevline)
    elif _check_diffline(prevline, '+') and _check_diffline(line, '?'):
        return termcolors.error(prevline)
    elif _check_diffline(prevline, '-'):
        return termcolors.critical(prevline)
    elif _check_diffline(prevline, '+'):
        return termcolors.okgreen(prevline)
    elif _check_diffline(prevline, '?'):
        return termcolors.error(prevline)
    else:
        return prevline


def colorise_diff(lines):
    """Colorise the lines of any kind of difflib outputs."""
    newdiff = list()
    prevline = None
    for l in lines:
        if prevline:
            newdiff.append(_color_diffline(prevline, l))
        prevline = l
    newdiff.append(_color_diffline(prevline))
    return newdiff
