#!/bin/env python
# -*- coding: utf-8 -*-

"""
Top level interface for accessing to the VORTEX facilities.
"""

#: Automatic export of superstar interface.
__all__ = [ 'rload', 'rget', 'rput' ]

import re
from vortex.autolog import logdefault as logger
from vortex import sessions, syntax, data
from vortex.data import resources, containers, providers, stores
from vortex.algo import components
from vortex.tools import caches, targets
from vortex.layout.dataflow import stripargs_section

#: Shortcut to footprint env defaults
defaults = syntax.footprint.envfp
setfpext = syntax.footprint.setfpext
sectionmap = {'input':'get', 'output':'put', 'executable':'get'}
justdoit = False
getinsitu = False
verbose = False

# Most commonly used functions

def quickview(args, nb=0, indent=0):
    """Recursive call to any quick view of objects specified as arguments."""
    if not isinstance(args, list) and not isinstance(args, tuple):
        args = ( args, )
    for x in args:
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
    and then expanded according to rules defined in the syntax module. For any
    expanded descriptor, the resources module will try to pickup the best
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
    rx = [ containers.pickup(providers.pickup(resources.pickup(x))) for x in syntax.expand(rd)]
    logger.debug('Resource desc %s', rx)
    return [data.handlers.Handler(x) for x in rx]

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

def pushsection(section, args, kw):
    """Add a ``section`` type to the current sequence."""
    now = kw.setdefault('now', justdoit)
    del kw['now']
    ctx = sessions.ticket().context
    ctx.record_off()
    opts, kwclean = stripargs_section(**kw)
    rl = rload(*args, **kwclean)
    rlok = list()
    push = getattr(ctx.sequence, section)
    doitmethod = sectionmap[section]
    if verbose and now:
        logger.info('Just Do It ... active for method [%s]', doitmethod)
    for rhandler in rl:
        push(rh=rhandler, **opts)
        ok = True
        if now:
            if verbose:
                logger.info(' > %s %s ...', doitmethod, rhandler.location())
            ok = getattr(rhandler, doitmethod)()
            if verbose:
                logger.info(' > %s', str(ok))
        if ok:
            rlok.append(rhandler)
    ctx.record_on()
    return rlok

def input(*args, **kw):
    """Add an input section to the current sequence."""
    kw.setdefault('insitu', getinsitu)
    return pushsection('input', args, kw)

def output(*args, **kw):
    """Add an output section to the current sequence."""
    return pushsection('output', args, kw)

def executable(*args, **kw):
    """Add an executable section to the current sequence."""
    kw.setdefault('insitu', getinsitu)
    loaded = pushsection('executable', args, kw)
    if len(loaded) == 1:
        loaded = loaded[0]
    return loaded

def magic(uri, localpath):
    return rh(unknown=True, magic=uri, filename=localpath)

def namespaces(**kw):
    """
    Some kind of interactive help to find out quickly which namespaces are in used.
    By default tracks ``stores`` and ``providers`` but one could give an ``only`` argument.
    """
    rematch = re.compile('|'.join(kw.get('match', '.').split(',')), re.IGNORECASE)
    usedcat = dict(
        providers = providers.catalog(),
        stores = stores.catalog()
    )
    select = usedcat.keys()
    if 'only' in kw:
        select = kw['only'].split(',')
    nameseen = dict()
    for cat in [ usedcat[x] for x in select ]:
        for cls in cat():
            fp = cls.footprint().attr
            netattr = fp.get('namespace', None)
            if not netattr:
                netattr = fp.get('netloc', None)
            if netattr and 'values' in netattr:
                for netname in filter(lambda x: rematch.search(x), netattr['values']):
                    if netname not in nameseen:
                        nameseen[netname] = list()
                    nameseen[netname].append(cls.fullname())
    return nameseen

# Shortcuts

algo = components.load
component = components.load
container = containers.load
provider = providers.load
resource = resources.load
store = stores.load
target = targets.load
cache = caches.load
