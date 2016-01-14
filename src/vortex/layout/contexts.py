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


_RHANDLERS_OBSBOARD = 'Resources-Handlers'
_STORES_OBSBOARD = 'Stores-Activity'


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


class ContextObserverRecorder(footprints.observers.Observer):
    """Record events related to a given Context.

    In order to start recording, this object should be associated with a
    :obj:`Context` object using the :meth:`register` method. The recording will
    be stopped when the :meth:`unregister` method is called. The recording is
    automatically stopped whenever the object is pickled.

    At any time, the `record` can be replayed in a given Context using the
    :meth:`replay_in` method.
    """

    def __init__(self):
        self._binded_context = None
        self._tracker_recorder = None
        self._stages_recorder = None

    def __del__(self):
        self.unregister()

    def __getstate__(self):
        # Objects have to be unregistered before being pickled
        self.unregister()
        return self.__dict__

    def register(self, context):
        """Associate a particular :obj:`Context` object and start recording.

        :param context: The :obj:`Context` object that will be recorded.
        """
        self._binded_context = context
        self._tracker_recorder = dataflow.LocalTracker()
        self._stages_recorder = list()
        footprints.observers.get(tag=_RHANDLERS_OBSBOARD).register(self)
        footprints.observers.get(tag=_STORES_OBSBOARD).register(self)

    def unregister(self):
        """Stop recording."""
        if self._binded_context is not None:
            self._binded_context = None
            footprints.observers.get(tag=_RHANDLERS_OBSBOARD).unregister(self)
            footprints.observers.get(tag=_STORES_OBSBOARD).unregister(self)

    def updobsitem(self, item, info):
        if (self._binded_context is not None) and self._binded_context.has_focus():
            logger.debug('Recording upd item %s', item)
            if info['observerboard'] == _RHANDLERS_OBSBOARD:
                processed_item = item.as_dict()
                self._stages_recorder.append((processed_item, info))
                self._tracker_recorder.update_rh(item, info)
            elif info['observerboard'] == _STORES_OBSBOARD:
                self._tracker_recorder.update_store(item, info)

    def replay_in(self, context):
        """Replays the observer's record in a given context.

        :param context: The :obj:`Context` object where the record will be replayed.
        """
        # First the stages of the sequence
        if self._stages_recorder:
            logger.info('The recorder is replaying stages for context <%s>', context.tag)
            rhdicts = [ section.rh.as_dict() for section in context.sequence ]
            for (pr_item, info) in self._stages_recorder:
                for section, rhdict in zip(context.sequence, rhdicts):
                    if rhdict == pr_item:
                        section.updstage(info)
        # Then the localtracker
        if self._tracker_recorder is not None:
            logger.info('The recorder is updating the LocalTracker for context <%s>', context.tag)
            context.localtracker.append(self._tracker_recorder)


class Context(footprints.util.GetByTag, footprints.observers.Observer):
    """Physical layout of a session or task, etc."""

    _tag_default = 'ctx'

    def __init__(self, path=None, topenv=None, sequence=None, localtracker=None,
                 task=None):
        """Initiate a new execution context."""
        logger.debug('Context initialisation %s', self)
        if path is None:
            logger.critical('Try to define a new context without virtual path')
            raise ValueError('No virtual path given to new context.')
        if topenv is None:
            logger.critical('Try to define a new context without a topenv.')
            raise ValueError('No top environment given to new context.')
        self._env      = Environment(env=topenv, active=topenv.active(), verbose=topenv.verbose())
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

        if localtracker:
            self._localtracker = localtracker
        else:
            self._localtracker = dataflow.LocalTracker()

        self.bind(self._task)
        footprints.observers.get(tag=_RHANDLERS_OBSBOARD).register(self)
        footprints.observers.get(tag=_STORES_OBSBOARD).register(self)

    def newobsitem(self, item, info):
        """
        Resources-Handlers / Store-Activity observing facility.
        Register a new section in void active context with the resource handler ``item``.
        """
        if self.has_focus():
            logger.debug('Notified %s new item %s', self, item)
            if (self.void and info['observerboard'] == _RHANDLERS_OBSBOARD):
                self._sequence.section(rh=item, stage='load')

    def updobsitem(self, item, info):
        """
        Resources-Handlers / Store-Activity observing facility.
        Track the new stage of the section containing the resource handler ``item``.
        """
        if self.has_focus():
            logger.debug('Notified %s upd item %s', self, item)
            if info['observerboard'] == _RHANDLERS_OBSBOARD:
                # Update the sequence
                for section in self._sequence:
                    if section.rh == item:
                        section.updstage(info)
                # Update the local tracker
                self._localtracker.update_rh(item, info)
            elif info['observerboard'] == _STORES_OBSBOARD:
                # Update the local tracker
                self._localtracker.update_store(item, info)

    def get_recorder(self):
        """Return a :obj:`ContextObserverRecorder` object recording the changes in this Context."""
        rec = ContextObserverRecorder()
        rec.register(self)
        return rec

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
        if self.rundir is None:
            subpath = self.path.replace(self.session.path, '', 1)
            self._rundir = self.session.rundir + subpath
        self.system.cd(self.rundir, create=True)
        self._cocooned = True

    @property
    def cocooned(self):
        """Check if the current context had cocooned."""
        return self._cocooned

    @property
    def void(self):
        """
        Return whether the current context is a void context, and therefore not bound to a task.
        One may be aware that this value could be temporarily overwritten through the record on/off mechanism.
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
    def localtracker(self):
        """Return the :class:`~vortex.layout.dataflow.LocalTracker` object associated to that context."""
        return self._localtracker

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
        The tagname of the new kid is given through the mandatory ``name`` argument,
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
        """Restore default value to void context as it was before any :func:`record_off` call."""
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
