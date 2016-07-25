#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Vortex Sessions Handling

A :mod:`vortex` session is a virtual identifier gathering information on the current
#usage of the toolbox. A session has a starting time, and possibly a closing
time. A session also defines the level of the internal logging used in all
the vortex modules.
"""

#: No automatic export
__all__ = []

import logging

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.tools.env import Environment

from vortex        import gloves
from vortex.tools  import date
from vortex.layout import contexts


# Module Interface

def get(**kw):
    """Return actual session ticket object matching description."""
    return Ticket(**kw)


def keys():
    """Return the list of current session tickets names collected."""
    return Ticket.tag_keys()


def values():
    """Return the list of current session ticket values collected."""
    return Ticket.tag_values()


def items():
    """Return the items of the session tickets table."""
    return Ticket.tag_items()


def current():
    """Return the current active session."""
    return get(tag = Ticket.tag_focus())


def prompt():
    """Returns a built string that could be used as a prompt for reporting."""
    return current().prompt


def switch(tag=None):
    """Set the session associated to the actual ``tag`` as active."""
    return current().switch(tag=tag)


def getglove(**kw):
    """Proxy to :mod:`gloves` collector."""
    return footprints.proxy.gloves.default(**kw)


def system(**kw):
    """Returns the system associated to the current ticket."""
    return get(tag = kw.pop('tag', Ticket.tag_focus())).system(**kw)


# noinspection PyShadowingBuiltins
def exit():
    """Ask all inactive sessions to close, then close the active one."""
    tags = keys()
    xtag = Ticket.tag_focus()
    tags.remove(xtag)
    tags.append(xtag)
    ok = True
    for s in [ get(tag=x) for x in tags ]:
        ok = s.exit() and ok
    return ok


class Ticket(footprints.util.GetByTag):
    """
    Default session ticket class, defined by tag.
    """

    _tag_default = 'root'

    def __init__(self,
                 active  = False,
                 topenv  = None,
                 glove   = None,
                 context = None,
                 prompt  = 'Vortex:'):
        self.prompt = prompt
        self.line   = "\n" + '-' * 100 + "\n"

        self._active  = active
        self._started = date.now()
        self._closed  = 0
        self._system  = None

        logger.debug('New session system is %s', self.system())

        self._rundir  = self.sh.getcwd()

        if topenv:
            self._topenv = topenv
        else:
            self._topenv = Environment()

        if glove:
            self._glove = glove
        else:
            if self._topenv.glove:
                self._glove = self._topenv.glove
            else:
                self._glove = getglove()

        logger.debug('Open session %s %s', self.tag, self)

        if context is None:
            context = contexts.Context(tag=self.tag, topenv=self._topenv, path=self.path)
            if context.env.active() and not self._active:
                context.env.active(False)

        context.env.glove = self._glove
        if self._active:
            Ticket.set_focus(self)
            contexts.Context.set_focus(context)
            context.env.active(True)

    def _get_rundir(self):
        """Return the path of the directory associated to current session."""
        return self._rundir

    def _set_rundir(self, path):
        """Set a new default rundir for this session."""
        if self._rundir:
            logger.warning('Session <%s> is changing its workding directory <%s>', self.tag, self._rundir)
        if self.sh.path.isdir(path):
            self._rundir = path
            logger.info('Session <%s> set rundir <%s>', self.tag, self._rundir)
        else:
            logger.error('Try to change session <%s> to invalid path <%s>', self.tag, path)

    rundir = property(_get_rundir, _set_rundir)

    @property
    def active(self):
        """Return whether this session is active or not."""
        return self._active

    @property
    def started(self):
        """Return opening time stamp."""
        return self._started

    @property
    def closed(self):
        """Return closing time stamp if any."""
        return self._closed

    @property
    def opened(self):
        """Boolean. True if the session is not closed."""
        return not bool(self.closed)

    @property
    def topenv(self):
        """Return top environment binded to this session."""
        return self._topenv

    @property
    def env(self):
        """Return environment binded to current active context."""
        return self.context.env

    @property
    def sh(self):
        """Return shell interface binded to current active context."""
        return self._system

    @property
    def glove(self):
        """Return the default glove associated to this session."""
        return self._glove

    @property
    def context(self):
        """Returns the active context binded to this section."""
        return contexts.focus()

    def system(self, **kw):
        """
        Returns the current OS handler used or set a new one according
        to ``kw`` dictionary-like arguments.
        """
        refill = kw.pop('refill', False)
        if not self._system or kw or refill:
            self._system = footprints.proxy.system(**kw)
            if not self._system:
                logger.critical('Could not load a system object with description %s', str(kw))
        return self._system

    def duration(self):
        """
        Time since the opening of the session if still opened
        or complete duration time if closed.
        """
        if self.closed:
            return self.closed - self.started
        else:
            return date.now() - self.started

    def activate(self):
        """Force the current session as active."""
        if self.opened:
            return Ticket.switch(self.tag)
        else:
            return False

    def close(self):
        """Closes the current session."""
        if self.closed:
            logger.warning('Session %s already closed at %s', self.tag, self.closed)
        else:
            self._closed = date.now()
            logger.debug('Close session %s ( time = %s )', self.tag, self.duration())

    @property
    def path(self):
        return '/'  + self.tag

    @property
    def subcontexts(self):
        """The current contexts binded to this session."""
        rootpath = self.path + '/'
        return [ x for x in contexts.values() if x.path.startswith(rootpath) ]

    def exit(self):
        """Exit from the current session."""
        ok = True
        logger.debug('Exit session %s %s', self.tag, self)
        for kid in self.subcontexts:
            logger.debug('Exit from context %s', kid)
            ok = ok and kid.exit()
        self.close()
        return ok

    def warning(self):
        """Switch current loglevel to WARNING."""
        self.setloglevel(logging.WARNING)

    def debug(self):
        """Switch current loglevel to DEBUG."""
        self.setloglevel(logging.DEBUG)

    def info(self):
        """Switch current loglevel to INFO."""
        self.setloglevel(logging.INFO)

    def error(self):
        """Switch current loglevel to ERROR."""
        self.setloglevel(logging.ERROR)

    def critical(self):
        """Switch current loglevel to CRITICAL."""
        self.setloglevel(logging.CRITICAL)

    def setloglevel(self, level):
        """
        Explicitly sets the logging level to the ``level`` value.
        Shortcuts such as :method::`debug' or :method:`error` should be used.
        """
        for logname in footprints.loggers.roots:
            logger = logging.getLogger(logname)
            logger.setLevel(level)

    @property
    def loglevel(self):
        """
        Returns the logging level.
        """
        logger = logging.getLogger('vortex')
        return logging.getLevelName(logger.level)

    def idcard(self, indent='+ '):
        """Returns a printable description of the current session."""
        card = "\n".join((
            '{0}Name     = {1:s}',
            '{0}Started  = {2:s}',
            '{0}Opened   = {3:s}',
            '{0}Duration = {4:s}',
            '{0}Loglevel = {5:s}'
        )).format(
            indent,
            self.tag, str(self.started), str(self.opened), self.duration(), self.loglevel
        )
        return card

    def switch(self, tag=None):
        """
        Allows the user to switch to an other session,
        assuming that the provided tag is already known.
        """
        if tag in self.tag_keys():
            focus = self.tag_focus()
            table = dict(self.tag_items())
            if tag != focus:
                table[focus]._active = False
                table[focus].env.active(False)
                table[tag]._active = True
                table[tag].env.active(True)
                self.set_focus(table[tag])
                contexts.Context.set_focus(table[focus].context)
            return table[tag]
        else:
            logger.error('Try to switch to an undefined session: %s', tag)
            return None

    def __del__(self):
        self.close()
