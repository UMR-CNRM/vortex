#!/usr/bin/env python3

"""
Run various code checkers on the Vortex' repository.
"""

import abc
from argparse import ArgumentParser, RawDescriptionHelpFormatter
import concurrent.futures
import logging
import os
import re
import sys
import typing

import astroid
import pycodestyle
import pydocstyle
import yaml


logging.basicConfig()
logger = logging.getLogger()

# The present Vortex code repository location
_VTXBASE = re.sub('{0:}project{0:}bin$'.format(os.path.sep), '',
                  os.path.dirname(os.path.realpath(__file__)))

# Default configuration file location
_CONF_DIR = os.path.join(_VTXBASE, 'project', 'conf')
_CONF_DEFAULT = 'vortex_codechecker.yaml'

# The packages available in Vortex' src
_VTXPACKAGES = {sditem.name
                for sditem in os.scandir(os.path.join(_VTXBASE, 'src'))
                if (sditem.is_dir() and
                    os.path.exists(os.path.join(_VTXBASE, 'src', sditem.name, '__init__.py')))}


# VERY GENERIC UTILITY METHODS -----------------------------------------------

def _property_auto_add(* what):
    """Automatically add property to expose read only attributes listed in **what."""

    class RoAttrDescriptor:
        """Abstract accessor class to read-only attributes."""

        def __init__(self, attr, doc=None):
            self._attr = attr
            self.__doc__ = doc if doc else 'The {:s} attribute'.format(self._attr)

        def __get__(self, obj, objtype=None):  # @UnusedVariable
            return getattr(obj, '_' + self._attr)

    def _property_auto_add_deco(cls):
        for item in what:
            setattr(cls, item, RoAttrDescriptor(item))
        return cls
    return _property_auto_add_deco


# UTILITY CLASS REPRESENTING A PYTHON CODE THAT SHOULD BE ANALYSED -----------

@_property_auto_add('path', 'shortpath', 'fpdetect')
class VortexPythonCode:
    """The content of a Vortex' Python code file."""

    def __init__(self, path: str, shortpath: str, fpdetect: bool):
        """Ingest the code and detect footprint definitions if need be.

        :param path: The absolute path to a code file
        :param shortpath: Path relative to the vortex repository root
        :param fpdetect: Try to detect footprints declarations
        """
        self._path = path
        self._shortpath = shortpath
        self._fpdetect = fpdetect
        self._code = None
        self._codelist = None
        self._p_astroid = None
        self._fplines = None
        self._expanded_fplines = None
        self._slices_locations = None

    @property
    def code(self):
        """Read the source file and returns it as a string."""
        if self._code is None:
            with open(self._path, encoding='utf-8') as fhcode:
                self._code = fhcode.read()
        return self._code

    @property
    def codelist(self):
        """Return the source code as an array of one-line strings."""
        if self._codelist is None:
            self._codelist = self.code.split('\n')
        return self._codelist

    @property
    def p_astroid(self):
        """Return the code parsed by astroid."""
        if self._p_astroid is None:
            try:
                self._p_astroid = astroid.parse(self.code)
            except astroid.AstroidError:
                logger.error('There is probably a syntax error in %s. Check your code !', self.path)
                raise
        return self._p_astroid

    @property
    def fplines(self):
        """The list of line ranges that encompasses footprint definitions."""
        if self._fplines is None:
            self._do_fpinit()
        return self._fplines

    @property
    def expanded_fplines(self):
        """The set of lines that encompasses footprint definitions."""
        if self._expanded_fplines is None:
            self._do_fpinit()
        return self._expanded_fplines

    def _do_fpinit(self):
        """Initialise the _fplines and _expanded_fplines data."""
        self._fplines = list()
        self._expanded_fplines = set()
        if self._fpdetect:
            self._do_fpdetect()

    def _do_fpdetect(self):
        """Actualy detect footprints using astroid."""
        for node in self.p_astroid.values():
            # Look only for Class definition
            if isinstance(node, astroid.ClassDef):
                # Crawl into the class content
                for cnode in node.body:
                    # We are only interested in assignments
                    if isinstance(cnode, astroid.Assign):
                        # Look for an assignment target named "_footprint"
                        for target in [tnode for tnode in cnode.targets
                                       if isinstance(tnode, astroid.AssignName)]:
                            if target.name == '_footprint':
                                self._fplines.append((cnode.lineno, cnode.tolineno))

        if self._fplines:
            logger.debug('Found footprint defs in %s: %s', self.path,
                         ", ".join(['({:d}, {:d})'.format(fpl[0], fpl[1])
                                    for fpl in self._fplines]))
            # Expand the _footprint definition line numbers
            for fplines in [range(s, e + 1) for (s, e) in self._fplines]:
                self._expanded_fplines.update(fplines)

    def _slices_recurse(self, asttree):
        slices = set()
        for node in asttree.get_children():
            if isinstance(node, astroid.Slice):
                slices.add((node.fromlineno, node.tolineno))
            else:
                slices.update(self._slices_recurse(node))
        return slices

    @property
    def slices_locations(self):
        """
        Return a set of tuple that indicate line interval where slice
        definitions are detected.
        """
        if self._slices_locations is None:
            self._slices_locations = self._slices_recurse(self.p_astroid)
        return self._slices_locations


