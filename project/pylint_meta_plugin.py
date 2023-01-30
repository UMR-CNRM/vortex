"""
A pylint plugin that combine several useful things for Vortex.
"""

from astroid import MANAGER
from astroid import scoped_nodes
from astroid import Instance
import builtins
import glob
import os
import re
import sys
import json

VORTEXBASE = os.path.dirname(os.path.abspath(__file__))

HGEO_str = ('area', 'runit')
HGEO_num = ('nlon', 'nlonmax', 'lonmin', 'nlat', 'latmin', 'ni', 'nj', 'resolution', 'truncation', 'stretching',)
HGEO_bool = ('lam', )
PRIORITIES = ('default', 'toolbox', 'olive', 'oper', 'debug', 'advanced', 'guru')

_FP_EXPORT = []


def _footprint_members_add(cls):
    fname = '{:s}.{:s}'.format(cls.root().name, cls.name)
    thefp = None
    # Find the collector
    for coldata in _FP_EXPORT:
        if fname in coldata:
            thefp = coldata[fname]['footprint']
            break
    if thefp is not None:
        # Loop on footprint attributes
        for attr, desc in thefp['attr'].items():

            thetype = desc.get('type', str.__name__)

            # If the attribute is a complex type, try to load the
            # module's AST
            if '.' in thetype:
                module = '.'.join(thetype.split('.')[:-1])
                theclass = thetype.split('.')[-1]
                ast_mod = MANAGER.ast_from_module_name(module)
                try:
                    ast_class = ast_mod.locals[theclass]
                except ImportError:
                    # That's bad: go ahead but does nothing
                    sys.stderr.write('{!r} could not be found in {!r}\n'.format(thetype,
                                                                                module))
                    continue
                # Recursive if ast_class is a footprint...
                for one_ast_class in ast_class:
                    for ancestor in one_ast_class.ancestors():
                        # Only works on classes based on FootprintBase
                        if ancestor.name == 'FootprintBase':
                            _footprint_members_add(one_ast_class)
                            break
                # Register the new AST node
                if not desc.get('isclass', False):
                    ast_class = [Instance(proxied=one_ast_class) for one_ast_class in ast_class]
                cls.instance_attrs[attr] = ast_class

            # If it's a builtin type that's good !
            else:
                module = builtins
                theclass = thetype
                try:
                    theclass = getattr(module, theclass)
                except AttributeError:
                    # That's bad: go ahead but does nothing
                    sys.stderr.write('{:s} not found in {!r}. For {!s}.\n'.format(theclass, module, thefp))
                    continue
                ast_class = MANAGER.ast_from_class(theclass)
                # Register the new AST node
                cls.instance_attrs[attr] = [Instance(proxied=ast_class), ]


def _tweak_specials(cls):
    ast_manager = MANAGER
    # Add some of the default attributes of geometry objects
    if cls.name == 'HorizontalGeometry':
        str_ast = ast_manager.ast_from_class(str)
        float_ast = ast_manager.ast_from_class(float)
        bool_ast = ast_manager.ast_from_class(bool)
        for attr in HGEO_str:
            cls.instance_attrs[attr] = [Instance(proxied=str_ast), ]
        for attr in HGEO_num:
            cls.instance_attrs[attr] = [Instance(proxied=float_ast), ]
        for attr in HGEO_bool:
            cls.instance_attrs[attr] = [Instance(proxied=bool_ast), ]
    # Pick routines in os, shutil and resource
    if cls.name == 'System':
        for proxymod in ('os', 'shutil', 'resource'):
            new_ast = ast_manager.ast_from_module_name(proxymod)
            for proxy_local, proxy_class_ast in new_ast.locals.items():
                if proxy_local not in cls.locals:
                    cls.locals[proxy_local] = proxy_class_ast
    # Some very common priorities
    if cls.name == 'PrioritySet':
        new_ast_mod = ast_manager.ast_from_module_name('footprints.priorities')
        new_ast = new_ast_mod.locals['PriorityLevel']
        new_ast = [Instance(proxied=one_ast_class) for one_ast_class in new_ast]
        for attr in PRIORITIES:
            cls.instance_attrs[attr.upper()] = new_ast
    # Contents: for a strange reason, the property is not recognised by pylint
    # ... we help a little bit
    if re.match('Almost(Dict|List)Content', cls.name):
        cls.instance_attrs['data'] = cls.instance_attrs['_data']


def transform_classes(cls):
    for ancestor in cls.ancestors():
        # Only works on classes based on FootprintBase
        if ancestor.name == 'FootprintBase':
            _footprint_members_add(cls)
            break
    _tweak_specials(cls)


def transform_modules(mod):
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


def register(linter):
    # First, read the footprint dumps Json files
    for colfile in glob.glob('{:s}/tbinterface_*.json'.format(VORTEXBASE)):
        with open(colfile, 'rb') as fd:
            _FP_EXPORT.append(json.load(fd))
    MANAGER.register_transform(scoped_nodes.ClassDef, transform_classes)
    MANAGER.register_transform(scoped_nodes.Module, transform_modules)
