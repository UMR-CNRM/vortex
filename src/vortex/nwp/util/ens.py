"""
A collection of utility functions used in the context of Ensemble forecasts.
"""

import io
import json
import re
import time

from bronx.compat import random
from bronx.fancies import loggers
from bronx.stdtypes.date import Period

from vortex import sessions
from vortex.data.stores import FunctionStoreCallbackError
from vortex.util import helpers

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


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

    :return: Content of a :obj:`nwp.data.ens.Sample` resource

    :rtype: A file like object
    """
    rhdict = options.get("rhandler", None)
    if rhdict:
        date = rhdict["resource"]["date"]
        rgen = random.Random()
        rgen.seed(int(date[:-2]))
        nbsample = rhdict["resource"].get("nbsample", 0)
        if not nbsample:
            raise FunctionStoreCallbackError(
                "The resource must hold a non-null nbsample attribute"
            )
        population = rhdict["resource"].get("population", [])
        if not population:
            raise FunctionStoreCallbackError(
                "The resource must hold a non-empty population attribute"
            )
        nbset = len(population)

        tirage = rgen.sample(
            population * (nbsample // nbset), (nbsample // nbset) * nbset
        ) + rgen.sample(population, nbsample % nbset)
        logger.info(
            "List of random elements: %s", ", ".join([str(x) for x in tirage])
        )
    else:
        raise FunctionStoreCallbackError("no resource handler here :-(")
    # NB: The result have to be a file like object !
    outdict = dict(
        vapp=rhdict["provider"].get("vapp", None),
        vconf=rhdict["provider"].get("vconf", None),
        cutoff=rhdict["resource"].get("cutoff", None),
        date=rhdict["resource"].get("date", None),
        resource_kind=rhdict["resource"].get("kind", None),
        drawing=tirage,
        population=population,
    )
    if rhdict["provider"].get("experiment", None) is not None:
        outdict["experiment"] = rhdict["provider"]["experiment"]
    return io.BytesIO(json.dumps(outdict, indent=4).encode(encoding="utf_8"))


def _checkingfunction_dict(options):
    """
    Internal function that returns a dictionnary that describes the available
    inputs.
    """
    rhdict = options.get("rhandler", None)
    if rhdict:
        # If no nbsample is provided, easy to achieve...
        nbsample = rhdict["resource"].get("nbsample", None)
        # ...and if no explicit minimum of resources, nbsample is the minimum
        nbmin = int(
            options.get(
                "min",
                [
                    (0 if nbsample is None else nbsample),
                ],
            ).pop()
        )
        if nbsample is not None and nbsample < nbmin:
            logger.warning(
                "%d resources needed, %d required: sin of gluttony ?",
                nbsample,
                nbmin,
            )
        # What to look for ?
        checkrole = rhdict["resource"].get("checkrole", None)
        if not checkrole:
            raise FunctionStoreCallbackError(
                "The resource must hold a non-empty checkrole attribute"
            )
        rolematch = re.match(r"(\w+)(?:\+(\w+))?$", checkrole)
        cur_t = sessions.current()
        if rolematch:
            ctx = cur_t.context
            checklist = [
                sec.rh
                for sec in ctx.sequence.filtered_inputs(
                    role=rolematch.group(1)
                )
            ]
            mandatorylist = (
                [
                    sec.rh
                    for sec in ctx.sequence.filtered_inputs(
                        role=rolematch.group(2)
                    )
                ]
                if rolematch.group(2)
                else []
            )
        else:
            raise FunctionStoreCallbackError(
                "checkrole is not properly formatted"
            )
        # Other options
        nretries = int(
            options.get(
                "nretries",
                [
                    0,
                ],
            ).pop()
        )
        retry_wait = Period(
            options.get(
                "retry_wait",
                [
                    "PT5M",
                ],
            ).pop()
        )
        comp_delay = Period(
            options.get(
                "comp_delay",
                [
                    0,
                ],
            ).pop()
        )
        fakecheck = options.get(
            "fakecheck",
            [
                False,
            ],
        ).pop()

        def _retry_cond(the_ntries, the_acceptable_time):
            return (
                the_acceptable_time is None and the_ntries <= nretries
            ) or (
                the_acceptable_time
                and (time.time() - the_acceptable_time)
                < comp_delay.total_seconds()
            )

        # Ok let's work...
        ntries = 0
        acceptable_time = None
        found = []
        while _retry_cond(ntries, acceptable_time):
            if ntries:
                logger.info(
                    "Let's sleep %d sec. before the next check round...",
                    retry_wait.total_seconds(),
                )
                cur_t.sh.sleep(retry_wait.total_seconds())
            ntries += 1
            try:
                logger.info("Starting an input check...")
                found, candidates = helpers.colorfull_input_checker(
                    nbmin,
                    checklist,
                    mandatory=mandatorylist,
                    fakecheck=fakecheck,
                )
                if acceptable_time is None and (found or nbmin == 0):
                    acceptable_time = time.time()
                    if comp_delay.total_seconds() and len(found) != len(
                        candidates
                    ):
                        logger.info(
                            "The minimum required size was reached (nbmin=%d). "
                            + "That's great but we are waiting a little longer "
                            + "(for at most %d sec.)",
                            nbmin,
                            comp_delay.total_seconds(),
                        )

                if len(found) == len(candidates):
                    # No need to wait any longer...
                    break
            except helpers.InputCheckerError as e:
                if not _retry_cond(ntries, acceptable_time):
                    raise FunctionStoreCallbackError(
                        "The input checher failed ({!s})".format(e)
                    )
        return found
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

    :return: Content of a :obj:`nwp.data.ens.PopulationList` resource

    :rtype: A file like object
    """
    rhdict = options.get("rhandler", None)
    avail_list = _checkingfunction_dict(options)
    outdict = dict(
        vapp=rhdict["provider"].get("vapp", None),
        vconf=rhdict["provider"].get("vconf", None),
        cutoff=rhdict["resource"].get("cutoff", None),
        date=rhdict["resource"].get("date", None),
        resource_kind=rhdict["resource"].get("kind", None),
        population=avail_list,
    )
    if rhdict["provider"].get("experiment", None) is not None:
        outdict["experiment"] = rhdict["provider"]["experiment"]
    return io.BytesIO(json.dumps(outdict, indent=4).encode(encoding="utf_8"))


def safedrawingfunction(options):
    """Combined called to :func:`checkingfunction` and :func:`drawingfunction`.

    See the documentation of these two functions for more details.
    """
    checkedlist = _checkingfunction_dict(options)
    options["rhandler"]["resource"]["population"] = checkedlist
    return drawingfunction(options)


def unsafedrawingfunction(options):
    """Combined called to :func:`checkingfunction` and :func:`drawingfunction`...
    but with a big lie on the checking: no real check, all the resources are assumed ok.

    See the documentation of these two functions for more details.
    """
    options["fakecheck"] = [
        True,
    ]
    checkedlist = _checkingfunction_dict(options)
    options["rhandler"]["resource"]["population"] = checkedlist
    return drawingfunction(options)
