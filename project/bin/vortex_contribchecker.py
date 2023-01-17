#!/usr/bin/env python3
# encoding: utf-8
# python >= 3.5 required

"""
Run a series of test and produce something close to what the test server would
give (tests with various Python's version, documentation building,
style checking).
"""

import abc
from argparse import ArgumentParser, RawDescriptionHelpFormatter
import concurrent.futures
from configparser import ConfigParser
import contextlib
import locale
import logging
import os
import pprint
import re
import subprocess
import sys

# Setup the logging facility
logger_handler = logging.StreamHandler()
logger_handler.setFormatter(
    logging.Formatter('%(asctime)s - %(filename)s - %(levelname)s - %(message)s')
)
logger = logging.getLogger()
logger.addHandler(logger_handler)

# The present Vortex code repository location
_VTXBASE = re.sub('{0:}project{0:}bin$'.format(os.path.sep), '',
                  os.path.dirname(os.path.realpath(__file__)))

# Default configuration file location
_CONF_DEFAULT = os.path.join(os.environ['HOME'],
                             '.vortex_contribchecker.ini')

# The default encoding used by the system
_DEFAULT_ENC = locale.getpreferredencoding(do_setlocale=True)


class ContribCheckerConfig(ConfigParser):
    """Gives access to configuration data read from the INI file."""

    def __init__(self, vortexbase):
        """
        :param vortexbase: The path to the Vortex directory that will be tested.
        """
        super().__init__()
        self._vortexbase = vortexbase
        self._nosetesters = None
        self._pytesters = None
        self._codechecker_interpreter = None
        self._doc_buildtarget = None
        self._doc_interpreter = None
        self._doc_sphinxbuilder = None

    @staticmethod
    def _check_exists(a_file, label="file"):
        """Checks if *a_file* exists. If not, raise an exception."""
        if not os.path.exists(a_file):
            raise OSError('The "{:s}" {:s} does not esists.'
                          .format(a_file, label))

    @property
    def vortexbase(self):
        """The path to the Vortex directory that will be tested."""
        return self._vortexbase

    @property
    def do_parallel(self):
        """Whether to launch the various checks in parallel."""
        return re.match(r'(1|True|ok)',
                        self.get('settings', 'parallel_firstlevel', fallback='True'),
                        flags=re.IGNORECASE)

    @property
    def nosetests_ntasks(self):
        """During unit-testing with nose, the number of parallel threads to be used."""
        return int(self.get('settings', 'nosetests_ntasks', fallback=3))

    @property
    def pytests_ntasks(self):
        """During unit-testing with pytest, the number of parallel threads to be used."""
        return int(self.get('settings', 'pytests_ntasks', fallback=3))

    @property
    def codechecker_ntasks(self):
        """During the codestyle check, the number of parallel tasks to be used."""
        return int(self.get('settings', 'codechecker_ntasks', fallback=1))

    @property
    def nicevalue(self):
        """The nice value adjustment for this process (and its children)."""
        return int(self.get('settings', 'nicevalue', fallback=15))

    @property
    def nosetesters(self):
        """The various ``nosetests`` executable to run the unit tests with.

        :rtype: dict
        :return: A dictionary that associates a label and a path to a nosetests
                 utility
        """
        if self._nosetesters is None:
            self._nosetesters = dict()
            if self.has_section('nosetesters'):
                for k, n in self.items('nosetesters'):
                    self._check_exists(n, 'nose launcher')
                    self._nosetesters[k] = n
        return self._nosetesters

    @property
    def pytesters(self):
        """The various ``pytests`` executable to run the unit tests with.

        :rtype: dict
        :return: A dictionary that associates a label and a path to a nosetests
                 utility
        """
        if self._pytesters is None:
            self._pytesters = dict()
            if self.has_section('pytesters'):
                for k, n in self.items('pytesters'):
                    self._check_exists(n, 'pytest launcher')
                    self._pytesters[k] = n
        return self._pytesters

    def _docinit(self):
        """Read all of the documentation related configuration data."""
        if self._doc_buildtarget is None:
            if self.has_section('doc'):
                self._doc_interpreter = self.get('doc', 'interpreter', fallback=None)
                self._doc_sphinxbuilder = self.get('doc', 'sphinxbuilder', fallback=None)
                self._doc_buildtarget = self.get('doc', 'buildtarget', fallback='html')
            if self._doc_interpreter is None or self._doc_sphinxbuilder is None:
                self._doc_buildtarget = False
            else:
                self._check_exists(self._doc_interpreter, 'interpreter')
                self._check_exists(self._doc_sphinxbuilder, 'sphinxbuilder')

    @property
    def doc_buildtarget(self):
        """The makefile target to use when building the documentation.

        :note: May return ``False`` if no sphinx-build executable is provided.
        """
        self._docinit()
        return self._doc_buildtarget

    @property
    def doc_interpreter(self):
        """
        The path to the Python's interpreter to be used when building and
        checking the documentation.
        """
        self._docinit()
        return self._doc_interpreter

    @property
    def doc_sphinxbuilder(self):
        """
        The path to the sphinx-build executable that is used to build the
        documentation.
        """
        self._docinit()
        return self._doc_sphinxbuilder

    @property
    def doc_extrapath(self):
        """An extra path to be added to the system's path (to find things like pandoc)."""
        return self.get('doc', 'extrapath', fallback='')

    @property
    def codechecker_interpreter(self):
        """
        The path to the Python's interpreter to be used when performing the
        codestyle check.
        """
        if self._codechecker_interpreter is None:
            self._codechecker_interpreter = self.get('codechecker', 'interpreter', fallback=False)
            if self._codechecker_interpreter:
                self._check_exists(self._codechecker_interpreter, 'interpreter')
        return self._codechecker_interpreter


