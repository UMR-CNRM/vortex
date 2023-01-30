"""
Utility functions of the :mod:`footprints` package.
"""

import re
import copy
import glob
from collections import deque
import string

from bronx.fancies import loggers
from bronx.stdtypes.date import timeintrangex
from bronx.syntax import dictmerge as _b_dictmerge
from bronx.syntax import mktuple as _b_mktuple

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)

# For legacy calls
dictmerge = _b_dictmerge
mktuple = _b_mktuple

# For legacy calls to footprints.util.rangex...
rangex = timeintrangex


def list2dict(a, klist):
    """
    Reshape any entry of *a* specified in *klist* as a dictionary of the
    iterable contents of these entries.
    """
    for k in klist:
        if k in a and isinstance(a[k], (list, tuple)):
            ad = dict()
            for item in a[k]:
                ad.update(item)
            a[k] = ad
    return a


def inplace(desc, key, value, globs=None, globalindex=None):
    """
    Redefine the ``key`` value in a deep copy of the description ``desc``.

    Examples::

        >>> (inplace({'test':'alpha'}, 'ajout', 'beta') ==
        ...  {'test': 'alpha', 'ajout': 'beta'})
        True

        >>> (inplace({'test':'alpha', 'recurs':{'a':1, 'b':2}}, 'ajout', 'beta') ==
        ...  {'test': 'alpha', 'ajout': 'beta', 'recurs': {'a': 1, 'b': 2}})
        True

    """
    newd = copy.deepcopy(desc)
    newd[key] = value
    if globs:
        for k in [x for x in newd.keys() if (x != key and isinstance(newd[x], str))]:
            for g in globs.keys():
                newd[k] = re.sub(r'\[glob:' + g + r'\]', globs[g], newd[k])
    if globalindex is not None:
        newd['index_expansion'] = globalindex + 1
    return newd


def _parse_globs(todo):
    """Process the **todo** string that contains ``glob`` statements.

    Nested brackets are dealt with.

    Returns a 3-elements tuple consisting of:

        * A set that contains the glob's names ;
        * The compiled regular expression that can be used to select the files
          and detect the glob's expressions ;
        * The python's glob string that can be used to look for files.

    """
    gstart = re.compile(r'^{glob:(\w+):')
    glob_names = set()
    finalglob = ''
    finalpattern = ''
    curbuffer = ''
    curname = None
    bracket_count = 0

    def glob2re(cbuffer):
        """Convert a Unix glob string to a regular expression (very crude)."""
        fpattern = ''
        for c in cbuffer:
            if c == '*':
                fpattern += '.*'
            elif c == '?':
                fpattern += '.'
            else:
                fpattern += re.escape(c)
        return fpattern

    while todo:
        # Usual text processing
        if not curname:
            gmatch = gstart.match(todo)
            if gmatch:
                # Starting a glob pattern match
                if curbuffer:
                    finalpattern += glob2re(curbuffer)
                    finalglob += curbuffer
                    curbuffer = ''
                curname = gmatch.group(1)
                if curname in glob_names:
                    raise ValueError("Duplicated glob's name ('{:s}' has already been defined)"
                                     .format(curname))
                glob_names.add(curname)
                todo = gstart.sub('', todo)
                continue
        # Pattern processing
        else:
            if (not curbuffer or curbuffer[-1] != '\\') and todo[0] == '{':
                # Opening bracket detected
                bracket_count += 1
            elif (not curbuffer or curbuffer[-1] != '\\') and todo[0] == '}':
                # Closing bracket detected
                if bracket_count:
                    bracket_count -= 1
                else:
                    # Pattern definition is done
                    try:
                        re.compile(curbuffer)
                    except re.error:
                        raise ValueError("Unable to compile << {:s} >> for glob's name = << {:s} >>"
                                         .format(curbuffer, curname))
                    finalpattern += '(?P<{:s}>{:s})'.format(curname, curbuffer)
                    finalglob += '*'
                    curname = None
                    curbuffer = ''
                    todo = todo[1:]
                    continue

        curbuffer += todo[0]
        todo = todo[1:]

    if curname:
        raise ValueError("Unbalanced brackets in << {:s} >> for glob's name = << {:s} >>"
                         .format(curbuffer, curname))

    if curbuffer:
        # Save the remain
        finalpattern += glob2re(curbuffer)
        finalglob += curbuffer

    return glob_names, re.compile('^' + finalpattern + '$'), finalglob


