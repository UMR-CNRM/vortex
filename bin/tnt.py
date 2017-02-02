#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import re
import vortex, common
import footprints

tntlog = footprints.loggers.getLogger('tntlog')

# Other known namelist macros (not to be substituted)
_OTHER_KNM = set(['substr6', 'substrA', 'substrC', 'XMP_TYPE', 'XLOPT_SCALAR',
                  'XNCOMBFLEN', 'val_sitr', 'val_sipr', '_lbias_', '_lincr_'])
KNOWN_NAMELIST_MACROS = common.data.namelists.KNOWN_NAMELIST_MACROS.union(_OTHER_KNM)

#############
# Functions #
#############
def add_blocks(nam, blocks):
    """
    Add a set of new blocks inside a NamelistContent object.
    
    **nam**: NamelistContent
    
    **blocks**: ['BLOCK1', 'BLOCK2', ...]
    """
    assert isinstance(nam, common.data.namelists.NamelistContent)
    for b in blocks:
        if b not in nam:
            nam.newblock(b)
        else:
            tntlog.info(" ".join(["block", b,
                                  "already present"]))

def remove_blocks(nam, blocks):
    """
    Remove a set of blocks from a NamelistContent object.
    
    **nam**: NamelistContent
    
    **blocks**: ['BLOCK1', 'BLOCK2', ...]
    """
    assert isinstance(nam, common.data.namelists.NamelistContent)
    for b in blocks:
        if b in nam:
            nam.pop(b)
        else:
            tntlog.info(" ".join(["block", b,
                                  "to be removed but already missing."]))

def move_blocks(nam, blocks):
    """
    Move a set of blocks inside a NamelistContent object.
    
    **nam**: NamelistContent
    
    **blocks**: {'BLOCK_OLD':'BLOCK_NEW', ...}
    """
    assert isinstance(nam, common.data.namelists.NamelistContent)
    for (old_b, new_b) in blocks.items():
        if old_b in nam:
            if new_b not in nam:
                nam.mvblock(old_b, new_b)
            else:
                raise ValueError(" ".join(["block", new_b,
                                           "already present"]))
        else:
            tntlog.warning(" ".join(["block", old_b,
                                     "to be moved but missing from namelist: ignored."]))

def _expand_keys(nam, keys, radics=False):
    """
    Find all entries corresponding to the given keys,
    due to attributes and/or indexes.
    
    **keys**: [('BLOCK1','KEY1'), ('BLOCK2','KEY2'), ...]
    
    If **radics**, add the radical in the tuples.
    """
    assert isinstance(nam, common.data.namelists.NamelistContent)
    expanded_keys = []
    for (b, k) in keys:
        if b in nam:
            ek = [(b, nk) for nk in nam[b].keys()
                  if re.match(k.replace('(','\(').replace(')','\)') + r'(\(.+\)|%.+)*', nk)]
            if radics:
                ek = [(b, k, nk) for (b, nk) in ek]
            expanded_keys.extend(ek)
    return set(expanded_keys)

def remove_keys(nam, keys):
    """
    Remove a set of keys from a NamelistContent object.
    
    **nam**: NamelistContent
    
    **keys**: [('BLOCK1','KEY1'), ('BLOCK2','KEY2'), ...]
    """
    assert isinstance(nam, common.data.namelists.NamelistContent)
    for (b, k) in _expand_keys(nam, keys):
        if b in nam:
            if k in nam[b]:
                nam[b].delvar(k)
            else:
                tntlog.info(" ".join(["key", k,
                                      "to be removed but already missing from block", b]))
        else:
            tntlog.info(" ".join(["block", b,
                                  "missing: cannot remove its key", k]))

def set_keys(nam, keys):
    """
    Set a set of keys inside a NamelistContent object.
    
    **nam**: NamelistContent
    
    **keys**: {('BLOCK','KEY'):value, ...}
    """
    assert isinstance(nam, common.data.namelists.NamelistContent)
    for ((b, k), v) in keys.items():
        if b in nam:
            nam[b][k] = v
        else:
            raise KeyError(" ".join(["block", b,
                                     "missing: cannot set its key", k]))

