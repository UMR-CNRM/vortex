"""
Hierarchical documents to store footprints information.
StandardReport is derived from :class:`xml.dom.minidom.Document`.
"""

import collections
from datetime import datetime
import re
import weakref

from bronx.fancies import dump
from bronx.patterns import getbytag

#: No automatic export
__all__ = []

REPORT_WHY_MISSING = 'Missing value'
REPORT_WHY_INVALID = 'Invalid value'
REPORT_WHY_OUTSIDE = 'Not in values'
REPORT_WHY_OUTCAST = 'Outcast value'
REPORT_WHY_RECLASS = 'Could not reclass'
REPORT_WHY_SUBCLASS = 'Not a subclass'

REPORT_ONLY_NOTFOUND = 'No value found'
REPORT_ONLY_NOTMATCH = 'Do not match'


# Module Interface

def get(**kw):
    """Return actual footprint log object matching description."""
    return FootprintLog(**kw)


def keys():
    """Return the list of current entries names collected."""
    return FootprintLog.tag_keys()


def values():
    """Return the list of current entries values collected."""
    return FootprintLog.tag_values()


def items():
    """Return the items of the footprint logs table."""
    return FootprintLog.tag_items()


class FootprintBadLogEntry(Exception):
    """Exception raised when inappropriate log entries are met."""
    pass


class NullReport:
    """Fake reporting: accept any log report command but do nothing."""

    def __init__(self, *args, **kw):
        self._maxlen = 1000
        self._blindlog = collections.deque(maxlen=self._maxlen)

    def __len__(self):
        return len(self._blindlog)

    def items(self):
        """Internal list of items recorded."""
        return self._blindlog

    def clear(self):
        """Rewind internal raw list of log commands."""
        self._blindlog = collections.deque(maxlen=self._maxlen)

    def add(self, *args, **kw):
        """Push any arg provided to the internal raw list of log commands."""
        if args:
            self._blindlog.append(args)
        if kw:
            self._blindlog.append(kw)


class FootprintLogEntry:
    """
    Generic entry item in the footprint log.
    Could be :

      * a collector item
      * a candidate item (i.e.: a class)
    """
    def __init__(self, node, **kw):
        self.context = 'void'
        self.stamp = datetime.now()
        self._items = list()
        self._weak = kw.pop('weak', True)
        self.__dict__.update(kw)
        if self._weak:
            self._node = weakref.ref(node)
        else:
            self._node = node

    @property
    def node(self):
        if self._weak:
            return self._node()
        else:
            return self._node

    def add(self, item):
        """Push the specified ``item`` at the end of the internal log list."""
        self._items.append(item)


class FootprintLogCollector(FootprintLogEntry):
    """Dedicated entry to :class:`footprints.Collector` items."""

    def __init__(self, node, **kw):
        """Default name is the ``node`` entry keypoint."""
        super().__init__(node, **kw)
        self.name = self.node.tag

    def __iter__(self):
        """Iterates on :class:`FootprintLogClass` items."""
        yield from sorted(self._items, key=lambda item: item.name)

    def feed_xml(self, xmlnode):
        """Insert in the specified ``xmlnode`` informations relative to candidate classes."""
        xmlbase = xmlnode.new_entry('collector', name=self.name, stamp=self.stamp.isoformat())
        for kid in self:
            xmlnode.current(xmlbase)
            kid.feed_xml(xmlnode)

    def as_dict(self):
        """Convenient method for retrieving some handy dictionary."""
        dico = dict()
        for item in self._items:
            dico[item.name] = item.as_dict()
        return dico

    def as_tree(self, **kw):
        """Feed a :class:`FactorizedReport` according to the order specified."""
        fr = FactorizedReport(**kw)
        for kid in self:
            for item in kid:
                info = item.copy()
                info['class'] = kid.name
                fr.add(**info)
        return fr

    def as_flat(self, **kw):
        """Feed a :class:`FlatReport` according to the order specified."""
        flat = FlatReport(**kw)
        for kid in self:
            for item in kid:
                info = item.copy()
                info['attribute'] = info.pop('name')
                flat.add(focus=kid.name, **info)
        return flat

    def lightdump(self, **kw):
        """Pseudo structured dump of the current collector item report."""
        for kid in self:
            kid.lightdump(**kw)


