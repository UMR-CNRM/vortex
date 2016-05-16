#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
Data dumper... mostly used in objects' docstring with a footprint.
"""

#: No automatic export
__all__ = []

from xml.dom import minidom
import re

from . import util


def DEBUG(msg, obj=None, level=None):
    """Fake method for debug purpose (then should provide a print statement)."""
    # print msg, str(obj)
    pass


# Global settings for the Txt dumper
max_depth = 32

indent_first = 6
indent_size = 4
indent_space = ' '

break_base = False
break_string = False
break_bool = False

break_before_list_item = False
break_before_list_begin = False
break_after_list_begin = False
break_before_list_end = False
break_after_list_end = False

break_before_set_item = False
break_before_set_begin = False
break_after_set_begin = False
break_before_set_end = False
break_after_set_end = False

break_before_tuple_item = False
break_before_tuple_begin = False
break_after_tuple_begin = False
break_before_tuple_end = False
break_after_tuple_end = False

break_before_dict_key = True
break_before_dict_value = False
break_before_dict_begin = False
break_after_dict_begin = False
break_before_dict_end = True
break_after_dict_end = False


def is_an_instance(val):
    # Change: This routine will no longer detect old-style classes !
    #         (because the support of old-style classes will be removed)
    # instance of extension class, but not an actual extension class
    if (hasattr(val, '__class__') and
            hasattr(val, '__dict__') and
            not hasattr(val, '__bases__')):
        return True
    else:
        return False


def is_class(val):
    return hasattr(val, '__bases__')


def indent(level=0, nextline=True):
    if nextline:
        return "\n" + indent_space * (indent_first + indent_size * level)
    else:
        return ""


def get(**kw):
    """Return actual dumper object matching description."""
    return TxtDumper(**kw)


class _AbstractDumper(util.GetByTag):
    """Could dump almost anything."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.seen = dict()

    def _dump_internal_dict(self, obj, level=0, nextline=True):
        return self.dump_dict(obj, level + 1, nextline)

    def _dump_as_proxy(self, proxy, obj, level=0, nextline=True):
        return getattr(self, 'dump_' + proxy,
                       self._lazzy_dump)(obj, level + 1, nextline)

    def _unknown_obj_overview(self, obj):
        strobj = str(obj)
        reprobj = repr(obj)
        if '\n' not in strobj and strobj != reprobj:
            return strobj
        else:
            return reprobj

    def _dump_unknown_obj(self, obj, level=0, nextline=True):
        return "{:s}.{:s}::{:s}".format(type(obj).__module__, type(obj).__name__,
                                        self._unknown_obj_overview(obj))

    def _dump_class(self, obj, level=0, nextline=True):
        return '{0:s}.{1:s}'.format(obj.__module__, obj.__name__)

    def _dump_builtin(self, obj, level=0, nextline=True):
        return obj.__name__

    def _dump_obj_shortcut(self, obj, level=0, nextline=True):
        return "{:s}.{:s}::{:s}".format(type(obj).__module__, type(obj).__name__,
                                        obj.as_dump())

    def dump_default(self, obj, level=0, nextline=True):
        DEBUG('dump_default')
        # Great, obj as a as_dict method: top choice
        if hasattr(obj, '__dict__') and hasattr(obj, 'as_dict'):
            return self._dump_internal_dict(obj.as_dict(), level + 1)
        # Rely on parent classes: ok it should work
        if isinstance(obj, dict):
            return self._dump_as_proxy('dict', obj, level + 1, nextline)
        if isinstance(obj, set):
            return self._dump_as_proxy('set', obj, level + 1, nextline)
        if isinstance(obj, list):
            return self._dump_as_proxy('list', obj, level + 1, nextline)
        if isinstance(obj, tuple):
            return self._dump_as_proxy('tuple', obj, level + 1, nextline)
        # Can't do anything better, sorry !
        return self._dump_unknown_obj(obj, level, nextline)

    def _lazzy_dump(self, obj, level=0, nextline=True):
        return obj

    dump_dict = _lazzy_dump
    dump_int = _lazzy_dump
    dump_long = _lazzy_dump
    dump_float = _lazzy_dump
    dump_bool = _lazzy_dump
    dump_str = _lazzy_dump

    def _recursive_dump(self, obj, level=0, nextline=True):
        """This routine can be called recursively (if necessary)."""
        DEBUG('dump top', obj)

        this_id = id(obj)

        if this_id in self.seen:
            return self.seen[this_id]

        if is_an_instance(obj) and hasattr(obj, 'as_dump'):
            DEBUG('dump shortcut', obj)
            self.seen[this_id] = self._dump_obj_shortcut(obj, level, nextline)
            return self.seen[this_id]

        if is_class(obj):
            if obj.__module__ == '__builtin__':
                DEBUG('builtin')
                self.seen[this_id] = self._dump_builtin(obj, level, nextline)
            else:
                DEBUG('class ' + str(obj))
                self.seen[this_id] = self._dump_class(obj, level, nextline)
            return self.seen[this_id]

        name = type(obj).__name__
        dump_func = getattr(self, "dump_%s" % name, self.dump_default)
        return dump_func(obj, level, nextline)

    def dump(self, obj, level=0, nextline=True):
        """Call this method to dump anything (or at least try to...)."""
        return self._recursive_dump(obj, level=level, nextline=nextline)

    def cleandump(self, obj):
        """Clear cache dump and provide a dump of the provided ``obj``."""
        self.reset()
        return self.dump(obj)