def move_keys(nam, keys):
    """
    Move a set of keys within a NamelistContent object.
    
    **nam**: NamelistContent
    
    **keys**: {('BLOCK_OLD','KEY_OLD'):('BLOCK_NEW','KEY_NEW'), ...}
    """
    assert isinstance(nam, common.data.namelists.NamelistContent)
    
    origin_keys = _expand_keys(nam, keys.keys(), radics=True)
    expanded_keys = {}
    for (ob, o_r, ok) in origin_keys:
        (nb, n_r) = keys[(ob, o_r)]
        expanded_keys[(ob, ok)] = (nb, ok.replace(o_r, n_r, 1))
    for (ob, ok), (nb, nk) in expanded_keys.items():
        if ob in nam:
            if ok in nam[ob]:
                v = nam[ob][ok]
                remove_keys(nam, [(ob, ok)])
                if nb in nam:
                    if nk not in nam[nb]:
                        set_keys(nam, {(nb, nk):v})
                    else:
                        raise ValueError(" ".join(["key", nk,
                                                   "in block", nb,
                                                   "already exists: prevent moving from block", ob,
                                                   "key", ok]))
                else:
                    raise KeyError(" ".join(["block", nb,
                                             "missing: cannot move key", ok,
                                             "from block", ob,
                                             "to it as key", nk]))
            else:
                tntlog.warning(" ".join(["key", ok,
                                         "missing from block", ob,
                                         ": cannot move it."]))
        else:
            tntlog.warning(" ".join(["block", ob,
                                     "missing: cannot move its key", ok]))

def _all_macros(arg_macros):
    macros = {k:None for k in KNOWN_NAMELIST_MACROS}
    if arg_macros is not None:
        macros.update(arg_macros)
    return macros

def check_blocks(nam, another, macros=None):
    """
    Check that the namelist **nam** contains the same set of blocks as
    **another**.
    
    **another can be either the filename of a namelist to be read, or a 
    NamelistContent instance.
    
    If **macros** is not None, it can contain the macros a.k.a. values to be
    replaced, e.g.: {'NPROC':8, 'substrA':None} will replace all NPROC values
    by 8 and will let substrA untouched.
    
    Return the set of blocks that differ.
    """
    macros = _all_macros(macros)
    if isinstance(another, str):
        container = footprints.proxy.container(filename=another, cwdtied=True)
        another = common.data.namelists.NamelistContent(macros=macros)
        another.slurp(container)
    assert isinstance(another, common.data.namelists.NamelistContent)
    return set(nam.keys()).symmetric_difference(set(another.keys()))

def write_directives_template(out=sys.stdout):
    """Write out a directives template."""
    if isinstance(out, str):
        out = open(out, 'w')
    lines = [
    "#!/usr/bin/env python",
    "# -*- coding: utf-8 -*",
    "",
    "# 1. Blocks to be added.",
    "new_blocks = set(['NAMNEW',",
    "                  ])",
    "# 2. Blocks to be moved. If target block exists, raise an error.",
    "blocks_to_move = {'NAMOLD':'NAMMOVED',",
    "                  }",
    "# 3. Keys to be moved. If target exists or target block is missing, raise an error.",
    "# Blocks need to be consistent with above blocks movings.",
    "keys_to_move = {('NAMOLD', 'KEYOLD'):('NAMNEW', 'KEYNEW'),  # change the key from block, and/or rename it",
    "                }",
    "# 4. Keys to be removed. Already missing keys are ignored.",
    "# Blocks need to be consistent with above movings.",
    "keys_to_remove = set([('NAMBLOCK', 'KEYTOREMOVE'),",
    "                      ])",
    "# 5. Keys to be set with a value (new or modified). If block is missing, raise an error.",
    "# Blocks need to be consistent with above movings.",
    "keys_to_set = {('NAMBLOCK1', 'KEY1'):46.5,",
    "               ('NAMBLOCK2', 'KEY2(1:3)'):[5,6,7],",
    "               ('NAMBLOCK3', 'KEY3(50)'):-50,",
    "               }",
    "# 6. Blocks to be removed. Already missing blocks are ignored.",
    "blocks_to_remove = set(['NAMBLOCK',",
    "                        ])",
    "# 7. Macros: substitutions in the namelist's values. A *None* value ignores",
    "# the substitution (keeps the keyword, to be substituted later on).",
    "macros = {'VAL_TO_SUBSTITUTE':8,",
    "          'VAL_TO_KEEP_AND_BE_SUBSTITUTED_LATER':None}"
    ]
    for l in lines:
        out.write(l + "\n")

def read_directives(filename):
    """
    Read directives in an external file (**filename**).
    
    For a template of directives, call function *write_directives_template()*.
    """
    directives = set(['keys_to_remove', 'keys_to_set', 'keys_to_move',
                      'blocks_to_move', 'blocks_to_remove', 'new_blocks',
                      'macros'])
    if sys.version_info.major == 3 and sys.version_info.minor >= 4:
        import importlib.util as imputil
        spec = imputil.spec_from_file_location(os.path.basename(filename),
                                               os.path.abspath(filename))
        m = imputil.module_from_spec(spec)
        spec.loader.exec_module(m)
    else:
        import imp
        m = imp.load_source(filename, os.path.abspath(filename))

    return {k:v for k, v in m.__dict__.items() if k in directives}

