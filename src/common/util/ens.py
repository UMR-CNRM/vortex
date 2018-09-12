#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A collection of utility functions used in the context of Ensemble forecasts.
"""

from __future__ import print_function, absolute_import, division, unicode_literals

import json
from random import seed, sample
import re
import six

import footprints
from vortex import sessions
from vortex.data.stores import FunctionStoreCallbackError
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
            raise FunctionStoreCallbackError('The resource must hold a non-null nbsample attribute')
        population = rhdict['resource'].get('population', [])
        if not population:
            raise FunctionStoreCallbackError('The resource must hold a non-empty population attribute')
        nbset = len(population)

        tirage = (sample(population * (nbsample // nbset), (nbsample // nbset) * nbset) +
                  sample(population, nbsample % nbset))
        logger.info('List of random elements: %s', ', '.join([six.text_type(x) for x in tirage]))
    else:
        raise FunctionStoreCallbackError("no resource handler here :-(")
    # NB: The result have to be a file like object !
    outdict = dict(vapp = rhdict['provider'].get('vapp', None),
                   vconf = rhdict['provider'].get('vconf', None),
                   cutoff = rhdict['resource'].get('cutoff', None),
                   date = rhdict['resource'].get('date', None),
                   resource_kind = rhdict['resource'].get('kind', None),
                   drawing = tirage,
                   population = population)
    if rhdict['provider'].get('experiment', None) is not None:
        outdict['experiment'] = rhdict['provider']['experiment']
    return six.StringIO(json.dumps(outdict, indent=4))


def _checkingfunction_dict(options):
    """
    Internal function that returns a dictionnary that describes the available
    inputs.
    """
    rhdict = options.get('rhandler', None)
    if rhdict:
        # If no nbsample is provided, easy to achieve...
        nbsample = rhdict['resource'].get('nbsample', None)
        # ...and if no explicit minimum of resources, nbsample is the minimum
        nbmin = int(options.get('min', [(0 if nbsample is None else nbsample), ]).pop())
        if nbsample is not None and nbsample < nbmin:
            logger.warning('%d resources needed, %d required: sin of gluttony ?', nbsample, nbmin)
        checkrole = rhdict['resource'].get('checkrole', None)
        if not checkrole:
            raise FunctionStoreCallbackError('The resource must hold a non-empty checkrole attribute')
        rolematch = re.match('(\w+)(?:\+(\w+))?$', checkrole)
        if rolematch:
            ctx = sessions.current().context
            checklist = [sec.rh for sec in ctx.sequence.filtered_inputs(role=rolematch.group(1))]
            mandatorylist = ([sec.rh for sec in ctx.sequence.filtered_inputs(role=rolematch.group(2))]
                             if rolematch.group(2) else [])
        else:
            raise FunctionStoreCallbackError('checkrole is not properly formatted')
        try:
            return helpers.colorfull_input_checker(nbmin, checklist, mandatory=mandatorylist,
                                                   fakecheck = options.get('fakecheck', False))
        except helpers.InputCheckerError as e:
            raise FunctionStoreCallbackError('The input checher failed ({!s})'.format(e))
    else:
        raise FunctionStoreCallbackError("no resource handler here :-(\n")


def checkingfunction(options):
    """Check what are the available resources and returns the list.

    This function is designed to be executed by a
    :obj:`vortex.data.stores.FunctionStore` object.

    The *checkrole* resource attribute is used to look into the current context
    in order to establish the list of resources that will checked.

    :param dict options: All the options passed to the store plus anything from
        the query part of the URI.

    :return: Content of a :obj:`common.data.ens.PopulationList` resource

    :rtype: A file like object
    """
    rhdict = options.get('rhandler', None)
    avail_list = _checkingfunction_dict(options)
    outdict = dict(vapp = rhdict['provider'].get('vapp', None),
                   vconf = rhdict['provider'].get('vconf', None),
                   cutoff = rhdict['resource'].get('cutoff', None),
                   date = rhdict['resource'].get('date', None),
                   resource_kind = rhdict['resource'].get('kind', None),
                   population = avail_list)
    if rhdict['provider'].get('experiment', None) is not None:
        outdict['experiment'] = rhdict['provider']['experiment']
    return six.StringIO(json.dumps(outdict, indent=4))


def safedrawingfunction(options):
    """Combined called to :func:`checkingfunction` and :func:`drawingfunction`.

    See the documentation of these two functions for more details.
    """
    checkedlist = _checkingfunction_dict(options)
    options['rhandler']['resource']['population'] = checkedlist
    return drawingfunction(options)


def unsafedrawingfunction(options):
    """Combined called to :func:`checkingfunction` and :func:`drawingfunction`...
    but with a big lie on the checking: no real check, all the resources are assumed ok.

    See the documentation of these two functions for more details.
    """
    options['fakecheck'] = True
    checkedlist = _checkingfunction_dict(options)
    options['rhandler']['resource']['population'] = checkedlist
    return drawingfunction(options)
