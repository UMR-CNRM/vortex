# -*- coding: utf-8 -*-

'''
Core classes needed to run names tests.
'''


from __future__ import print_function, division, absolute_import, unicode_literals
import six

import collections
import functools
import hashlib
import io
import os
import pprint

import yaml

from bronx.fancies import loggers
import bronx.stdtypes.catalog
import bronx.stdtypes.date
import footprints as fp
import vortex.syntax.stdattrs
import gco

import common  # @UnusedImport
import olive  # @UnusedImport
import iga  # @UnusedImport
import intairpol  # @UnusedImport
import cen  # @UnusedImport
import previmar  # @UnusedImport

from .utils import YamlOrderedDict


logger = loggers.getLogger(__name__)


# ------------------------------------------------------------------------------
# Exceptions

class TestNamesError(Exception):
    """Abstract Exception of test_names's specific errors."""
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

    def __str__(self):
        outstr = super(TestNamesComparisonError, self).__str__() + '\n'
        outstr += 'List of defaults\n{!s}\n'.format(self._defaults)
        outstr += 'List of parameters\n{!s}'.format(self._desc)
        return(outstr)


class TestNamesComparisonDiffError(TestNamesComparisonError):
    """The reference data does not match the computed value."""

    def __init__(self, defaults, desc, ref, me, msg=None):
        self._ref = ref
        self._me = me
        super(TestNamesComparisonDiffError, self).__init__(defaults, desc, msg=None)

    def __str__(self):
        outstr = super(TestNamesComparisonDiffError, self).__str__() + '\n'
        outstr += '(me) {0._me!s}\n!=   {0._ref!s} (ref)'.format(self)
        return(outstr)


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
        """Load the content of a YAML test file."""
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
                except:  # @IgnorePep8
                    logger.error('Exception raised while processing TestStack# %d', i)
                    logger.error('TestStack definition was:\n%s', pprint.pformat(todo))
                    raise
                self._todo.append(tstack)

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

    def compute_results(self):
        """Launch all the tests (compute the associated locations)."""
        original_stag = vortex.sessions.get().tag
        try:
            gl = vortex.sessions.getglove(user='tourist')
            t = vortex.sessions.get(tag='nametest_{:s}'.format(self._inihash), glove=gl, active=True)
            logger.debug("Session %s/tag=%s/active=%s", str(t), t.tag, str(t.active))
            t.env.MTOOLDIR = '/'
            # Deal with genvs
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
                    rawdefault = default.raw.copy()
                    if 'vapp' in rawdefault:
                        t.glove.vapp = rawdefault['vapp']
                    if 'vconf' in rawdefault:
                        t.glove.vconf = rawdefault['vconf']
                    fp.setup.defaults = self._format_default(rawdefault)
                    logger.debug("Glove's vapp/vconf: %s/%s", t.glove.vapp, t.glove.vconf)
                    logger.debug("Footprints defaults: %s", str(fp.setup.defaults))
                    for tstack in self._todo:
                        tstack.compute_results(default)
                finally:
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
            yaml.dump(stackdump, fhyaml, default_flow_style = False)

    def load_references(self):
        """Read reference data from file."""
        self._refs = list()
        if not os.path.isfile(self._resultfile):
            raise TestNamesMissingReferenceError('The {:s} file is missing'.format(self._resultfile))
        with io.open(self._resultfile, 'r') as fhyaml:
            stackdump = yaml.load(fhyaml)
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
    """Contains a subset of SingleTests."""

    def __init__(self, *kargs, **kwargs):
        super(TestsStack, self).__init__(*kargs, **kwargs)
        self._lookupmap = collections.defaultdict(list)
        for item in self:
            self._lookupmap[item.desc].append(item)

    def add(self, *stuff):
        """Add a new SingleTest to the stack."""
        super(TestsStack, self).add(*stuff)
        for item in stuff:
            self._lookupmap[item.desc].append(item)

    def lookup(self, desc, default):
        """Look for test result given the test description and a set of defaut values."""
        for item in self._lookupmap[desc]:
            if default in item.results:
                return item.results[default]
        return None

    def load_test(self, dumpeddata):
        """Load the content of a YAML definition file."""
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
        """Launch all the SingleTests of this stack (compute the associated locations)."""
        for ntest in self:
            ntest.compute_results(defaults)

    def check_against(self, ref):
        """Check the results against reference data"""
        for test in self:
            for default, result in test.results.items():
                ref_result = ref.lookup(test.desc, default)
                if ref_result is None:
                    exc = TestNamesComparisonNoRefError(default, test.desc)
                    logger.warning(str(exc))
                    raise exc
                if ref_result != result:
                    exc = TestNamesComparisonDiffError(default, test.desc, ref_result, result)
                    logger.warning(str(exc))
                    raise exc
                else:
                    logger.debug("Comparison OK for desc:\n%s\ndefault:\n%s",
                                 str(test.desc), str(default))


