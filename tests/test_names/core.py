# -*- coding: utf-8 -*-

"""
Core classes needed to run names tests.
"""

from __future__ import absolute_import, division, print_function, unicode_literals

from six.moves import urllib

import collections
import functools
import hashlib
import io
import os
import pprint

import six
import yaml

import bronx.stdtypes.catalog
import bronx.stdtypes.date
import footprints as fp
import gco
import vortex.syntax.stdattrs
from bronx.compat.moves import collections_abc
from bronx.fancies import loggers
from bronx.fancies.loggers import contextboundGlobalLevel
from .utils import YamlOrderedDict

import alpha      # @UnusedImport
import cen        # @UnusedImport
import common     # @UnusedImport
import davai      # @UnusedImport
import iga        # @UnusedImport
import intairpol  # @UnusedImport
import olive      # @UnusedImport
import previmar   # @UnusedImport

logger = loggers.getLogger(__name__)


# ------------------------------------------------------------------------------
# Exceptions

class TestNamesError(Exception):
    """Abstract Exception of test_names' specific errors."""
    pass


class TestNamesMissingReferenceError(TestNamesError):
    """The reference data file is not available."""
    pass


class TestNamesInconsistentReferenceError(TestNamesError):
    """The reference data are not consistent with the test definition file."""
    pass


class TestNamesComparisonError(TestNamesError):
    """Abstract Exception for any comparison error during checks."""

    _DEFAULT_MSG = "Comparison failed"

    def __init__(self, defaults, desc, msg=None):
        self._defaults = defaults
        self._desc = desc
        super(TestNamesComparisonError, self).__init__(msg if msg else self._DEFAULT_MSG)

    def __reduce__(self):
        """What to do after pickling..."""
        return (TestNamesComparisonError,
                (self._defaults,
                 self._desc,
                 super(TestNamesComparisonError, self).__str__()))

    def __str__(self):
        outstr = super(TestNamesComparisonError, self).__str__() + '\n'
        outstr += 'List of defaults\n{!s}\n'.format(self._defaults)
        outstr += 'List of parameters\n{!s}'.format(self._desc)
        return outstr


class TestNamesComparisonDiffError(TestNamesComparisonError):
    """The reference data does not match the computed value."""

    def __init__(self, defaults, desc, ref, me, msg=None):
        self._ref = ref
        self._me = me
        super(TestNamesComparisonDiffError, self).__init__(defaults, desc, msg=None)

    def __reduce__(self):
        """What to do after pickling..."""
        _, (default, desc, msg) = super(TestNamesComparisonDiffError, self).__reduce__()
        return (TestNamesComparisonDiffError,
                (default, desc, self._ref, self._me, msg))

    def __str__(self):
        outstr = super(TestNamesComparisonDiffError, self).__str__() + '\n'
        outstr += '(me) {0._me!s}\n!=   {0._ref!s} (ref)'.format(self)
        return outstr


class TestNamesComparisonNoRefError(TestNamesComparisonError):
    """The reference data is missing for this individual test."""

    _DEFAULT_MSG = "No reference data available"


# ------------------------------------------------------------------------------
# Main Test Classes

