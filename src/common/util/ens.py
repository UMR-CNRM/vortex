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
    """Draw a random sample of values among a set

    :param options: The only argument is a dictionary that contains all the options passed to the store plus anything from the query part of the URI.

    :return: Content of the desired local file

    :rtype: A file like object
    """
    # Try to find out the name of the local file: more generally, one can
    # access every attributes from the resource handler.
    rhdict = options.get('rhandler', None)
    if rhdict:
        date = rhdict['resource']['date']
        seed(int(date))
        nbpert = rhdict['resource']['nblot']
        nbset = rhdict['resource']['nbset']
        print options.get('start', 1)
        start = int(options.get('start', [1])[0])
        population = footprints.util.rangex(start, nbset + start -1)
        tirage = sample(population * (nbpert / nbset), (nbpert / nbset) * nbset) + sample(population, nbpert % nbset)
        logger.info('List of random elements: ' + ', '.join(map(str, tirage)))
    else:
        raise ValueError("no resource handler here :-(\n")
    # NB: The result have to be a file like object !
    return StringIO(json.dumps({'drawing': tirage}))
