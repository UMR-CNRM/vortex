#!/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

from vortex.autolog import logdefault as logger

from vortex import sessions
from vortex.tools import net
from vortex.tools.date import Date
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
        self._history = [(Date.now(), self.__class__.__name__, 'init', 1)]
        self._stage = [ 'load' ]
        self._observer = observers.classobserver('Resources-Handlers')
        self._observer.notify_new(self, dict(stage = 'load'))
        logger.debug('New resource handler %s', self.__dict__)

    def __del__(self):
        self._observer.notify_del(self, dict())

    def __str__(self):
        return str(self.__dict__)

    @property
    def complete(self):
        """Returns either all the internal components are defined."""
        return bool(self.resource and self.provider and self.container)

    @property
    def stage(self):
        """Return current resource handler stage (load, get, put)."""
        return self._stage[-1]

    def updstage(self, newstage):
        """Notify the new stage to any observing system."""
        self._stage.append(newstage)
        self._observer.notify_upd(self, dict(stage = newstage))

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
            logger.warning('Contents requested without container or empty container [%s]', self.container)
            return None

    def location(self):
        """Returns the URL as defined by the internal provider and resource."""
        if self.provider and self.resource:
            return self.provider.uri(self.resource)
        else:
            logger.warning('Resource handler %s could not build location', self)
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
                    subobj.capitalize(), obj, obj.realkind, obj.puredict()
                )
            else:
                thisdoc = '{0}{1:s} undefined'.format(indent, subobj.capitalize())
            card = card + "\n\n" + thisdoc
        return card

    def locate(self):
        """Try to figure out what would be the physical location of the resource."""
        rst = None
        if self.complete:
            remotelocation = self.location()
            uridata = net.uriparse(remotelocation)
            store = stores.load(scheme = uridata['scheme'], netloc = uridata['netloc'])
            if store:
                logger.debug('Locate resource %s at %s from %s', self, remotelocation, store)
                del uridata['scheme']
                del uridata['netloc']
                rst = store.locate(uridata)
                self._history.append((Date.now(), store.fullname(), 'locate', rst))
            else:
                logger.error('Could not find any store to locate %s', remotelocation)
        else:
            logger.error('Could not locate an incomplete rh %s', self)
        return rst

    def get(self):
        """Method to retrieve through the provider the resource and feed the current container."""
        rst = False
        if self.complete:
            remotelocation = self.location()
            uridata = net.uriparse(remotelocation)
            store = stores.load(scheme = uridata['scheme'], netloc = uridata['netloc'])
            if store:
                logger.debug('Get resource %s at %s from %s', self, remotelocation, store)
                del uridata['scheme']
                del uridata['netloc']
                rst = store.get(uridata, self.container.localpath())
                self.container.updfill(rst)
                self._history.append((Date.now(), store.fullname(), 'get', rst))
                self.updstage('get')
                return rst
            else:
                logger.error('Could not find any store to get %s', remotelocation)
        else:
            logger.error('Could not get an incomplete rh %s', self)
        return rst

    def put(self):
        """Method to store data from the current container through the provider."""
        rst = False
        if self.complete:
            logger.debug('Put resource %s', self)
            remotelocation = self.location()
            uridata = net.uriparse(remotelocation)
            store = stores.load(scheme = uridata['scheme'], netloc = uridata['netloc'])
            if store:
                logger.debug('Put resource %s at %s from %s', self, remotelocation, store)
                del uridata['scheme']
                del uridata['netloc']
                rst = store.put(self.container.localpath(), uridata)
                self._history.append((Date.now(), store.fullname(), 'put', rst))
                self.updstage('put')
            else:
                logger.error('Could not find any store to put %s', remotelocation)
        else:
            logger.error('Could not put an incomplete rh %s', self)
        return rst

    def check(self):
        """Returns a stat-like information to the remote resource."""
        rst = None
        if self.resource and self.provider:
            logger.debug('Check resource %s', self)
            remotelocation = self.location()
            uridata = net.uriparse(remotelocation)
            store = stores.load(scheme = uridata['scheme'], netloc = uridata['netloc'])
            if store:
                logger.debug('Check resource %s at %s from %s', self, remotelocation, store)
                del uridata['scheme']
                del uridata['netloc']
                rst = store.check(uridata)
                self._history.append((Date.now(), store.fullname(), 'check', rst))
            else:
                logger.error('Could not find any store to check %s', remotelocation)
        else:
            logger.error('Could not check a rh without defined resource and provider %s', self)
        return rst

    def clear(self):
        """Clear the local container contents."""
        rst = False
        if self.container:
            logger.debug('Remove resource container %s', self.container)
            rst = sessions.system().remove(self.container.localpath())
            self._history.append((Date.now(), sessions.system().fullname(), 'clear', rst))
        return rst

    def save(self):
        """Rewrite data if contents have been updated."""
        rst = False
        if self.contents:
            rst = self.contents.rewrite(self.container)
        else:
            logger.warning('Try to save undefined contents %s', self)
        return rst

    def strlast(self):
        """String formatted log of the last action."""
        return ' '.join([ str(x) for x in self._history[-1] ])

    def history(self):
        """Copy of the internal history of the current handler."""
        return self._history[:]