class TestDriver(object):
    """Handles all the tests contained in a YAML definition file.

    From the user's point of view, this is the class to work with.
    """

    def __init__(self, inifile, resultfile, registerpath):
        """
        :param inifile: The path to the YAML configuration file to deal with.
        :param resultfile: The path to the YAML file that contains reference
                           data associated with the **inifile** configuration
                           file.
        :param registerpath: Path to the directory that contains hard-coded
                             test resources (such as Genv data).
        """
        hm5 = hashlib.md5()
        hm5.update(inifile.encode())
        self._inihash = hm5.hexdigest()
        self._resultfile = resultfile
        self._registerpath = registerpath
        self.clear()
        self._refs = list()

    def clear(self):
        """Erase all tests."""
        self._defaults_style = 'raw'
        self._defaults = list()
        self._genvs = list()
        self._todo = list()

    def load_test(self, dumpeddata):
        """Load the content of a YAML test file.

        :param dumpeddata: The raw data read from the YAML file. Beware that
                           **dumpeddata** is the content of the YAML file, not
                           the path to the YAML file itself.
        """
        self.clear()
        if 'default' in dumpeddata:
            dumpeddefaults = dumpeddata['default']
            self._defaults_style = dumpeddefaults.get('style', self._defaults_style)
            for dset in dumpeddefaults.get('sets', list()):
                for expandedset in fp.util.expand(dset):
                    self._defaults.append(TestParameters(expandedset))
        if 'register' in dumpeddata:
            dumpedregister = dumpeddata['register']
            self._genvs = dumpedregister.get('genv', list())
            if not isinstance(self._genvs, list):
                raise ValueError('The Genv to register must be a list...')
        if 'todo' in dumpeddata:
            dumpedtodos = dumpeddata['todo']
            for i, todo in enumerate(dumpedtodos):
                tstack = TestsStack()
                try:
                    tstack.load_test(todo)
                except Exception:
                    logger.error('Exception raised while processing TestStack# %d', i)
                    logger.error('TestStack definition was:\n%s', pprint.pformat(todo))
                    raise
                self._todo.append(tstack)

    def ntests(self):
        """Return the number of resource's Handlers tested by this driver."""
        return sum([len(stack) for stack in self._todo]) * len(self._defaults)

    def _format_default_raw(self, default):
        return default

    def _format_default_olive(self, default):
        if 'geometry' in default:
            default['geometry'] = vortex.data.geometries.get(tag=default['geometry'])
        if 'date' in default:
            default['date'] = bronx.stdtypes.date.Date(str(default['date']))
        if 'namespace' in default:
            default['namespace'] = vortex.syntax.stdattrs.Namespace(default['namespace'])
        return default

    def _format_default(self, default):
        del default['vapp']
        del default['vconf']
        return getattr(self, '_format_default_{:s}'.format(self._defaults_style))(default)

    def compute_results(self, loglevel='info'):
        """
        For each set of defaults and resource's Handler defined in the
        configuration file, compute the associated URI.

        :param loglevel: Temporarily change the logging level
        """
        original_stag = vortex.sessions.get().tag
        try:
            with contextboundGlobalLevel(loglevel):
                # A new session is created for each TestDriver object
                gl = vortex.sessions.getglove(user='tourist')
                t = vortex.sessions.get(tag='nametest_{:s}'.format(self._inihash), glove=gl, active=True)
                logger.debug("Session %s/tag=%s/active=%s", str(t), t.tag, str(t.active))
                t.env.MTOOLDIR = '/'
                # Deal with every defined Genv
                for genv in self._genvs:
                    try:
                        with io.open(os.path.join(self._registerpath, 'genv', genv), 'r') as fhgenv:
                            genvstuff = [l.rstrip('\n') for l in fhgenv.readlines()]
                    except IOError:
                        logger.error("Genv cycle << %s >> not found.", genv)
                        raise
                    gco.tools.genv.autofill(cycle=genv, gcout=genvstuff)
                    logger.debug("Genv cycle << %s >> registered", genv)
                # Run things for each default
                for default in self._defaults:
                    original_vapp = t.glove.vapp
                    original_vconf = t.glove.vconf
                    original_defaults = fp.setup.defaults.copy()  # @UndefinedVariable
                    try:
                        # Fix the glove and set the defaults
                        rawdefault = default.raw.copy()
                        if 'vapp' in rawdefault:
                            t.glove.vapp = rawdefault['vapp']
                        if 'vconf' in rawdefault:
                            t.glove.vconf = rawdefault['vconf']
                        fp.setup.defaults = self._format_default(rawdefault)
                        logger.debug("Glove's vapp/vconf: %s/%s", t.glove.vapp, t.glove.vconf)
                        logger.debug("Footprints defaults: %s", str(fp.setup.defaults))
                        # For each resource's Handler, actualy compute the URI
                        for tstack in self._todo:
                            tstack.compute_results(default)
                    finally:
                        # Restore the initial glove and defaults
                        t.glove.vapp = original_vapp
                        t.glove.vconf = original_vconf
                        fp.setup.defaults = original_defaults
        finally:
            vortex.sessions.switch(original_stag)

    def dump_results(self):
        """Dump the test results in the reference data file."""
        stackdump = list()
        for tstack in self._todo:
            stackdump.append(sorted(tstack, key=lambda t: t.desc))
        with io.open(self._resultfile, 'w') as fhyaml:
            yaml.dump(stackdump, fhyaml, Dumper=TestYamlDumper, default_flow_style=False)

    def load_references(self):
        """Read reference data from file."""
        self._refs = list()
        if not os.path.isfile(self._resultfile):
            raise TestNamesMissingReferenceError('The {:s} file is missing'.format(self._resultfile))
        with io.open(self._resultfile, 'r') as fhyaml:
            stackdump = yaml.load(fhyaml, Loader=TestYamlLoader)
        for tstack in stackdump:
            self._refs.append(TestsStack(items=tstack))

    def check_results(self):
        """Check the results against reference data"""
        if len(self._todo) != len(self._refs):
            raise TestNamesInconsistentReferenceError(
                'Hummm, apparently the number of tests and references differs.')
        for me, ref in zip(self._todo, self._refs):
            me.check_against(ref)


