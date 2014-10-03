#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Top level interface for accessing the VORTEX facilities.
"""

#: Automatic export of superstar interface.
__all__ = [ 'rload', 'rget', 'rput' ]

import re

import footprints

from vortex.autolog import logdefault as logger
from vortex import sessions, data, proxy
from vortex.layout.dataflow import stripargs_section
from vortex.util.structs import History

#: Shortcut to footprint env defaults
defaults = footprints.setup.defaults

sectionmap = {'input': 'get', 'output': 'put', 'executable': 'get'}
justdoit = False
getinsitu = False
verbose = 0

# History recording

history = History(tag='rload')

# Most commonly used functions


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
        proxy.containers.pickup(
            proxy.providers.pickup(
                proxy.resources.pickup(x)
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


def pushsection(section, args, kw):
    """Add a ``section`` type to the current sequence."""
    now = kw.pop('now', justdoit)
    t = sessions.ticket()
    ctx = t.context
    ctx.record_off()
    opts, kwclean = stripargs_section(**kw)
    if verbose > 1:
        print "New {0:s} section with options: {1:s}\n\nResource handler's description: {2:s}\n".format(
            section,
            footprints.dump.lightdump(opts),
            footprints.dump.lightdump(kwclean)
        )
    rl = rload(*args, **kwclean)
    rlok = list()
    push = getattr(ctx.sequence, section)
    doitmethod = sectionmap[section]
    if verbose and now:
        logger.info('Just Do It ... active for method [%s]', doitmethod)
    for rhandler in rl:
        newsections = push(rh=rhandler, **opts)
        ok = bool(newsections)
        if ok and now:
            if verbose:
                logger.info(' > %s %s ...', doitmethod, rhandler.location())
            ok = getattr(newsections[0], doitmethod)()
            if verbose and not ok:
                logger.warning(' > Could not %s resource:', doitmethod)
                rhandler.quickview(indent=4)
            if t.sh.trace:
                print
        if ok:
            rlok.append(rhandler)
    ctx.record_on()
    return rlok


# noinspection PyShadowingBuiltins
def input(*args, **kw):
    """Add an input section to the current sequence."""
    kw.setdefault('insitu', getinsitu)
    return pushsection('input', args, kw)


def inputs(ticket=None, context=None):
    """Return effective inputs in specified context."""
    if context is None:
        if ticket is None:
            ticket = sessions.ticket()
        context = ticket.context
    return context.sequence.effective_inputs()


def show_inputs(context=None):
    """Dump a summary of inputs sections."""
    t = sessions.ticket()
    for csi in inputs():
        t.sh.header('Input ' + str(csi))
        csi.show(ticket=t, context=context)
        print


def output(*args, **kw):
    """Add an output section to the current sequence."""
    return pushsection('output', args, kw)


def outputs(ticket=None, context=None):
    """Return effective outputs in specified context."""
    if context is None:
        if ticket is None:
            ticket = sessions.ticket()
        context = ticket.context
    return context.sequence.effective_outputs()


def show_outputs(context=None):
    """Dump a summary of outputs sections."""
    t = sessions.ticket()
    for cso in outputs():
        t.sh.header('Output ' + str(cso))
        cso.show(ticket=t, context=context)
        print


def executable(*args, **kw):
    """Add an executable section to the current sequence."""
    kw.setdefault('insitu', getinsitu)
    return pushsection('executable', args, kw)


def algo(*args, **kw):
    """Load an algo component and display the description provided."""
    ctx = sessions.ticket().context
    ctx.record_off()
    if verbose > 1:
        print 'Loading algo component with description:', footprints.dump.lightdump(kw), "\n"
    ok = proxy.component(**kw)
    ctx.record_on()
    return ok


def magic(url, localpath):
    """
    Return a minimal resource handler build with an unknown resource,
    a file container and an anonymous provider described with its url.
    """
    rhmagic = rh(unknown=True, magic=url, filename=localpath)
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
        usedcat = ( 'provider', 'store' )
    nameseen = dict()
    for cat in [ footprints.collectors.get(x) for x in usedcat ]:
        for cls in cat():
            fp = cls.retrieve_footprint().attr
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
    prefix  = kw.pop('prefix', '+ ')
    nd = namespaces(**kw)
    justify = max([ len(x) for x in nd.keys() ])
    linesep = ",\n" + ' ' * (justify+len(prefix)+2)
    for k, v in sorted(nd.iteritems()):
        nice_v = linesep.join(v) if len(v) > 1 else v[0]
        print prefix + k.ljust(justify), '[' + nice_v + ']'

