#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This modules defines the low level physical layout for data handling.
"""

#: No automatic export.
__all__ = []

import re
import collections
from collections import namedtuple, defaultdict
import json

import footprints
logger = footprints.loggers.getLogger(__name__)

from footprints.util import mktuple
from vortex.util.structs import Utf8PrettyPrinter


class SectionFatalError(Exception):
    """Exception when fatal mode is activated."""
    pass

#: Definition of a named tuple INTENT
IntentTuple = namedtuple('IntentTuple', ['IN', 'OUT', 'INOUT'], verbose=False)

#: Predefined INTENT values IN, OUT and INOUT.
intent = IntentTuple(IN='in', OUT='out', INOUT='inout')

#: Definition of a named tuple IXO sequence
IXOTuple = namedtuple('IXOTuple', ['INPUT', 'OUTPUT', 'EXEC'], verbose=False)

#: Predefined IXO sequence values INPUT, OUTPUT and EXEC.
ixo = IXOTuple(INPUT=1, OUTPUT=2, EXEC=3)

#: Arguments specific to a section (to be striped away from a resource handler description)
section_args = [ 'role', 'alternate', 'intent', 'fatal' ]


def stripargs_section(**kw):
    """
    Utility function to separate the named arguments in two parts: the one that describe section options
    and any other ones. Return a tuple with ( section_options, other_options ).
    """
    opts = dict()
    for opt in [ x for x in section_args if x in kw ]:
        opts[opt] = kw.pop(opt)
    return ( opts, kw )


class Section(object):
    """Low level unit to handle a resource."""

    def __init__(self, **kw):
        logger.debug('Section initialisation %s', self)
        self.kind       = ixo.INPUT
        self.intent     = intent.INOUT
        self.fatal      = True
        self.role       = kw.get('role', None)
        self.alternate  = None
        self.rh         = None
        self.stages     = [ kw.pop('stage', 'void') ]
        self.__dict__.update(kw)
        if self.rh:
            if self.rh.role and not self.role:
                self.role = self.rh.role
            if self.rh.alternate:
                self.alternate = self.rh.alternate
            self.rh.role = self.role
            self.rh.alternate = self.alternate

    @property
    def stage(self):
        """The last stage of the current section."""
        return self.stages[-1]

    def _updignore(self, info):
        """Fake function for undefined information driven updates."""
        logger.warning('Unable to update %s with info %s', self, info)

    def _updstage_get(self, info):
        """Upgrade current section to 'get' level."""
        if info.get('stage') == 'get' and self.kind in (ixo.INPUT, ixo.EXEC):
            self.stages.append('get')

    def _updstage_expected(self, info):
        """Upgrade current section to 'expected' level."""
        if info.get('stage') == 'expected' and self.kind in (ixo.INPUT, ixo.EXEC):
            self.stages.append('expected')

    def _updstage_put(self, info):
        """Upgrade current section to 'put' level."""
        if info.get('stage') == 'put' and self.kind == ixo.OUTPUT:
            self.stages.append('put')

    def _updstage_ghost(self, info):
        """Upgrade current section to 'ghost' level."""
        if info.get('stage') == 'ghost' and self.kind == ixo.OUTPUT:
            self.stages.append('ghost')

    def updstage(self, info):
        """Upgrade current section level according to information given in dict ``info``."""
        updmethod = getattr(self, '_updstage_' + info.get('stage'), self._updignore)
        updmethod(info)

    def get(self, **kw):
        """Shortcut to resource handler :meth:`~vortex.data.handlers.get`."""
        rc = False
        if self.kind == ixo.INPUT or self.kind == ixo.EXEC:
            kw['intent'] = self.intent
            try:
                rc = self.rh.get(**kw)
            except StandardError as e:
                logger.error('Something wrong (input section): %s', e)
                logger.error('Resource %s', self.rh.locate())
            if not rc and self.fatal:
                logger.critical('Fatal error with action get %s', self.rh.locate())
                raise SectionFatalError('Could not get resource [%s]' % str(rc))
        else:
            logger.error('Try to get from an output section')
        return rc

    def put(self, **kw):
        """Shortcut to resource handler :meth:`~vortex.data.handlers.put`."""
        rc = False
        if self.kind == ixo.OUTPUT:
            kw['intent'] = self.intent
            try:
                rc = self.rh.put(**kw)
            except Exception as e:
                logger.error('Something wrong (output section): %s', e)
                logger.error('Resource %s', self.rh.locate())
                raise
            if not rc and self.fatal:
                logger.critical('Fatal error with action put %s', self.rh.locate())
                raise SectionFatalError('Could not put resource [%s]', str(rc))
        else:
            logger.error('Try to put from an input section.')
        return rc

    def show(self, **kw):
        """Nice dump of the section attributes and contents."""
        for k, v in sorted(vars(self).items()):
            if k != 'rh':
                print ' ', k.ljust(16), ':', v
        self.rh.quickview(indent=1)


class Sequence(object):
    """
    Logical sequence of sections such as inputs or outputs sections.
    Instances are iterable and callable.
    """

    def __init__(self, *args, **kw):
        logger.debug('Sequence initialisation %s', self)
        self.sections = list()

    def __iter__(self):
        for s in self.sections:
            yield s

    def __call__(self):
        return self.sections[:]

    def clear(self):
        """Clear the internal list of sections."""
        self.sections = list()

    def add(self, candidate):
        """
        Push the ``candidate`` to the internal list of sections
        as long as it is a :class:`Section` object.
        """
        if isinstance(candidate, Section):
            self.sections.append(candidate)
        else:
            logger.warning('Try to add a non-section object %s in sequence %s', candidate, self)

    def remove(self, candidate):
        """
        Remove the ``candidate`` from the internal list of sections
        as long as it is a :class:`Section` object.
        """
        if isinstance(candidate, Section):
            self.sections.remove(candidate)
        else:
            logger.warning('Try to remove a non-section object %s in sequence %s', candidate, self)

    def section(self, **kw):
        """Section factory wrapping a given ``rh`` (Resource Handler)."""
        rhset = kw.get('rh', list())
        if type(rhset) != list:
            rhset = [ rhset ]
        ralter = kw.get('alternate', kw.get('role', 'anonymous'))
        newsections = list()
        for rh in rhset:
            kw['rh'] = rh
            this_section = Section(**kw)
            self.add(this_section)
            newsections.append(this_section)
            kw['alternate'] = ralter
            if 'role' in kw:
                del kw['role']
        return newsections

    def input(self, **kw):
        """Create a section with default kind equal to ``ixo.INPUT``."""
        if 'kind' in kw:
            del kw['kind']
        kw.setdefault('intent', intent.IN)
        return self.section(kind=ixo.INPUT, **kw)

    def output(self, **kw):
        """Create a section with default kind equal to ``ixo.OUTPUT`` and intent equal to ``intent.OUT``."""
        if 'kind' in kw:
            del kw['kind']
        kw.setdefault('intent', intent.OUT)
        return self.section(kind=ixo.OUTPUT, **kw)

    def executable(self, **kw):
        """Create a section with default kind equal to to ``ixo.EXEC``."""
        if 'kind' in kw:
            del kw['kind']
        kw.setdefault('intent', intent.IN)
        return self.section(kind=ixo.EXEC, **kw)

    def inputs(self):
        """Return a list of current sequence sections with ``ixo.INPUT`` or ``ixo.EXEC`` kind."""
        return [ x for x in self.sections if ( x.kind == ixo.INPUT or x.kind == ixo.EXEC ) ]

    def inputs_report(self):
        """Return a SequenceInputsReport object built using the current sequence."""
        return SequenceInputsReport(self.inputs())

    @staticmethod
    def _fuzzy_match(stuff, allowed):
        '''Check if ``stuff`` is in ``allowed``. ``allowed`` may contain regex.'''
        if (isinstance(allowed, basestring) or
                not isinstance(allowed, collections.Iterable)):
            allowed = [allowed, ]
        for pattern in allowed:
            if ((isinstance(pattern, re._pattern_type) and pattern.search(stuff)) or
                    (pattern == stuff)):
                return True
        return False

    def effective_inputs(self, **kw):
        """
        Walk through the inputs of the current sequence which reach the 'get' stage.
        If a ``role`` or ``kind`` (or both) is provided as named argument,
        it operates as a filter on the inputs list. If both keys are available
        the ``role`` applies first, and then the ``kind`` in case of empty match.

        The ``role`` or ``kind`` named arguments are lists that may contain
        strings and/or compiled regular expressions. Regular expressions are c
        hecked against the input's attributes using the 'search' function
        (i.e.  ^ should be explicitely added if one wants to match the begining
        of the string).
        """
        inset = [ x for x in self.inputs() if ( x.stage == 'get' or x.stage == 'expected' ) and x.rh.container.exists() ]
        if not kw:
            return inset
        inrole = list()
        inkind = list()
        if 'role' in kw and kw['role'] is not None:
            selectrole = mktuple(kw['role'])
            inrole = [ x for x in inset if (self._fuzzy_match(x.role, selectrole) or
                                            self._fuzzy_match(x.alternate, selectrole)) ]
        if not inrole and 'kind' in kw:
            selectkind = mktuple(kw['kind'])
            inkind = [ x for x in inset if self._fuzzy_match(x.rh.resource.realkind, selectkind) ]
        return inrole or inkind

    def executables(self):
        """Return a list of current sequence sections with ``ixo.EXEC`` kind."""
        return [ x for x in self.sections if ( x.kind == ixo.EXEC ) ]

    def outputs(self):
        """Return a list of current sequence sections with ``ixo.OUTPUT`` kind."""
        return [ x for x in self.sections if x.kind == ixo.OUTPUT ]

    def effective_outputs(self, **kw):
        """
        Walk through the outputs of the current sequence whatever the stage value is.
        If a ``role`` or ``kind`` (or both) is provided as named argument,
        it operates as a filter on the inputs list. If both keys are available
        the ``role`` applies first, and then the ``kind`` in case of empty match.
        """
        outset = self.outputs()
        if not kw:
            return outset
        outrole = list()
        outkind = list()
        if 'role' in kw and kw['role'] is not None:
            selectrole = mktuple(kw['role'])
            outrole = [ x for x in outset if x.role in selectrole ]
        if not outrole and 'kind' in kw:
            selectkind = mktuple(kw['kind'])
            outkind = [ x for x in outset if x.rh.resource.realkind in selectkind ]
        return outrole or outkind or outset


class SequenceInputsReport(object):
    """Summarize data about inputs (missing resources, alternates, ...)."""

    _StatusTupple = namedtuple('_StatusTupple',
                               ('PRESENT', 'EXPECTED', 'MISSING'))
    _Status = _StatusTupple(PRESENT='present', EXPECTED='expected',
                            MISSING='missing')
    _TranslateStage = dict(get=_Status.PRESENT,
                           expected=_Status.EXPECTED,
                           void=_Status.MISSING,
                           load=_Status.MISSING)

    def __init__(self, inputs):
        self._local_map = defaultdict(lambda: defaultdict(list))
        for insec in inputs:
            local = insec.rh.container.localpath()
            # Determine if the current section is an alternate or not...
            kind = 'alternate' if insec.alternate is not None else 'nominal'
            self._local_map[local][kind].append(insec)

    def _local_status(self, local):
        '''Find out the local resource status (see _Status).

        It returns a tupple that contains:

        * The local resource status (see _Status)
        * The resource handler that was actually used to get the resource
        * The resource handler that should have been used in the nominal case
        '''
        desc = self._local_map[local]
        # First, check the nominal resource
        nominal = desc['nominal'][-1]
        status = self._TranslateStage[nominal.stage]
        true_rh = None
        # Look for alternates:
        if status == self._Status.MISSING:
            for alter in desc['alternate']:
                alter_status = self._TranslateStage[alter.stage]
                if alter_status != self._Status.MISSING:
                    status = alter_status
                    true_rh = alter.rh
                    break
        else:
            true_rh = nominal.rh
        return status, true_rh, nominal.rh

    def synthetic_report(self, detailed=False):
        '''Returns a string that decribes each local resource with its status.

        :param detailed: when alternates are used, tell which resource handler
                         is actualy used and which one should have been used in
                         the nominal case.
        '''
        outstr = ''
        for local in sorted(self._local_map):
            status, true_rh, nominal_rh = self._local_status(local)
            extrainfo = ''
            if status != self._Status.MISSING and (true_rh is not nominal_rh):
                extrainfo = '(ALTERNATE USED)'
            outstr += "* {:8s} {:16s} : {:s}\n".format(status, extrainfo, local)
            if detailed and extrainfo != '':
                outstr += "  * The following resource is used:\n"
                outstr += true_rh.idcard(indent=6) + "\n"
                outstr += "  * Instead of:"
                outstr += nominal_rh.idcard(indent=6) + "\n"
        return outstr

    def print_report(self, detailed=False):
        '''Print a list of each local resource with its status.

        :param detailed: when alternates are used, tell which resource handler
                         is actualy used and which one should have been used in
                         the nominal case.
        '''
        print self.synthetic_report(detailed=detailed)

    def active_alternates(self):
        '''List the local resource for which an alternative resource has been used.

        It returns a dictionary that associates the local resource name with
        a tuple that contains:

        * The resource handler that was actually used to get the resource
        * The resource handler that should have been used in the nominal case
        '''
        outstack = dict()
        for local in self._local_map:
            status, true_rh, nominal_rh = self._local_status(local)
            if status != self._Status.MISSING and (true_rh is not nominal_rh):
                outstack[local] = (true_rh, nominal_rh)
        return outstack

    def missing_resources(self):
        '''List the missing local resources.'''
        outstack = dict()
        for local in self._local_map:
            (status, true_rh,  # @UnusedVariable
             nominal_rh) = self._local_status(local)
            if status == self._Status.MISSING:
                outstack[local] = nominal_rh
        return outstack


class LocalTrackerEntry(object):
    """Holds the data for a given local container.

    It includes data for two kinds of "actions": get/put. For each "action",
    Involved resource handlers, hook functions calls and get/put from low level
    stores are tracked.
    """

    _actions = ('get', 'put',)
    _internals = ('rhdict', 'hook', 'uri')

    def __init__(self):
        self._data = dict()
        for internal in self._internals:
            self._data[internal] = {act: list() for act in self._actions}

    @classmethod
    def _check_action(cls, action):
        return action in cls._actions

    @staticmethod
    def _jsonize(stuff):
        """Make 'stuff' comparable to the result of a json.load."""
        return json.loads(json.dumps(stuff))

    def _clean_uri(self, store, remote):
        return self._jsonize(dict(scheme=store.scheme, netloc=store.netloc,
                                  path=remote['path'], params=remote['params'],
                                  query=remote['query'], fragment=remote['fragment']))

    def _clean_rhdict(self, rhdict):
        if 'options' in rhdict:
            del rhdict['options']
        return self._jsonize(rhdict)

    def update_rh(self, rh, info):
        """Update the entry based on data received from the observer board.

        This method is to be called with data originated from the
        Resources-Handlers observer board (when updates are notified).

        :param rh: :class:`~vortex.data.handlers.Handler` object that sends the update.
        :param info: Info dictionary sent by the :class:`~vortex.data.handlers.Handler` object
        """
        stage = info['stage']
        if self._check_action(stage):
            if 'hook' in info:
                self._data['hook'][stage].append(self._jsonize((info['hook'])))
            elif not info.get('insitu', False):
                # We are using as_dict since this may be written to a JSON file
                self._data['rhdict'][stage].append(self._clean_rhdict(rh.as_dict()))

    def update_store(self, store, info):
        """Update the entry based on data received from the observer board.

        This method is to be called with data originated from the
        Stores-Activity observer board (when updates are notified).

        :param store: :class:`~vortex.data.stores.Store` object that sends the update.
        :param info: Info dictionary sent by the :class:`~vortex.data.stores.Store` object
        """
        action = info['action']
        # Only known action and successfull attempts
        if self._check_action(action) and info['status']:
            self._data['uri'][action].append(self._clean_uri(store, info['remote']))

    def dump_as_dict(self):
        """Export the entry as a dictionary."""
        return self._data

    def load_from_dict(self, dumpeddict):
        """Restore the entry from a previous export.

        :param dumpeddict: Dictionary that will be loaded (usually generated by
            the :meth:`dump_as_dict` method)
        """
        self._data = dumpeddict

    def append(self, anotherentry):
        """Append the content of another LocalTrackerEntry object into this one."""
        for internal in self._internals:
            for act in self._actions:
                self._data[internal][act].extend(anotherentry._data[internal][act])

    def latest_rhdict(self, action):
        """Return the dictionary that represents the latest :class:`~vortex.data.handlers.Handler` object involved.

        :param action: Action that is considered.
        """
        if self._check_action(action) and self._data['rhdict'][action]:
            return self._data['rhdict'][action][-1]
        else:
            return dict()

    def match_rh(self, action, rh):
        """Check if an :class:`~vortex.data.handlers.Handler` object matches the one stored internally.

        :param action: Action that is considered
        :param rh: :class:`~vortex.data.handlers.Handler` object that will be checked
        """
        if self._check_action(action):
            return self.latest_rhdict(action) == self._clean_rhdict(rh.as_dict())
        else:
            return False

    def check_uri_remote_delete(self, store, remote):
        """Called when a :class:`~vortex.data.stores.Store` object notifies a delete.

        The URIs stored for the "put" action are checked against the delete
        request. If a match is found, the URI is deleted.

        :param store: :class:`~vortex.data.stores.Store` object that requested the delete
        :param remote: Remote path to the deleted resource
        """
        theuri = self._clean_uri(store, remote)
        while theuri in self._data['uri']['put']:
            self._data['uri']['put'].remove(theuri)

    def _redundant_stuff(self, internal, action, stuff):
        if self._check_action(action):
            return stuff in self._data[internal][action]
        else:
            return False

    def redundant_hook(self, action, hookname):
        """Check of a hook function has already been applied.

        :param action: Action that is considered.
        :param hookname: Name of the Hook function that will be checked.
        """
        return self._redundant_stuff('hook', action, self._jsonize(hookname))

    def redundant_uri(self, action, store, remote):
        """Check if an URI has already been processed.

        :param action: Action that is considered.
        :param store: :class:`~vortex.data.stores.Store` object that will be checked.
        :param remote: Remote path that will be checked.
        """
        return self._redundant_stuff('uri', action, self._clean_uri(store, remote))

    def _grep_stuff(self, internal, action, skeleton=dict()):
        stack = []
        for element in self._data[internal][action]:
            if isinstance(element, collections.Mapping):
                succeed = True
                for key, val in skeleton.iteritems():
                    succeed = succeed and ((key in element) and (element[key] == val))
                if succeed:
                    stack.append(element)
        return stack

    def __str__(self):
        out = ''
        for action in self._actions:
            for internal in self._internals:
                if len(self._data[internal][action]) > 0:
                    out += "+ {:4s} / {}\n{}\n".format(action.upper(), internal,
                                                       Utf8PrettyPrinter().pformat(self._data[internal][action]))
        return out


class LocalTracker(defaultdict):
    """Dictionary like structure that gathers data on the various local containers.

    For each local container (identified by the result of its iotarget method), a
    dictionary entry is created. Its value is a :class:`~vortex.layout.dataflow.LocalTrackerEntry`
    object.
    """

    _default_json_filename = 'local-tracker-state.json'

    def __missing__(self, key):
        self[key] = LocalTrackerEntry()
        return self[key]

    def update_rh(self, rh, info):
        """Update the object based on data received from the observer board.

        This method is to be called with data originated from the
        Resources-Handlers observer board (when updates are notified).

        :param rh: :class:`~vortex.data.handlers.Handler` object that sends the update.
        :param info: Info dictionary sent by the :class:`~vortex.data.handlers.Handler` object
        """
        lpath = rh.container.iotarget()
        if isinstance(lpath, basestring):
            self[lpath].update_rh(rh, info)
        else:
            logger.info("The iotarget isn't a basestring: It will be skipped in %s",
                        self.__class__)

    def update_store(self, store, info):
        """Update the object based on data received from the observer board.

        This method is to be called with data originated from the
        Stores-Activity observer board (when updates are notified).

        :param store: :class:`~vortex.data.stores.Store` object that sends the update.
        :param info: Info dictionary sent by the :class:`~vortex.data.stores.Store` object
        """
        lpath = info.get('local', None)
        if lpath is None:
            # Check for file deleted on the remote side
            if info['action'] == 'del' and info['status']:
                for atracker in self.itervalues():
                    atracker.check_uri_remote_delete(store, info['remote'])
        else:
            if isinstance(lpath, basestring):
                self[lpath].update_store(store, info)
            else:
                logger.info("The iotarget isn't a basestring: It will be skipped in %s",
                            self.__class__)

    def is_tracked_input(self, local):
        """Check if the given `local` container is listed as an input and associated with a valid :class:`~vortex.data.handlers.Handler`.

        :param local: Local name of the input that will be checked
        """
        return (isinstance(local, basestring) and
                (local in self) and
                (self[local].latest_rhdict('get')))

    def _grep_stuff(self, internal, action, skeleton=dict()):
        stack = []
        for entry in self.itervalues():
            stack.extend(entry._grep_stuff(internal, action, skeleton))
        return stack

    def grep_uri(self, action, skeleton=dict()):
        """Returns all the URIs that contains the same key/values than `skeleton`.

        :param action: Action that is considered.
        :param skeleton: Dictionary that will be used as a search pattern
        """
        return self._grep_stuff('uri', action, skeleton)

    def json_dump(self, filename=_default_json_filename):
        """Dump the object to a JSON file.

        :param filename: Path to the JSON file.
        """
        outdict = {loc: entry.dump_as_dict() for loc, entry in self.iteritems()}
        with file(filename, 'w') as fpout:
            json.dump(outdict, fpout, indent=2, sort_keys=True)

    def json_load(self, filename=_default_json_filename):
        """Restore the object using a JSON file.

        :param filename: Path to the JSON file.
        """
        with file(filename, 'r') as fpin:
            indict = json.load(fpin)
        # Start from scratch
        self.clear()
        for loc, adict in indict.iteritems():
            self[loc].load_from_dict(adict)

    def append(self, othertracker):
        """Append the content of another LocalTracker object into this one."""
        for loc, entry in othertracker.iteritems():
            self[loc].append(entry)

    def __str__(self):
        out = ''
        for loc, entry in self.iteritems():
            entryout = str(entry)
            if entryout:
                out += "========== {} ==========\n{}".format(loc, entryout)
        return out
