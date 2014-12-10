#!/usr/bin/env python
# -*- coding: utf-8 -*-

r"""
This modules defines the physical layout.
"""

#: No automatic export.
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.util.structs import Tracker
from vortex.tools.env    import Environment

from . import dataflow


# Module Interface

def get(**kw):
    """Return actual context object matching description."""
    return Context(**kw)

def keys():
    """Return the list of current context tags."""
    return Context.tag_keys()

def values():
    """Return the list of current context values."""
    return Context.tag_values()

def items():
    """Return the items of the contexts table."""
    return Context.tag_items()

def focus():
    """Return the context with the focus on, if any."""
    tf = Context.tag_focus()
    if tf is not None:
        tf = Context(tag=tf)
    return tf


class Context(footprints.util.GetByTag):
    """Physical layout of a session or task, etc."""

    _tag_default = 'ctx'

    def __init__(self, path=None, topenv=None, sequence=None, task=None):
        """Initate a new execution context."""
        logger.debug('Context initialisation %s', self)
        if path is None:
            logger.critical('Try to define a new context without virtual path')
            raise ValueError('No virtual path given to new context.')
        self._env      = Environment(env=topenv, active=topenv.active)
        self._path     = path + '/' + self.tag
        self._session  = None
        self._rundir   = None
        self._task     = task
        self._void     = True
        self._stamp    = '-'.join(('vortex', 'stamp', self.tag, str(id(self))))
        self._fstore   = dict()
        self._cocooned = False

        if sequence:
            self._sequence = sequence
            self._void = False
        else:
            self._sequence = dataflow.Sequence()

        self.bind(self._task)
        footprints.observers.get(tag='Resources-Handlers').register(self)

    def newobsitem(self, item, info):
        """
        Resources-Handlers observing facility.
        Register a new section in void active context with the resource handler ``item``.
        """
        logger.debug('Notified %s new item %s', self, item)
        if self.void and self.has_focus():
            self._sequence.section(rh=item, stage='load')

    def delobsitem(self, item, info):
        """
        Resources-Handlers observing facility.
        Should removed the associated section. Yet to be coded.
        """
        if self.has_focus():
            logger.debug('Notified %s del item %s', self, item)

    def updobsitem(self, item, info):
        """
        Resources-Handlers observing facility.
        Track the new stage of the section containing the resource handler ``item``.
        """
        if self.has_focus():
            logger.debug('Notified %s upd item %s', self, item)
            for section in self._sequence:
                if section.rh == item:
                    section.updstage(info)

    @property
    def path(self):
        """Return the virtual path of the current context."""
        return self._path

    @property
    def session(self):
        """Return the session bound to the current virtual context path."""
        if self._session is None:
            from vortex import sessions
            self._session = sessions.get(tag = [ x for x in self.path.split('/') if x ][0])
        return self._session

    def _get_rundir(self):
        """Return the path of the directory associated to that context."""
        return self._rundir

    def _set_rundir(self, path):
        """Set a new rundir."""
        if self._rundir:
            logger.warning('Context <%s> is changing its workding directory <%s>', self.tag, self._rundir)
        if self.system.path.isdir(path):
            self._rundir = path
            logger.info('Context <%s> set rundir <%s>', self.tag, self._rundir)
        else:
            logger.error('Try to change context <%s> to invalid path <%s>', self.tag, path)

    rundir = property(_get_rundir, _set_rundir)

    def cocoon(self):
        """Change directory to the one associated to that context."""
        if self._rundir is None:
            subpath = self.path.replace(self.session.path, '', 1)
            self._rundir = self.session.rundir + subpath
        self.system.cd(self._rundir, create=True)
        self._cocooned = True

    @property
    def cocooned(self):
        """Check if the current context had cocooned."""
        return self._cocooned

    @property
    def void(self):
        """
        Return whether the current context is a void context, and therefore not bound to a task.
        One may be aware that this value could be temporarly overwritten through the record on/off mechanism.
        """
        return self._void

    @property
    def env(self):
        """Return the :class:`~vortex.tools.env.Environment` object associated to that context."""
        return self._env

    @property
    def system(self):
        """Return the :class:`~vortex.tools.env.System` object associated to the root session."""
        return self.session.system()

    @property
    def task(self):
        """Return the possibly bound task."""
        return self._task

    @property
    def sequence(self):
        """Return the :class:`~vortex.layout.dataflow.Sequence` object associated to that context."""
        return self._sequence

    @property
    def bound(self):
        """Boolean property to check whether the current context is bound to a task or not."""
        return bool(self._task)

    def bind(self, task, **kw):
        """
        Bind the current context to the specified ``task``.
        The task sequence becomes the current context sequence.
        """
        if task and hasattr(task, 'sequence'):
            logger.info('Binding context <%s> to task <%s>', self.tag, task.tag)
            self._sequence = task.sequence
            self._task = task
            self._void = False

    @property
    def subcontexts(self):
        """The current contexts virtually included in the current one."""
        rootpath = self.path + '/'
        return [ x for x in self.__class__.tag_values() if x.path.startswith(rootpath) ]

    def newcontext(self, name, focus=False):
        """
        Create a new child context, attached to the current one.
        The tagname of the new kid is given through the mandatory ``name`` arugument,
        as well as the default ``focus``.
        """
        newctx = self.__class__(tag=name, topenv=self.env, path=self.path)
        if focus:
            self.__class__.set_focus(newctx)
        return newctx

    def stamp(self, tag='default'):
        """Return a stamp name that could be used for any generic purpose."""
        return self._stamp + '.' + str(tag)

    def fstrack_stamp(self, tag='default'):
        """Set a stamp to track changes on the filesystem."""
        stamp = self.stamp(tag)
        self.system.touch(stamp)
        self._fstore[stamp] = set(self.system.ffind())

    def fstrack_check(self, tag='default'):
        """
        Return a anonymous dictionary with for the each key, the list of entries
        in the file system that are concerned since the last associated ``tag`` stamp.
        Keys are: ``deleted``, ``created``, ``updated``.
        """
        stamp = self.stamp(tag)
        if not self.system.path.exists(stamp):
            logger.warning('Missing stamp %s', stamp)
            return None
        ffinded = set(self.system.ffind())
        bkuptrace = self.system.trace
        self.system.trace = False
        fscheck = Tracker(self._fstore[stamp], ffinded)
        stroot = self.system.stat(stamp)
        fscheck.updated = [ f for f in fscheck.unchanged if self.system.stat(f).st_mtime > stroot.st_mtime ]
        self.system.trace = bkuptrace
        return fscheck

    def record_off(self):
        """Avoid automatic recording of section while loading resource handlers."""
        self._record = self._void
        self._void = False

    def record_on(self):
        """Restaure default value to void context as it was before any :func:`record_off` call."""
        self._void = self._record

    def clear_stamps(self):
        """Remove local context stamps."""
        if self._fstore:
            fstamps = self._fstore.keys()
            self.system.rmall(*fstamps)
            logger.info('Removing context stamps %s', fstamps)

    def clear(self):
        """Make a clear place of local cocoon directory."""
        self.clear_stamps()

    def exit(self):
        """Clean exit from the current context."""
        try:
            self.clear()
        except TypeError:
            logger.error('Could not clear local context <%s>', self.tag)