def expand(desc):
    r"""
    Expand the given description according to iterable or expandable arguments.

    List expansion::

        >>> expand({'test': 'alpha'}) == [{'test': 'alpha', 'index_expansion': 1}]
        True

        >>> (expand({ 'test': 'alpha', 'niv2': [ 'a', 'b', 'c' ]}) ==
        ...  [{'test': 'alpha', 'niv2': 'a', 'index_expansion': 1},
        ...   {'test': 'alpha', 'niv2': 'b', 'index_expansion': 2},
        ...   {'test': 'alpha', 'niv2': 'c', 'index_expansion': 3}])
        True

        >>> (expand({'test': 'alpha', 'niv2': 'x,y,z'}) ==
        ...  [{'test': 'alpha', 'niv2': 'x', 'index_expansion': 1},
        ...   {'test': 'alpha', 'niv2': 'y', 'index_expansion': 2},
        ...   {'test': 'alpha', 'niv2': 'z', 'index_expansion': 3}])
        True

        >>> (expand({'test': 'alpha', 'niv2': 'range(1,3)'}) ==
        ...  [{'test': 'alpha', 'niv2': 1, 'index_expansion': 1},
        ...   {'test': 'alpha', 'niv2': 2, 'index_expansion': 2},
        ...   {'test': 'alpha', 'niv2': 3, 'index_expansion': 3}])
        True
        >>> (expand({'test': 'alpha', 'niv2': 'range(0,6,3)'}) ==
        ...  [{'test': u'alpha', 'niv2': 0, 'index_expansion': 1},
        ...   {'test': 'alpha', 'niv2': 3, 'index_expansion': 2},
        ...   {'test': 'alpha', 'niv2': 6, 'index_expansion': 3}])
        True

    List expansion + dictionary matching::

        >>> (expand({'test': 'alpha', 'niv2': ['x', 'y'], 'niv3': {'niv2': {'x': 'niv2 is x', 'y': 'niv2 is y'}}}) ==
        ...  [{'test': 'alpha', 'niv3': 'niv2 is x', 'niv2': 'x', 'index_expansion': 1},
        ...   {'test': 'alpha', 'niv3': 'niv2 is y', 'niv2': 'y', 'index_expansion': 2}])
        True

    Globbing::

        >>> # Let's assume that the following files are present in the current working directory: # doctest: +SKIP
        ... # - testfile_abc_1
        ... # - testfile_abc_2
        ... # - testfile_def_2
        ... # - testfile_def_3
        ... # - testfile_a_trap
        >>> expand({'fname': r'testfile_{glob:i:\w+}_{glob:n:\d+}', 'id':'[glob:i]', 'n':'[glob:n]'}) # doctest: +SKIP
        [{'id': 'abc', 'fname': 'testfile_abc_1', 'n': '1', 'index_expansion': 1},
         {'id': 'abc', 'fname': 'testfile_abc_2', 'n': '2', 'index_expansion': 2},
         {'id': 'def', 'fname': 'testfile_def_2', 'n': '2', 'index_expansion': 3},
         {'id': 'def', 'fname': 'testfile_def_3', 'n': '3', 'index_expansion': 4}
         ]

    Explanation: The files currently in the working directory are matched using regular
    expressions. If the filename matches, some matching parts may be re-used to fill
    other keys in the dictionary.
    """
    ld = deque([desc, ])
    todo = True
    nbpass = 0

    while todo:
        todo = False
        nbpass += 1
        globalindex = 0
        if nbpass > 25:
            logger.error('Expansion is getting messy... (%d) ?', nbpass)
            raise MemoryError('Expand depth too high')
        newld = deque()
        while ld:
            d = ld.popleft()
            somechanges = False
            for k, v in d.items():
                if v.__class__.__name__.startswith('FP'):
                    continue
                if isinstance(v, list) or isinstance(v, tuple) or isinstance(v, set):
                    logger.debug(' > List expansion %s', v)
                    for x in v:
                        newld.append(inplace(d, k, x, globalindex=globalindex))
                        globalindex += 1
                    somechanges = True
                    break
                if isinstance(v, str) and re.match(r'range\(\d+(,\d+)?(,\d+)?\)$', v, re.IGNORECASE):
                    logger.debug(' > Range expansion %s', v)
                    lv = [int(x) for x in re.split(r'[\(\),]+', v) if re.match(r'\d+$', x)]
                    if len(lv) < 2:
                        lv.append(lv[0])
                    lv[1] += 1
                    for x in range(*lv):
                        newld.append(inplace(d, k, x, globalindex=globalindex))
                        globalindex += 1
                    somechanges = True
                    break
                if isinstance(v, str) and re.search(r',', v):
                    logger.debug(' > Coma separated string %s', v)
                    for x in v.split(','):
                        newld.append(inplace(d, k, x, globalindex=globalindex))
                        globalindex += 1
                    somechanges = True
                    break
                if isinstance(v, str) and re.search(r'{glob:\w+:', v):
                    logger.debug(' > Globbing from string %s', v)
                    g_names, g_re, g_glob = _parse_globs(v)
                    repld = list()
                    for filename in sorted(glob.glob(g_glob)):
                        m = g_re.match(filename)
                        if m:
                            globmap = dict()
                            for g in g_names:
                                globmap[g] = m.group(g)
                            repld.append(inplace(d, k, filename, globmap, globalindex=globalindex))
                            globalindex += 1
                    newld.extend(repld)
                    somechanges = True
                    break
                if isinstance(v, dict):
                    for dk in [x for x in v.keys() if x in d]:
                        dv = d[dk]
                        if not (isinstance(dv, list) or isinstance(dv, tuple) or isinstance(dv, set)):
                            newld.append(inplace(d, k, v[dk][str(dv)], globalindex=globalindex))
                            globalindex += 1
                            somechanges = True
                            break
                    if somechanges:
                        break
            todo = todo or somechanges
            if not somechanges:
                newd = d.copy()
                newd['index_expansion'] = globalindex + 1
                newld.append(newd)
                globalindex += 1
        ld = newld

    logger.debug('Expand in %d loops', nbpass)
    return list(ld)


class FoxyFormatter(string.Formatter):
    """A string formatter that may try to call an argument-less method."""

    def get_field(self, field_name, args, kwargs):
        """Given a **field_name**, find the object it references."""
        obj, used_key = super().get_field(field_name, args, kwargs)
        if callable(obj):
            obj = obj()
        return (obj, used_key)