########
# MAIN #
########
def main(filename,
         sorting=vortex.tools.fortran.NO_SORTING,
         blocks_ref=None,
         in_place=False,
         verbose=False,
         new_blocks=None,
         blocks_to_move=None,
         keys_to_move=None,
         keys_to_remove=None,
         keys_to_set=None,
         blocks_to_remove=None,
         macros=None):
    """
    If **in_place** is True, the namelist is written back in the same file;
    else (default), the target namelist is suffixed with '.tnt'.
    
    Sorting option **sorting** (from vortex.tools.fortran):
      NO_SORTING;
      FIRST_ORDER_SORTING => sort all keys within blocks;
      SECOND_ORDER_SORTING => sort only within indexes or attributes of the same key, within blocks.
    
    If **blocks_ref** is not None, defines the path for a reference namelist to
    which the set of blocks is asserted to be equal.
    
    For the syntax of keys & blocks arguments, please refer to the according
    functions.
    
    The order of processing is that of the arguments. As movings are done first,
    check consistency.
    
    If **macros** is not None, it can contain the macros a.k.a. values to be
    replaced, e.g.: {'NPROC':8, 'substrA':None} will replace all NPROC values
    by 8 and will let substrA untouched.
    """
    
    if verbose:
        print "==> " + filename
        tntlog.setLevel('INFO')
    else:
        tntlog.setLevel('WARNING')
    
    # macros stuff
    macros = _all_macros(macros)

    # read namelist
    initial_container = footprints.proxy.container(filename=filename)
    if not in_place:
        target_container = footprints.proxy.container(filename=filename + '.tnt')
    else:
        target_container = initial_container
    namelist = common.data.namelists.NamelistContent(macros=macros)
    namelist.slurp(initial_container)

    # process (in the right order !)
    if new_blocks is not None:
        add_blocks(namelist, new_blocks)
    if blocks_to_move is not None:
        move_blocks(namelist, blocks_to_move)
    if keys_to_move is not None:
        move_keys(namelist, keys_to_move)
    if keys_to_remove is not None:
        remove_keys(namelist, keys_to_remove)
    if keys_to_set is not None:
        set_keys(namelist, keys_to_set)
    if blocks_to_remove is not None:
        remove_blocks(namelist, blocks_to_remove)
    if blocks_ref is not None:
        cb = check_blocks(namelist, blocks_ref, macros)
        if len(cb) != 0:
            tntlog.warning('Set of blocks is different from reference: ' + blocks_ref)
            tntlog.warning('diff: ' + str(cb))
    
    # write to file
    namelist.rewrite(target_container, sorting=sorting)



if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='TNT - The Namelist Tool: a namelist modificator.',
                                     epilog='End of help for: %(prog)s')
    parser.add_argument('namelists',
                        type=str,
                        nargs='+',
                        help='namelist(s) file(s) to be processed.')
    directives = parser.add_mutually_exclusive_group(required=True)
    directives.add_argument('-d',
                            dest='directives',
                            type=str,
                            help='the file in which directives of modification are \
                                  stored. Activate option -D instead of -d to generate a template.')
    directives.add_argument('-D',
                            dest='generate_directives_template',
                            action='store_true',
                            help="generate a directives template 'tmpl_directives.tnt'.")
    parser.add_argument('-i',
                        action='store_true',
                        dest='in_place',
                        help='modifies the namelist(s) in place. \
                              Else, modified namelists are suffixed with .tnt',
                        default=False)
    sorting = parser.add_mutually_exclusive_group()
    sorting.add_argument('-S',
                         action='store_true',
                         dest='firstorder_sorting',
                         help='first order sorting: sort all keys within blocks.',
                         default=False)
    sorting.add_argument('-s',
                         action='store_true',
                         dest='secondorder_sorting',
                         help='second order sorting: sort only within indexes \
                               or attributes of the same key within blocks.',
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
        sorting = vortex.tools.fortran.FIRST_ORDER_SORTING
    elif args.secondorder_sorting:
        sorting = vortex.tools.fortran.SECOND_ORDER_SORTING
    else:
        sorting = vortex.tools.fortran.NO_SORTING
    if args.generate_directives_template:
        write_directives_template('tmpl_directives.tnt')
    else:
        directives = read_directives(args.directives)
        for nam in args.namelists:
            main(nam,
                 sorting=sorting,
                 in_place=args.in_place,
                 blocks_ref=args.blocks_ref,
                 verbose=args.verbose,
                 **directives)
