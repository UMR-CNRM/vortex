#!/usr/bin/env python
# -*- coding: utf-8 -*-

from StringIO import StringIO

#: No automatic export
__all__ = []

import footprints
logger = footprints.loggers.getLogger(__name__)

import json
from random import seed, sample


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
        nbpert = rhdict['resource']['nblot']
        nbset = rhdict['resource']['nbset']
        start = int(options.get('start', [1])[0])
        population = footprints.util.rangex(start, nbset + start - 1)
        tirage = (sample(population * (nbpert / nbset), (nbpert / nbset) * nbset) +
                  sample(population, nbpert % nbset))
        logger.info('List of random elements: ' + ', '.join(map(str, tirage)))
    else:
        raise ValueError("no resource handler here :-(\n")
    # NB: The result have to be a file like object !
    return StringIO(json.dumps({'drawing': tirage}))
