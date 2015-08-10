#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
This modules defines the low level physical layout for data handling.
"""

#: No automatic export.
__all__ = []

from collections import namedtuple

import footprints
logger = footprints.loggers.getLogger(__name__)

from footprints.util import mktuple


class SectionFatalError(StandardError):
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

    def updignore(self, info):
        """Fake function for undefined information driven updates."""
        logger.warning('Unable to update %s with info %s', self, info)

    def updstage_get(self, info):
        """Upgrade current section to 'get' level."""
        if info.get('stage') == 'get' and self.kind == ixo.INPUT:
            self.stages.append('get')

    def updstage_expected(self, info):
        """Upgrade current section to 'expected' level."""
        if info.get('stage') == 'expected' and self.kind == ixo.INPUT:
            self.stages.append('expected')

    def updstage_put(self, info):
        """Upgrade current section to 'put' level."""
        if info.get('stage') == 'put' and self.kind == ixo.OUTPUT:
            self.stages.append('put')

    def updstage_ghost(self, info):
        """Upgrade current section to 'ghost' level."""
        if info.get('stage') == 'ghost' and self.kind == ixo.OUTPUT:
            self.stages.append('ghost')

    def updstage(self, info):
        """Upgrade current section level according to information given in dict ``info``."""
        updmethod = getattr(self, 'updstage_' + info.get('stage'), self.updignore)
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
        """Nice dump of the section attributs and contents."""
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

    def effective_inputs(self, **kw):
        """
        Walk through the inputs of the current sequence which reach the 'get' stage.
        If a ``role`` or ``kind`` (or both) is provided as named argument,
        it operates as a filter on the inputs list. If both keys are available
        the ``role`` applies first, and then the ``kind`` in case of empty match.
        """
        inset = [ x for x in self.inputs() if ( x.stage == 'get' or x.stage == 'expected' ) and x.rh.container.exists() ]
        if not kw:
            return inset
        inrole = list()
        inkind = list()
        if 'role' in kw and kw['role'] is not None:
            selectrole = mktuple(kw['role'])
            inrole = [ x for x in inset if x.role in selectrole or x.alternate in selectrole ]
        if not inrole and 'kind' in kw:
            selectkind = mktuple(kw['kind'])
            inkind = [ x for x in inset if x.rh.resource.realkind in selectkind ]
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