class FootprintLogClass(FootprintLogEntry):
    """Dedicated entry to :class:`footprints.FootprintBase` items."""

    def __init__(self, node, parent, **kw):
        """Default name is the ``node`` fullname method output."""
        super().__init__(node, **kw)
        self.name = self.node.fullname()
        self.parent = parent
        self.parent.add(self)

    def __iter__(self):
        yield from self._items

    def feed_xml(self, xmlnode):
        """Insert in the specified ``xmlnode`` informations relative to attributes of the candidate class."""
        xmlnode.current(xmlnode.add('class', name=self.name))
        for kid in self._items:
            kidstr = {k: str(v) for k, v in kid.items()}
            xmlnode.add('attribute', **kidstr)

    def as_dict(self):
        """Convenient method for retrieving a handy dictionary."""
        dico = dict()
        for item in self._items:
            info = item.copy()
            attr = info.pop('name')
            dico[attr] = info
        return dico

    def lightdump(self, indent='    ', attrjust=10):
        """Pseudo structured dump of the current class item report."""
        if self._items:
            print(indent, self.name)
            for item in self._items:
                info = item.copy()
                print(indent * 2, info.pop('name').ljust(attrjust), ':', info)
        else:
            print('=>'.rjust(len(indent)), self.name)
        print()


class FootprintLog(getbytag.GetByTag):
    """Collect log informations to produce footprints reports."""

    def __init__(self, log_maxlen=None, weak=True):
        self._log = collections.deque(maxlen=log_maxlen)
        self._weak = weak
        self._current = None
        self._xml = None
        self._dict = dict()
        self._touch = False

    def info(self):
        """Return a simple description as a string."""
        return 'Report ' + self.tag.title() + ':'

    @property
    def weak(self):
        """Boolean value, true if the log was built with weak references (default)."""
        return self._weak

    def __len__(self):
        return len(self._log)

    def __iter__(self):
        yield from self._log

    def items(self):
        """Internal list of items recorded."""
        return self._log

    def clear(self):
        """Start a fresh new log history."""
        self._log = list()

    def reduce_to_last(self):
        """Remove from the current log history all but the last collector resolution attempt."""
        self._log[0:-1] = []

    @property
    def last(self):
        return self._log[-1] if self._log else None

    def current(self, node=None):
        """Return current active entry (collector or class) of the log."""
        if node:
            self._current = node
        return self._current

    def add_collector(self, node, **kw):
        """Insert a collector entry into the log."""
        self._current = FootprintLogCollector(node, **kw)
        self._log.append(self._current)
        self._touch = True

    def add_candidate(self, node, **kw):
        """Insert a class entry into the log."""
        if self._current is not None and isinstance(self._current, FootprintLogClass):
            self._current = self._current.parent
        if self._current is None or not isinstance(self._current, FootprintLogCollector):
            raise FootprintBadLogEntry('Current log context is either empty or not a collector')
        self._current = FootprintLogClass(node, parent=self._current, **kw)
        self._touch = True

    def add_attribute(self, name, **kw):
        """Insert an attribute resolution information entry into the log."""
        if self._current is None or not isinstance(self._current, FootprintLogClass):
            raise FootprintBadLogEntry('Current log context is either empty or not a class candidate')
        kw['name'] = name
        self._current.add(kw)
        self._touch = True

    def add(self, **kw):
        """
        Add an entry to the current log.
        One of these arguments should be provided:

          * collector
          * candidate
          * attribute
        """
        this_collector = kw.pop('collector', None)
        if this_collector is not None:
            return self.add_collector(this_collector, weak=self.weak, **kw)
        this_candidate = kw.pop('candidate', None)
        if this_candidate is not None:
            return self.add_candidate(this_candidate, weak=self.weak, **kw)
        this_attribute = kw.pop('attribute', None)
        if this_attribute is not None:
            return self.add_attribute(this_attribute, **kw)
        raise FootprintBadLogEntry('Log entry should be a collector, a class candidate or an attribute.')

    def whynot(self, select):
        """
        Diagnostic method for retrieving valuable information on the reason why some class candidates
        have failed. The ``select`` argument is used as a pattern matching on full class names
        (case insensitive).
        """
        if self.last:
            info = self.last.as_dict()
            for k in [x for x in info
                      if not re.search(select, x, re.IGNORECASE) or not info[x]]:
                del info[k]
            return info
        else:
            return None

    def as_xml(self, force=False):
        """Return a true class:`xml.dom.minidom.Document`."""
        if not self._xml or self._touch or force:
            self._xml = StandardReport(tag=self.tag)
            for item in self._log:
                item.feed_xml(self._xml)
            self._touch = False
        return self._xml

    def as_dict(self, force=False, stamp=True):
        """Convenient method for retrieving some handy dictionary."""
        if not self._dict or self._touch or force:
            self._dict = dict()
            for i, item in enumerate(self._log):
                key = item.name
                if stamp:
                    key += ' ' + item.stamp.isoformat()
                else:
                    key += '_{:04d}'.format(i + 1)
                self._dict[key] = item.as_dict()
            self._touch = False
        return self._dict

    def fulldump(self, stamp=False):
        """Shortcut to :mod:``dump`` facilities."""
        print(dump.fulldump(self.as_dict(force=True, stamp=stamp)))


