#!/usr/bin/env python3
# encoding: utf-8

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

import astroid
import pycodestyle
import pydocstyle
import yaml


argparse_epilog = ""

logging.basicConfig()
logger = logging.getLogger()

_VTXBASE = re.sub('{0:}project{0:}bin$'.format(os.path.sep), '',
                  os.path.dirname(os.path.realpath(__file__)))
_CONF_DIR = os.path.join(_VTXBASE, 'project', 'conf')


class MyPycodestyleReporter(pycodestyle.BaseReport):
    """Store the pycodestyle messages for latter use..."""

    def init_file(self, filename, lines, expected, line_offset):
        """Signal a new file."""
        self._deferred_messages = []
        return super(MyPycodestyleReporter, self).init_file(
            filename, lines, expected, line_offset)

    def error(self, line_number, offset, text, check):
        """Report an error, according to options."""
        code = super(MyPycodestyleReporter, self).error(line_number, offset,
                                                        text, check)
        if code and (self.counters[code] == 1):
            self._deferred_messages.append(
                (line_number, offset, code, text[5:], check.__doc__))
        return code

    @property
    def rawmessages(self):
        """The whole bunch of error messages (for a given file)."""
        return self._deferred_messages


class PycodestyleChecker(object):
    """Check the source code using pycodestyle."""

    _RESFMT = '{:s}-{:4s}  l.{:4d}.{:-3d}: {:s}'

    def __init__(self, **kwargs):
        """Keep track of pycodechecker arguments."""
        self._pcs_style_args = kwargs

    def _parse_results(self, vpycode, label, result):
        """Print the error messages but filter footprint related messages first."""
        errors = list()
        for message in result.rawmessages:
            if (message[0] not in vpycode.expanded_fplines or
                    message[2] not in ['E221', 'E251']):
                errors.append((message[0], self._RESFMT.format(label, message[2],
                                                               message[0], message[1],
                                                               message[3],)))
        return errors

    def __call__(self, vpycode, label):
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


class PydocstyleChecker(object):
    """Check the source code using pycodestyle."""

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

    def __call__(self, vpycode, label):
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


_AVAILABLE_CHECKERS = dict(
    pycodestyle=PycodestyleChecker,
    pydocstyle=PydocstyleChecker,
)


def _property_auto_add(* what):
    """Automatically add property to expose read only attributes."""

    class RoAttrDescriptor(object):
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


@_property_auto_add('path', 'shortpath', 'fpdetect')
class VortexPythonCode(object):
    """The content of a Vortex' Python code file."""

    def __init__(self, path, shortpath, fpdetect):
        """Ingest the code and detect footprint definitions if need be."""
        self._path = path
        self._shortpath = shortpath
        self._fpdetect = fpdetect
        self._code = None
        self._p_astroid = None
        self._fplines = None
        self._expanded_fplines = None

    @property
    def code(self):
        """Read the source file and returns it as a string."""
        if self._code is None:
            with open(self._path) as fhcode:
                self._code = fhcode.read()
        return self._code

    @property
    def p_astroid(self):
        """Return the code parsed by astroid."""
        if self._p_astroid is None:
            try:
                self._p_astroid = astroid.parse(self.code)
            except astroid.exceptions.AstroidError:
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
        fpstarts = None
        for node in self.p_astroid.values():
            if fpstarts is not None:
                self._fplines.append((fpstarts, node.lineno - 1))
                fpstarts = None
            if isinstance(node, astroid.nodes.ClassDef):
                # This class may contain a footprint definition...
                for cnode_name, cnode in node.items():
                    if cnode_name == '_footprint' and isinstance(cnode, astroid.nodes.AssignName):
                        fpstarts = cnode.lineno
                        next_s = cnode.next_sibling()
                        if next_s:
                            self._fplines.append((fpstarts, next_s.lineno - 1))
                            fpstarts = None
        if fpstarts is not None:
            self._fplines.append((fpstarts, len("\n".split(self._codestr))))
            fpstarts = None

        if self._fplines:
            logger.debug('Found footprint defs in %s: %s', self.path,
                         ", ".join(['({:d}, {:d})'.format(fpl[0], fpl[1]) for fpl in self._fplines]))

        for fplines in [range(s, e + 1) for (s, e) in self._fplines]:
            self._expanded_fplines.update(fplines)


class _AnyConfigEntry(object):
    """handle any kind of configuration data read from the YAML file."""

    __metaclass__ = abc.ABCMeta

    _MANDATORY_ENTRIES = set()
    _ALLOWED_ENTRIES = set()
    _CLASS_LABEL = 'to_be_changed'

    @abc.abstractmethod
    def __init__(self, name, description):
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


