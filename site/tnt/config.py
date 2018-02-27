"""
A bunch of classes and functions that deal with TNT configuration files and
directives
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import collections
import io
import os
import six
import string
import sys

# Detect TNT's configuration files directory
TPL_DIRECTORY = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                             'templates')


class TntDirectiveError(Exception):
    pass


class TntDirectiveUnkownError(TntDirectiveError):
    def __init__(self, name):
        errmsg = 'The "{:s}" directive is not allowed with TNT.'.format(name)
        super(TntDirectiveUnkownError, self).__init__(errmsg)


class TntDirectiveValueError(TntDirectiveError):
    def __init__(self, name, value):
        errmsg = '"{!s}" is not an appropriate value for the "{:s}" directive.'.format(value, name)
        super(TntDirectiveValueError, self).__init__(errmsg)


class TntDirective(object):

    _ALLOWED_DIRECTIVES = set(('keys_to_remove', 'keys_to_set', 'keys_to_move',
                               'blocks_to_move', 'blocks_to_remove', 'new_blocks',
                               'macros'))

    def _check_keytuple(self, val, theexc, unique=False):
        """Verify if *val* is some kind of a (block, key) tuple description."""
        keylist = list()
        # Reformat dictionaries, iterables, ...
        if isinstance(val, collections.Mapping):
            for b, v in val.items():
                if isinstance(v, collections.Iterable) and not isinstance(v, six.string_types):
                    keylist.extend([(b, kk) for kk in v])
                else:
                    keylist.append((b, v), )
        elif isinstance(val, collections.Iterable):
            if all([isinstance(v, collections.Iterable) and not isinstance(v, six.string_types)
                    for v in val]):
                keylist.extend(val)
            else:
                keylist.append(tuple(val))
        else:
            raise theexc
        # Final check...
        if not all([len(k) == 2 and
                    isinstance(k[0], six.string_types) and
                    isinstance(k[1], six.string_types)
                    for k in keylist]):
            raise theexc
        # Unique element wanted ?
        if unique:
            if len(keylist) > 1:
                raise theexc
            return keylist[0]
        else:
            return set(keylist)

    def _process_keys_to_remove(self, val):
        myexc = TntDirectiveValueError('keys_to_remove', val)
        return self._check_keytuple(val, myexc)

    def _process_keys_to_set(self, val, theexc=None):
        kdict = dict()
        myexc = theexc or TntDirectiveValueError('keys_to_set', val)
        if isinstance(val, collections.Mapping):
            for k, v in val.items():
                if isinstance(v, collections.Mapping):
                    for kk, vv in v.items():
                        kdict[self._check_keytuple((k, kk), myexc, unique=True)] = vv
                elif isinstance(k, collections.Iterable):
                    kdict[self._check_keytuple(k, myexc, unique=True)] = v
                else:
                    raise myexc
        else:
            raise myexc
        return kdict

    def _process_keys_to_move(self, val):
        kdict = dict()
        myexc = TntDirectiveValueError('keys_to_move', val)
        keystructure = self._process_keys_to_set(val, theexc=myexc)
        for k, v in keystructure.items():
            kdict[k] = self._check_keytuple(v, myexc, unique=True)
        return kdict

    def _process_blocks_to_move(self, val):
        if not (isinstance(val, collections.Mapping) and
                all([isinstance(k, six.string_types) and isinstance(v, six.string_types)
                     for k, v in val.items()])):
            raise TntDirectiveValueError('blocks_to_move', val)
        return {k: v for k, v in val.items()}

    def _process_set_of_blocks(self, val, realname):
        if (isinstance(val, collections.Iterable) and
                not isinstance(val, six.string_types) and
                all([isinstance(v, six.string_types) for v in val])):
            return set(val)
        elif isinstance(val, six.string_types):
            return set([val, ])
        else:
            raise TntDirectiveValueError(realname, val)

    def _process_blocks_to_remove(self, val):
        return self._process_set_of_blocks(val, 'blocks_to_remove')

    def _process_new_blocks(self, val):
        return self._process_set_of_blocks(val, 'new_blocks')

    def _process_macros(self, val):
        if not (isinstance(val, collections.Mapping) and
                all([isinstance(k, six.string_types) for k in val.keys()])):
            raise TntDirectiveValueError('macros', val)
        return {k: v for k, v in val.items()}

    def __init__(self, **kwargs):
        self._internals = dict()
        # Is the directive allowed ?
        for k, v in kwargs.items():
            if k not in self._ALLOWED_DIRECTIVES:
                raise TntDirectiveUnkownError(k)
            self._internals[k] = getattr(self, '_process_{:s}'.format(k))(v)

    def __getattr__(self, item):
        if item not in self._ALLOWED_DIRECTIVES:
            raise TntDirectiveUnkownError(item)
        else:
            return self._internals.get(item, None)


def read_directives(filename):
    """
    Read directives in an external file (**filename**).

    For a template of directives, call function *write_directives_template()*.
    """
    if os.path.splitext(filename)[1] in ('.yaml', '.yml'):
        import yaml
        with open(filename, 'r') as yamlfh:
            return TntDirective(** yaml.load(yamlfh))
    else:
        prev_bytecode_flag = sys.dont_write_bytecode
        try:
            sys.dont_write_bytecode = True
            if sys.version_info.major == 3 and sys.version_info.minor >= 4:
                import importlib.util as imputil  # @UnresolvedImport
                spec = imputil.spec_from_file_location(os.path.basename(filename),
                                                       os.path.abspath(filename))
                m = imputil.module_from_spec(spec)
                spec.loader.exec_module(m)
            else:
                import imp  # @UnresolvedImport
                m = imp.load_source(filename, os.path.abspath(filename))
        finally:
            sys.dont_write_bytecode = prev_bytecode_flag
        return TntDirective(** {k: v for k, v in m.__dict__.items() if not k.startswith('_')})


def get_template(tplname, encoding=None):
    tplfile = os.path.join(TPL_DIRECTORY, tplname)
    with io.open(tplfile, 'r', encoding=encoding) as fhtpl:
        tpl = string.Template(fhtpl.read())
    return tpl


def write_directives_template(out=sys.stdout):
    """Write out a directives template."""
    tplname = 'tnt-directive.tpl.py'
    if isinstance(out, six.string_types):
        outfh = io.open(out, 'w')
        if os.path.splitext(out)[1] in ('.yaml', '.yml'):
            tplname = 'tnt-directive.tpl.yaml'
    else:
        outfh = out
    outtpl = os.path.join(TPL_DIRECTORY, tplname)
    try:
        with io.open(outtpl, 'r') as tplfh:
            for line in tplfh:
                outfh.write(line)
    finally:
        if isinstance(out, six.string_types):
            outfh.close()
