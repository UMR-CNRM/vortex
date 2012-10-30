#!/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import logging
from datetime import datetime

from vortex import sessions
from vortex.tools import net
from vortex.utilities import observers, roles

import stores


class Handler(object):
    """
    The resource object gathers a provider, a resource and a container
    for any specific resource. Other parameters given at construct time
    are stored as options.
    """

    def __init__(self, rd, **kw):
        self.role = roles.setrole(rd.get('role', 'anonymous'))
        if 'role' in rd: del rd['role']
        self.alternate = roles.setrole(rd.get('alternate', None))
        if 'alternate' in rd:
            del rd['alternate']
            self.role = None
        self.resource = rd.get('resource', None)
        self.provider = rd.get('provider', None)
        self.container = rd.get('container', None)
        self.options = dict()
        self._contents = None
        if 'glove' in rd:
            del rd['glove']
        for k in filter(lambda x: not self.__dict__.has_key(x), rd.keys()):
            self.options[k] = rd.get(k)
        self.options.update(kw)
        self.historic = [(datetime.now(), self.__class__.__name__, 'init', 1)]
        self._observer = observers.classobserver('Resources-Handlers')
        self._observer.notify_new(self, dict(stage = 'load'))
        logging.debug('New resource handler %s', self.__dict__)

    def __del__(self):
        self._observer.notify_del(self, dict())

    def __str__(self):
        return str(self.__dict__)

    @property
    def complete(self):
        """Returns either all the internal components are defined."""
        return bool(self.resource and self.provider and self.container)

    @property
    def contents(self):
        """
        Returns an valid data layout object as long as the current handler
        is complete and the container filled.
        """
        if self.complete and self.container.filled:
            if not self._contents:
                self._contents = self.resource.contents_handler()
                self._contents.slurp(self.container)
            return self._contents
        else:
            logging.warning('Contents requested without container or empty container [%s]', self.container)
            return None

    def location(self):
        """Returns the URL as defined by the internal provider and resource."""
        if self.provider and self.resource:
            return self.provider.uri(self.resource)
        else:
            logging.warning('Resource handler %s could not build location', self)
            return None

    def idcard(self, indent=2):
        """
        Returns a multilines documentation string with a summary
        of the valuable information contained by this handler.
        """
        indent = ' ' * indent
        card = "\n".join((
            '{0}Handler {1!r}',
            '{0}{0}Role      : {2:s}',
            '{0}{0}Alternate : {3:s}',
            '{0}{0}Complete  : {4}',
            '{0}{0}Options   : {5}',
            '{0}{0}Location  : {6}'
       )).format(
            indent,
            self, self.role, self.alternate, self.complete, self.options, self.location()
        )
        for subobj in ( 'resource', 'provider', 'container' ):
            obj = getattr(self, subobj, None)
            if obj:
                thisdoc ="\n".join((
                    '{0}{1:s} {2!r}',
                    '{0}{0}Realkind   : {3:s}',
                    '{0}{0}Attributes : {4:s}'
                )).format(
                    indent,
                    subobj.capitalize(), obj, obj.realkind(), obj.puredict()
                )
            else:
                thisdoc = '{0}{1:s} undefined'.format(indent, subobj.capitalize())
            card = card + "\n\n" + thisdoc
        return card

    def locate(self):
        """Try to figure out what would be the physical location of the resource."""
        locst = None
        if self.complete:
            remotelocation = self.location()
            uridata = net.uriparse(remotelocation)
            store = stores.load(scheme = uridata['scheme'], netloc = uridata['netloc'])
            if store:
                logging.debug('Locate resource %s at %s from %s', self, remotelocation, store)
                del uridata['scheme']
                del uridata['netloc']
                locst = store.locate(uridata)
                self.historic.append((datetime.now(), store.fullname(), 'locate', locst))
            else:
                logging.error('Could not find any store to locate %s', remotelocation)
        else:
            logging.error('Could not locate an incomplete rh %s', self)
        return locst

    def get(self):
        """Method to retrieve through the provider the resource and feed the current container."""
        gst = False
        if self.complete:
            remotelocation = self.location()
            uridata = net.uriparse(remotelocation)
            store = stores.load(scheme = uridata['scheme'], netloc = uridata['netloc'])
            if store:
                logging.debug('Get resource %s at %s from %s', self, remotelocation, store)
                del uridata['scheme']
                del uridata['netloc']
                gst = store.get(uridata, self.container.localpath())
                self.container.updfill(gst)
                self.historic.append((datetime.now(), store.fullname(), 'get', gst))
                self._observer.notify_upd(self, dict(stage = 'get'))
                return gst
            else:
                logging.error('Could not find any store to get %s', remotelocation)
        else:
            logging.error('Could not get an incomplete rh %s', self)
        return gst

    def put(self):
        """Method to store data from the current container through the provider."""
        pst = False
        if self.complete:
            logging.debug('Put resource %s', self)
            remotelocation = self.location()
            uridata = net.uriparse(remotelocation)
            store = stores.load(scheme = uridata['scheme'], netloc = uridata['netloc'])
            if store:
                logging.debug('Put resource %s at %s from %s', self, remotelocation, store)
                del uridata['scheme']
                del uridata['netloc']
                pst = store.put(self.container.localpath(), uridata)
                self.historic.append((datetime.now(), store.fullname(), 'put', pst))
                self._observer.notify_upd(self, dict(stage = 'put'))
            else:
                logging.error('Could not find any store to put %s', remotelocation)
        else:
            logging.error('Could not put an incomplete rh %s', self)
        return pst

    def check(self):
        """Returns a stat-like information to the remote resource."""
        stcheck = None
        if self.resource and self.provider:
            logging.debug('Check resource %s', self)
            remotelocation = self.location()
            uridata = net.uriparse(remotelocation)
            store = stores.load(scheme = uridata['scheme'], netloc = uridata['netloc'])
            if store:
                logging.debug('Check resource %s at %s from %s', self, remotelocation, store)
                del uridata['scheme']
                del uridata['netloc']
                stcheck = store.check(uridata)
                self.historic.append((datetime.now(), store.fullname(), 'check', stcheck))
            else:
                logging.error('Could not find any store to check %s', remotelocation)
        else:
            logging.error('Could not check a rh without defined resource and provider %s', self)
        return stcheck

    def clear(self):
        """Clear the local container contents."""
        if self.container:
            logging.debug('Remove resource container %s', self.container)
            self.historic.append((datetime.now(), sessions.system().fullname(), 'clear', sessions.system().remove(self.container.localpath())))

    def save(self):
        """Rewrite data if contents have been updated."""
        if self.contents:
            self.contents.rewrite(self.container)
        else:
            logging.warning('Try to save undefined contents %s', self)

    def strlast(self):
        """String formatted log of the last action."""
        return ' '.join(map(lambda x: str(x), self.historic[-1]))
