#!/usr/bin/env python
# -*- coding: utf-8 -*-

from StringIO import StringIO
import json
from random import seed, sample

import footprints
from vortex import sessions
from vortex.util import helpers

#: No automatic export
__all__ = []

logger = footprints.loggers.getLogger(__name__)


def drawingfunction(options):
    """Draw a random sample from a *set* of values.

    This function is designed to be executed by a
    :obj:`vortex.data.stores.FunctionStore` object.

    The *set* of values is computed using the resource's argument:
    *set = [resource.start, resource.start + resource.nbset - 1]*. If
    *resource.start* does not exists, *resource.start=1* is assumed.

    The size of the sample is given by the *nblot* argument of the resource

    The random generator is initialised using the resource's date. Consequently,
    for a given date, the drawing is reproducible.

    :param dict options: All the options passed to the store plus anything from
        the query part of the URI.

    :return: Content of a :obj:`common.data.ens.Sample` resource

    :rtype: A file like object
    """
    rhdict = options.get('rhandler', None)
    if rhdict:
        date = rhdict['resource']['date']
        seed(int(date[:-2]))
        nbsample = rhdict['resource'].get('nbsample', 0)
        if not nbsample:
            raise ValueError('The resource must hold a non-null nbsample attribute')
        population = rhdict['resource'].get('population', [])
        if not population:
            raise ValueError('The resource must hold a non-empty population attribute')
        nbset = len(population)

        tirage = (sample(population * (nbsample / nbset), (nbsample / nbset) * nbset) +
                  sample(population, nbsample % nbset))
        logger.info('List of random elements: ' + ', '.join(map(str, tirage)))
    else:
        raise ValueError("no resource handler here :-(\n")
    # NB: The result have to be a file like object !
    outdict = dict(vapp = rhdict['provider'].get('vapp', None),
                   vconf = rhdict['provider'].get('vconf', None),
                   cutoff = rhdict['resource'].get('cutoff', None),
                   date = rhdict['resource'].get('date', None),
                   resource_kind = rhdict['resource'].get('kind', None),
                   drawing = tirage,
                   population = population)
    return StringIO(json.dumps(outdict, indent=4))


def _checkingfunction_dict(options):
    rhdict = options.get('rhandler', None)
    if rhdict:
        # If no nbsample id provided, this is fine...
        nbsample = rhdict['resource'].get('nbsample', 0)
        checkrole = rhdict['resource'].get('checkrole', None)
        if not checkrole:
            raise ValueError('The resource must hold a non-empty checkrole attribute')
        t = sessions.current()
        ctx = t.context
        checklist = [sec.rh for sec in ctx.sequence.filtered_inputs(role=checkrole)]
        return helpers.colorfull_input_checker(nbsample, checklist)
    else:
        raise ValueError("no resource handler here :-(\n")


def checkingfunction(options):
    """Check what are the available resources and returns the list."""
    rhdict = options.get('rhandler', None)
    avail_list = _checkingfunction_dict(options)
    outdict = dict(vapp = rhdict['provider'].get('vapp', None),
                   vconf = rhdict['provider'].get('vconf', None),
                   cutoff = rhdict['resource'].get('cutoff', None),
                   date = rhdict['resource'].get('date', None),
                   resource_kind = rhdict['resource'].get('kind', None),
                   population = avail_list)
    return StringIO(json.dumps(outdict, indent=4))


def safedrawingfunction(options):
    """Combined called to checkingfunction and drawingfunction."""
    checkedlist = _checkingfunction_dict(options)
    options['rhandler']['resource']['population'] = checkedlist
    return drawingfunction(options)