@_property_auto_add('path', 'shortpath', 'fpdetect', 'checkconfigs')
class VortexPlace(_AnyConfigEntry):
    """Handle a given place entry of the configuration file."""

    _MANDATORY_ENTRIES = {'path', 'checkconfigs', }
    _ALLOWED_ENTRIES = {'footprints_detect', }
    _CLASS_LABEL = 'place'

    def __init__(self, name, description, checkconfigs, vortexpath):
        """Parse the **decription** read in the YAML configuration file."""
        super(VortexPlace, self).__init__(name, description)
        self._path = os.path.join(vortexpath, description['path'])
        self._shortpath = description['path']
        self._fpdetect = bool(description.get('footprints_detect', False))
        self._checkconfigs = list()
        for checkconfig in description['checkconfigs']:
            if checkconfig not in checkconfigs:
                raise ValueError('Improper {:s} checker value'.format(description['checkconfig']))
            self._checkconfigs.append(checkconfigs[checkconfig])

    def _pycode_crawl(self, path, shortpath, places_paths):
        """Actualy iterate over **path**."""
        for item in os.scandir(path):
            fullpath = os.path.join(path, item.name)
            new_shortpath = os.path.join(shortpath, item.name)
            if item.name.endswith('.py') and item.is_file():
                yield VortexPythonCode(fullpath, new_shortpath, self.fpdetect)
            elif item.name != '__pycache__' and item.is_dir():
                if fullpath not in places_paths:
                    yield from self._pycode_crawl(fullpath, new_shortpath, places_paths)

    def iter_pycode(self, places_paths):
        """
        Iterate through all the python's files of the place and returns
        :class:`VortexPythonCode` objects.
        """
        return self._pycode_crawl(self.path, self.shortpath, places_paths)

    def check_pycode(self, vpc):
        """Check a given code file (represented as a VortexPythonCode object)."""
        logger.info('Dealing with the %s file.', vpc.path)
        errors = list()
        for checkconfig in self.checkconfigs:
            for checker in checkconfig.checkers:
                errors.extend(checker(vpc, checkconfig.label))
        return errors

    def summarize_pycode(self, vpc_name, errors):
        """Print the errors summary."""
        if errors:
            print('=== ' + vpc_name + ' ===')
            for errordesc in sorted(errors):
                print('    ' + errordesc[1])
        return len(errors)


@_property_auto_add('checkers', 'label')
class CheckConfig(_AnyConfigEntry):
    """Holds information on a given checkerconfig entry."""

    _MANDATORY_ENTRIES = {'checkers', 'label'}
    _CLASS_LABEL = 'checkconfig'

    def __init__(self, name, description):
        """Create the configuration object starting form its **description**."""
        super(CheckConfig, self).__init__(name, description)
        # Process the definition
        self._label = description['label']
        self._checkers = list()
        for checker in description['checkers']:
            if checker.get('type', None) not in _AVAILABLE_CHECKERS:
                raise ValueError('The {:s} checker is unavailable'.format(checker))
            checker_args = checker.copy()
            del checker_args['type']
            try:
                self.checkers.append(_AVAILABLE_CHECKERS.get(checker['type'])(** checker_args))
            except Exception:
                logger.error('Could not create the %s checker using the following attributes:\n %s',
                             checker['type'], checker_args)
                raise


class CheckerConfig(object):
    """Gives access to the checker config file."""

    def __init__(self, configfile, vortexpath, configdir=None):
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
            raise IOError("The configuration file {:s} is missing.".format(self._file))
        # Load the yaml configuration file
        with open(self._file) as fhconf:
            try:
                self._confdata = yaml.load(fhconf, yaml.SafeLoader)
            except yaml.YAMLError:
                logger.info('An error occured while parsing: %s', self._file)
                raise
        # Basic checks
        if not isinstance(self._confdata, dict):
            raise ValueError('Configuration must be a dictionary')
        conf_l1_entries = {'places', 'checkconfigs'}
        if set(self._confdata.keys()) != conf_l1_entries:
            raise ValueError('Configuration must have exactly the following entries: {:s}'
                             .format(','.join(conf_l1_entries)))
        # Cache
        self._places = None
        self._places_paths = None
        self._checkconfigs = None

    @property
    def vortexpath(self):
        """The place where the vortex directory lies."""
        return self._vortexpath

    @property
    def checkconfigs(self):
        """The list of available check configurations."""
        if self._checkconfigs is None:
            self._checkconfigs = {n: CheckConfig(n, c)
                                  for n, c in self._confdata['checkconfigs'].items()}
        return self._checkconfigs

    @property
    def places(self):
        """The list of places where to run the code check."""
        if self._places is None:
            self._places = {n: VortexPlace(n, p, self.checkconfigs, self.vortexpath)
                            for n, p in self._confdata['places'].items()}
        return self._places

    @property
    def places_paths(self):
        """The list of code directories that will be checked."""
        if self._places_paths is None:
            self._places_paths = {p.path for p in self.places.values()}
        return self._places_paths


def main():
    """Process command line options."""

    program_name = os.path.basename(sys.argv[0])
    program_shortdesc = program_name + ' -- ' + __import__('__main__').__doc__.lstrip("\n")
    program_desc = program_shortdesc

    # Setup argument parser
    parser = ArgumentParser(description=program_desc, epilog=argparse_epilog,
                            formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument("places", nargs='*',
                        help="test only the following places... (all if omitted).")
    parser.add_argument("-v", "--verbose", dest="verbose", action="count",
                        default=0, help="Set verbosity level [default: %(default)s]")
    parser.add_argument("-n", "--nprocs", dest="nprocs", action="store", type=int,
                        help=("The number of processes to use during the check "
                              "(by default the number of CPUs on the machine)"))
    parser.add_argument("-c", "--config", dest="config", action="store",
                        default='@vortex_codechecker.yaml',
                        help="Configuration file location [default: %(default)s]")
    parser.add_argument("-p", "--vortexpath", dest="vortexpath", action="store",
                        default=_VTXBASE,
                        help="Vortex repository location [default: %(default)s]")

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

    # Loop on the various places
    total_errors = 0
    for placename, place in confdata.places.items():
        if args.places and placename not in args.places:
            continue
        logger.info('Crawling into: %s. path=%s.', placename, place.path)
        with concurrent.futures.ProcessPoolExecutor(max_workers=args.nprocs) as executor:
            c_checkers = {vpc.shortpath: executor.submit(place.check_pycode, vpc)
                          for vpc in place.iter_pycode(confdata.places_paths)}
            total_errors += sum([place.summarize_pycode(vpc_name, checker.result())
                                 for vpc_name, checker in c_checkers.items()])

    if total_errors:
        logger.error('Total number of errors: %d', total_errors)
    return total_errors > 0


if __name__ == "__main__":
    sys.exit(main())