class AbstractChecker(metaclass=abc.ABCMeta):
    """
    The "Checker" classes are responsible to conduct a test on Vortex and to
    summarise and display the results.

    This class is an abstract class that defines an interface to be implemented
    by any "Checker" class.
    """

    _TXT_OK = 'SUCCESS'
    _FANCY_OK = '\x1b[32m{:s}\x1b[0m'
    _TXT_KO = 'FAILURE'
    _FANCY_KO = '\x1b[1;91m{:s}\x1b[0m'

    _TEST_SUBDIR = None

    def __init__(self, config):
        """
        :param ContribCheckerConfig config: Configuration data for this run.
        """
        self._config = config
        if self._TEST_SUBDIR:
            self._testdir = os.path.join(self.config.vortexbase, self._TEST_SUBDIR)
        else:
            self._testdir = None

    @property
    def config(self):
        """The current configuration data."""
        return self._config

    @contextlib.contextmanager
    def _spawn_switch(self):
        """Jump into the ``self._testdir`` directory if needed."""
        if self._testdir:
            prevdir = os.getcwd()
            try:
                os.chdir(self._testdir)
                yield
            finally:
                os.chdir(prevdir)
        else:
            yield

    def _spawn_generic(self, cmd, **kwargs):
        """Run any external command and return the return code and output."""
        rcode = 0
        logger.debug("Start running: %s", ' '.join(cmd))
        try:
            n_output = subprocess.check_output(cmd,
                                               stderr=subprocess.STDOUT,
                                               **kwargs)
        except subprocess.CalledProcessError as e:
            rcode = e.returncode
            n_output = e.output
        logger.debug("Done  running: %s", ' '.join(cmd))
        return (rcode, n_output.decode(encoding=_DEFAULT_ENC))

    def _spawn(self, cmd, *args, **kwargs):
        """Run an external command and return the return code and output."""
        return self._spawn_generic([cmd] + list(args), **kwargs)

    @classmethod
    def _rc_display(cls, rc):
        """Generate a string the summarise a return code."""
        txt = cls._TXT_OK if rc == 0 else cls._TXT_KO
        if sys.stdout.isatty():
            fmt = (cls._FANCY_OK if rc == 0 else cls._FANCY_KO)
        else:
            fmt = '{:s}'
        return fmt.format(txt)

    @abc.abstractmethod
    def check(self):
        """Perform the check this class is expected to perform."""
        pass

    @abc.abstractmethod
    def dumperrors(self):
        """Dump the output of the check if it failed."""
        pass

    @abc.abstractmethod
    def summarise(self):
        """Generate a short summary for this check (SUCCESS/FAILURE)."""
        pass