class StandardReport:
    """XML structured report."""

    def __init__(self, doc=None, tag=None):
        if doc is None:
            import xml.dom.minidom
            self._doc = xml.dom.minidom.Document()
        else:
            self._doc = doc
        self.root = self._doc.createElement('report')
        self.root.setAttribute('tag', tag)
        self._doc.appendChild(self.root)
        self._current = self.root

    def __call__(self):
        """Print the complete dump of the current report object."""
        print(self.dump_all())

    @property
    def doc(self):
        return self._doc

    def add(self, key, **kw):
        """Add a information node to the ``base`` or to the current node."""
        base = kw.pop('base', self.current())
        entry = self.doc.createElement(key)
        for k, v in sorted(kw.items()):
            entry.setAttribute(k, v)
        base.appendChild(entry)
        return base.lastChild

    def new_entry(self, key, **kw):
        """Insert a top level entry (child of the root node)."""
        kw['base'] = self.root
        return self.add(key, **kw)

    def current(self, node=None):
        """Return the current active node of the document."""
        if node:
            self._current = node
        return self._current

    def dump_all(self):
        """Return a string with a complete formatted dump of the document."""
        return self.doc.toprettyxml(indent='    ')

    def dump_last(self):
        """Return a string with a complete formatted dump of the last entry."""
        return self.root.lastChild.toprettyxml(indent='    ')

    def iter_last(self):
        """Iterate on last node and return ( class, name, why ) information."""
        for kid in self.root.lastChild.childNodes:
            dico = dict(classname=kid.getAttribute('name'))
            for subkid in kid.childNodes:
                dico['name'] = subkid.getAttribute('name')
                dico['why'] = subkid.getAttribute('why')
                yield dico


class FlatReport:
    """Store entries as simple dictionaries that could be hierarchically reshuffled afterward."""

    def __init__(self, sortlist=None):
        """By default the report is empty."""
        self._items = list()
        self._tree = dict()
        if sortlist is None:
            sortlist = list()
        self._sort = list(sortlist)

    def add(self, **kw):
        """Push the current key-value description as a new report entry."""
        self._items.append(kw)

    def reshuffle(self, sortlist=None, skip=True):
        """
        Sort the entire set of items as a hierarchical tree driven by keys of the
        specified ``sortlist``.
        """
        self._tree = dict()
        if sortlist is not None:
            self._sort = sortlist[:]
        for item in self._items:
            current = self._tree
            info = item.copy()
            done = True
            for k in self._sort:
                if k in info:
                    entry = k + ': ' + info.pop(k)
                    if entry not in current:
                        current[entry] = dict()
                    current = current[entry]
                else:
                    done = False
                    if not skip:
                        break
            if done or skip:
                focus = info.pop('focus')
                if info:
                    current[focus] = ' / '.join([str(x) + ': ' + str(info[x])
                                                 for x in info.keys()])
                else:
                    current[focus] = None

    def fulldump(self):
        """Print out the internal tree."""
        print('- ' * 5, "\n")
        print(self.__class__.__name__, 'shuffle', self._sort)
        print(dump.fulldump(self._tree))
        print()