# DEFINITON OF CHECKER CLASSES -----------------------------------------------

# Any checker's __call__ method should return a list of errors represented by
# a tuple that contains (line number, error_message).
CheckerErrorsList = typing.List[typing.Tuple[int, str]]


class MyPycodestyleReporter(pycodestyle.BaseReport):
    """Store the pycodestyle messages for later use...

    Internal use by the :class:`PycodestyleChecker` class.
    """

    def init_file(self, filename, lines, expected, line_offset):
        """Signal a new file."""
        self._deferred_messages = []
        return super().init_file(
            filename, lines, expected, line_offset)

    def error(self, line_number, offset, text, check):
        """Report an error, according to options."""
        code = super().error(line_number, offset, text, check)
        if code:
            self._deferred_messages.append(
                (line_number, offset, code, text[5:], check.__doc__))
        return code

    @property
    def rawmessages(self):
        """The whole bunch of error messages (for a given file)."""
        return self._deferred_messages


class PycodestyleChecker:
    """Check the source code using pycodestyle."""

    _RESFMT = '{:s}-{:4s}  l.{:4d}.{:-3d}: {:s}'

    def __init__(self, **kwargs):
        """Keep track of pycodechecker arguments."""
        self._pcs_style_args = kwargs

    def _parse_results(self, vpycode: VortexPythonCode, label: str,
                       result: MyPycodestyleReporter) -> CheckerErrorsList:
        """Print the error messages but filter footprint related messages first."""
        errors = list()
        for message in result.rawmessages:
            # Ignore some errors while working in footprints
            if (message[2] in ['E221', 'E251'] and
                    message[0] in vpycode.expanded_fplines):
                continue
            # PyCodeStyle detects false positives in slices.
            # See: https://github.com/psf/black/blob/master/README.md#line-breaks--binary-operators
            # This is annoying... try to prevent this issue
            if (message[2] in ['E203'] and
                    (any([message[0] in set(range(lines[0], lines[1] + 1))
                          for lines in vpycode.slices_locations])) and
                    not (any([message[0] == lines[1]
                              for lines in vpycode.slices_locations]) and
                         re.match(r'[^:]*:[^]]*$',
                                  vpycode.codelist[message[0] - 1][message[1]:]))):
                continue
            errors.append((message[0], self._RESFMT.format(label, message[2],
                                                           message[0], message[1],
                                                           message[3],)))
        return errors

    def __call__(self, vpycode: VortexPythonCode, label: str) -> CheckerErrorsList:
        """Run the check on **vpycode**."""
        pcs_options = self._pcs_style_args.copy()
        try:
            pcs_style = pycodestyle.StyleGuide(reporter=MyPycodestyleReporter, **pcs_options)
            result = pcs_style.check_files([vpycode.path, ])
        except Exception:
            logger.error('with %s, pycodestyle failed with the following options:\n%s',
                         vpycode.path, pcs_options)
            raise
        return self._parse_results(vpycode, label, result)


class PydocstyleChecker:
    """Check the source code using pydocstyle."""

    _RESFMT = '{:s}-{:4s}  l.{:4d}    : {!s}: {!s}'

    def __init__(self, **kwargs):
        self._checkopts = kwargs
        self._convention = self._checkopts.pop('convention', None)
        if self._convention is not None:
            convention_incl = pydocstyle.conventions[self._convention]
            incl = convention_incl | set(self._checkopts.get('select', {}))
            self._checkopts['select'] = incl
        if 'ignore' in self._checkopts and 'select' in self._checkopts:
            ignore_set = set(self._checkopts.pop('ignore', {}))
            self._checkopts['select'] = self._checkopts['select'] - ignore_set

    def __call__(self, vpycode: VortexPythonCode, label: str) -> CheckerErrorsList:
        """Run the check on **vpycode**."""
        errors = list()
        try:
            pydocchecker = pydocstyle.check([vpycode.path, ], **self._checkopts)
        except Exception:
            logger.error('with %s, pydocstyle failed with the following options:\n%s',
                         vpycode.path, self._checkopts)
            raise
        for error in pydocchecker:
            errors.append((error.line,
                           self._RESFMT.format(label, error.code, error.line,
                                               error.definition, error.message[6:])))
        return errors