class TestsStack(bronx.stdtypes.catalog.Catalog):
    """Contains a set of SingleTests."""

    def __init__(self, *kargs, **kwargs):
        super(TestsStack, self).__init__(*kargs, **kwargs)
        self._lookupmap = collections.defaultdict(list)
        for item in self:
            self._lookupmap[item.desc].append(item)

    def add(self, *stuff):
        """Add a new SingleTest to the stack.

        :param stuff: a tuple of :class:`SingleTest` objects.
        """
        super(TestsStack, self).add(*stuff)
        for item in stuff:
            self._lookupmap[item.desc].append(item)

    def lookup(self, desc, default):
        """
        Look for a test result given the test description (**desc**) and a
        set of **defaut** values.

        :param desc: the description of the test to look for
        :param default: the set of defaults to look for
        :rtype: SingleTest
        """
        for item in self._lookupmap[desc]:
            if default in item.results:
                return item.results.getparsed(default)
        return None

    def load_test(self, dumpeddata):
        """Load the content of a YAML definition file.

        :param dumpeddata: The subset of raw data, read from the YAML file,
                           that is relevant to this subset of tests.
        """
        self.clear()
        dumpedcommons = dict()
        if 'commons' in dumpeddata:
            dumpedcommons = dumpeddata['commons']
        if not isinstance(dumpedcommons, dict):
            raise ValueError('TestsStask commons must be dictionaries...')
        dumpedtests = dumpeddata.get('tests', list())
        for dumpedtest in dumpedtests:
            thetest = dumpedcommons.copy()
            thetest.update(dumpedtest)
            for expandedtest in fp.util.expand(thetest):
                self.add(SingleTest(expandedtest))

    def compute_results(self, defaults):
        """
        For a given set of **defaults**, compute the associated URI for each of
        the resource's Handlers defined in this object.
        """
        for ntest in self:
            ntest.compute_results(defaults)

    def check_against(self, ref):
        """
        Check the results (that must have been computed with the
        :meth:`compute_results` method) against reference data

        :param ref: A :class:`TestsStack` object that holds the reference
                    data we are comparing to.
        """
        for test in self:
            for default, result in test.results.parseditems():
                ref_result = ref.lookup(test.desc, default)
                if ref_result is None:
                    exc = TestNamesComparisonNoRefError(default, test.desc)
                    logger.warning(str(exc))
                    raise exc
                if ref_result != result:
                    raise TestNamesComparisonDiffError(default, test.desc, ref_result, result)
                else:
                    logger.debug("Comparison OK for desc:\n%s\ndefault:\n%s",
                                 str(test.desc), str(default))


class SingleTest(object):
    """Handle a single test case (i.e. A single resource's Handler to be tested)."""

    _DEFAULT_CONTAINER = fp.proxy.container(incore=True)

    def __init__(self, desc, results=None):
        """
        :param desc: The description that is used to build the resource's Handler
        :param results: A :class:`TestResults` object where tests results will
                        be appended (if missing a new :class:`TestResults` object
                        is created)
        """
        self._desc = TestParameters(desc) if not isinstance(desc, TestParameters) else desc
        self._results = TestResults() if results is None else results

    @property
    def desc(self):
        """
        The footprint's descrition for this test :class:`TestParameters` object.
        """
        return self._desc

    @property
    def results(self):
        """Results for this test (as a :class:`TestResults` object)."""
        return self._results

    @property
    def rh(self):
        """Generate the ResourceHandler associated with this test and return it."""
        picked_up = fp.proxy.providers.pickup(  # @UndefinedVariable
            *fp.proxy.resources.pickup_and_cache(self.desc.raw.copy())  # @UndefinedVariable
        )
        logger.debug('Resource desc %s', picked_up)
        picked_up['container'] = self._DEFAULT_CONTAINER
        picked_rh = vortex.data.handlers.Handler(picked_up)
        if not picked_rh.complete:
            logger.error('Raw description:\n%s', str(self.desc))
            logger.error('After pickup:\n%s', pprint.pformat(picked_up))
            raise ValueError("The ResourceHandler is incomplete")
        return picked_rh

    def compute_results(self, defaults):
        """For a given set of **defaults**, compute the associated URI."""
        tmprh = self.rh
        try:
            self.results.append(defaults, 'location', tmprh.location())
        except Exception:
            logger.error('Location error on ResourceHandler:')
            tmprh.quickview()
            raise

    @classmethod
    def to_yaml(cls, dumper, data):
        """Internal YAML exporter for this object."""
        odict = YamlOrderedDict()
        odict['description'] = data.desc
        odict['results'] = data.results
        return dumper.represent_mapping('!test_names.core.SingleTest', odict.items())

    @classmethod
    def from_yaml(cls, loader, node):  # @UnusedVariable
        """Internal YAML constructor for this object."""
        d = loader.construct_mapping(node)
        return cls(d['description'], d['results'])


# ------------------------------------------------------------------------------
# Utility classes that handles footprint's descriptions and test results