class AbstractUnitTestChecker(AbstractChecker):
    """Run Vortex's unit-tests using various Python's version."""

    _TEST_SUBDIR = 'tests'

    #: Argument to be added to the nosetests command line
    _DEFAULT_ARGS = []

    #: A list of tests not to be launched in parallel
    _CRITCALTESTS = set()

    #: A list of tests that last a while (they should be run first)
    _LONGTESTS = {'test_names',
                  'test_twistednet',
                  'test_net_ssh.py',
                  'test_algo_server.py',
                  'test_taylorism.py',
                  'test_job_examples.py',
                  'test_uget.py'}

    #: Seconds (the longest test should not last more than...)
    _TIMEOUT = 120

    #: The associated configuration in the configuration file
    _CONFIGFILE_SECTION = ''

    #: The test launcher name
    _TESTLAUNCHER_NAME = ''

    def __init__(self, config):
        """
        :param ContribCheckerConfig config: Configuration data for this run.
        """
        super().__init__(config)
        self._allresults = dict()

    @property
    def _ntasks(self):
        raise NotImplementedError

    @contextlib.contextmanager
    def _spawn_switch(self):
        """Jump into the ``self._testdir`` directory and setup the environment."""
        vtxpath = (os.path.join(self.config.vortexbase, 'src') + ':' +
                   os.path.join(self.config.vortexbase, 'project') + ':' +
                   os.path.join(self.config.vortexbase, 'site') + ':')
        prev_names_tasks = os.environ.get('VORTEX_TEST_NAMES_NTASKS', None)
        prev_pythonpath = os.environ.get('PYTHONPATH', None)
        try:
            os.environ['PYTHONPATH'] = vtxpath
            if prev_pythonpath:
                os.environ['PYTHONPATH'] += ':' + os.environ['PYTHONPATH']
            os.environ['VORTEX_TEST_NAMES_NTASKS'] = '2'
            with super()._spawn_switch():
                yield
        finally:
            if prev_names_tasks is not None:
                os.environ['VORTEX_TEST_NAMES_NTASKS'] = prev_names_tasks
            else:
                del os.environ['VORTEX_TEST_NAMES_NTASKS']
            if prev_pythonpath is not None:
                os.environ['PYTHONPATH'] = prev_pythonpath
            else:
                del os.environ['PYTHONPATH']

    def _spawn(self, cmd, *args, **kwargs):
        """Run the nosetests command and automatically adds some arguments."""
        args = self._DEFAULT_ARGS + list(args)
        return super()._spawn(cmd, *args, **kwargs)

    def _discover_tests(self):
        """Crawl into the tests directory to find the test modules/packages."""
        tests_critical = list()
        tests_long = list()
        tests_packages = list()
        tests_simple = list()
        for item in os.listdir(self._testdir):
            if item.startswith('test_') or item.startswith('tests_'):
                if item in self._LONGTESTS:
                    tests_long.append(item)
                elif item in self._CRITCALTESTS:
                    tests_critical.append(item)
                else:
                    if os.path.isdir(os.path.join(self._testdir, item)):
                        tests_packages.append(item)
                    else:
                        if item.endswith('.py'):
                            tests_simple.append(item)
        return (sorted(tests_critical),
                sorted(tests_long) + sorted(tests_packages) + sorted(tests_simple))

    def check(self):
        """Run Vortex's unit-tests."""
        critical, todo = self._discover_tests()
        # Parallel run of all nose tests
        for nkey, ntester in getattr(self.config, self._CONFIGFILE_SECTION).items():
            logger.info("Starting tests with %s's %s (%s)",
                        nkey, self._TESTLAUNCHER_NAME, ntester)
            self._allresults[nkey] = dict()
            for a_test in critical:
                self._allresults[nkey][a_test] = self._spawn(ntester, a_test)
            with self._spawn_switch():
                with concurrent.futures.ThreadPoolExecutor(
                        max_workers=self._ntasks
                ) as executor:
                    bareresults = executor.map(self._spawn, [ntester, ] * len(todo), todo,
                                               timeout=self._TIMEOUT)
            self._allresults[nkey].update({t: r for t, r in zip(todo, bareresults)})
            logger.info("Done     testing with %s's %s", nkey, self._TESTLAUNCHER_NAME)
        logger.debug('%s overall results:\n%s',
                     self._TESTLAUNCHER_NAME, pprint.pformat(self._allresults))

    def dumperrors(self):
        """Display the test output if something went wrong with a test."""
        for nkey, nresults in self._allresults.items():
            accrc = sum([rc for rc, _ in nresults.values()])
            if accrc:
                print()
                print('Error detected in Unit-tests with Python {:s}:\n'.format(nkey))
                for rc, noutput in nresults.values():
                    if rc:
                        print(noutput + '\n')

    def summarise(self):
        """Summarise the tests results (for each Python's version)."""
        for nkey, nresults in self._allresults.items():
            accrc = sum([r[0] for r in nresults.values()])
            print('[{:s}] Unit-tests with Python {:s} ({:s})'
                  .format(self._rc_display(accrc), nkey, getattr(self.config, self._CONFIGFILE_SECTION)[nkey]))


