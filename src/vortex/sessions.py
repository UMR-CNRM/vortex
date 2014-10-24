#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Vortex Sessions Handling

A :mod:`vortex` session is a virtual identifier gathering information on the current
#usage of the toolbox. A session has a starting time, and possibly a closing
time. A session also defines the level of the internal logging used in all
the vortex modules.

This module also defines the GLOVE, ie: GLObal Versatile Environment
which is a kind of user profile able to carry on some basic information,
preferences and default behavior definition.

Sessions and Gloves are retrieved from interface methods of the session module.
A special internal object, the :class:`Desk`, is specifically in charge of handling sessions.
"""

#: No automatic export
__all__ = []

import logging

import footprints

from vortex.autolog import logdefault as logger

from vortex.util.patterns import Singleton
from vortex.util.structs import idtree
from vortex.tools import date
from vortex.tools.env import Environment
from vortex.layout.contexts import Context
from vortex import gloves


def ticket(**kw):
    """
    Ask the :class:`Desk` to return a session ticket according to actual arguments.
    It could be a new one if the specified ``tag`` argument does not
    actually exists in the :class:`Desk` table.
    """
    return Desk().getticket(**kw)


def glove(**kw):
    """
    Ask the :class:`Desk` to return a glove according to actual arguments.
    It could be a new one.
    """
    return Desk().getglove(**kw)


def system(**kw):
    """Returns the system associated to the current ticket."""
    return ticket().system(**kw)


def glovestags():
    """Ask the :class:`Desk` to return the list of opened gloves tags."""
    return Desk().glovestags()


def sessionstags():
    """Ask the :class:`Desk` to return the list of opened sessions tags."""
    return Desk().sessionstags()


def current():
    """Ask the :class:`Desk` to return the current active session."""
    return Desk().current


def switch(tag):
    """Set the session associated to the actual tag as active."""
    return Desk().switch(tag)


def prompt():
    """Returns a built string that could be used as a prompt for reporting."""
    return Desk().current.prompt


# noinspection PyShadowingBuiltins
def exit():
    """Ask all inactive sessions to close, then close the active one."""
    thedesk = Desk()
    tags = thedesk.sessionstags()
    xtag = thedesk.current_tag
    tags.remove(xtag)
    tags.append(xtag)
    ok = True
    for s in [ thedesk.getticket(tag=x) for x in tags ]:
        ok = s.exit() and ok
    return ok


class Ticket(object):

    def __init__(self, active=False, config=None, topenv=None,
                 glove=None, context=None, tag='root', prompt='Vortex:'):
        self.tag = tag
        self._active = active
        self.config = config
        self.prompt = prompt
        self.line = "\n" + '-' * 100 + "\n"
        self.started = date.now()
        self.closed = 0
        self.fake = 0
        self._system = None

        self.tagtree = '-'.join(('session', self.tag))
        tree = idtree(self.tagtree)
        tree.setroot(self)

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
                self._glove = Desk().getglove()

        logger.debug('Open session %s %s', self.tag, self)

        if context:
            context.tagtree = self.tagtree
        else:
            context = Context(topenv=self._topenv, tagtree=self.tagtree)
            if context.env.active() and not self._active:
                context.env.active(False)

        context.env.glove = self._glove
        if self._active:
                context.env.active(True)

        tree.addnode(context, parent=self, token=True)

    @property
    def active(self):
        """Return whether this session is active or not."""
        return self._active

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
    def tree(self):
        """Returns the associated tree."""
        return idtree(self.tagtree)

    @property
    def context(self):
        """Returns the active context binded to this section."""
        return self.tree.token

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

    @property
    def opened(self):
        """Boolean. <True> if the session is not closed."""
        return not self.closed

    def activate(self):
        """Force the current session as active."""
        if self.opened:
            return Desk().switch(self.tag)
        else:
            return False

    def close(self):
        """Closes the current session."""
        if self.closed:
            logger.warning('Session %s already closed at %s', self.tag, self.closed)
        else:
            self.closed = date.now()
            logger.debug('Close session %s ( time = %s )', self.tag, self.duration())

    def exit(self):
        """Exit from the current session."""
        ok = True
        logger.debug('Exit session %s %s', self.tag, self)
        for kid in self.tree.kids(self):
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
        logger = logging.getLogger()
        logger.setLevel(level)

    @property
    def loglevel(self):
        """
        Returns the logging level.
        """
        logger = logging.getLogger()
        return logging.getLevelName(logger.level)

    def idcard(self):
        """Returns a printable description of the current session."""
        indent = ''
        card = "\n".join((
            '{0}Name     : {1:s}',
            '{0}Started  : {2:s}',
            '{0}Opened   : {3:s}',
            '{0}Duration : {4:s}',
            '{0}Loglevel : {5:s}'
        )).format(
            indent,
            self.tag, str(self.started), str(self.opened), self.duration(), self.loglevel
        )
        return card

    def __del__(self):
        self.close()


class Desk(Singleton):
    """
    The Desk class is a singleton in charge of handling all the defined sessions.
    It encapsulates the class Ticket which is really supposed to be the so-called
    session.
    """

    def __init__(self):
        if '_tickets' not in self.__dict__:
            self._tickets = dict()
            self._gloves  = dict()
            self._current_ticket = 'root'
            self._current_glove  = 'default'
        logger.debug('Tickets desk init %s', self._tickets)

    def getglove(self, **kw):
        """
        This method is the priviledged entry point to obtain a Glove.
        If the default tag 'current' is provided as an argument, the tag
        of the current glove is used.
        A new glove is created if the actual tag value is unknown.
        """
        tag = kw.get('tag', 'current')

        if tag == 'current':
            tag = self._current_glove

        if not self._gloves.has_key(tag):
            self._gloves[tag] = footprints.proxy.glove(**kw)

        return self._gloves[tag]

    def getticket(self, active=False, tag='current', prompt='Vortex:', topenv=None, glove=None, context=None):
        """
        This method is the only entry point to obtain a :class:`Ticket` session.
        If the default tag 'current' is provided as an argument, the tag
        of the current active session is used.
        A new ticket session is created if the actual tag value is unknown.
        """
        if tag == 'current':
            tag = self._current_ticket

        if not self._tickets.has_key(tag):
            self._tickets[tag] = Ticket(
                active  = active,
                tag     = tag,
                prompt  = prompt,
                topenv  = topenv,
                glove   = glove,
                context = context
            )

        if active:
            self.switch(tag)

        return self._tickets[tag]

    def __iter__(self):
        """
        Desk is iterable.
        Rolling over tickets values (not tags).
        """
        for t in self._tickets.values():
            yield t

    def __call__(self):
        """
        Desk is callable.
        It returns the list of actual tickets values.
        """
        return self._tickets.values()

    @property
    def current(self):
        """Shortcut to get the ticket value matching the current tag name."""
        return self.getticket(tag=self._current_ticket)

    @property
    def current_tag(self):
        """Shortcut to get the tag name of the current active session."""
        return self._current_ticket

    def switch(self, tag):
        """
        Allows the user to switch to an other session, as long that the actual tag
        provided is already known.
        """
        if tag in self._tickets:
            if tag != self._current_ticket:
                self._tickets[self._current_ticket]._active = False
                self._tickets[self._current_ticket].env.active(False)
                self._tickets[tag]._active = True
                self._tickets[tag].env.active(True)
                self._current_glove = self._tickets[tag].glove.tag
                self._current_ticket = tag
            return self._tickets[tag]
        else:
            logger.warning('Try to switch to an undefined session: %s', tag)
            return None

    def sessionstags(self):
        """Returns an alphabeticaly sorted list of sessions tag names."""
        return sorted(self._tickets.keys())

    def glovestags(self):
        """Returns an alphabeticaly sorted list of gloves tag names."""
        return sorted(self._gloves.keys())
