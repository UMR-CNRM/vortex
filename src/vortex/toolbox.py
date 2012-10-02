#!/bin/env python
# -*- coding:Utf-8 -*-

r"""
Top level interface for accessing to the VORTEX facilities.
"""

#: Automatic export of superstar interface.
__all__ = [ 'rload', 'rget', 'rput' ]

import logging, re
from vortex import sessions, syntax, data
from vortex.data import resources, containers, providers, stores
from vortex.algo import components
from vortex.layout.dataflow import stripargs_section
from vortex.utilities.decorators import printargs

@printargs
def rload(*args, **kw):
    r"""
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
            logging.warning('Discard rload argument <%s>', a)
    rd.update(kw)
    rx = [ containers.pickup(providers.pickup(resources.pickup(x))) for x in syntax.expand(rd)]
    logging.debug('Resource desc %s', rx)
    return [data.handlers.Handler(x) for x in rx]


@printargs
def rh(*args, **kw):
    r"""
    This function selects the first complete resource handler as returned
    by the *rload* function.
    """
    rl = filter(lambda x: x.complete, rload(*args, **kw))
    if rl:
        return rl[0]
    else:
        return None


@printargs
def rget(*args, **kw):
    r"""
    This function calls the :meth:`get` method on any resource handler returned
    by the *rload* function.
    """
    rl = rload(*args, **kw)
    for rh in rl:
        rh.get()
    return rl


@printargs
def rput(*args, **kw):
    r"""
    This function calls the :meth:`put` method on any resource handler returned
    by the *rload* function.
    """
    rl = rload(*args, **kw)
    for rh in rl:
        rh.put()
    return rl

@printargs
def input(*args, **kw):
    r"""
    This function adds an input section to the current sequence.
    """
    ctx = sessions.ticket().context
    ctx.record_off()
    ( opts, kwclean ) =  stripargs_section(**kw)
    rl = rload(*args, **kwclean)
    for rhandler in rl:
        ctx.sequence.input(rh=rhandler, **opts)
    ctx.record_on()
    return rl

@printargs
def output(*args, **kw):
    r"""
    This function adds an output section to the current sequence.
    """
    ctx = sessions.ticket().context
    ctx.record_off()
    ( opts, kwclean ) =  stripargs_section(**kw)
    rl = rload(*args, **kwclean)
    for rhandler in rl:
        ctx.sequence.output(rh=rhandler, **opts)
    ctx.record_on()
    return rl

def namespaces(**kw):
    r"""
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

component = components.load
container = containers.load
provider = providers.load
resource = resources.load
store = stores.load