class NoseChecker(AbstractUnitTestChecker):
    """Run Vortex's unit-tests using various Python's version."""

    #: Argument to be added to the nosetests command line
    _DEFAULT_ARGS = ['--no-byte-compile']

    #: The associated configuration in the configuration file
    _CONFIGFILE_SECTION = 'nosetesters'

    #: The test launcher name
    _TESTLAUNCHER_NAME = 'nose'

    @property
    def _ntasks(self):
        return self.config.nosetests_ntasks

    def _spawn(self, cmd, *args, **kwargs):
        """Run the nosetests command and automatically adds some arguments."""
        args = self._DEFAULT_ARGS + ['--where={:s}'.format(self._testdir)] + list(args)
        return super()._spawn(cmd, *args, **kwargs)


class PyTestChecker(AbstractUnitTestChecker):
    """Run Vortex's unit-tests using various Python's version."""

    #: The associated configuration in the configuration file
    _CONFIGFILE_SECTION = 'pytesters'

    #: The test launcher name
    _TESTLAUNCHER_NAME = 'pytest'

    @property
    def _ntasks(self):
        return self.config.pytests_ntasks

    def _spawn(self, cmd, *args, **kwargs):
        """Run the nosetests command and automatically adds some arguments."""
        args = self._DEFAULT_ARGS + [os.path.join(self._testdir, a) for a in args]
        return super()._spawn(cmd, *args, **kwargs)


class AbstractOneShotChecker(AbstractChecker):
    """
    An abstract "Checker" that runs a single external command and summarise its
    results.

    The :meth:``_spawn_cmdl`` needs to be redefined in the sub-classes.
    """

    #: The check description (used when errors are dumped)
    _DUMP_TXT = 'XXX'
    #: The check description (used when test results are summarised)
    _SUMMARY_TXT = 'XXX'

    def __init__(self, config):
        """
        :param ContribCheckerConfig config: Configuration data for this run.
        """
        super().__init__(config)
        self._result = None

    @abc.abstractmethod
    def _spawn_cmdl(self):
        """Returns an iterable that represents the external command should be run."""
        pass

    def check(self):
        """Launch the external command returned by the :meth:`_spawn_cmdl` method."""
        logger.info("Starting the %s", self._DUMP_TXT)
        with self._spawn_switch():
            self._result = self._spawn(* self._spawn_cmdl())
        logger.info("Done     with the %s", self._DUMP_TXT)

    def dumperrors(self):
        """Display the test output if something went wrong with the external command."""
        if self._result[0]:
            print()
            print('Error detected during {:s}:\n'.format(self._DUMP_TXT))
            print(self._result[1])

    def summarise(self):
        """Summarise the test result."""
        print('[{:s}] {:s}'
              .format(self._rc_display(self._result[0]), self._SUMMARY_TXT))


class StyleChecker(AbstractOneShotChecker):
    """Run the Vortex's code style checker."""

    _DUMP_TXT = 'code style check'
    _SUMMARY_TXT = 'Code Style Check'

    def _spawn_cmdl(self):
        return [self.config.codechecker_interpreter,
                os.path.join(self.config.vortexbase,
                             'project', 'bin', 'vortex_codechecker.py'),
                '--vortexpath={:s}'.format(self.config.vortexbase),
                '--nprocs={:d}'.format(self.config.codechecker_ntasks)]


class DocMissChecker(AbstractOneShotChecker):
    """Run the Vortex's documentation checker."""

    _TEST_SUBDIR = 'sphinx'
    _DUMP_TXT = 'doc completion check'
    _SUMMARY_TXT = 'Doc Completion Check'

    def _spawn_cmdl(self):
        return [self.config.doc_interpreter,
                os.path.join(self.config.vortexbase,
                             'project', 'bin', 'checkdoc.py'),
                '--light', '--fail']


class DocSphinxChecker(AbstractOneShotChecker):
    """Try to build the Vortex' Sphinx documentation and look for warnings."""

    _TEST_SUBDIR = 'sphinx'
    _DUMP_TXT = 'sphinx doc building'
    _SUMMARY_TXT = 'Sphinx Doc Build'
    _BAD_WORDS = ('WARNING', 'ERROR', 'SEVERE')

    @contextlib.contextmanager
    def _spawn_switch(self):
        """Jump into the ``self._testdir`` directory and setup the environment."""
        extrapath = self.config.doc_extrapath
        if extrapath:
            try:
                os.environ['PATH'] = extrapath + ':' + os.environ['PATH']
                with super()._spawn_switch():
                    yield
            finally:
                os.environ['PATH'] = os.environ['PATH'][len(extrapath) + 1:]
        else:
            with super()._spawn_switch():
                yield

    def _spawn_cmdl(self):
        return ['make',
                "PYTHON={:s}".format(self.config.doc_interpreter),
                "SPHINXBUILD={:s}".format(self.config.doc_sphinxbuilder),
                "clean", self.config.doc_buildtarget]

    def check(self):
        """Run the Sphinx documentation build and look for warnings in the output."""
        super().check()
        # Parse the result in order to spot any warning message
        warnings = False
        for line in self._result[1].split('\n'):
            for bad_word in self._BAD_WORDS:
                if (bad_word in line and
                        not re.search(r'The \w+ package is unavailable', line) and
                        not re.search(r'\[epygram.formats\]', line)):
                    warnings = True
        if warnings:
            self._result = (1, self._result[1])


