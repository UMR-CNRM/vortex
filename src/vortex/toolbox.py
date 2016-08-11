#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Top level interface for accessing the VORTEX facilities.
"""

#: Automatic export of superstar interface.
__all__ = [ 'rload', 'rget', 'rput' ]

import re

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex import sessions, data, proxy, VortexForceComplete
from vortex.layout.dataflow import stripargs_section
from vortex.util.structs import History

#: Shortcut to footprint env defaults
defaults = footprints.setup.defaults

sectionmap = {'input': 'get', 'output': 'put', 'executable': 'get'}

active_now              = False
active_insitu           = False
active_verbose          = True
active_promise          = True
active_clear            = False
active_metadatacheck    = True

#: History recording
history = History(tag='rload')

# Most commonly used functions


def show_toolbox_settings(ljust=24):
    """Print the current settings of the toolbox."""
    for key in ['active_{}'.format(act) for act in
                ('now', 'insitu', 'verbose', 'promise', 'metadatacheck', 'clear')]:
        kval = globals().get(key, None)
        if kval is not None:
            print '+', key.ljust(ljust), '=', kval


def quickview(args, nb=0, indent=0):
    """Recursive call to any quick view of objects specified as arguments."""
    if not isinstance(args, list) and not isinstance(args, tuple):
        args = ( args, )
    for x in args:
        if nb:
            print
        nb += 1
        quickview = getattr(x, 'quickview', None)
        if quickview:
            quickview(nb, indent)
        else:
            print '{0:02d}. {1:s}'.format(nb, x)


def rload(*args, **kw):
    """
    Resource Loader.

    This function behaves as a factory for any possible pre-defined family
    of VORTEX object resources.

    Arguments could be a mix of a list of dictionay-type objects and key/value
    parameters. Other type of arguments will be discarded.

    An abstract resource descriptor is built as the agregation of these arguments
    and then expanded according to rules defined in the :mod:`footprints.util` module.
    For any expanded descriptor, the resources module will try to pickup the best
    candidate (if any) that could match the description (ie: Resource,
    Provider, Container, etc.)

    Finaly, a :class:`vortex.data.Handler` object is associated to this list of candidates.
    The outcome of the rload function is therefore a list of resources.Handler objects.
    """
    rd = dict()
    for a in args:
        if isinstance(a, dict):
            rd.update(a)
        else:
            logger.warning('Discard rload argument <%s>', a)
    rd.update(kw)
    if rd:
        history.append(rd.copy())
    rx = [
        proxy.containers.pickup(  # @UndefinedVariable
            proxy.providers.pickup(  # @UndefinedVariable
                proxy.resources.pickup(x)  # @UndefinedVariable
            )
        ) for x in footprints.util.expand(rd)
    ]
    logger.debug('Resource desc %s', rx)
    return [ data.handlers.Handler(x) for x in rx ]


def rh(*args, **kw):
    """
    This function selects the first complete resource handler as returned
    by the *rload* function.
    """
    rl = filter(lambda x: x.complete, rload(*args, **kw))
    if rl:
        return rl[0]
    else:
        return None


def rget(*args, **kw):
    """
    This function calls the :meth:`get` method on any resource handler returned
    by the *rload* function.
    """
    rl = rload(*args, **kw)
    for rh in rl:
        rh.get()
    return rl


def rput(*args, **kw):
    """
    This function calls the :meth:`put` method on any resource handler returned
    by the *rload* function.
    """
    rl = rload(*args, **kw)
    for rh in rl:
        rh.put()
    return rl


def nicedump(msg, **kw):
    """Simple dump of the dict contents with ``msg`` as header."""
    print '#', msg, ':'
    for k, v in sorted(kw.iteritems()):
        print '+', k.ljust(12), '=', str(v)
    print


def add_section(section, args, kw):
    """Add a ``section`` type to the current sequence."""

    t = sessions.current()

    # First, retrieve arguments of the toolbox command itself
    now       = kw.pop('now', active_now)
    loglevel  = kw.pop('loglevel', None)
    talkative = kw.pop('verbose', active_verbose)
    complete  = kw.pop('complete', False)

    if complete:
        kw['fatal'] = False

    # Second, retrieve arguments that could be used by the now command
    cmdopts = dict(
        force = kw.pop('force', False)
    )

    # Third, collect arguments for triggering some hook
    hooks = dict()
    for ahook in [ x for x in kw.keys() if x.startswith('hook_') ]:
        cbhook = footprints.util.mktuple(kw.pop(ahook))
        cbfunc = cbhook[0]
        if not callable(cbfunc):
            cbfunc = t.sh.import_function(cbfunc)
        hooks[ahook] = footprints.FPTuple((cbfunc, cbhook[1:]))

    # Swich off autorecording of the current context
    ctx = t.context
    ctx.record_off()

    # Possibily change the log level if necessary
    oldlevel = t.loglevel
    if loglevel is not None:
        t.setloglevel(loglevel.upper())

    # Distinguish between section arguments, and resource loader arguments
    opts, kwclean = stripargs_section(**kw)

    # Strip the metadatacheck option depending on active_metadatacheck
    if not active_metadatacheck:
        if kwclean.get('metadatacheck', False):
            logger.info("The metadatacheck option is forced to False since active_metadatacheck=False.")
            kwclean['metadatacheck'] = False

    # Show the actual set of arguments
    if talkative:
        nicedump('New {0:s} section with options'.format(section), **opts)
        nicedump('Resource handler description', **kwclean)
        nicedump(
            'This command options',
            complete = complete,
            loglevel = loglevel,
            now = now,
            verbose  = talkative,
        )
        if hooks:
            nicedump('Hooks triggered', **hooks)

    # Let the magic of footprints resolution operate...
    kwclean.update(hooks)
    rl = rload(*args, **kwclean)
    rlok = list()

    # Prepare the references to the actual section method to perform
    push = getattr(ctx.sequence, section)
    doitmethod = sectionmap[section]

    # Create a section for each resource handler, and perform action on demand
    for ir, rhandler in enumerate(rl):
        newsections = push(rh=rhandler, **opts)
        ok = bool(newsections)
        if ok and now:
            if talkative:
                t.sh.subtitle('Resource no {0:02d}/{1:02d}'.format(ir + 1, len(rl)))
                rhandler.quickview(nb=ir + 1, indent=0)
                t.sh.header('Action ' + doitmethod)
                logger.info('%s %s ...', doitmethod.upper(), rhandler.location())
            ok = getattr(newsections[0], doitmethod)(**cmdopts)
            if talkative:
                t.sh.header('Result from ' + doitmethod)
                logger.info('%s returns [%s]', doitmethod.upper(), ok)
            if talkative and not ok:
                logger.error('Could not %s resource %s', doitmethod, rhandler.container.localpath())
                print t.line
            if not ok:
                if complete:
                    logger.warning('Force complete for %s', rhandler.location())
                    raise VortexForceComplete('Force task complete on resource error')
            if t.sh.trace:
                print
        if ok:
            rlok.append(rhandler)

    if loglevel is not None:
        t.setloglevel(oldlevel)
    ctx.record_on()
    return rlok


# noinspection PyShadowingBuiltins
def input(*args, **kw):  # @ReservedAssignment
    """Add an input section to the current sequence."""
    kw.setdefault('insitu', active_insitu)
    return add_section('input', args, kw)


def inputs(ticket=None, context=None):
    """Return effective inputs in specified context."""
    if context is None:
        if ticket is None:
            ticket = sessions.current()
        context = ticket.context
    return context.sequence.effective_inputs()


def show_inputs(context=None):
    """Dump a summary of inputs sections."""
    t = sessions.current()
    for csi in inputs(ticket=t):
        t.sh.header('Input ' + str(csi))
        csi.show(ticket=t, context=context)
        print


def output(*args, **kw):
    """Add an output section to the current sequence."""
    return add_section('output', args, kw)


def outputs(ticket=None, context=None):
    """Return effective outputs in specified context."""
    if context is None:
        if ticket is None:
            ticket = sessions.current()
        context = ticket.context
    return context.sequence.effective_outputs()


def show_outputs(context=None):
    """Dump a summary of outputs sections."""
    t = sessions.current()
    for cso in outputs(ticket=t):
        t.sh.header('Output ' + str(cso))
        cso.show(ticket=t, context=context)
        print


def promise(*args, **kw):
    """Log a promise before execution."""
    kw.update(
        promised = True,
        force    = True,
        now      = active_promise,
    )
    if not active_promise:
        logger.warning('Promise flag is <%s> in that context', active_promise)
    return add_section('output', args, kw)


def executable(*args, **kw):
    """Add an executable section to the current sequence."""
    kw.setdefault('insitu', active_insitu)
    return add_section('executable', args, kw)


def algo(*args, **kw):
    """Load an algo component and display the description provided."""

    # First, retrieve arguments of the toolbox command itself
    loglevel  = kw.pop('loglevel', None)
    talkative = kw.pop('verbose', active_verbose)

    # Swich off autorecording of the current context
    t = sessions.current()
    ctx = t.context
    ctx.record_off()

    # Possibily change the log level if necessary
    oldlevel = t.loglevel
    if loglevel is not None:
        t.setloglevel(loglevel.upper())

    if talkative:
        nicedump('Loading algo component with description:', **kw)

    ok = proxy.component(**kw)  # @UndefinedVariable
    if ok and talkative:
        print t.line
        ok.quickview(nb=1, indent=0)

    if loglevel is not None:
        t.setloglevel(oldlevel)

    ctx.record_on()
    return ok


def diff(*args, **kw):
    """Perform a diff with a resource with the same local name."""

    # First, retrieve arguments of the toolbox command itself
    fatal     = kw.pop('fatal', True)
    loglevel  = kw.pop('loglevel', None)
    talkative = kw.pop('verbose', active_verbose)

    # Distinguish between section arguments, and resource loader arguments
    opts, kwclean = stripargs_section(**kw)

    # Show the actual set of arguments
    if talkative:
        nicedump('Discard section options', **opts)
        nicedump('Resource handler description', **kwclean)

    # Fast exit in case of undefined value
    rlok = list()
    if None in kwclean.values():
        logger.warning('Skip diff because of undefined argument(s)')
        return rlok

    # Swich off autorecording of the current context
    t = sessions.current()
    ctx = t.context
    ctx.record_off()

    # Possibily change the log level if necessary
    oldlevel = t.loglevel
    if loglevel is not None:
        t.setloglevel(loglevel.upper())

    # Do not track the reference files
    kwclean['storetrack'] = False

    # Let the magic of footprints resolution operate...
    for ir, rhandler in enumerate(rload(*args, **kwclean)):
        if talkative:
            print t.line
            rhandler.quickview(nb=ir + 1, indent=0)
            print t.line
        if not rhandler.complete:
            logger.error('Incomplete Resource Handler for diff [%s]', rhandler)
            if fatal:
                raise ValueError('Incomplete Resource Handler for diff')
        comp_source = rhandler.container

        # Create a new container to hold the reference file
        lazzycontainer = footprints.proxy.container(shouldfly=True,
                                                    actualfmt=comp_source.actualfmt)
        # Swapp the original container with the lazzy one
        rhandler.container = lazzycontainer
        # Get the reference file
        rcget = rhandler.get()
        if not rcget:
            logger.error('Cannot get the reference resource: %s', rhandler.locate())
            if fatal:
                raise ValueError('Cannot get the reference resource')
        else:
            logger.info('The reference file is stored under: %s',
                        rhandler.container.localpath())
        # What are the differences ?
        rc = rcget and t.sh.diff(comp_source.localpath(),
                                 rhandler.container.localpath(),
                                 fmt = rhandler.container.actualfmt)
        # Delete the reference file
        lazzycontainer.clear()

        # Now proceed with the result
        logger.info('Diff return %s', str(rc))
        try:
            logger.info('Diff result %s', str(rc.result))
        except AttributeError:
            pass
        if not rc:
            logger.warning('Some diff occurred with %s', rhandler.locate())
            try:
                rc.result.differences()
            except StandardError:
                pass
            if fatal:
                logger.critical('Difference in resource comparison is fatal')
                raise ValueError('Fatal diff')
        if t.sh.trace:
            print
        rlok.append(rc)

    if loglevel is not None:
        t.setloglevel(oldlevel)

    ctx.record_on()
    return rlok


def magic(localpath, **kw):
    """
    Return a minimal resource handler build with an unknown resource,
    a file container and an anonymous provider described with its url.
    """
    kw.update(
        unknown  = True,
        magic    = 'magic://localhost/' + localpath,
        filename = localpath,
    )
    rhmagic = rh(**kw)
    rhmagic.get()
    return rhmagic


def namespaces(**kw):
    """
    Some kind of interactive help to find out quickly which namespaces are in used.
    By default tracks ``stores`` and ``providers`` but one could give an ``only`` argument.
    """
    rematch = re.compile('|'.join(kw.get('match', '.').split(',')), re.IGNORECASE)
    if 'only' in kw:
        usedcat = kw['only'].split(',')
    else:
        usedcat = ('provider', 'store')
    nameseen = dict()
    for cat in [ footprints.collectors.get(tag=x) for x in usedcat ]:
        for cls in cat():
            fp = cls.footprint_retrieve().attr
            netattr = fp.get('namespace', None)
            if not netattr:
                netattr = fp.get('netloc', None)
            if netattr and 'values' in netattr:
                for netname in filter(lambda x: rematch.search(x), netattr['values']):
                    if netname not in nameseen:
                        nameseen[netname] = list()
                    nameseen[netname].append(cls.fullname())
    return nameseen


def print_namespaces(**kw):
    """Formatted print of current namespaces."""
    prefix = kw.pop('prefix', '+ ')
    nd = namespaces(**kw)
    justify = max([ len(x) for x in nd.keys() ])
    linesep = ",\n" + ' ' * (justify + len(prefix) + 2)
    for k, v in sorted(nd.iteritems()):
        nice_v = linesep.join(v) if len(v) > 1 else v[0]
        print prefix + k.ljust(justify), '[' + nice_v + ']'


def clear_promises(clear=None, netloc='promise.cache.fr', scheme='vortex',
                   storeoptions=None):
    """Remove all promises that have been made in the current python session.

    :param netloc: Netloc of the promise's cache store to clean up
    :param scheme: Scheme of the promise's cache store to clean up
    :param storeoptions: Option dictionary passed to the store (may be None)
    """
    if clear is None:
        clear = active_clear
    if clear:
        t = sessions.current()
        t.sh.header('Clear promises for {}://{}'.format(scheme, netloc))
        skeleton = dict(scheme=scheme, netloc=netloc)
        promises = t.context.localtracker.grep_uri('put', skeleton)
        if promises:
            logger.info('Some promises are left pending...')
            if storeoptions is None:
                storeoptions = dict()
            store = footprints.proxy.store(scheme=scheme, netloc=netloc,
                                           **storeoptions)
            for promise in [pr.copy() for pr in promises]:
                del promise['scheme']
                del promise['netloc']
                store.delete(promise)
        else:
            logger.info('No promises were left pending.')


def rescue(*files, **opts):
    """Action to be undertaken when things really went bad."""

    t   = sessions.current()
    sh  = t.sh
    env = t.env

    # Force clearing of all promises
    clear_promises(clear=True)

    sh.subtitle('Rescue current dir')
    sh.dir(output=False)

    logger.info('Rescue files %s', files)

    if 'VORTEX_RESCUE' in env and env.false('VORTEX_RESCUE'):
        logger.warning('Skip rescue <VORTEX_RESCUE=%s>', env.VORTEX_RESCUE)
        return False

    if files:
        items = list(files)
    else:
        items = sh.glob('*')

    rfilter = opts.get('filter', env.VORTEX_RESCUE_FILTER)
    if rfilter is not None:
        logger.warning('Rescue filter <%s>', rfilter)
        select = '|'.join(re.split(r'[,;:]+', rfilter))
        items = [ x for x in items if re.search(select, x, re.IGNORECASE) ]
        logger.info('Rescue filter [%s]', select)

    rdiscard = opts.get('discard', env.VORTEX_RESCUE_DISCARD)
    if rdiscard is not None:
        logger.warning('Rescue discard <%s>', rdiscard)
        select = '|'.join(re.split(r'[,;:]+', rdiscard))
        items = [ x for x in items if not re.search(select, x, re.IGNORECASE) ]
        logger.info('Rescue discard [%s]', select)

    if items:

        bkupdir = opts.get('bkupdir', env.VORTEX_RESCUE_PATH)

        if bkupdir is None:
            logger.error('No rescue directory defined.')
        else:
            logger.info('Backup directory defined by user <%s>', bkupdir)
            items.sort()
            logger.info('Rescue items %s', str(items))
            sh.mkdir(bkupdir)
            mkmove = False
            st1 = sh.stat(sh.getcwd())
            st2 = sh.stat(bkupdir)
            if st1 and st2 and st1.st_dev == st2.st_dev:
                mkmove = True
            if mkmove:
                thisrescue = sh.mv
            else:
                thisrescue = sh.cp
            for ritem in items:
                rtarget = sh.path.join(bkupdir, ritem)
                if sh.path.exists(ritem) and not sh.path.islink(ritem):
                    if sh.path.isfile(ritem):
                        sh.rm(rtarget)
                        thisrescue(ritem, rtarget)
                    else:
                        thisrescue(ritem, rtarget)

    else:
        logger.warning('No item to rescue.')

    return bool(items)