class FactorizedReport:

    def __init__(
            self,
            focus='class',
            indent='    ',
            ordering=(
                (('name', ), ('kind', )),
                (('why', 'only'), (REPORT_WHY_MISSING, REPORT_WHY_INVALID,
                                   REPORT_WHY_OUTSIDE, REPORT_WHY_OUTCAST,
                                   REPORT_WHY_RECLASS, REPORT_WHY_SUBCLASS,
                                   REPORT_ONLY_NOTFOUND, REPORT_ONLY_NOTMATCH)),
            ),
            renaming=(('name', 'attribute_name'),)):
        """
        Generates a report whose items are sorted using some parameters:

        * ``tag`` is the end-level entry that has to be sorted
        * ``ordering`` describes the sorting options.

        Ordering must be a list of pair (key-name, selected-values) where:

        * the order of the list defines the priority order for sorting
        * the selected-values is a tuple of values to focus on if encountered.

        """
        self.focus = focus
        self._define = collections.OrderedDict(ordering)
        self._renaming = dict(renaming)
        self._indent = indent
        self._tree = dict()

    def _depth_key(self, depth):
        return list(self.keys())[depth]

    def get_order(self, dic, depth):
        order = list()
        other = list(dic.keys())
        for val in self.interestingValues(list(self.keys())[depth]):
            for v in other:
                if v[1].startswith(val):
                    order.append(v)
                    other.remove(v)
        order.extend(other)
        return order

    def keys(self):
        return self._define.keys()

    def __len__(self):
        return len(self._define)

    def interestingValues(self, key):
        return self._define[key]

    def add(self, **kw):
        tagvalue = kw[self.focus]
        dic = self._tree
        for k in self.keys():
            for ki in k:
                kj = self._renaming.get(ki, ki)
                v = kw.get(ki, None)
                if v is not None:
                    if (kj, v) not in dic:
                        dic[(kj, v)] = dict()
                    dic = dic[(kj, v)]
                    break
            if v is None:
                raise KeyError("Ordering key not found: {:s}".format(k))
        info = kw.get('args', '')
        dic[tagvalue] = str(info)

    def printer(self, dic, currentindent, depth, ordered=False):
        if depth == len(self):
            for tagValue in sorted(dic.keys()):
                print(currentindent, self.focus, ':', tagValue,
                      '(' + dic[tagValue] + ')')
        else:
            if ordered:
                order = self.get_order(dic, depth)
            else:
                order = dic
            for v in order:
                print('{:s} {:s} = {:s}'.format(currentindent, *v))
                self.printer(dic[v], currentindent + self._indent, depth + 1, ordered)

    def softprint(self):
        self.printer(self._tree, self._indent, 0)

    def orderedprint(self):
        self.printer(self._tree, self._indent, 0, ordered=True)

    def simpleprinter(self, dic, depth, msg=None, space=True):
        if depth == len(self):
            if space:
                print()
            for tagValue in sorted(dic.keys()):
                print(self._indent, self.focus, ':', tagValue,
                      '(' + dic[tagValue] + ')')
            if msg:
                print(self._indent * 3, msg)
        else:
            for v in self.get_order(dic, depth):
                newmsg = msg + ' | ' if msg else ''
                newmsg += '{:s} = {:s}'.format(*v)
                self.simpleprinter(dic[v], depth + 1, newmsg)

    def niceprinter(self, dic, depth, maxdepth, group, msg=None, separator='+'):
        if depth == maxdepth:
            self.simpleprinter(dic, depth, msg, depth % group != 0)
        else:
            toprint = None
            if depth % group == 0:
                toprint = msg
                msg = None
            if toprint:
                separator = {'+': '-', '-': '~'}.get(separator, separator)
            for v in self.get_order(dic, depth):
                newmsg = msg + ' | ' if msg else ''
                newmsg += '{:s} = {:s}'.format(*v)
                self.niceprinter(dic[v], depth + 1, maxdepth, group, newmsg, separator)
                if depth % group == 0:
                    print(self._indent + (separator * (40 + 5 * len(self._indent))))
            if toprint:
                print(self._indent * ((maxdepth - depth) // group + 4), toprint)

    def dumper(self, maxdepth=1, group=1):
        if maxdepth > len(self):
            maxdepth = len(self)
        self.niceprinter(self._tree, 0, maxdepth, group)