class JsonableDumper(_AbstractDumper):

    def dump_dict(self, obj, level=0, nextline=True):
        return {self._recursive_dump(k, level, nextline):
                self._recursive_dump(v, level + 1, nextline)
                for k, v in obj.iteritems()}

    def dump_list(self, obj, level=0, nextline=True):
        return [self._recursive_dump(v, level + 1, nextline) for v in obj]

    dump_tuple = dump_list
    dump_set = dump_list

    def dump_NoneType(self, obj, level=0, nextline=True):
        return 'None'


class XmlDomDumper(JsonableDumper):

    def __init__(self, named_nodes=()):
        super(XmlDomDumper, self).__init__()
        self._named_nodes = named_nodes

    def _unknown_obj_overview(self, obj):
        return re.sub(r'^<(.*)>$', r'\1',
                      super(XmlDomDumper, self)._unknown_obj_overview(obj))

    def _dump_unknown_obj(self, obj, level=0, nextline=True):
        return dict(generic_object=dict(type='{}.{}'.format(type(obj).__module__,
                                                            type(obj).__name__),
                                        overview=self._unknown_obj_overview(obj)))

    def _dump_as_proxy(self, proxy, obj, level=0, nextline=True):
        if proxy in ('list', 'set', 'tuple') or type(obj).__name__.startswith('FP'):
            return self._dump_unknown_obj(obj, level, nextline)
        else:
            return super(XmlDomDumper, self)._dump_as_proxy(proxy, obj, level, nextline)

    def _dump_obj_shortcut(self, obj, level=0, nextline=True):
        return dict(generic_object=dict(type='{}.{}'.format(type(obj).__module__,
                                                            type(obj).__name__),
                                        overview=obj.as_dump()))

    def _dump_class(self, obj, level=0, nextline=True):
        return {'class': super(XmlDomDumper, self)._dump_class(obj, level, nextline)}

    def _dump_builtin(self, obj, level=0, nextline=True):
        return {'builtin': super(XmlDomDumper, self)._dump_builtin(obj, level, nextline)}

    def _xdump_dict(self, xdoc, xroot, obj, myname):
        for k, v in obj.iteritems():
            if not isinstance(v, list):
                if myname in self._named_nodes:
                    xnode = xdoc.createElement(myname)
                    xnode.setAttribute('name', str(k))
                else:
                    if str(k) in self._named_nodes:
                        xnode = xroot
                    else:
                        xnode = xdoc.createElement(str(k))
            else:
                xnode = xroot
            self._xdump(xdoc, xnode, v, myname=str(k))
            if xnode is not xroot:
                xroot.appendChild(xnode)

    def _xdump_list(self, xdoc, xroot, obj, myname, topelt=False):
        for v in obj:
            if topelt:
                xnode = xdoc.createElement('generic_item')
            else:
                xnode = xdoc.createElement(myname)
            self._xdump(xdoc, xnode, v, myname=str(v), topelt=True)
            xroot.appendChild(xnode)

    def _xdump(self, xdoc, xroot, obj, myname, topelt=False):
        if isinstance(obj, list):
            self._xdump_list(xdoc, xroot, obj, myname, topelt=topelt)
        elif isinstance(obj, dict):
            self._xdump_dict(xdoc, xroot, obj, myname)
        else:
            # Generic case
            xroot.appendChild(xdoc.createTextNode(str(obj)))

    def dump(self, obj, root, rootattr=None, level=0, nextline=True):
        parent_dump = self._recursive_dump(obj, level, nextline)
        xdoc = minidom.Document()
        xroot = xdoc.createElement(root)
        if rootattr is not None and isinstance(rootattr, dict):
            for k, v in rootattr.iteritems():
                xroot.setAttribute(k, v)
        self._xdump(xdoc, xroot, parent_dump, myname=root, topelt=True)
        xdoc.appendChild(xroot)
        return xdoc


