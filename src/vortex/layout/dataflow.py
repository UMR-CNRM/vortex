#!/bin/env python
# -*- coding: utf-8 -*-

r"""
This modules defines the low level physical layout for data handling.
"""

#: No automatic export.
__all__ = []

from vortex.autolog import logdefault as logger
from collections import namedtuple, _itemgetter


#: Definition of a named tuple INTENT
IntentTuple = namedtuple('IntentTuple', ['IN', 'OUT', 'INOUT'], verbose=False)

#: Predefined INTENT values IN, OUT and INOUT.
intent = IntentTuple(IN=1, OUT=2, INOUT=3)

#: Definition of a named tuple IXO sequence
IXOTuple = namedtuple('IXOTuple', ['INPUT', 'OUTPUT', 'EXEC'], verbose=False)

#: Predefined IXO sequence values INPUT, OUTPUT and EXEC.
ixo = IXOTuple(INPUT=1, OUTPUT=2, EXEC=3)


def stripargs_section(**kw):
    """
    Utility function to separate the named arguments in two parts: the one that describe section options
    and any other ones. Return a tuple with ( section_options, other_options ).
    """
    opts = dict()
    for opt in filter(lambda x: x in kw, ( 'role', 'alternate', 'intent' )):
        opts[opt] = kw[opt]
        del kw[opt]
    return ( opts, kw )


class Section(object):
    """Low level unit to handle a resource."""

    def __init__(self, **kw):
        logger.debug('Section initialisation %s', self)
        self.kind      = ixo.INPUT
        self.intent    = intent.INOUT
        self.role      = kw.get('role', None)
        self.alternate = None
        self.rh        = None
        self.stages    = [ kw.get('stage', 'void') ]
        if 'stage' in kw: del kw['stage']
        self.__dict__.update(kw)
        if self.rh:
            if self.rh.role and not self.role: self.role = self.rh.role
            if self.rh.alternate: self.alternate = self.rh.alternate
            self.rh.role = self.role
            self.rh.alternate = self.alternate

    @property
    def stage(self):
        """The last stage of the current section."""
        return self.stages[-1]

    def updignore(self, info):
        """Fake function for undefined information driven updates."""
        logger.warning('Unable to update %s with info %s', self, info)

    def updstage_get(self, info):
        """Upgrade current section to 'get' level."""
        if info.get('stage') == 'get' and self.kind == ixo.INPUT:
            self.stages.append('get')

    def updstage_put(self, info):
        """Upgrade current section to 'put' level."""
        if info.get('stage') == 'put' and self.kind == ixo.OUTPUT:
            self.stages.append('put')

    def updstage(self, info):
        """Upgrade current section level according to information given in dict ``info``."""
        updmethod = getattr(self, 'updstage_' + info.get('stage'), self.updignore)
        updmethod(info)


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
        rhset = kw.get('rh', list())
        if type(rhset) != list: rhset = [ rhset ]
        ralter = kw.get('alternate', kw.get('role', 'anonymous'))
        for rh in rhset:
            kw['rh'] = rh
            self.add(Section(**kw))
            kw['alternate'] = ralter
            if 'role' in kw: del kw['role']

    def input(self, **kw):
        """Create a section with default kind equal to ``ixo.INPUT``."""
        self.section(kind=ixo.INPUT, **kw)

    def output(self, **kw):
        """Create a section with default kind equal to ``ixo.OUTPUT`` and intent equal to ``intent.OUT``."""
        self.section(kind=ixo.OUTPUT, intent=intent.OUT, **kw)

    def inputs(self):
        """Return a list of current sequence sections with ``ixo.INPUT`` kind."""
        return [ x for x in self.sections if x.kind == ixo.INPUT ]

    def effective_inputs(self, **kw):
        """
        Walk through the inputs of the current sequence which reach the 'get' stage.
        If a ``role`` or ``kind`` (or both) is provided as named argument,
        it operates as a filter on the inputs list. If both keys are available
        the ``role`` applies first, and then the ``kind`` in case of empty match.
        """
        inset = filter(lambda x: x.stage == 'get', self.inputs())
        if not kw: return inset
        inrole = list()
        inkind = list()
        if 'role' in kw:
            inrole = filter(lambda x: x.role == kw['role'] or x.alternate == kw['role'], inset)
        if not inrole and 'kind' in kw:
            inkind = filter(lambda x: x.rh.resource.realkind() == kw['kind'], inset)
        return inrole or inkind

    def outputs(self):
        """Return a list of current sequence sections with ``ixo.OUTPUT`` kind."""
        return [ x for x in self.sections if x.kind == ixo.OUTPUT ]

    def effective_outputs(self, **kw):
        """
        Wakl through the outputs of the current sequence whatever the stage value is.
        If a ``role`` or ``kind`` (or both) is provided as named argument,
        it operates as a filter on the inputs list. If both keys are available
        the ``role`` applies first, and then the ``kind`` in case of empty match.
        """
        outset = self.outputs()
        if not kw: return outset
        outrole = list()
        outkind = list()
        if 'role' in kw:
            outrole = filter(lambda x: x.role == kw['role'], outset)
        if not outrole and 'kind' in kw:
            outkind = filter(lambda x: x.rh.resource.realkind() == kw['kind'], outset)
        return outrole or outkind or outset


