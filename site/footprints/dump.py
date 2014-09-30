#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
Data dumper... mostly used in objects' docstring with a footprint.
"""

#: No automatic export
__all__ = []

from types import *  # @UnusedWildImport

from . import util


def DEBUG(msg, obj=None, level=None):
    """Fake method for debug purpose (then should provide a print statement)."""
    #print msg, str(obj)
    pass

max_depth = 99

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

DICT_TYPES = {DictionaryType: 1}


def atomic_type(t):
    return t in (NoneType, StringType, IntType, LongType, FloatType, ComplexType)


def is_instance(val):
    if type(val) is InstanceType:
        return True
    # instance of extension class, but not an actual extension class
    elif (hasattr(val, '__class__') and
          hasattr(val, '__dict__') and
          not hasattr(val, '__bases__')):
        return True
    else:
        return False


def is_class(val):
    return hasattr(val, '__bases__')


def simple_value(val):
    t = type(val)

    if atomic_type(val):
        return True

    if t not in DICT_TYPES and t not in (ListType, TupleType) and not is_instance(val):
        return True
    elif t in (ListType, TupleType) and len(val) <= 10:
        for x in val:
            if not atomic_type(type(x)):
                return False
        return True
    elif t in DICT_TYPES and len(val) <= 5:
        for (k, v) in val.items():
            if not (atomic_type(type(k)) and atomic_type(type(v))):
                return False
        return True
    else:
        return False


def indent(level=0, nextline=True):
    if nextline:
        return "\n" + indent_space * ( indent_first + indent_size * level )
    else:
        return ""


def get(**kw):
    """Return actual dumper object matching description."""
    return Dumper.get(**kw)

class Dumper(util.GetByTag):
    """Could dump almost anything."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.seen = dict()

    def dump_default(self, obj, level=0, nextline=True):
        DEBUG('dump_default')
        if level + 1 > max_depth:
            return " <%s...>" % type(obj).__class__
        else:
            result = "%s::%s <<" % (type(obj).__name__, obj.__class__)
            if hasattr(obj, '__dict__'):
                if hasattr(obj, 'as_dict'):
                    exploredict = obj.as_dict()
                else:
                    exploredict = obj.__dict__
                result = "%s%s__dict__ :: %s" % (
                    result,
                    indent(level+1),
                    self.dump_dict(exploredict, level+1)
                )

            if isinstance(obj, dict):
                result = "%s%sas_dict :: %s" % (
                    result,
                    indent(level+1),
                    self.dump_dict(obj, level+1)
                )
            elif isinstance(obj, list):
                result = "%s%sas_list :: %s" % (
                    result,
                    indent(level+1),
                    self.dump_list(obj, level+1)
                )

            result = "%s%s>>" % (result, indent(level))

        return result

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
            items = ["%s%s" % (
                    indent(level + 1, break_before_tuple_item),
                    self.dump(x, level + 1)
                ) for x in obj
            ]
            return "%s(%s%s%s)%s" % (
                indent(level, nextline and break_before_tuple_begin),
                indent(level + 1, break_after_tuple_begin), ', '.join(items),
                indent(level, break_before_tuple_end),
                indent(level, break_after_tuple_end)
            )

    def dump_list(self, obj, level=0, nextline=True):
        DEBUG('dump_list', obj)
        if level + 1 > max_depth:
            exit()
            return "%s[...]%s" % (
                indent(level, break_before_list_begin),
                indent(level, break_after_list_end)
            )
        else:
            items = ["%s%s" % (
                    indent(level + 1, break_before_list_item),
                    self.dump(x, level + 1)
                ) for x in obj
            ]
            return "%s[%s%s%s]%s" % (
                indent(level, nextline and break_before_list_begin),
                indent(level + 1, break_after_list_begin), ', '.join(items),
                indent(level, break_before_list_end),
                indent(level, break_after_list_end)
            )

    def dump_set(self, obj, level=0, nextline=True):
        DEBUG('dump_set', obj)
        if level + 1 > max_depth:
            exit()
            return "%sset([...])%s" % (
                indent(level, break_before_set_begin),
                indent(level, break_after_set_end)
            )
        else:
            items = [
                "%s%s" % (
                    indent(level + 1, break_before_set_item),
                    self.dump(x, level + 1)
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
            items = ["%s%s = %s%s," % (
                    indent(level + 1, break_before_dict_key),
                    #self.dump(k, level + 1),
                    str(k),
                    indent(level + 2, break_before_dict_value),
                    self.dump(v, level + 1)
                ) for k, v in sorted(obj.items())
            ]
            breakdict = break_before_dict_end
            if not len(obj):
                breakdict = False
            return "%sdict(%s%s%s)%s" % (
                indent(level, nextline and break_before_dict_begin),
                indent(level + 1, break_after_dict_begin), ' '.join(items),
                indent(level, breakdict),
                indent(level, break_after_dict_end)
            )

    def dump(self, obj, level=0, nextline=True):
        DEBUG('dump top', obj)

        if self.seen.has_key(id(obj)):
            return self.seen[id(obj)]

        if is_instance(obj) and hasattr(obj, 'dumpshortcut'):
            DEBUG('dump shortcut', obj)
            self.seen[id(obj)] = obj.dumpshortcut()
            return self.seen[id(obj)]

        if is_class(obj):
            if obj.__module__ == '__builtin__':
                DEBUG('builtin')
                self.seen[id(obj)] = obj.__name__
            else:
                DEBUG('class ' + str(obj))
                self.seen[id(obj)] = '{0:s}.{1:s}'.format(obj.__module__, obj.__name__)
            return self.seen[id(obj)]

        name = type(obj).__name__
        dump_func = getattr(self, "dump_%s" % name, self.dump_default)
        return dump_func(obj, level, nextline)

    def cleandump(self, obj):
        """Clear cache dump and provide a top indented dump of the provided ``obj``."""
        self.reset()
        return indent_space * indent_first + self.dump(obj)


def fulldump(obj, startpos=indent_first, reset=True):
    """Entry point. Return a string."""
    d = Dumper()
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