class TestResults(collections_abc.Mapping):
    """Utility class that holds test's results."""

    def __init__(self):
        self._results = collections.defaultdict(dict)

    def append(self, default, key, value):
        """Append a result (a generated URI) to this object.

        :param TestParameters default: The set of default used for this test
        :param TestParameters key: The footprint description for this test
        :param value: The generated URI
        """
        self._results[default][key] = value

    def __len__(self):
        return len(self._results)

    def __iter__(self):
        for k in self._results:
            yield k

    def __contains__(self, default):
        return default in self._results

    def __getitem__(self, default):
        return self._results[default]

    def items(self):
        """Iterate over results."""
        for k, v in self._results.items():
            yield k, v

    def getparsed(self, default):
        """Return a result dictinary wher URI are parsed."""
        what = self._results[default]
        parsed = dict()
        for k, v in what.items():
            if k in ('location', ):
                v = urllib.parse.urlparse(v)
                v = urllib.parse.ParseResult(v.scheme, v.netloc, v.path, v.params,
                                             urllib.parse.parse_qs(v.query), v.fragment)
            parsed[k] = v
        return parsed

    def parseditems(self):
        """Iterate over parsed results."""
        for k in self._results.keys():
            yield k, self.getparsed(k)

    @classmethod
    def to_yaml(cls, dumper, data):
        """Internal YAML exporter for this object."""
        tests = list()
        for d, v in sorted(data._results.items()):
            odict = YamlOrderedDict()
            odict['default'] = d
            for k, vv in sorted(v.items()):
                odict[k] = vv
            tests.append(odict)
        return dumper.represent_sequence('!test_names.core.TestResults', tests)

    @classmethod
    def from_yaml(cls, loader, node):  # @UnusedVariable
        """Internal YAML constructor for this object."""
        newobj = cls()
        for item in node.value:
            d = loader.construct_mapping(item)
            default = d.pop('default')
            for k, v in d.items():
                newobj.append(default, k, v)
        return newobj


@functools.total_ordering
class TestParameters(collections_abc.Hashable):
    """Utility class that holds a footprint's description."""

    def __init__(self, desc):
        """
        :param desc: The footprint's description (as a dictionary)
        """
        self._desc_dict = desc
        self._desc = [(k, desc[k]) for k in sorted(desc.keys())]
        self._desc = tuple(self._desc)

    @property
    def raw(self):
        """The footprint's description (as a dictionary)."""
        return self._desc_dict

    def __hash__(self):
        return hash(self._desc)

    def __eq__(self, other):
        if isinstance(other, TestParameters):
            return self._desc == other._desc
        else:
            return False

    if six.PY3:
        @staticmethod
        def _py27_like_gt(me, other):
            try:
                return me > other
            except TypeError:
                return type(me).__name__ > type(other).__name__
    else:
        @staticmethod
        def _py27_like_gt(me, other):
            return me > other

    def __gt__(self, other):
        for i_me, i_other in zip(self._desc, other._desc):
            for ii_me, ii_other in zip(i_me, i_other):
                if self._py27_like_gt(ii_me, ii_other):
                    return True
                if ii_me != ii_other:
                    return False
        return len(self._desc) > len(other._desc)

    def __str__(self):
        return pprint.pformat(self._desc_dict)

    @classmethod
    def to_yaml(cls, dumper, data):
        """Internal YAML exporter for this object."""
        odict = YamlOrderedDict()
        for item in data._desc:
            odict[item[0]] = item[1]
        return dumper.represent_mapping('!test_names.core.TestParameters', odict.items())

    @classmethod
    def from_yaml(cls, loader, node):  # @UnusedVariable
        """Internal YAML constructor for this object."""
        return cls(loader.construct_mapping(node))


# ------------------------------------------------------------------------------
# PyYAML package configuration

TestYamlDumper = yaml.dumper.SafeDumper
TestYamlDumper.add_representer(SingleTest, SingleTest.to_yaml)
TestYamlDumper.add_representer(TestParameters, TestParameters.to_yaml)
TestYamlDumper.add_representer(TestResults, TestResults.to_yaml)
TestYamlDumper.add_representer(
    YamlOrderedDict,
    lambda self, data: self.represent_mapping('tag:yaml.org,2002:map',
                                              data.items()))

TestYamlLoader = yaml.loader.SafeLoader
if six.PY2:
    TestYamlLoader.add_constructor(unicode, lambda self, data: self.represent_str(str(data)))

TestYamlLoader.add_constructor('!test_names.core.SingleTest', SingleTest.from_yaml)
TestYamlLoader.add_constructor('!test_names.core.TestParameters', TestParameters.from_yaml)
TestYamlLoader.add_constructor('!test_names.core.TestResults', TestResults.from_yaml)