DictOfImports = typing.Dict[str, typing.Tuple[int, str]]
SetOfNames = typing.Set[str]


class AstroidChecker:
    """Check the source code for unused imports using astroid."""

    _RESFMT_I = '{:s}-imp   l.{:4d}    : {!s}'
    _RESFMT_B = '{:s}-bbla  l.XXXX    : {!s}'
    _UI_MSG = 'unused import "{:s}" (as "{:s}").'
    _BL_MSG = 'blacklisted import (should never be used in Vortex) "{:s}".'
    _DE_MSG = 'deprecated import "{:s}". Use "{:s}" instead.'
    _BB_MSG = 'blacklisted builtin "{:s}" ({:s})'

    def __init__(self,
                 importuse_overall_whitelist=None,
                 importuse_local_whitelist=None,
                 importblacklist=None,
                 importdeprecated=None,
                 builtinblacklist=None):
        self._o_whitelist = (set(importuse_overall_whitelist)
                             if importuse_overall_whitelist else set())
        self._l_whitelist = (dict(importuse_local_whitelist)
                             if importuse_local_whitelist else dict())
        self._blacklist = dict(importblacklist) if importblacklist else dict()
        self._deprecated = dict(importdeprecated) if importdeprecated else dict()
        self._builtin_bl = dict(builtinblacklist) if builtinblacklist else dict()

    def _astroid_imports_tree_recurse(self,
                                      tree: astroid.node_classes.NodeNG,
                                      imports: DictOfImports,
                                      l_whitelist: typing.Set[str]):
        """Identify all the import statements in a given source tree.

        Whitelisted imports are not taken into account.
        """

        def filter_imports(node: typing.Union[astroid.Import, astroid.ImportFrom]):
            """Deal with any Import/ImportFrom astroid node."""
            what = dict()
            for name in node.names:
                origname = name[0]
                if isinstance(node, astroid.ImportFrom):
                    origname = node.modname + '.' + origname
                targetname = name[1] or name[0]
                if (name[0] == '*' or origname in _VTXPACKAGES or
                        origname in self._o_whitelist or
                        origname in l_whitelist):
                    continue
                what[targetname] = (node.lineno, origname)
            return what

        # Explore the whale source tree recursively
        for node in tree.get_children():
            if isinstance(node, astroid.Import):
                imports.update(filter_imports(node))
            elif (isinstance(node, astroid.ImportFrom) and
                  node.modname not in ('__future__')):
                imports.update(filter_imports(node))
            else:
                self._astroid_imports_tree_recurse(node, imports, l_whitelist)

    def _astroid_attr_recurse(self, attr: astroid.node_classes.NodeNG) -> str:
        """Parse recursively any Attribute astroid node.

        This may fail and return ``None``
        """
        if isinstance(attr.expr, astroid.Attribute):
            base = self._astroid_attr_recurse(attr.expr)
            return (base if base is None else
                    '{:s}.{:s}'.format(base, attr.attrname))
        elif isinstance(attr.expr, astroid.Name):
            return '{:s}.{:s}'.format(attr.expr.name, attr.attrname)
        else:
            return None

    def _astroid_names_tree_recurse(self,
                                    tree: astroid.node_classes.NodeNG,
                                    names: SetOfNames):
        """
        Parse recursively the whole source tree looking for names that are
        actualy used.
        """
        for node in tree.get_children():
            if isinstance(node, (astroid.Import, astroid.ImportFrom)):
                continue
            elif isinstance(node, (astroid.AssignAttr, astroid.Attribute)):
                attr = self._astroid_attr_recurse(node)
                if attr:
                    names.add(attr)
            elif isinstance(node, (astroid.AssignName, astroid.Name)):
                names.add(node.name)
            self._astroid_names_tree_recurse(node, names)

    def _newresult_i(self, label, import_item, msgfmt, *args):
        return (import_item[0],
                self._RESFMT_I.format(label, import_item[0], msgfmt.format(* args)))

    def _newresult_b(self, label, msgfmt, *args):
        return (0,
                self._RESFMT_B.format(label, msgfmt.format(* args)))

    def __call__(self, vpycode: VortexPythonCode, label: str) -> CheckerErrorsList:
        """Run the check on **vpycode**."""
        astp = vpycode.p_astroid
        errors = []
        # import whitelist for this specific code file
        l_whitelist = set(self._l_whitelist.get(vpycode.shortpath, ()))
        # Check for unused imports (ignore __init__.py files)
        if os.path.basename(vpycode.path) != '__init__.py':
            imports: DictOfImports = dict()
            names: SetOfNames = set()
            self._astroid_imports_tree_recurse(astp, imports, l_whitelist)
            self._astroid_names_tree_recurse(astp, names)
            # Unused code
            errors.extend([self._newresult_i(label, imports[imp], self._UI_MSG,
                                             imports[imp][1], imp)
                           for imp in set(imports.keys()) - names])
            # Blacklisted modules
            for bmod, excl in self._blacklist.items():
                if (vpycode.shortpath not in excl):
                    errors.extend([self._newresult_i(label, iitem, self._BL_MSG, iitem[1])
                                   for imp, iitem in imports.items()
                                   if re.match('^' + bmod + r'(\.|$)', iitem[1])])
            # Decprecated modules
            for dmod, repl in self._deprecated.items():
                errors.extend([self._newresult_i(label, iitem, self._DE_MSG, iitem[1], repl)
                               for imp, iitem in imports.items()
                               if re.match(dmod + r'(\.|$)', imports[imp][1])])
            # Builtin blacklist
            for bblt, desc in self._builtin_bl.items():
                if bblt in names and bblt not in imports and vpycode.shortpath not in desc['whitelist']:
                    errors.append(self._newresult_b(label, self._BB_MSG, bblt, desc['why']))
        return errors


