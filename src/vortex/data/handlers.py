#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import io
import re
import sys
import functools

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex import sessions

from vortex.tools  import net
from vortex.util   import config, structs
from vortex.layout import contexts, dataflow
from vortex.data   import containers, resources, providers

OBSERVER_TAG = 'Resources-Handlers'


class HandlerError(RuntimeError):
    """Exception in case of missing resource during the wait mechanism."""
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
        self._resource      = rd.pop('resource', None)
        self._provider      = rd.pop('provider', None)
        self._container     = rd.pop('container', None)
        self._empty         = rd.pop('empty', False)
        self._contents      = None
        self._uridata       = None
        self._options       = rd.copy()
        self._observer      = observer_board(obsname=kw.pop('observer', None))
        self._options.update(kw)
        self._mdcheck       = self._options.pop('metadatacheck', False)
        self._mddelta       = self._options.pop('metadatadelta', dict())
        self._ghost         = self._options.pop('ghost', False)
        self._hooks         = {x[5:]: self._options.pop(x)
                               for x in self._options.keys()
                               if x.startswith('hook_')}
        self._delayhooks    = self._options.pop('delayhooks', False)

        self._history = structs.History(tag='data-handler')
        self._history.append(self.__class__.__name__, 'init', True)
        self._stage = ['load']
        self._observer.notify_new(self, dict(stage = 'load'))
        self._localpr_cache = None  # To cache the promise dictionary
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
            oldhash = self.simplified_hashkey
            self._resource = value
            self._notifyhash(oldhash)
        else:
            raise ValueError('This value is not a plain Resource <%s>', value)

    resource = property(_get_resource, _set_resource)

    def _get_provider(self):
        """Getter for ``provider`` property."""
        return self._provider

    def _set_provider(self, value):
        """Setter for ``provider`` property."""
        if isinstance(value, providers.Provider):
            oldhash = self.simplified_hashkey
            self._provider = value
            self._notifyhash(oldhash)
        else:
            raise ValueError('This value is not a plain Provider <%s>', value)

    provider = property(_get_provider, _set_provider)

    def _get_container(self):
        """Getter for ``container`` property."""
        return self._container

    def _set_container(self, value):
        """Setter for ``container`` property."""
        if isinstance(value, containers.Container):
            oldhash = self.simplified_hashkey
            self._container = value
            self._notifyhash(oldhash)
        else:
            raise ValueError('This value is not a plain Container <%s>', value)

    container = property(_get_container, _set_container)

    @property
    def history(self):
        return self._history

    @property
    def observer(self):
        """Footprint observer devoted to resource handlers tracking."""
        return self._observer

    def observers(self):
        """Remote objects observing the current resource handler... and my be some others."""
        return self._observer.observers()

    def observed(self):
        """Other objects observed by the observers of the current resource handler."""
        return [x for x in self._observer.observed() if x is not self]

    @property
    def complete(self):
        """Returns whether all the internal components are defined."""
        return bool(self.resource and self.provider and self.container)

    @property
    def stage(self):
        """Return current resource handler stage (load, get, put)."""
        return self._stage[-1]

    @property
    def simplified_hashkey(self):
        """Returns a tuple that can be used as a hashkey to quickly identify the handler."""
        if self.complete:
            rkind = getattr(self.resource, 'kind', None)
            rfile = getattr(self.container, 'filename', None)
            return (rkind, rfile)
        else:
            return ('incomplete', )

    @property
    def _cur_session(self):
        """Return the current active session."""
        return sessions.current()

    @property
    def _cur_context(self):
        """Return the current active context."""
        return contexts.current()

    def external_stage_update(self, newstage):
        """This method must not be used directly by users!

        Update the stage upon request (e.g. the file has been fetched by another
        process).
        """
        self._stage.append(newstage)
        if newstage in ('get', ):
            self.container.updfill(True)

    def _updstage(self, newstage, insitu=False):
        """Notify the new stage to any observing system."""
        self._stage.append(newstage)
        self._observer.notify_upd(self, dict(stage = newstage, insitu = insitu))

    def _notifyhook(self, stage, hookname):
        """Notify that a hook function has been executed."""
        self._observer.notify_upd(self, dict(stage = stage, hook = hookname))

    def _notifyhash(self, oldhash):
        """Notify that the hashkey has changed."""
        self._observer.notify_upd(self, dict(oldhash = oldhash, ))

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

    @property
    def delayhooks(self):
        return self._delayhooks

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
            '{0}{0}Complete  : {2}',
            '{0}{0}Options   : {3}',
            '{0}{0}Location  : {4}'
        )).format(
            tab,
            self, self.complete, self.options, self.location()
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
                    subobj.capitalize(),
                    obj, obj.realkind, obj.footprint_as_shallow_dict()
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
        for subobj in ('container', 'provider', 'resource'):
            obj = getattr(self, subobj, None)
            if obj:
                print '{0}  {1:10s}: {2:s}'.format(tab, subobj.capitalize(), str(obj))

    def wide_key_lookup(self, key, exports=False):
        """Return the *key* attribute if it exists in the provider or resource.

        If *exports* is True, the footprint_export() or the export_dict() function
        is called upon the return value.
        """
        try:
            if key == 'safeblock':
                # In olive experiments, the block may contain an indication of
                # the member's number. Usually we do not want to get that...
                a_value = getattr(self.provider, 'block')
                a_value = re.sub(r'(member|fc)_?\d+/', '', a_value)
            else:
                a_value = getattr(self.provider, key)
        except AttributeError:
            try:
                a_value = getattr(self.resource, key)
            except AttributeError:
                raise AttributeError('The {:s} attribute could not be found in {!r}'.format(key, self))
        if exports:
            if hasattr(a_value, 'footprint_export'):
                a_value = a_value.footprint_export()
            elif hasattr(a_value, 'export_dict'):
                a_value = a_value.export_dict()
        return a_value

    def as_dict(self):
        """Produce a raw json-compatible dictionary."""
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
            stopts = {k: v for k, v in self.options.items() if k.startswith('stor')}
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
                if rst and self._mdcheck:
                    logger.info('metadatacheck is on: we are forcing a real get()...')
                    # We are using a temporary fake container
                    mycontainer = footprints.proxy.container(shouldfly=True,
                                                             actualfmt=self.container.actualfmt)
                    try:
                        rst = store.get(
                            self.uridata,
                            mycontainer.iotarget(),
                            self.mkopts(extras)
                        )
                        if rst:
                            if store.delayed:
                                logger.warning("The resource is expected... let's say that's fine.")
                            else:
                                # Create the content manually and drop it when we are done.
                                contents = self.resource.contents_handler(datafmt=mycontainer.actualfmt)
                                contents.slurp(mycontainer)
                                rst = contents.metadata_check(self.resource, delta = self._mddelta)
                    finally:
                        # Delete the temporary container
                        mycontainer.clear()
                self.history.append(store.fullname(), 'check', rst)
                if rst and self.stage == 'load':
                    # Indicate that the resource was checked
                    self._updstage('checked')
                if not rst:
                    # Always signal failures
                    self._updstage('void')
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

    def _generic_apply_hooks(self, action, **extras):
        """Apply the hooks after a get request (or verify that they were done)."""
        if self.hooks:
            mytracker = extras.get('mytracker', None)
            if mytracker is None:
                iotarget = self.container.iotarget()
                mytracker = self._cur_context.localtracker[iotarget]
            for hook_name in sorted(self.hooks.keys()):
                if mytracker.redundant_hook(action, hook_name):
                    logger.info('Hook already executed <hook_name:%s>', hook_name)
                else:
                    logger.info('Executing Hook <hook_name:%s>', hook_name)
                    hook_func, hook_args = self.hooks[hook_name]
                    hook_func(self._cur_session, self, *hook_args)
                    self._notifyhook(action, hook_name)

    def apply_get_hooks(self, **extras):
        """Apply the hooks after a get request (or verify that they were done)."""
        self._generic_apply_hooks(action='get', **extras)

    def apply_put_hooks(self, **extras):
        """Apply the hooks before a put request (or verify that they were done)."""
        self._generic_apply_hooks(action='put', **extras)

    def _actual_get(self, **extras):
        """Internal method in charge of the getting the resource.

        If requested, it will check the metadata of the resource and apply the
        hook functions.
        """
        rst = False
        store = self.store
        if store:
            logger.debug('Get resource %s at %s from %s', self, self.lasturl, store)
            st_options = self.mkopts(dict(rhandler = self.as_dict()), extras)
            # Actual get
            rst = store.get(
                self.uridata,
                self.container.iotarget(),
                st_options,
            )
            self.container.updfill(rst)
            # Check metadata if sensible
            if self._mdcheck and rst and not store.delayed:
                rst = self.contents.metadata_check(self.resource,
                                                   delta = self._mddelta)
                if not rst:
                    logger.info("We are now cleaning up the container and data content.")
                    self.reset_contents()
                    self.clear()
            # For the record...
            self.history.append(store.fullname(), 'get', rst)
            if rst:
                # This is an expected resource
                if store.delayed:
                    self._updstage('expected')
                    logger.info('Resource <%s> is expected', self.container.iotarget())
                # This is a "real" resource
                else:
                    self._updstage('get')
                    if self.hooks:
                        if not self.delayhooks:
                            self.apply_get_hooks(**extras)
                        else:
                            logger.info("(get-)Hooks were delayed")
            else:
                # Always signal failures
                self._updstage('void')
        else:
            logger.error('Could not find any store to get %s', self.lasturl)

        # Reset the promise dictionary cache
        self._localpr_cache = None  # To cache the promise dictionary

        return rst

    def get(self, alternate=False, **extras):
        """Method to retrieve the resource through the provider and feed the current container.

        The behaviour of this method depends on the insitu and alternate options:

        * When insitu is True, the :class:`~vortex.layout.dataflow.LocalTracker`
          object associated with the active context is checked to determine
          whether the resource has already been fetched or not. If not, another
          try is made (but without using any non-cache store).
        * When insitu is False, an attempt to get the resource is systematically
          made except if "alternate" is defined and the local container already
          exists.
        """
        rst = False
        if self.complete:
            if self.options.get('insitu', False):  # This a second pass (or third, forth, ...)
                cur_tracker = self._cur_context.localtracker
                iotarget = self.container.iotarget()
                # The localpath is here and listed in the tracker
                if self.container.exists() and cur_tracker.is_tracked_input(iotarget):
                    # Am I consistent with the ResourceHandler recorded in the tracker ?
                    if cur_tracker[iotarget].match_rh('get', self):
                        rst = True
                        self.container.updfill(True)
                        self._updstage('get', insitu=True)
                        logger.info('The <%s> resource is already here and matches the RH description :-)',
                                    self.container.iotarget())
                    else:
                        # This may happen if fatal=False and the local file was fetched
                        # by an alternate
                        if alternate:
                            logger.info("Alternate is on and the local file exists: ignoring the error.")
                            rst = True
                        else:
                            logger.info("The resource is already here but doesn't matches the RH description :-(")
                            cur_tracker[iotarget].match_rh('get', self, verbose=True)
                            self._updstage('void', insitu=True)
                # Bloody hell, the localpath doesn't exist
                else:
                    rst = self._actual_get(**extras)  # This might be an expected resource...
                    if rst:
                        logger.info("The resource was successfully fetched :-)")
                    else:
                        logger.info("Could not get the resource :-(")
            else:
                if alternate and self.container.exists():
                    logger.info('Alternate <%s> exists', alternate)
                    rst = True
                else:
                    if self.container.exists():
                        logger.warning('The resource is already here: That should not happen at this stage !')
                    rst = self._actual_get(**extras)
        else:
            logger.error('Could not get an incomplete rh %s', self)
        return rst

    def insitu_quickget(self, alternate=False, **extras):
        """This method attempts a straightforward insitu get.

        It is designed to minimise the amount of outputs when everything goes
        smoothly.
        """
        rst = False
        if self.complete:
            if self.options.get('insitu', False):  # This a second pass (or third, forth, ...)
                cur_tracker = self._cur_context.localtracker
                iotarget = self.container.iotarget()
                # The localpath is here and listed in the tracker
                if (self.container.exists() and
                        cur_tracker.is_tracked_input(iotarget)):
                    if cur_tracker[iotarget].match_rh('get', self):
                        rst = True
                        self.container.updfill(True)
                        self._updstage('get', insitu=True)
                    elif alternate:
                        # Alternate is on and the local file exists: ignoring the error.
                        rst = True
            else:
                logger.error('This method should not be called with insitu=False (rh %s)', self)
        return rst

    def put(self, **extras):
        """Method to store data from the current container through the provider.

        Hook functions may be applied before the put in the designated store. We
        will ensure that a given hook function (identified by its name) is not
        applied more than once to the local container.

        Conversely, the low-level stores are made aware of the previous successful
        put. That way, a local container is not put twice to the same destination.
        """
        rst = False
        if self.complete:
            store = self.store
            if store:
                iotarget = self.container.iotarget()
                logger.debug('Put resource %s as io %s at store %s', self, iotarget, store)
                if iotarget is not None and (self.container.exists() or self.provider.expected):
                    mytracker = self._cur_context.localtracker[iotarget]
                    # Execute the hooks only if the local file exists
                    if self.container.exists():
                        if self.hooks:
                            if not self.delayhooks:
                                self.apply_put_hooks(mytracker=mytracker, **extras)
                            else:
                                logger.info("(put-)Hooks were delayed")
                    # Add a filter function to remove duplicated PUTs to the same uri
                    extras_ext = dict(extras)
                    extras_ext['urifilter'] = functools.partial(mytracker.redundant_uri, 'put')
                    # Actual put
                    logger.debug('Put resource %s at %s from %s', self, self.lasturl, store)
                    rst = store.put(
                        iotarget,
                        self.uridata,
                        self.mkopts(dict(rhandler = self.as_dict()), extras_ext)
                    )
                    # For the record...
                    self.history.append(store.fullname(), 'put', rst)
                    self._updstage('put')
                elif self.ghost:
                    self.history.append(store.fullname(), 'put', False)
                    self._updstage('ghost')
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
            rst = self.container.clear()
            self.history.append(self.container.actualpath(), 'clear', rst)
        return rst

    def mkgetpr(self, pr_getter=None, tplfile=None, tplskip='@sync-skip.tpl',
                tplfetch='@sync-fetch.tpl', py_exec=sys.executable, py_opts=''):
        """Build a getter for the expected resource."""
        if tplfile is None:
            tplfile = tplfetch if self.is_expected() else tplskip
        if pr_getter is None:
            pr_getter = self.container.localpath() + '.getpr'
        t = self._cur_session
        tpl = config.load_template(t, tplfile)
        with io.open(pr_getter, 'wb') as fd:
            fd.write(tpl.substitute(
                python  = py_exec,
                pyopts  = py_opts,
                promise = self.container.localpath(),
            ))
        t.sh.chmod(pr_getter, 0555)
        return pr_getter

    @property
    def _localpr_json(self):
        if self.is_expected():
            if self._localpr_cache is None:
                self._localpr_cache = self._cur_session.sh.json_load(self.container.localpath())
            return self._localpr_cache
        else:
            return None

    def is_grabable(self, check_exists=False):
        """Return if an expected resource is availlable or not.

        Note: If it returns True, the user still need to :meth:`get` the resource.
        """
        rc = True
        if self.is_expected():
            pr = self._localpr_json
            itself  = pr.get('itself')
            rc = not self._cur_session.sh.path.exists(itself)
            if rc and check_exists:
                remote = pr.get('locate').split(';')[0]
                rc = self._cur_session.sh.path.exists(remote)
        return rc

    def wait(self, sleep=10, timeout=300, fatal=False):
        """Wait for an expected resource or return immediately."""
        rc = True
        local = self.container.localpath()
        if self.is_expected():
            nb = 0
            sh = self._cur_session.sh
            pr = self._localpr_json
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
        return ' '.join([str(x) for x in self.history.last])

