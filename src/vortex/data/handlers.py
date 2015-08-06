#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import sys, io

import footprints
logger = footprints.loggers.getLogger(__name__)


from vortex import sessions

from vortex.tools  import net
from vortex.util   import config, roles, structs
from vortex.layout import dataflow
from vortex.data   import stores, containers, resources, providers

OBSERVER_TAG = 'Resources-Handlers'


class HandlerError(StandardError):
    """Exception in case of missing resource during the wait mecanism."""
    pass


def observer_board(obsname=None):
    """Proxy to :func:`footprints.observers.get`."""
    if obsname is None:
        obsname = OBSERVER_TAG
    return footprints.observers.get(tag=obsname)


class Handler(object):
    """
    The resource handler object gathers a provider, a resource and a container
    for any specific resource. Other parameters given at construct time
    are stored as options.
    """

    def __init__(self, rd, **kw):
        if 'glove' in rd:
            del rd['glove']
        self.role      = roles.setrole(rd.pop('role', 'anonymous'))
        self.alternate = roles.setrole(rd.get('alternate', None))
        if 'alternate' in rd:
            del rd['alternate']
            self.role  = None
        self._resource  = rd.pop('resource', None)
        self._provider  = rd.pop('provider', None)
        self._container = rd.pop('container', None)
        self._empty     = rd.pop('empty', False)
        self._contents  = None
        self._uridata   = None
        self._options   = rd.copy()
        self._observer  = observer_board(kw.pop('observer', None))
        self._options.update(kw)
        self._ghost   = self._options.pop('ghost', False)
        self._hooks   = { x[5:]:self._options.pop(x) for x in self._options.keys() if x.startswith('hook_') }
        self._history = structs.History(tag='data-handler')
        self._history.append(self.__class__.__name__, 'init', True)
        self._stage = ['load']
        self._observer.notify_new(self, dict(stage = 'load'))
        logger.debug('New resource handler %s', self.__dict__)

    def __del__(self):
        try:
            self._observer.notify_del(self, dict())
        except TypeError:
            try:
                logger.debug('Too late to notify del of %s', self)
            except AttributeError:
                pass

    def __str__(self):
        return str(self.__dict__)

    def _get_resource(self):
        """Getter for ``resource`` property."""
        return self._resource

    def _set_resource(self, value):
        """Setter for ``resource`` property."""
        if isinstance(value, resources.Resource):
            self._resource = value
        else:
            raise ValueError('This value is not a plain Resource <%s>', value)

    resource = property(_get_resource, _set_resource)

    def _get_provider(self):
        """Getter for ``provider`` property."""
        return self._provider

    def _set_provider(self, value):
        """Setter for ``provider`` property."""
        if isinstance(value, providers.Provider):
            self._provider = value
        else:
            raise ValueError('This value is not a plain Provider <%s>', value)

    provider = property(_get_provider, _set_provider)

    def _get_container(self):
        """Getter for ``container`` property."""
        return self._container

    def _set_container(self, value):
        """Setter for ``container`` property."""
        if isinstance(value, containers.Container):
            self._container = value
        else:
            raise ValueError('This value is not a plain Container <%s>', value)

    container = property(_get_container, _set_container)

    @property
    def history(self):
        return self._history

    @property
    def observer(self):
        """Footprint observer devoted to ressource handlers tracking."""
        return self._observer

    def observers(self):
        """Remote objects observing the current ressource handler... and my be some others."""
        return self._observer.observers()

    def observed(self):
        """Other objects observed by the observers of the current ressource handler."""
        return [ x for x in self._observer.observed() if x is not self ]

    @property
    def complete(self):
        """Returns whether all the internal components are defined."""
        return bool(self.resource and self.provider and self.container)

    @property
    def stage(self):
        """Return current resource handler stage (load, get, put)."""
        return self._stage[-1]

    def updstage(self, newstage):
        """Notify the new stage to any observing system."""
        self._stage.append(newstage)
        self._observer.notify_upd(self, dict(stage = newstage))

    def is_expected(self):
        """Return a boolean value according to the last stage value (expected or not)."""
        return self.stage.startswith('expect')

    @property
    def contents(self):
        """
        Returns an valid data layout object as long as the current handler
        is complete and the container filled.
        """
        if self._empty:
            self.container.write('')
            self._empty = False
        if self.complete:
            if self.container.filled or self.stage == 'put':
                if self._contents is None:
                    self._contents = self.resource.contents_handler(datafmt=self.container.actualfmt)
                    self._contents.slurp(self.container)
                return self._contents
            else:
                logger.warning('Contents requested on an empty container [%s]', self.container)
        else:
            logger.warning('Contents requested for an uncomplete handler [%s]', self.container)
            return None

    def reset_contents(self):
        """Delete actual internal reference to data contents manager."""
        self._contents = None

    @property
    def ghost(self):
        return self._ghost

    @property
    def hooks(self):
        return self._hooks

    @property
    def options(self):
        return self._options

    def mkopts(self, *dicos, **kw):
        """Returns options associated to that handler and a system reference."""
        opts = dict(
            intent = dataflow.intent.IN,
            fmt    = self.container.actualfmt,
        )
        opts.update(self.options)
        for d in dicos:
            opts.update(d)
        opts.update(kw)
        return opts

    def location(self):
        """Returns the URL as defined by the internal provider and resource."""
        self._lasturl = None
        if self.provider and self.resource:
            self._lasturl = self.provider.uri(self.resource)
            return self._lasturl
        else:
            logger.warning('Resource handler %s could not build location', self)
            return None

    def idcard(self, indent=2):
        """
        Returns a multilines documentation string with a summary
        of the valuable information contained by this handler.
        """
        tab = ' ' * indent
        card = "\n".join((
            '{0}Handler {1!r}',
            '{0}{0}Role      : {2:s}',
            '{0}{0}Alternate : {3:s}',
            '{0}{0}Complete  : {4}',
            '{0}{0}Options   : {5}',
            '{0}{0}Location  : {6}'
       )).format(
            tab,
            self, self.role, self.alternate, self.complete, self.options, self.location()
        )
        for subobj in ('resource', 'provider', 'container'):
            obj = getattr(self, subobj, None)
            if obj:
                thisdoc = "\n".join((
                    '{0}{1:s} {2!r}',
                    '{0}{0}Realkind   : {3:s}',
                    '{0}{0}Attributes : {4:s}'
                )).format(
                    tab,
                    subobj.capitalize(), obj, obj.realkind, obj.footprint_as_dict()
                )
            else:
                thisdoc = '{0}{1:s} undefined'.format(tab, subobj.capitalize())
            card = card + "\n\n" + thisdoc
        return card

    def quickview(self, nb=0, indent=0):
        """Standard glance to objects."""
        tab = '  ' * indent
        print '{0}{1:02d}. {2:s}'.format(tab, nb, repr(self))
        print '{0}  Complete  : {1:s}'.format(tab, str(self.complete))
        for subobj in ( 'container', 'provider', 'resource' ):
            obj = getattr(self, subobj, None)
            if obj:
                print '{0}  {1:10s}: {2:s}'.format(tab, subobj.capitalize(), str(obj))

    def as_dict(self):
        """Produce a raw json-compatible dictionnay."""
        rhd = dict(options=dict())
        for k, v in self.options.iteritems():
            try:
                v = v.export_dict()
            except AttributeError:
                pass
            rhd['options'][k] = v
        for subobj in ('resource', 'provider', 'container'):
            obj = getattr(self, subobj, None)
            if obj is not None:
                rhd[subobj] = obj.footprint_export()
        return rhd

    @property
    def lasturl(self):
        """The last actual URL value evaluated."""
        return self._lasturl

    @property
    def uridata(self):
        """Actual extra URI values after store definition."""
        return self._uridata

    @property
    def store(self):
        if self.resource and self.provider:
            self._uridata = net.uriparse(self.location())
            stopts = { k:v for k, v in self.options.items() if k.startswith('stor') }
            return footprints.proxy.store(
                scheme = self._uridata.pop('scheme'),
                netloc = self._uridata.pop('netloc'),
                **stopts
            )
        else:
            return None

    def check(self, **extras):
        """Returns a stat-like information to the remote resource."""
        rst = None
        if self.resource and self.provider:
            store = self.store
            if store:
                logger.debug('Check resource %s at %s from %s', self, self.lasturl, store)
                rst = store.check(
                    self.uridata,
                    self.mkopts(extras)
                )
                self.history.append(store.fullname(), 'check', rst)
            else:
                logger.error('Could not find any store to check %s', self.lasturl)
        else:
            logger.error('Could not check a rh without defined resource and provider %s', self)
        return rst

    def locate(self, **extras):
        """Try to figure out what would be the physical location of the resource."""
        rst = None
        if self.resource and self.provider:
            store = self.store
            if store:
                logger.debug('Locate resource %s at %s from %s', self, self.lasturl, store)
                rst = store.locate(
                    self.uridata,
                    self.mkopts(extras)
                )
                self.history.append(store.fullname(), 'locate', rst)
            else:
                logger.error('Could not find any store to locate %s', self.lasturl)
        else:
            logger.error('Could not locate an incomplete rh %s', self)
        return rst

    def get(self, **extras):
        """Method to retrieve through the provider the resource and feed the current container."""
        rst = False
        if self.complete:
            store = self.store
            if store:
                logger.debug('Get resource %s at %s from %s', self, self.lasturl, store)
                rst = store.get(
                    self.uridata,
                    self.container.iotarget(),
                    self.mkopts(dict(rhandler = self.as_dict()), extras)
                )
                self.container.updfill(rst)
                self.history.append(store.fullname(), 'get', rst)
                if rst:
                    if store.delayed:
                        self.updstage('expected')
                        logger.info('Resource <%s> is expected', self.container.iotarget())
                    else:
                        self.updstage('get')
                        for hook_name in sorted(self.hooks.keys()):
                            hook_func, hook_args = self.hooks[hook_name]
                            #logger.info('HOOK after get <%s(%s)>' % (hook_func, hook_args))
                            hook_func(sessions.current(), self, *hook_args)
            else:
                logger.error('Could not find any store to get %s', self.lasturl)
        else:
            logger.error('Could not get an incomplete rh %s', self)
        return rst

    def put(self, **extras):
        """Method to store data from the current container through the provider."""
        rst = False
        if self.complete:
            store = self.store
            if store:
                iotarget = self.container.iotarget()
                logger.debug('Put resource %s as io %s at store %s', self, iotarget, store)
                if iotarget is not None and ( self.container.exists() or self.provider.expected ):
                    for hook_name in sorted(self.hooks.keys()):
                        hook_func, hook_args = self.hooks[hook_name]
                        logger.info('HOOK before put <%s(%s)>' % (hook_func, hook_args))
                        hook_func(sessions.current(), self, *hook_args)
                    logger.debug('Put resource %s at %s from %s', self, self.lasturl, store)
                    rst = store.put(
                        iotarget,
                        self.uridata,
                        self.mkopts(dict(rhandler = self.as_dict()), extras)
                    )
                    self.history.append(store.fullname(), 'put', rst)
                    self.updstage('put')
                elif self.ghost:
                    self.history.append(store.fullname(), 'put', False)
                    self.updstage('ghost')
                    rst = True
                else:
                    logger.error('Could not find any source to put [%s]', iotarget)
            else:
                logger.error('Could not find any store to put [%s]', self.lasturl)
        else:
            logger.error('Could not put an incomplete rh [%s]', self)
        return rst

    def delete(self, **extras):
        """Delete the remote resource from store."""
        rst = None
        if self.resource and self.provider:
            store = self.store
            if store:
                logger.debug('Delete resource %s at %s from %s', self, self.lasturl, store)
                rst = store.delete(
                    self.uridata,
                    self.mkopts(dict(rhandler = self.as_dict()), extras)
                )
                self.history.append(store.fullname(), 'delete', rst)
            else:
                logger.error('Could not find any store to delete %s', self.lasturl)
        else:
            logger.error('Could not delete a rh without defined resource and provider %s', self)
        return rst

    def clear(self):
        """Clear the local container contents."""
        rst = False
        if self.container:
            logger.debug('Remove resource container %s', self.container)
            sh = sessions.system()
            rst = sh.remove(
                self.container.localpath(),
                fmt = self.container.actualfmt
            )
            self.history.append(sh.fullname(), 'clear', rst)
        return rst

    def mkgetpr(self, pr_getter=None, tplfile=None, tplskip='sync-skip.tpl', tplfetch='sync-fetch.tpl', py_exec=sys.executable, py_opts=''):
        """Build a getter for the expected resource."""
        if tplfile is None:
            tplfile = tplfetch if self.is_expected() else tplskip
        if pr_getter is None:
            pr_getter = self.container.localpath() + '.getpr'
        tpl = config.load_template(sessions.current(), tplfile)
        with io.open(pr_getter, 'wb') as fd:
            fd.write(tpl.substitute(
                python  = py_exec,
                pyopts  = py_opts,
                promise = self.container.localpath(),
            ))
        sh = sessions.system()
        sh.chmod(pr_getter, 0555)
        return pr_getter

    def wait(self, sleep=10, timeout=300, fatal=False):
        """Wait for an expected resource or return immediatly."""
        rc = True
        local = self.container.localpath()
        if self.is_expected():
            nb = 0
            sh = sessions.system()
            pr = sh.json_load(local)
            itself  = pr.get('itself')
            nbtries = int(timeout / sleep)
            logger.info('Waiting %d x %d s. for expected resource <%s>', nbtries, sleep, local)
            while sh.path.exists(itself):
                sh.sleep(sleep)
                nb += 1
                if nb > nbtries:
                    logger.error('Could not wait anymore <%d>', nb)
                    rc = False
                    if fatal:
                        logger.critical('Missing expected resource is fatal <%s>', local)
                        raise HandlerError('Expected resource missing')
                    break
            else:
                remote = pr.get('locate').split(';')[0]
                if sh.path.exists(remote):
                    logger.info('Keeping promise for remote resource <%s>', remote)
                else:
                    logger.warning('Empty promise for remote resource <%s>', remote)
                    rc = False
        else:
            logger.info('Resource <%s> not expected', local)
        return rc

    def save(self):
        """Rewrite data if contents have been updated."""
        rst = False
        if self.contents:
            rst = self.contents.rewrite(self.container)
            if not self.container.is_virtual():
                self.container.close()
        else:
            logger.warning('Try to save undefined contents %s', self)
        return rst

    def strlast(self):
        """String formatted log of the last action."""
        return ' '.join([ str(x) for x in self.history.last ])