class SingleTest(object):
    """Handle a single test case."""

    _DEFAULT_CONTAINER = fp.proxy.container(incore=True)

    def __init__(self, desc, results=None):
        self._desc = TestParameters(desc) if not isinstance(desc, TestParameters) else desc
        self._results = TestResults() if results is None else results

    @property
    def desc(self):
        """The footprint's descrition for this test."""
        return self._desc

    @property
    def results(self):
        """Results fo rthis test."""
        return self._results

    @property
    def rh(self):
        """Generate the ResourceHandler associated with this test."""
        picked_up = fp.proxy.providers.pickup(  # @UndefinedVariable
            * fp.proxy.resources.pickup_and_cache(self.desc.raw.copy())  # @UndefinedVariable
        )
        logger.debug('Resource desc %s', picked_up)
        picked_up['container'] = self._DEFAULT_CONTAINER
        picked_rh = vortex.data.handlers.Handler(picked_up)
        if not picked_rh.complete:
            logger.error('Raw description:\n%s', str(self.desc))
            logger.error('After pickup:\n%s', pprint.pformat(picked_up))
            raise ValueError("The ResourceHandler is incomplete")
        return picked_rh

    def compute_results(self, default):
        """Launch this SingleTest for a given set of defaults."""
        tmprh = self.rh
        try:
            self.results.append(default, 'location', tmprh.location())
        except:  # @IgnorePep8
            logger.error('Location error on ResourceHandler:')
            tmprh.quickview()
            raise

    @classmethod
    def to_yaml(cls, dumper, data):
        """YAML exporter."""
        odict = YamlOrderedDict()
        odict['description'] = data.desc
        odict['results'] = data.results
        return dumper.represent_mapping('!test_names.core.SingleTest', odict.items())

    @classmethod
    def from_yaml(cls, loader, node):  # @UnusedVariable
        """YAML constructor."""
        d = loader.construct_mapping(node)
        return cls(d['description'], d['results'])


# ------------------------------------------------------------------------------
# Utility classes that handles footprint's descriptions and test results

class TestResults(collections.Mapping):
    """Utility class that holds test's results."""

    def __init__(self):
        self._results = collections.defaultdict(dict)

    def append(self, default, key, value):
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
        for k, v in self._results.items():
            yield k, v

    @classmethod
    def to_yaml(cls, dumper, data):
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
        newobj = cls()
        for item in node.value:
            d = loader.construct_mapping(item)
            default = d.pop('default')
            for k, v in d.items():
                newobj.append(default, k, v)
        return newobj


@functools.total_ordering
class TestParameters(collections.Hashable):
    """Utility class that holds a footprint's description."""

    def __init__(self, desc):
        self._desc_dict = desc
        self._desc = [(k, desc[k]) for k in sorted(desc.keys())]
        self._desc = tuple(self._desc)

    @property
    def raw(self):
        return self._desc_dict

    def __hash__(self):
        return hash(self._desc)

    def __eq__(self, other):
        if isinstance(other, TestParameters):
            return self._desc == other._desc
        else:
            return False

    def __gt__(self, other):
        return self._desc > other._desc

    def __str__(self):
        return pprint.pformat(self._desc_dict)

    @classmethod
    def to_yaml(cls, dumper, data):
        odict = YamlOrderedDict()
        for item in data._desc:
            odict[item[0]] = item[1]
        return dumper.represent_mapping('!test_names.core.TestParameters', odict.items())

    @classmethod
    def from_yaml(cls, loader, node):  # @UnusedVariable
        return cls(loader.construct_mapping(node))


# ------------------------------------------------------------------------------
# PyYAML package configuration

yaml.add_representer(SingleTest, SingleTest.to_yaml)
yaml.add_representer(TestParameters, TestParameters.to_yaml)
yaml.add_representer(TestResults, TestResults.to_yaml)
yaml.add_representer(YamlOrderedDict,
                     lambda self, data: self.represent_mapping('tag:yaml.org,2002:map',
                                                               data.items()))
if six.PY2:
    yaml.add_representer(unicode, lambda self, data: self.represent_str(str(data)))

yaml.add_constructor('!test_names.core.SingleTest', SingleTest.from_yaml)
yaml.add_constructor('!test_names.core.TestParameters', TestParameters.from_yaml)
yaml.add_constructor('!test_names.core.TestResults', TestResults.from_yaml)