# DEAL WITH THE COMMAND LINE AND RUN THE TESTS --------------------------------


_ARGPARSE_EPILOG = """

This executable relies on a configuration file (.ini format). The default is to
use the ``~/.vortex_contribchecker.ini`` file (however, an alternative location
can be provided on the command-line; see above). It looks like that:

; The commented entries corresponds to default values (they are mentioned here
; for documentation purposes).

[settings]
; Whether to launch the various checks in parallel
;parallel_firstlevel=True
; During unit-testing with nose, the number of parallel threads to be used
;nosetests_ntasks=3
; During the codestyle check, the number of parallel tasks to be used
;codechecker_ntasks=1
; The nice value adjustment for this process (and its children)
;nicevalue=15


; The various nosetests executables that will be used to launch the unit-tests
; It looks like:
; label=path_to_nosetests
;
; The label is only used when printing the final summary (and logs)
[nosetesters]
v3.7=/usr/bin/nosetests-3.7
v2.7=/usr/bin/nosetests-2.7


; The configuration related to codestyle checking
[codechecker]
; The path to the Python's interpreter to be used when performing the
; codestyle check. If this entry is omitted, no code style check will
; be performed
interpreter=/usr/bin/python3


; The configuration related to the documentation building
[doc]
; The path to the Python's interpreter to be used when checking and
; building the documentation. If this entry is omitted, documentation
; check and build will not be performed
interpreter=/usr/bin/python3
; The path to the sphinx-build utility used when building the
; documentation. If this entry is omitted, the documentation
; will not be built.
sphinxbuilder=/usr/bin/sphinx-build
; The makefile target to use when building the documentation.
;buildtarget=html
; An extra directory to be added to the system's PATH (for things like pandoc)
;extrapath=

"""


def main():
    """Process command line options."""

    program_name = os.path.basename(sys.argv[0])
    program_shortdesc = program_name + ' -- ' + __import__('__main__').__doc__.lstrip("\n")
    program_desc = program_shortdesc

    # Setup argument parser
    parser = ArgumentParser(description=program_desc, epilog=_ARGPARSE_EPILOG,
                            formatter_class=RawDescriptionHelpFormatter)

    parser.add_argument("-v", "--verbose", dest="verbose", action="count",
                        default=0, help="Set verbosity level [default: %(default)s]")
    parser.add_argument("-c", "--config", dest="config", action="store",
                        default=_CONF_DEFAULT,
                        help="Configuration file location [default: %(default)s]")
    parser.add_argument("-p", "--vortexpath", dest="vortexpath", action="store",
                        default=_VTXBASE,
                        help="Vortex repository location [default: %(default)s]")

    # Process arguments
    args = parser.parse_args()

    # Setup logger verbosity
    log_levels = {0: 'WARNING', 1: 'INFO', 2: 'DEBUG'}
    mylog_levels = log_levels.get(args.verbose, 'DEBUG')
    logger.setLevel(mylog_levels)

    # Configuration data
    confdata = ContribCheckerConfig(args.vortexpath)
    try:
        with open(args.config, 'r') as fhc:
            confdata.read_file(fhc, source=args.config)
    except (IOError, OSError):
        logger.error("Could not open the configuration file '%s'", args.config)
        raise

    # Adjust the nice value
    os.nice(confdata.nicevalue)

    checkers = list()
    if confdata.doc_buildtarget:
        checkers.append(DocSphinxChecker(confdata))
    if confdata.nosetesters:
        checkers.append(NoseChecker(confdata))
    if confdata.pytesters:
        checkers.append(PyTestChecker(confdata))
    if confdata.doc_interpreter:
        checkers.append(DocMissChecker(confdata))
    if confdata.codechecker_interpreter:
        checkers.append(StyleChecker(confdata))

    max_workers = None if confdata.do_parallel else 1
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(checker.check) for checker in checkers]
        concurrent.futures.wait(futures)

    for checker in checkers:
        checker.dumperrors()
    print()
    for checker in checkers:
        checker.summarise()
    print()


if __name__ == "__main__":
    sys.exit(main())
