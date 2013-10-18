#!/bin/env python
# -*- coding: utf-8 -*-

r"""
This modules defines the physical layout.
"""

#: No automatic export.
__all__ = []

from footprints import observers

from vortex.autolog import logdefault as logger

from vortex.utilities.structs import idtree
from vortex.tools.env import Environment
import dataflow


class Context(object):
    """Physical layout of a session or task, etc."""

    _count = 0

    def __init__(self, tag='foo', rundir=None, tagtree=None, topenv=None, sequence=None, task=None, mkrundir=False, rootrd=None, keeprd=False):
        """Initate a new execution context."""
        logger.debug('Context initialisation %s', self)
        self._env = Environment(env=topenv, active=topenv.active)
        self._tag = tag
        self.tagtree = tagtree
        self._keeprd = keeprd
        self._task = task
        self._void = True
        self._fstore = dict()
        self._stampradical = '.'.join(('.ctx', str(id(self))))

        tree = idtree(self.tagtree)
        csys = tree.root.system()

        if rootrd:
            self._rootrd = rootrd
        else:
            self._rootrd = tree.root.glove.configrc

        if rundir:
            self._rundir = rundir
        else:
            self.__class__._count = self.__class__._count + 1
            self._rundir = '{0:s}/ctx{1:04d}_{2:s}'.format(self._rootrd, self.__class__._count, self._tag)

        self._rundir = csys.path.abspath(self._rundir)
        if mkrundir:
            logger.info('Make context rundir %s', self._rundir)
            csys.filecocoon(self.system.path.join(self._rundir, 'ctx'))
        else:
            logger.debug('Do not create any context rundir %s', self._rundir)

        if sequence:
            self._sequence = sequence
            self._void = False
        else:
            self._sequence = dataflow.Sequence()

        self.bind(self._task)
        observers.getbyname('Resources-Handlers').register(self)

    def newobsitem(self, item, info):
        """
        Resources-Handlers observing facility.
        Register a new section in void active context with the resource handler ``item``.
        """
        logger.debug('Notified %s new item %s', self, item)
        if self._void and self.hasfocus():
            self._sequence.section(rh=item, stage='load')

    def delobsitem(self, item, info):
        """
        Resources-Handlers observing facility.
        Should removed the associated section. Yet to coded.
        """
        if self.hasfocus():
            logger.debug('Notified %s del item %s', self, item)

    def updobsitem(self, item, info):
        """
        Resources-Handlers observing facility.
        Track the new stage of the section containing the resource handler ``item``.
        """
        if self.hasfocus():
            logger.debug('Notified %s upd item %s', self, item)
            for section in self._sequence:
                if section.rh == item:
                    section.updstage(info)

    def _gettag(self):
        """Return the current tag name."""
        return self._tag

    def _settag(self, value):
        """
        Set the formal tag name of the current context to the provided value, if any.
        The current tag name is returned.
        """
        if value: self._tag = value
        return self._tag

    tag = property(_gettag, _settag, None)

    @property
    def tree(self):
        """Returns the associated tree."""
        return idtree(self.tagtree)

    @property
    def rundir(self):
        """Return the path of the directory associated to that context."""
        return self._rundir

    @property
    def keeprundir(self):
        """Return permanent status of the directory associated to that context."""
        return self._keeprd

    def cocoon(self):
        """Change directory to the one associated to that context."""
        self.system.cd(self._rundir)

    @property
    def void(self):
        """
        Return either the current context is a void context, and therefore not binded to a task.
        One may be aware that this value could be temporarly overwritten through the record on/off mechanism.
        """
        return self._void

    @property
    def env(self):
        """Return the :class:`~vortex.tools.env.Environment` object associated to that context."""
        return self._env

    @property
    def system(self):
        """
        Return the :class:`~vortex.tools.env.System` object associated to the root node
        of the tree holding that context.
        """
        return self.tree.root.system()

    @property
    def task(self):
        """Return the possibly binded task."""
        return self._task

    @property
    def active(self):
        """Return the context who has the focus in the same tree as the current context."""
        return self.tree.token

    @property
    def sequence(self):
        """Return the :class:`~vortex.layout.dataflow.Sequence` object associated to that context."""
        return self._sequence

    @property
    def binded(self):
        """Boolean property to check either the current context is binded to a task or not."""
        return bool(self._task)

    def bind(self, task, **kw):
        """
        Bind the current context to the specified ``task``.
        The task sequence becomes the current context sequence.
        """
        if task and hasattr(task, 'sequence'):
            logger.info('Binding context <%s> to task %s', self.tag(), task)
            self._sequence = task.sequence
            self._task = task
            self._void = False

    def newcontext(self, name, focus=False):
        """
        Create a new child context, attached to the current one.
        The tagname of the new kid is given through the mandatory ``name`` arugument,
        as well as the default ``focus``.
        """
        context = Context(tag=name, topenv=self._env, tree=self.tree)
        self.tree.addnode(context, parent=self, token=focus)

    def subcontexts(self):
        """Return the list of contexts attached to the current one."""
        return self.tree.kids(self)

    def hasfocus(self):
        """Return either the current context has the active focus in the tree it belongs."""
        return self.tree.token == self

    def stamp(self, tag='default'):
        """Return a stamp name that could be used for any generic purpose."""
        return self._stampradical + '.' + str(tag)

    def fstrack_stamp(self, tag='default'):
        """Set a stamp to track changes on the filesystem."""
        stamp = self.stamp(tag)
        self.system.touch(stamp)
        self._fstore[stamp] = self.system.ffind()

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
        ffinded = self.system.ffind()
        bkuptrace = self.system.trace
        self.system.trace = False
        fscheck = dict()
        fscheck['deleted'] = filter(lambda f: f not in ffinded, self._fstore[stamp])
        fscheck['created'] = filter(lambda f: f not in self._fstore[stamp], ffinded)
        stroot = self.system.stat(stamp)
        fscheck['updated'] = filter(lambda f: self.system.stat(f).st_mtime > stroot.st_mtime and f not in fscheck['created'], ffinded)
        self.system.trace = bkuptrace
        return fscheck

    def record_off(self):
        """Avoid automatic recording of section while loading resource handlers."""
        self._record = self._void
        self._void = False

    def record_on(self):
        """Restaure default value to void context as it was before any :func:`record_off` call."""
        self._void = self._record

    def exit(self):
        """Clean exit from the current context."""
        actualsys = None
        try:
            actualsys = self.system
        except TypeError:
            pass
        except:
            raise
        if not actualsys:
            try:
                from vortex import sessions
                actualsys = sessions.system()
            except:
                logger.critical('Could not get a ticket session while exiting context %s', self.tag)
                raise
        if not actualsys:
            return False
        if self._fstore:
            fstamps = self._fstore.keys()
            actualsys.rmall(*fstamps)
            logger.info('Removing context stamps %s', fstamps)
        if self._keeprd:
            logger.warning('Preserving context rundir %s', self._rundir)
            return True
        else:
            if actualsys.path.isdir(self._rundir):
                logger.info('Removing context rundir %s', self._rundir)
                return actualsys.rmsafe(self._rundir, self.tree.root.glove.safedirs())

