from astroid import MANAGER
from astroid import scoped_nodes
from astroid import Instance
import __builtin__
import glob
import os
import sys
import json

VORTEXBASE = os.path.dirname(os.path.abspath(__file__))

_FP_EXPORT = []


def register(linter):
    # First, read the footprint dumps Json files
    for colfile in glob.glob('{:s}/tbinterface_*.json'.format(VORTEXBASE)):
        with open(colfile, 'r') as fd:
            _FP_EXPORT.append(json.load(fd))


def _footprint_members_add(cls):
    fname = '{:s}.{:s}'.format(cls.root().name, cls.name)
    thefp = None
    # Find the collector
    for coldata in _FP_EXPORT:
        if fname in coldata:
            thefp = coldata[fname]['footprint']
    if thefp is not None:
        # Loop on footprint attributes
        for attr, desc  in thefp['attr'].iteritems():

            thetype = desc.get('type', 'str')
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
                cls.locals[attr] = ast_class

            # If it's a builtin type that's good !
            else:
                module = __builtin__
                theclass = thetype
                try:
                    theclass = getattr(module, theclass)
                except AttributeError:
                    # That's bad: go ahead but does nothing
                    sys.stderr.write('{:s} not found in {!r}\n'.format(theclass, module))
                    continue
                ast_class = MANAGER.ast_from_class(theclass)
                # Register the new AST node
                cls.locals[attr] = [Instance(proxied=ast_class), ]


def transform(cls):
    for ancestor in cls.ancestors():
        # Only works on classes based on FootprintBase
        if ancestor.name == 'FootprintBase':
            _footprint_members_add(cls)
            break

MANAGER.register_transform(scoped_nodes.Class, transform)