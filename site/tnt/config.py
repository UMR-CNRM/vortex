"""
A bunch of classes and functions that deal with TNT configuration files and
directives
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import io
import os
import six
import string
import sys

# Detect TNT's configuration files directory
TPL_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                             'templates')


def get_template(tplname, encoding=None):
    tplfile = os.path.join(TPL_DIRECTORY, tplname)
    with io.open(tplfile, 'r', encoding=encoding) as fhtpl:
        tpl = string.Template(fhtpl.read())
    return tpl


def write_directives_template(out=sys.stdout):
    """Write out a directives template."""
    outtpl = os.path.join(TPL_DIRECTORY, 'tnt-directive.tpl')
    if isinstance(out, six.string_types):
        outfh = io.open(out, 'w')
    else:
        outfh = out
    try:
        with io.open(outtpl, 'r') as tplfh:
            for line in tplfh:
                outfh.write(line)
    finally:
        if isinstance(out, six.string_types):
            outfh.close()


def read_directives(filename):
    """
    Read directives in an external file (**filename**).

    For a template of directives, call function *write_directives_template()*.
    """
    directives = set(['keys_to_remove', 'keys_to_set', 'keys_to_move',
                      'blocks_to_move', 'blocks_to_remove', 'new_blocks',
                      'macros'])
    if sys.version_info.major == 3 and sys.version_info.minor >= 4:
        import importlib.util as imputil  # @UnresolvedImport
        spec = imputil.spec_from_file_location(os.path.basename(filename),
                                               os.path.abspath(filename))
        m = imputil.module_from_spec(spec)
        spec.loader.exec_module(m)
    else:
        import imp  # @UnresolvedImport
        m = imp.load_source(filename, os.path.abspath(filename))

    return {k: v for k, v in m.__dict__.items() if k in directives}