_AVAILABLE_CHECKERS = dict(
    pycodestyle=PycodestyleChecker,
    pydocstyle=PydocstyleChecker,
    astroidcheck=AstroidChecker,
)

_ARGPARSE_EPILOG = """
Various checker are available:
{:s}

The default configuration file is:
  {:s}
Take a look inside it to see how and where the various checkers are used.

New checker can easily be created by creating a dedicated class that:
- accepts keyword options (that may be specified in the configuration file in
  its checkconfig sections) through the __init__ method;
- defines a __call__ method that accepts a *vpycode* argument that is a
  VortexPythonCode object representing the file to be analysed and a *label*
  argument that will be used when generating error messages.
""".format("\n".join(['- {:s}: {:s}'.format(k, v.__doc__.split("\n")[0])
                      for k, v in _AVAILABLE_CHECKERS.items()]),
           os.path.join(_CONF_DIR, _CONF_DEFAULT))


# DEFINITON OF UTILITY CLASSES TO PARSE THE CONFIG FILE AND CRAWL INTO FILES --


class _AnyConfigEntry:
    """handle any kind of configuration data read from the YAML file."""

    __metaclass__ = abc.ABCMeta

    _MANDATORY_ENTRIES: typing.Set[str] = set()
    _ALLOWED_ENTRIES: typing.Set[str] = set()
    _CLASS_LABEL = 'to_be_changed'

    @abc.abstractmethod
    def __init__(self, name: str, description: dict):
        """Check the description dictionary content."""
        if not isinstance(description, dict):
            raise ValueError('The {:s} {:s} description must be a dictionary'
                             .format(name, self._CLASS_LABEL))
        dkeys = set(description.keys())
        if not self._MANDATORY_ENTRIES <= dkeys:
            raise ValueError('Missing mandatory keys in the {:s} {:s} description'
                             .format(name, self._CLASS_LABEL))
        if not dkeys <= self._MANDATORY_ENTRIES | self._ALLOWED_ENTRIES:
            raise ValueError('Unknown keys in the {:s} {:s} description'
                             .format(name, self._CLASS_LABEL))

        logger.debug('New %s creation: %s -> %s', self._CLASS_LABEL, name, description)