class TxtDumper(_AbstractDumper):

    def _dump_internal_dict(self, obj, level=0, nextline=True):
        parent_dump = super(TxtDumper, self)._dump_internal_dict(obj, level + 1, nextline)
        return "<<{:s}__dict__:: {!s}{:s}>>".format(indent(level + 1),
                                                    parent_dump,
                                                    indent(level))

    def _dump_as_proxy(self, proxy, obj, level=0, nextline=True):
        parent_dump = super(TxtDumper, self)._dump_as_proxy(proxy, obj, level + 1, nextline)
        return "<<{:s}as_{:s}:: {!s}{:s}>>".format(indent(level + 1),
                                                   proxy, parent_dump,
                                                   indent(level),)

    def _dump_unknown_obj(self, obj, level=0, nextline=True):
        return self._unknown_obj_overview(obj)

    def dump_default(self, obj, level=0, nextline=True):
        DEBUG('dump_default')
        if level + 1 > max_depth:
            return " <%s...>" % type(obj).__class__
        else:
            parent_dump = super(TxtDumper, self).dump_default(obj, level, nextline)
            return "{:s}.{:s}::{!s}".format(type(obj).__module__, type(obj).__name__,
                                            parent_dump)

    def dump_base(self, obj, level=0, nextline=True):
        DEBUG('dump base ' + type(obj).__name__)
        return "%s%s" % (indent(level, break_base), obj)

    dump_NoneType = dump_base
    dump_int = dump_base
    dump_long = dump_base
    dump_float = dump_base

    def dump_str(self, obj, level=0, nextline=True):
        DEBUG('dump_str', obj)
        return "%s'%s'" % (indent(level, break_string), obj)

    def dump_bool(self, obj, level=0, nextline=True):
        DEBUG('dump_bool', obj)
        return "%s%s" % (indent(level, break_bool), str(obj))

    def dump_tuple(self, obj, level=0, nextline=True):
        DEBUG('dump_tuple', obj)
        if level + 1 > max_depth:
            return "%s(...)%s" % (
                indent(level, break_before_tuple_begin),
                indent(level, break_after_tuple_end)
            )
        else:
            items = ["%s%s" % (indent(level + 1, break_before_tuple_item),
                               self._recursive_dump(x, level + 1))
                     for x in obj]
            return "%s(%s%s%s)%s" % (
                indent(level, nextline and break_before_tuple_begin),
                indent(level + 1, break_after_tuple_begin), ', '.join(items),
                indent(level, break_before_tuple_end),
                indent(level, break_after_tuple_end)
            )

    def dump_list(self, obj, level=0, nextline=True):
        DEBUG('dump_list', obj)
        if level + 1 > max_depth:
            return "%s[...]%s" % (
                indent(level, break_before_list_begin),
                indent(level, break_after_list_end)
            )
        else:
            items = ["%s%s" % (indent(level + 1, break_before_list_item),
                               self._recursive_dump(x, level + 1))
                     for x in obj]
            return "%s[%s%s%s]%s" % (
                indent(level, nextline and break_before_list_begin),
                indent(level + 1, break_after_list_begin), ', '.join(items),
                indent(level, break_before_list_end),
                indent(level, break_after_list_end)
            )

    def dump_set(self, obj, level=0, nextline=True):
        DEBUG('dump_set', obj)
        if level + 1 > max_depth:
            return "%sset([...])%s" % (
                indent(level, break_before_set_begin),
                indent(level, break_after_set_end)
            )
        else:
            items = [
                "%s%s" % (
                    indent(level + 1, break_before_set_item),
                    self._recursive_dump(x, level + 1)
                ) for x in obj
            ]
            return "%sset([%s%s%s])%s" % (
                indent(level, nextline and break_before_set_begin),
                indent(level + 1, break_after_set_begin), ', '.join(items),
                indent(level, break_before_set_end),
                indent(level, break_after_set_end)
            )

    def dump_dict(self, obj, level=0, nextline=True):
        DEBUG('dump_dict', obj)
        if level + 1 > max_depth:
            return "%s{...}%s" % (
                indent(level, break_before_dict_begin),
                indent(level, break_after_dict_end)
            )
        else:
            items = ["%s%s = %s%s," % (indent(level + 1, break_before_dict_key),
                                       # self.dump(k, level + 1),
                                       str(k),
                                       indent(level + 2, break_before_dict_value),
                                       self._recursive_dump(v, level + 1))
                     for k, v in sorted(obj.items())]
            breakdict = break_before_dict_end
            if not len(obj):
                breakdict = False
            return "%sdict(%s%s%s)%s" % (
                indent(level, nextline and break_before_dict_begin),
                indent(level + 1, break_after_dict_begin), ' '.join(items),
                indent(level, breakdict),
                indent(level, break_after_dict_end)
            )

    def cleandump(self, obj):
        """Clear cache dump and provide a top indented dump of the provided ``obj``."""
        parent_dump = super(TxtDumper, self).cleandump(obj)
        return indent_space * indent_first + parent_dump


def fulldump(obj, startpos=indent_first, reset=True):
    """Entry point. Return a string."""
    d = TxtDumper()
    if reset:
        d.reset()
    return indent_space * startpos + d.dump(obj)


def lightdump(obj, break_before_dict_key=True, break_before_dict_value=False):
    """Have a quick glance to an assumed 1-depth dictionary."""
    DEBUG('dump_dict', obj)
    items = [
        "%s%s = %s%s," % (
            indent(0, break_before_dict_key),
            str(k),
            indent(1, break_before_dict_value),
            str(v)
        ) for k, v in sorted(obj.items())
    ]
    return ''.join(items)
