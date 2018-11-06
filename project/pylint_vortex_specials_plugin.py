from __future__ import print_function, absolute_import, unicode_literals, division

from astroid import MANAGER
from astroid import scoped_nodes
from astroid import Instance

import os
import re
import six
import glob

VORTEXBASE = os.path.dirname(os.path.abspath(__file__))

HGEO_str = ('area', 'runit')
HGEO_num = ('nlon', 'nlat', 'ni', 'nj', 'resolution', 'truncation', 'stretching',)
HGEO_bool = ('lam', )
PRIORITIES = ('default', 'toolbox', 'olive', 'oper', 'debug', 'advanced', 'guru')


def register(linter):
    pass


def transform(cls):
    # Add some of the default attributes of geometry objects
    if cls.name == 'HorizontalGeometry':
        str_ast = MANAGER.ast_from_class(six.text_type)
        float_ast = MANAGER.ast_from_class(float)
        bool_ast = MANAGER.ast_from_class(bool)
        for attr in HGEO_str:
            cls.locals[attr] = [Instance(proxied=str_ast), ]
        for attr in HGEO_num:
            cls.locals[attr] = [Instance(proxied=float_ast), ]
        for attr in HGEO_bool:
            cls.locals[attr] = [Instance(proxied=bool_ast), ]
    # Pick routines in os, shutil and resource
    if cls.name == 'System':
        for proxymod in ('os', 'shutil', 'resource'):
            new_ast = MANAGER.ast_from_module_name(proxymod)
            for proxy_local, proxy_class_ast in new_ast.locals.items():
                if proxy_local not in cls.locals:
                    cls.locals[proxy_local] = proxy_class_ast
    # Some very common priorities
    if cls.name == 'PrioritySet':
        new_ast_mod = MANAGER.ast_from_module_name('footprints.priorities')
        new_ast = new_ast_mod.locals['PriorityLevel']
        new_ast = [Instance(proxied=one_ast_class) for one_ast_class in new_ast]
        for attr in PRIORITIES:
            cls.locals[attr.upper()] = new_ast
    # Contents: for a strange reason, the property is not recognised by pylint
    # ... we help a little bit
    if re.match('Almost(Dict|List)Content', cls.name):
        cls.instance_attrs['data'] = cls.instance_attrs['_data']


def transform_module(mod):
    # Add the collectors proxies
    if mod.name == 'vortex.proxy':
        tbfiles = glob.glob('{:s}/tbinterface_*.json'.format(VORTEXBASE))
        collectors = [re.sub(r'.*/tbinterface_([-_\w]+)\.json', r'\1', f)
                      for f in tbfiles]
        new_ast_mod = MANAGER.ast_from_module_name('footprints.collectors')
        new_ast = new_ast_mod.locals['Collector']
        new_ast = [Instance(proxied=one_ast_class) for one_ast_class in new_ast]
        for attr in collectors:
            mod.globals[attr] = new_ast
            mod.globals[attr + 's'] = new_ast


MANAGER.register_transform(scoped_nodes.Class, transform)
MANAGER.register_transform(scoped_nodes.Module, transform_module)