@_property_auto_add('checkers', 'label')
class CheckConfig(_AnyConfigEntry):
    """Holds information on a given **checkconfigs** entry."""

    _MANDATORY_ENTRIES = {'checkers', 'label'}
    _CLASS_LABEL = 'checkconfig'

    def __init__(self, name: str, description: dict):
        """Create the configuration object starting form its **description**."""
        super().__init__(name, description)
        # Process the definition
        self._label = description['label']
        self._checkers = list()
        for checker in description['checkers']:
            if checker.get('type', None) not in _AVAILABLE_CHECKERS:
                raise ValueError('The {!s} checker is unavailable'.format(checker))
            checker_args = checker.copy()
            del checker_args['type']
            try:
                self.checkers.append(_AVAILABLE_CHECKERS.get(checker['type'])(** checker_args))
            except Exception:
                logger.error('Could not create the %s checker using the following attributes:\n %s',
                             checker['type'], checker_args)
                raise


DictOfCheckConfigs = typing.Dict[str, CheckConfig]

SetOfPlacesLocations = typing.Set[str]


@_property_auto_add('path', 'shortpath', 'fpdetect', 'checkconfigs')
class VortexPlace(_AnyConfigEntry):
    """Handle a given **place** entry of the configuration file."""

    _MANDATORY_ENTRIES = {'path', 'checkconfigs', }
    _ALLOWED_ENTRIES = {'footprints_detect', }
    _CLASS_LABEL = 'place'

    def __init__(self, name: str, description: dict,
                 checkconfigs: DictOfCheckConfigs, vortexpath: str):
        """Parse the **decription** read in the YAML configuration file."""
        super().__init__(name, description)
        self._path = os.path.join(vortexpath, description['path'])
        self._shortpath = description['path']
        self._fpdetect = bool(description.get('footprints_detect', False))
        self._checkconfigs: typing.List[CheckConfig] = list()
        for checkconfig in description['checkconfigs']:
            if checkconfig not in checkconfigs:
                raise ValueError('Improper {:s} checker value'.format(description['checkconfig']))
            self._checkconfigs.append(checkconfigs[checkconfig])

    def _pycode_crawl(self, path: str, shortpath: str, places_paths: SetOfPlacesLocations
                      ) -> typing.Iterator[VortexPythonCode]:
        """Actualy iterate over **path**."""
        for item in os.scandir(path):
            fullpath = os.path.join(path, item.name)
            new_shortpath = os.path.join(shortpath, item.name)
            if item.name.endswith('.py') and item.is_file():
                yield VortexPythonCode(fullpath, new_shortpath, self.fpdetect)
            elif item.name != '__pycache__' and item.is_dir():
                if fullpath not in places_paths:
                    yield from self._pycode_crawl(fullpath, new_shortpath, places_paths)

    def iter_pycode(self, places_paths: SetOfPlacesLocations
                    ) -> typing.Iterator[VortexPythonCode]:
        """
        Iterate through all the python's files of the place and returns
        :class:`VortexPythonCode` objects.
        """
        return self._pycode_crawl(self.path, self.shortpath, places_paths)

    def check_pycode(self, vpc: VortexPythonCode) -> CheckerErrorsList:
        """Check a given code file (represented as a VortexPythonCode object)."""
        logger.info('Dealing with the %s file.', vpc.path)
        errors: CheckerErrorsList = list()
        for checkconfig in self.checkconfigs:
            for checker in checkconfig.checkers:
                errors.extend(checker(vpc, checkconfig.label))
        return errors

    def summarize_pycode(self,
                         vpc_name: str, errors: CheckerErrorsList,
                         rfilter: typing.Union[None, re.Pattern]) -> int:
        """Print the errors summary.

        :return: The number of errors
        """
        errors = [err for err in errors
                  if not rfilter or rfilter.match(err[1])]
        if errors:
            print('=== ' + vpc_name + ' ===')
            for errordesc in sorted(errors):
                print('    ' + errordesc[1])
        return len(errors)


DictOfPlaces = typing.Dict[str, VortexPlace]


