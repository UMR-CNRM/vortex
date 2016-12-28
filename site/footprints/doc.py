#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
Footprint's docstring generator
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import collections

from . import dump, priorities

__all__ = ['visibility', ]


# We just re-use the classes provided in priorities (it is exactly the feature we needed)

#: Predefined documentation visibilities
visibility = priorities.PrioritySet(('default', 'advanced', 'guru'))


def set_before(visibilityref, *args):
    """Set ``args`` visibility before specified ``visibilityref``."""
    for newpriority in args:
        visibility.insert(tag=newpriority, before=visibilityref)


def set_after(visibilityref, *args):
    """Set ``args`` visibility after specified ``visibilityref``."""
    for newpriority in reversed(args):
        visibility.insert(tag=newpriority, after=visibilityref)


def _formating_basic(fp):
    """Just use the default TxTDumper to generate a raw documentation."""
    return "\n\n    Footprint::\n\n" + fp.nice()


def _formating_sphinx_v1(fp):
    """Create a docstring that will hopefully be nice in Sphinx."""
    indent = ' ' * 4  # Default indentation
    dumper = dump.OneLineTxtDumper(tag='sphinxdumper')
    dumper.reset()
    out = ['', '']

    # Footprint's level attributes
    out.append(".. note:: This class is managed by footprint.\n")
    out.append("     * info: {0.info}".format(fp))
    out.append("     * priority: {}".format(dumper.dump(fp.level)))
    # Now, print out the rest (whatever is found)
    for k, v in [(k, v) for k, v in fp.as_dict().items()
                 if k not in ['info', 'priority', 'attr'] and v]:
        out.append("     * {}: {}".format(k, dumper.dump(v)))
    out.append('')

    # Now the attributes...
    out.append('   Automatic parameters from the footprint:\n')
    aliases = collections.OrderedDict()  # For later use
    # First sort alphabetically with respect to the attribute names
    s_attrs = sorted(fp.as_dict()['attr'].items(), key=lambda item: item[0])
    # Then use visibility and zorder
    s_attrs = sorted(s_attrs,
                     key=lambda item: item[1]['doc_visibility'].rank * 200 - item[1]['doc_zorder'])
    for attr, desc in s_attrs:
        # Find out the type name
        t = desc.get('type', str)
        tname = (t.__module__ + '.' if not t.__module__.startswith('__') else '')
        tname += t.__name__
        # The attribute name, typen ...
        out.append('     * **{}** (:class:`{}`) - {} - {}'.
                   format(attr, tname, desc['access'],
                          desc.get('info', 'Not documented, sorry.'), ))
        subdesc = list()
        # Is it optional ?
        if desc['optional']:
            subdesc.append('       * Optional. Default is {0:}.'.format(dumper.dump(desc['default'])))
        # The superstars
        for k, v in [(i, desc[i]) for i in ['values', 'outcast'] if desc[i]]:
            subdesc.append('       * {0:}: {1:}'.format(k.capitalize(), dumper.dump(v)))
        # Now, print out the rest (whatever is found)
        for k, v in [(i, v) for i, v in desc.items()
                     if i not in ['info', 'type', 'values', 'outcast', 'optional', 'alias',
                                  'default', 'access', 'doc_visibility', 'doc_zorder'] and v]:
            subdesc.append('       * {0:}: {1:}'.format(k.capitalize(), dumper.dump(v)))
        if subdesc:
            out.extend(['', ] + subdesc + ['', ])
        # Store aliases (they will be displayed later)
        if desc['alias']:
            for alias in desc['alias']:
                aliases[alias] = attr
    out.append('')

    # Aliases
    if aliases:
        out.append("   Aliases of some parameters:")
        out.append('')
        for k, v in aliases.items():
            out.append("     * **{}** is an alias of {}.".format(k, v))
    out.append('')

    return '\n'.join([indent + l for l in out])


# Default function for docstrings formating
_formating_styles = {1: _formating_basic,
                     2: _formating_sphinx_v1}


def format_docstring(fp, formating_style):
    """Call the appropriate formatting function given *formating_style*."""
    return _formating_styles.get(formating_style, 1)(fp)
