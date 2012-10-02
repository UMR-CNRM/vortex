#!/bin/env python
# -*- coding:Utf-8 -*-

r"""
Vortex Sessions Handling

A :mod:`vortex` session is a virtual identifier gathering information on the current
usage of the toolbox. A session has a starting time, and possibly a closing
time. A session defined also the level of the internal logging used in all
the vortex modules.

This module also defines the GLOVE, ie : GLObal Versatile Environment
which is a kind of user profile able to carry on some basic information,
preferences and default behavior definition.

Sessions and Gloves are retrieved from interface methods of the session module.
A special object, the :class:`Desk`, is specifically in charge of handling sessions.

"""

#: No automatic export
__all__ = []

import logging

logging.basicConfig(
    format='[%(asctime)s][%(module)-10s][%(levelname)8s]: %(message)s',
    datefmt='%m/%d/%Y %H:%M:%S',
    level=logging.WARNING
)

from datetime import datetime

from vortex.utilities.patterns import Singleton
from vortex.utilities.structs import idtree
from vortex.tools import systems
from vortex.tools.env import Environment
from vortex.layout.contexts import Context
import gloves


def ticket(**kw):
    r"""
    Ask the Desk to return a session ticket according to actual arguments.
    It could be a new one.
    """
    return Desk().getticket(**kw)

def glove(**kw):
    r"""
    Ask the Desk to return a glove according to actual arguments.
    It could be a new one.
    """
    return Desk().getglove(**kw)

def system():
    """Returns the system associated to the current ticket."""
    return ticket().system()

def opened():
    """Ask the Desk to return the list of opened sessions names."""
    return Desk().sessionsnames()

def current():
    """Ask the Desk to return the current active session."""
    return Desk().current()

def switch(tag):
    """Set the session associated to the actual tag as active."""
    return Desk().switch(tag)

def prompt():
    """Returns a built string that could be used as a prompt for reporting."""
    return current().prompt



class Ticket(object):

    def __init__(self, config=None, topenv=None, glove=None, context=None, tag='root', prompt='Vortex:'):
        self.tag = tag
        self.config = config
        self.prompt = prompt
        self.line = "\n" + '-' * 80 + "\n"
        self.started = datetime.now()
        self.closed = 0
        self.fake = 0
        self._system = None
 
        self.tree = idtree('-'.join(('session', self.tag)))
        self.tree.setroot(self)
               
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

        logging.info('Open session %s %s', self.tag, self.started)

        if context:
            context.tree = self.tree
        else:
            context = Context(topenv=self._topenv, tree=self.tree, mkrundir=False)

        self.tree.addnode(context, parent=self, token=True)
        

    @property
    def topenv(self):
        """Return top environment binded to this session."""
        return self._topenv

    @property
    def env(self):
        """Return environment binded to current active context."""
        return self.context.env

    @property
    def glove(self):
        """Return the default glove associated to this session."""
        return self._glove

    @property
    def context(self):
        """Returns the active context binded to this section."""
        return self.tree.token

    def system(self, **kw):
        """
        Returns the current OS handler used or set a new one according
        to ``kw`` dictionary-like arguments.
        """
        if not self._system or kw:
            self._system = systems.load(**kw)
        return self._system

    def duration(self):
        r"""
        Time since the opening of the session if still opened
        or complete duration time if closed.
        """
        if self.closed:
            return self.closed - self.started
        else:
            return datetime.now() - self.started

    @property
    def active(self):
        """Boolean. <True> if the session is opened and active."""
        return not self.closed

    def close(self):
        """Closes the current session."""
        self.closed = datetime.now()
        logging.info('Close session %s %s', self.tag, self.duration())
    
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
        r"""
        Explicitly sets the logging level to the ``level`` value.
        Shortcuts such as :method::`debug' or :method:`error` should be used.
        """
        logger = logging.getLogger()
        logger.setLevel(level)

    @property
    def loglevel(self):
        r"""
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
            '{0}Active   : {3:s}',
            '{0}Duration : {4:s}',
            '{0}Loglevel : {5:s}'
        )).format(
            indent,
            self.tag, str(self.started), str(self.active), self.duration(), self.loglevel
        )
        return card

    def __del__(self):
        self.close()


class Desk(Singleton):
    r"""
    The Desk class is a singleton in charge of handling all the defined sessions.
    It encapsulates the class Ticket which is really supposed to be the so-called
    session.
    """

    _tickets = dict()
    _gloves = dict()
    _current_ticket = 'root'
    _current_glove = 'default'

    def __init__(self):
        logging.debug('Tickets desk %s', self._tickets)

    def getglove(self, **kw):
        r"""
        This method is the priviledged entry point to obtain a Glove.
        If the default tag 'current' is provided as an argument, the tag
        of the current glove is used.
        A new glove is created if the actual tag value is unknown. 
        """
        if 'tag' in kw:
            tag = kw.get('tag', 'current')
            del kw['tag']
        else:
            tag = 'current'

        if tag == 'current':
            tag = self._current_glove

        if not self._gloves.has_key(tag): self._gloves[tag] = gloves.load(**kw)
        return self._gloves[tag]

    def getticket(self, tag='current', prompt='Vortex:', topenv=None, glove=None, context=None):
        r"""
        This method is the only entry point to obtain a Ticket session.
        If the default tag 'current' is provided as an argument, the tag
        of the current active session is used.
        A new ticket session is created if the actual tag value is unknown. 
        """
        if tag == 'current':
            tag = self._current_ticket

        if not self._tickets.has_key(tag):
            self._tickets[tag] = Ticket(tag=tag, prompt=prompt, topenv=topenv, glove=glove, context=context)
        
        return self._tickets[tag]

    def __iter__(self):
        r"""
        Desk is iterable.
        Rolling over tickets values (not tags).
        """
        for t in self._tickets.values():
            yield t

    def __call__(self):
        r"""
        Desk is callable.
        It returns the list of actual tickets values.
        """
        return self._tickets.values()

    def current(self):
        """Shortcut to get the ticket value matching the current tag name."""
        return self.getticket(tag=self._current_ticket)

    def switch(self, tag):
        r"""
        Allows the user to switch to an other session, as long that the actual tag
        provided is already known.
        """
        if self._tickets.has_key(tag):
            self._current_ticket = tag
        else:
            logging.warning('Try to switch to an undefined session: %s', tag)
        return self._tickets[tag]

    def sessionsnames(self):
        """Returns an alphabeticaly sorted list of sessions tag names."""
        return sorted(self._tickets.keys())