class CheckerConfig:
    """Gives access to this checker config file."""

    def __init__(self, configfile: str, vortexpath: str, configdir: str = None):
        """Load the checker config file.

        :param configfile: The configuration file path
        :param configdir: The place where configuration file are stored by default
                          (this is used only if *configfile* starts with ``@``).
        """
        self._vortexpath = vortexpath
        # Find out the config file location
        if configdir is None:
            configdir = _CONF_DIR
        if configfile.startswith('@'):
            self._file = os.path.join(configdir, configfile.lstrip('@'))
        else:
            self._file = configfile
        logger.info('Configuration file in use: %s', self._file)
        if not os.path.exists(self._file):
            raise OSError("The configuration file {:s} is missing.".format(self._file))
        # Load the yaml configuration file
        with open(self._file, encoding='utf-8') as fhconf:
            try:
                self._confdata = yaml.load(fhconf, yaml.SafeLoader)
            except yaml.YAMLError:
                logger.info('An error occurred while parsing: %s', self._file)
                raise
        # Basic checks
        if not isinstance(self._confdata, dict):
            raise ValueError('Configuration must be a dictionary')
        conf_l1_entries = {'places', 'checkconfigs'}
        if set(self._confdata.keys()) != conf_l1_entries:
            raise ValueError('Configuration must have exactly the following entries: {:s}'
                             .format(','.join(conf_l1_entries)))
        # Cache
        self._places: typing.Union[None, DictOfPlaces] = None
        self._places_paths: typing.Union[None, SetOfPlacesLocations] = None
        self._checkconfigs: typing.Union[None, DictOfCheckConfigs] = None

    @property
    def vortexpath(self) -> str:
        """The place where the vortex directory lies."""
        return self._vortexpath

    @property
    def checkconfigs(self) -> DictOfCheckConfigs:
        """The dict of available check configurations."""
        if self._checkconfigs is None:
            self._checkconfigs = {n: CheckConfig(n, c)
                                  for n, c in self._confdata['checkconfigs'].items()}
        return self._checkconfigs

    @property
    def places(self) -> DictOfPlaces:
        """The dict of places where to run the code check."""
        if self._places is None:
            self._places = {n: VortexPlace(n, p, self.checkconfigs, self.vortexpath)
                            for n, p in self._confdata['places'].items()}
        return self._places

    @property
    def places_paths(self) -> SetOfPlacesLocations:
        """The list of code directories that will be checked."""
        if self._places_paths is None:
            self._places_paths = {p.path for p in self.places.values()}
        return self._places_paths


# DEAL WITH THE COMMAND LINE AND RUN THE TESTS --------------------------------

def main():
    """Process command line options."""

    program_name = os.path.basename(sys.argv[0])
    program_shortdesc = program_name + ' -- ' + __import__('__main__').__doc__.lstrip("\n")
    program_desc = program_shortdesc

    # Setup argument parser
    parser = ArgumentParser(description=program_desc, epilog=_ARGPARSE_EPILOG,
                            formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("places", nargs='*',
                        help="test only the following places... (all if omitted).")
    parser.add_argument("-v", "--verbose", dest="verbose", action="count",
                        default=0, help="Set verbosity level [default: %(default)s]")
    parser.add_argument("-n", "--nprocs", dest="nprocs", action="store", type=int,
                        help=("The number of processes to use during the check "
                              "(by default the number of CPUs on the machine)"))
    parser.add_argument("-c", "--config", dest="config", action="store",
                        default='@' + _CONF_DEFAULT,
                        help="Configuration file location [default: %(default)s]")
    parser.add_argument("-p", "--vortexpath", dest="vortexpath", action="store",
                        default=_VTXBASE,
                        help="Vortex repository location [default: %(default)s]")
    parser.add_argument("-f", "--filter", dest="filter", action="store", type=re.compile,
                        help="Filter the results based on a regex")

    # Process arguments
    args = parser.parse_args()

    # Setup logger verbosity
    log_levels = {0: ('WARNING', 'ERROR'), 1: ('INFO', 'WARNING'), 2: ('DEBUG', 'INFO'), }
    mylog_levels = log_levels.get(args.verbose, ('DEBUG', 'DEBUG'))
    logger.setLevel(mylog_levels[0])
    logging.getLogger('pydocstyle').setLevel(mylog_levels[1])
    logging.getLogger('pycodestyle').setLevel(mylog_levels[1])

    # Configuration data
    confdata = CheckerConfig(args.config, args.vortexpath)
    if args.places:
        for a_place in args.places:
            if a_place not in confdata.places:
                raise ValueError('The "{:s}" place is not setup in the configuration file.'
                                 .format(a_place))

    # Loop on the various places
    total_errors = 0
    for placename, place in confdata.places.items():
        if args.places and placename not in args.places:
            continue
        logger.info('Crawling into: %s. path=%s.', placename, place.path)
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.nprocs) as executor:
            c_checkers = {vpc.shortpath: executor.submit(place.check_pycode, vpc)
                          for vpc in place.iter_pycode(confdata.places_paths)}
            total_errors += sum([place.summarize_pycode(vpc_name, checker.result(), args.filter)
                                 for vpc_name, checker in c_checkers.items()])

    if total_errors:
        logger.error('Total number of errors: %d', total_errors)
    return total_errors > 0


if __name__ == "__main__":
    sys.exit(main())
