"""
Top level interface for accessing the VORTEX facilities.

This module does not provides any class, constant, or any nice object.
It defines a very basic interface to some (possibly) powerful capacities
of the :mod:`vortex` toolbox.
"""

from contextlib import contextmanager
import re
import traceback

from bronx.fancies import loggers
from bronx.stdtypes.history import History
from bronx.syntax import mktuple

import footprints

from vortex import sessions, data, proxy
from vortex.layout.dataflow import stripargs_section, intent, ixo, Section

#: Automatic export of superstar interface.
__all__ = ["rload", "rget", "rput"]

logger = loggers.getLogger(__name__)

#: Shortcut to footprint env defaults
defaults = footprints.setup.defaults

sectionmap = {"input": "get", "output": "put", "executable": "get"}


class VortexForceComplete(Exception):
    """Exception for handling fast exit mecanisms."""

    pass


# Toolbox defaults

#: Default value for the **now** attribute of :func:`input`, :func:`executable`
#: and :func:`output` functions
active_now = False
#: Default value for the **insitu** attribute of the :func:`input` and
#: :func:`executable` functions
active_insitu = False
#: If *False*, drastically reduces the amount of messages printed by the
#: toolbox module
active_verbose = True
#: If *False*, do not try to create/make any promise
active_promise = True
#: If *False*, this makes the :func:`clear_promises` function inactive
active_clear = False
#: If *False*, this will reset to *False* any ``metadatacheck`` attribute
#: passed to the :func:`input` or :func:`executable` functions
active_metadatacheck = True
#: If *True*, archive stores will not be used at all (only cache stores will
#: be used)
active_incache = False
#: Use the earlyget feature during :func:`input` calls
active_batchinputs = True

#: History recording
history = History(tag="rload")


# Most commonly used functions


def show_toolbox_settings(ljust=24):
    """Print the current settings of the toolbox."""
    for key in [
        "active_{}".format(act)
        for act in (
            "now",
            "insitu",
            "verbose",
            "promise",
            "clear",
            "metadatacheck",
            "incache",
        )
    ]:
        kval = globals().get(key, None)
        if kval is not None:
            print("+", key.ljust(ljust), "=", kval)


def quickview(args, nb=0, indent=0):
    """Recursive call to any quick view of objects specified as arguments."""
    if not isinstance(args, list) and not isinstance(args, tuple):
        args = (args,)
    for x in args:
        if nb:
            print()
        nb += 1
        quickview = getattr(x, "quickview", None)
        if quickview:
            quickview(nb, indent)
        else:
            print("{:02d}. {:s}".format(nb, x))


class VortexToolboxDescError(Exception):
    pass


def rload(*args, **kw):
    """
    Resource Loader.

    This function behaves as a factory for any possible pre-defined family
    of VORTEX resources (described by an aggregation of Resource, Provider and
    Container objects).

    Arguments could be a mix of a list of dictionary-type objects and key/value
    parameters. Other type of arguments will be discarded.

    An abstract resource descriptor is built as the aggregation of these
    arguments and then expanded according to rules defined by the
    :func:`footprints.util.expand` function.

    For each expanded descriptor, the ``rload`` method will try to pickup the
    best candidates (if any) that could match the description (*i.e.* Resource,
    Provider, Container). If no match is found for one of the Resource, Provider
    or Container objects, a :class:`VortexToolboxDescError` exception is raised.
    Otherwise,the resource's :class:`~vortex.data.handlers.Handler` built from
    those three objects is added to the result's list.

    :return: A list of :class:`vortex.data.handlers.Handler` objects.
    """
    rd = dict()
    for a in args:
        if isinstance(a, dict):
            rd.update(a)
        else:
            logger.warning("Discard rload argument <%s>", a)
    rd.update(kw)
    if rd:
        history.append(rd.copy())
    rhx = []
    for x in footprints.util.expand(rd):
        picked_up = proxy.containers.pickup(  # @UndefinedVariable
            *proxy.providers.pickup_and_cache(  # @UndefinedVariable
                *proxy.resources.pickup_and_cache(x)  # @UndefinedVariable
            )
        )
        logger.debug("Resource desc %s", picked_up)
        picked_rh = data.handlers.Handler(picked_up)
        if not picked_rh.complete:
            raise VortexToolboxDescError("The ResourceHandler is incomplete")
        rhx.append(picked_rh)

    return rhx


def rh(*args, **kw):
    """
    This function selects the first resource's handler as returned by the
    :func:`rload` function.
    """
    return rload(*args, **kw)[0]


def rget(*args, **kw):
    """
    This function calls the :meth:`get` method on any resource handler returned
    by the :func:`rload` function.
    """
    loc_incache = kw.pop("incache", active_incache)
    rl = rload(*args, **kw)
    for rh in rl:
        rh.get(incache=loc_incache)
    return rl


def rput(*args, **kw):
    """
    This function calls the :meth:`put` method on any resource handler returned
    by the :func:`rload` function.
    """
    loc_incache = kw.pop("incache", active_incache)
    rl = rload(*args, **kw)
    for rh in rl:
        rh.put(incache=loc_incache)
    return rl


def nicedump(msg, **kw):
    """Simple dump the **kw** dict content with ``msg`` as header."""
    print("#", msg, ":")
    for k, v in sorted(kw.items()):
        print("+", k.ljust(12), "=", str(v))
    print()


@contextmanager
def _tb_isolate(t, loglevel):
    """Handle the context and logger (internal use only)."""
    # Switch off autorecording of the current context
    ctx = t.context
    recordswitch = ctx.record
    if recordswitch:
        ctx.record_off()
    try:
        if loglevel is not None:
            # Possibly change the log level if necessary
            with loggers.contextboundGlobalLevel(loglevel):
                yield
        else:
            yield
    finally:
        if recordswitch:
            ctx.record_on()


def add_section(section, args, kw):
    """
    Add a :class:`~vortex.layout.dataflow.Section` object (of kind **section**)
    to the current sequence.

    1. The **kw** dictionary may contain keys that influence this function
       behaviour (such attributes are popped from **kw** before going further):

        * **now**: If *True*, call the appropriate action (``get()`` or ``put()``)
          on each added :class:`~vortex.layout.dataflow.Section`. (The default
          is given by :data:`active_now`).
        * **loglevel**: The logging facility verbosity level that will be used
          during the :class:`~vortex.layout.dataflow.Section` creation process.
          If *None*, nothing is done (i.e. the current verbosity level is
          preserved). (default: *None*).
        * **verbose**: If *True*, print some informations on the standard output
          (The default is given by :data:`active_verbose`).
        * **complete**: If *True*, force the task to complete (the
          :class:`VortexForceComplete` exception is raised) whenever an error
          occurs. (default: False).
        * **insitu**: It *True*, before actually getting data, we first check
          if the data is already there (in the context of a multi-step job,
          it might have been fetched during a previous step). (default: *False*).
        * **incache**: It *True*, archive stores will not be used at all (only cache
          stores will be used). (The default is given by :data:`active_incache`).

    2. **kw** is then looked for items relevant to the
       :class:`~vortex.layout.dataflow.Section` constructor (``role``, ``intent``,
       ...). (such items are popped from kw before going further).

    3. The remaining **kw** items are passed directly to the :func:`rload`
       function in order to create the resource's
       :class:`~vortex.data.handlers.Handler`.

    :return: A list of :class:`vortex.data.handlers.Handler` objects.
    """

    t = sessions.current()

    # First, retrieve arguments of the toolbox command itself
    now = kw.pop("now", active_now)
    loglevel = kw.pop("loglevel", None)
    talkative = kw.pop("verbose", active_verbose)
    complete = kw.pop("complete", False)
    insitu = kw.get("insitu", False)
    batch = kw.pop("batch", False)
    lastfatal = kw.pop("lastfatal", None)

    if complete:
        kw["fatal"] = False

    if batch:
        if section not in ("input", "excutable"):
            logger.info(
                "batch=True is not implemented for section=%s. overwriting to batch=Fase.",
                section,
            )
            batch = False

    # Second, retrieve arguments that could be used by the now command
    cmdopts = dict(
        incache=kw.pop("incache", active_incache), force=kw.pop("force", False)
    )

    # Third, collect arguments for triggering some hook
    hooks = dict()
    for ahook in [x for x in kw.keys() if x.startswith("hook_")]:
        cbhook = mktuple(kw.pop(ahook))
        cbfunc = cbhook[0]
        if not callable(cbfunc):
            cbfunc = t.sh.import_function(cbfunc)
        hooks[ahook] = footprints.FPTuple((cbfunc, cbhook[1:]))

    # Print the user inputs
    def print_user_inputs():
        nicedump("New {:s} section with options".format(section), **opts)
        nicedump("Resource handler description", **kwclean)
        nicedump(
            "This command options",
            complete=complete,
            loglevel=loglevel,
            now=now,
            verbose=talkative,
        )
        if hooks:
            nicedump("Hooks triggered", **hooks)

    with _tb_isolate(t, loglevel):
        # Distinguish between section arguments, and resource loader arguments
        opts, kwclean = stripargs_section(**kw)

        # Strip the metadatacheck option depending on active_metadatacheck
        if not active_metadatacheck and not insitu:
            if kwclean.get("metadatacheck", False):
                logger.info(
                    "The metadatacheck option is forced to False since "
                    + "active_metadatacheck=False."
                )
                kwclean["metadatacheck"] = False

        # Show the actual set of arguments
        if talkative and not insitu:
            print_user_inputs()

        # Let the magic of footprints resolution operate...
        kwclean.update(hooks)
        rl = rload(*args, **kwclean)
        rlok = list()

        # Prepare the references to the actual section method to perform
        push = getattr(t.context.sequence, section)
        doitmethod = sectionmap[section]

        # Create a section for each resource handler
        if rl and lastfatal is not None:
            newsections = [
                push(rh=rhandler, **opts)[0] for rhandler in rl[:-1]
            ]
            tmpopts = opts.copy()
            tmpopts["fatal"] = lastfatal
            newsections.append(push(rh=rl[-1], **tmpopts)[0])
        else:
            newsections = [push(rh=rhandler, **opts)[0] for rhandler in rl]

        # If insitu and now, try a quiet get...
        do_quick_insitu = section in ("input", "executable") and insitu and now
        if do_quick_insitu:
            quickget = [
                sec.rh.insitu_quickget(alternate=sec.alternate, **cmdopts)
                for sec in newsections
            ]
            if all(quickget):
                if len(quickget) > 1:
                    logger.info(
                        "The insitu get succeeded for all of the %d resource handlers.",
                        len(rl),
                    )
                else:
                    logger.info(
                        "The insitu get succeeded for this resource handler."
                    )
                rlok = [sec.rh for sec in newsections]
            else:
                # Start again with the usual get sequence
                print_user_inputs()

        # If not insitu, not now, or if the quiet get failed
        if not (do_quick_insitu and all(quickget)):
            if now:
                with t.sh.ftppool():
                    # Create a section for each resource handler, and perform action on demand
                    batchflags = [
                        None,
                    ] * len(newsections)
                    if batch:
                        if talkative:
                            t.sh.subtitle(
                                "Early-{:s} for all resources.".format(
                                    doitmethod
                                )
                            )
                        for ir, newsection in enumerate(newsections):
                            rhandler = newsection.rh
                            batchflags[ir] = getattr(
                                newsection, "early" + doitmethod
                            )(**cmdopts)
                        if talkative:
                            if any(batchflags):
                                for ir, newsection in enumerate(newsections):
                                    if talkative and batchflags[ir]:
                                        logger.info(
                                            "Resource no %02d/%02d: Early-%s registered with id: %s.",
                                            ir + 1,
                                            len(rl),
                                            doitmethod,
                                            str(batchflags[ir]),
                                        )
                                    else:
                                        logger.debug(
                                            "Resource no %02d/%02d: Early-%s registered with id: %s.",
                                            ir + 1,
                                            len(rl),
                                            doitmethod,
                                            str(batchflags[ir]),
                                        )
                            else:
                                logger.info(
                                    "Early-%s was unavailable for all of the resources.",
                                    doitmethod,
                                )
                        # trigger finalise for all of the DelayedActions
                        tofinalise = [
                            r_id
                            for r_id in batchflags
                            if r_id and r_id is not True
                        ]
                        if tofinalise:
                            if talkative:
                                t.sh.subtitle(
                                    "Finalising all of the delayed actions..."
                                )
                            t.context.delayedactions_hub.finalise(*tofinalise)
                    secok = list()
                    for ir, newsection in enumerate(newsections):
                        rhandler = newsection.rh
                        # If quick get was ok for this resource don't call get again...
                        if talkative:
                            t.sh.subtitle(
                                "Resource no {:02d}/{:02d}".format(
                                    ir + 1, len(rl)
                                )
                            )
                            rhandler.quickview(nb=ir + 1, indent=0)
                            if batchflags[ir] is not True or (
                                do_quick_insitu and quickget[ir]
                            ):
                                t.sh.highlight(
                                    "Action {:s} on {:s}".format(
                                        doitmethod.upper(),
                                        rhandler.location(fatal=False),
                                    )
                                )
                        ok = do_quick_insitu and quickget[ir]
                        if batchflags[ir]:
                            actual_doitmethod = "finalise" + doitmethod
                            ok = ok or getattr(newsection, actual_doitmethod)()
                        else:
                            actual_doitmethod = doitmethod
                            ok = ok or getattr(newsection, actual_doitmethod)(
                                **cmdopts
                            )
                        if talkative:
                            t.sh.highlight(
                                "Result from {:s}: [{!s}]".format(
                                    actual_doitmethod, ok
                                )
                            )
                        if talkative and not ok:
                            logger.error(
                                "Could not %s resource %s",
                                doitmethod,
                                rhandler.container.localpath(),
                            )
                        if not ok:
                            if complete:
                                logger.warning(
                                    "Force complete for %s",
                                    rhandler.location(fatal=False),
                                )
                                raise VortexForceComplete(
                                    "Force task complete on resource error"
                                )
                        else:
                            secok.append(newsection)
                        if t.sh.trace:
                            print()
                    rlok.extend(
                        [
                            newsection.rh
                            for newsection in secok
                            if newsection.any_coherentgroup_opened
                        ]
                    )
            else:
                rlok.extend([newsection.rh for newsection in newsections])

    return rlok


# noinspection PyShadowingBuiltins
def input(*args, **kw):  # @ReservedAssignment
    """Add input :class:`~vortex.layout.dataflow.Section` objects to the current sequence.

    Relies on the :func:`add_section` function (see its documentation), with:

        * It's ``section`` attribute is automatically set to 'input';
        * The ``kw``'s *insitu* item is set to :data:`active_insitu` by default.

    :return: A list of :class:`vortex.data.handlers.Handler` objects (associated
        with the newly created class:`~vortex.layout.dataflow.Section` objects).
    """
    kw.setdefault("insitu", active_insitu)
    kw.setdefault("batch", active_batchinputs)
    return add_section("input", args, kw)


def inputs(ticket=None, context=None):
    """Return effective inputs for the specified context.

    It actually returns both *inputs* and *executables*.

    :param ~vortex.sessions.Ticket ticket: A session's Ticket. If set to *None*,
        the current active session will be used (default: *None*)
    :param ~vortex.layout.contexts.Context context: A context object. If set to *None*,
        the current active context will be used (default: *None*)
    :return: A list of :class:`~vortex.layout.dataflow.Section` objects.
    """
    if context is None:
        if ticket is None:
            ticket = sessions.current()
        context = ticket.context
    return context.sequence.effective_inputs()


def show_inputs(context=None):
    """Dump a summary of inputs (+ executables) sections.

    :param ~vortex.layout.contexts.Context context: A context object. If set to *None*,
        the current active context will be used (default: *None*)
    """
    t = sessions.current()
    for csi in inputs(ticket=t):
        t.sh.header("Input " + str(csi))
        csi.show(ticket=t, context=context)
        print()


def output(*args, **kw):
    """Add output :class:`~vortex.layout.dataflow.Section` objects to the current sequence.

    Relies on the :func:`add_section` function (see its documentation), with:

        * It's ``section`` attribute is automatically set to 'output';

    :return: A list of :class:`vortex.data.handlers.Handler` objects (associated
        with the newly created class:`~vortex.layout.dataflow.Section` objects).
    """
    # Strip the metadatacheck option depending on active_metadatacheck
    if not active_promise:
        for target in ("promised", "expected"):
            if target in kw and kw[target]:
                logger.info(
                    "The %s argument is removed since active_promise=False.",
                    target,
                )
                del kw[target]
    return add_section("output", args, kw)


def outputs(ticket=None, context=None):
    """Return effective outputs in specified context.

    :param ~vortex.sessions.Ticket ticket: A session's Ticket. If set to *None*,
        the current active session will be used (default: *None*)
    :param ~vortex.layout.contexts.Context context: A context object. If set to *None*,
        the current active context will be used (default: *None*)
    :return: A list of :class:`~vortex.layout.dataflow.Section` objects.
    """
    if context is None:
        if ticket is None:
            ticket = sessions.current()
        context = ticket.context
    return context.sequence.effective_outputs()


def show_outputs(context=None):
    """Dump a summary of outputs sections.

    :param ~vortex.layout.contexts.Context context: A context object. If set to *None*,
        the current active context will be used (default: *None*)
    """
    t = sessions.current()
    for cso in outputs(ticket=t):
        t.sh.header("Output " + str(cso))
        cso.show(ticket=t, context=context)
        print()


def promise(*args, **kw):
    """Log promises before execution.

    Relies on the :func:`add_section` function (see its documentation), with:

        * It's ``section`` attribute is automatically set to 'output';
        * The ``kw``'s *promised* item is set to *True*;
        * The ``kw``'s *force* item is set to *True*;
        * The ``kw``'s *now* item is set to :data:`active_promise`.

    :return: A list of :class:`vortex.data.handlers.Handler` objects (associated
        with the newly created class:`~vortex.layout.dataflow.Section` objects).
    """
    kw.update(
        promised=True,
        force=True,
        now=active_promise,
    )
    if not active_promise:
        kw.setdefault("verbose", False)
        logger.warning("Promise flag is <%s> in that context", active_promise)
    return add_section("output", args, kw)


def executable(*args, **kw):
    """Add executable :class:`~vortex.layout.dataflow.Section` objects to the current sequence.

    Relies on the :func:`add_section` function (see its documentation), with:

        * It's ``section`` attribute is automatically set to 'executable';
        * The ``kw``'s *insitu* item is set to :data:`active_insitu` by default.

    :return: A list of :class:`vortex.data.handlers.Handler` objects (associated
        with the newly created class:`~vortex.layout.dataflow.Section` objects).
    """
    kw.setdefault("insitu", active_insitu)
    return add_section("executable", args, kw)


def algo(*args, **kw):
    """Load an algo component and display its description (if **verbose**).

    1. The **kw** dictionary may contain keys that influence this function
       behaviour (such attributes are popped from **kw** before going further):

        * **loglevel**: The logging facility verbosity level that will be used
          during the :class:`~vortex.layout.dataflow.Section` creation process.
          If *None*, nothing is done (i.e. the current verbosity level is
          preserved). (default: *None*).
        * **verbose**: If *True*, print some informations on the standard output
          (The default is given by :data:`active_verbose`).

    2. The remaining **kw** items are passed directly to the "algo" footprint's
        proxy in order to create the AlgoComponent object.

    :return: an object that is a subtype of :class:`vortex.algo.components.AlgoComponent`
    """

    t = sessions.current()

    # First, retrieve arguments of the toolbox command itself
    loglevel = kw.pop("loglevel", None)
    talkative = kw.pop("verbose", active_verbose)

    with _tb_isolate(t, loglevel):
        if talkative:
            nicedump("Loading algo component with description:", **kw)

        ok = proxy.component(**kw)  # @UndefinedVariable
        if ok and talkative:
            print(t.line)
            ok.quickview(nb=1, indent=0)

    return ok


def diff(*args, **kw):
    """Perform a diff with a resource with the same local name.

    1. The **kw** dictionary may contain keys that influence this function
       behaviour (such attributes are popped from **kw** before going further):

        * **fatal**: If *True*, a :class:`ValueError` exception will be raised
          whenever the "diff" detects differences.
        * **loglevel**: The logging facility verbosity level that will be used
          during the :class:`~vortex.layout.dataflow.Section` creation process.
          If *None*, nothing is done (i.e. the current verbosity level is
          preserved). (default: *None*).
        * **verbose**: If *True*, print some informations on the standard output
          (The default is given by :data:`active_verbose`).

    2. The remaining **kw** items are passed directly to the :func:`rload`
       function in order to create the resource's
       :class:`~vortex.data.handlers.Handler` objects for the reference files.

    3. The reference files resource's :class:`~vortex.data.handlers.Handler` objects
       are altered so that the reference files are stored in temporary Containers.

    4. The reference files are fetched.

    5. The diff between the containers described in the resource's description
       and the reference files is computed.

    :return: A list of *diff* results.
    """

    # First, retrieve arguments of the toolbox command itself
    fatal = kw.pop("fatal", True)
    loglevel = kw.pop("loglevel", None)
    talkative = kw.pop("verbose", active_verbose)
    batch = kw.pop("batch", active_batchinputs)

    # Distinguish between section arguments, and resource loader arguments
    opts, kwclean = stripargs_section(**kw)

    # Show the actual set of arguments
    if talkative:
        nicedump("Discard section options", **opts)
        nicedump("Resource handler description", **kwclean)

    # Fast exit in case of undefined value
    rlok = list()
    none_skip = {
        k
        for k, v in kwclean.items()
        if v is None and k in ("experiment", "namespace")
    }
    if none_skip:
        logger.warning("Skip diff because of undefined argument(s)")
        return rlok

    t = sessions.current()

    # Swich off autorecording of the current context + deal with loggging
    with _tb_isolate(t, loglevel):
        # Do not track the reference files
        kwclean["storetrack"] = False

        rhandlers = rload(*args, **kwclean)
        sections = list()
        earlyget_id = list()
        source_container = list()
        lazzy_container = list()

        if batch:
            # Early get
            print(t.line)
            for ir, rhandler in enumerate(rhandlers):
                source_container.append(rhandler.container)
                # Create a new container to hold the reference file
                lazzy_container.append(
                    footprints.proxy.container(
                        shouldfly=True, actualfmt=rhandler.container.actualfmt
                    )
                )
                # Swapp the original container with the lazzy one
                rhandler.container = lazzy_container[-1]
                # Create a new section
                sec = Section(
                    rh=rhandler, kind=ixo.INPUT, intent=intent.IN, fatal=False
                )
                sections.append(sec)
                # Early-get
                if rhandler.complete:
                    earlyget_id.append(sec.earlyget())
                else:
                    earlyget_id.append(None)
            # Finalising
            if any([r_id and r_id is not True for r_id in earlyget_id]):
                t.sh.highlight("Finalising Early-gets")
                t.context.delayedactions_hub.finalise(
                    *[
                        r_id
                        for r_id in earlyget_id
                        if r_id and r_id is not True
                    ]
                )

        for ir, rhandler in enumerate(rhandlers):
            if talkative:
                print(t.line)
                rhandler.quickview(nb=ir + 1, indent=0)
                print(t.line)
            if not rhandler.complete:
                logger.error(
                    "Incomplete Resource Handler for diff [%s]", rhandler
                )
                if fatal:
                    raise ValueError("Incomplete Resource Handler for diff")
                else:
                    rlok.append(False)
                    continue

            # Get the reference file through a Section so that intent + fatal
            # is properly dealt with... The section is discarded afterwards.
            if batch:
                rc = sections[ir].finaliseget()
            else:
                rc = sections[ir].get()
            if not rc:
                try:
                    logger.error(
                        "Cannot get the reference resource: %s",
                        rhandler.locate(),
                    )
                except Exception:
                    logger.error("Cannot get the reference resource: ???")
                if fatal:
                    raise ValueError("Cannot get the reference resource")
            else:
                logger.info(
                    "The reference file is stored under: %s",
                    rhandler.container.localpath(),
                )

            # What are the differences ?
            if rc:
                # priority is given to the diff implemented in the DataContent
                if rhandler.resource.clscontents.is_diffable():
                    source_contents = rhandler.resource.contents_handler(
                        datafmt=source_container[ir].actualfmt
                    )
                    source_contents.slurp(source_container[ir])
                    ref_contents = rhandler.contents
                    rc = source_contents.diff(ref_contents)
                else:
                    rc = t.sh.diff(
                        source_container[ir].localpath(),
                        rhandler.container.localpath(),
                        fmt=rhandler.container.actualfmt,
                    )

            # Delete the reference file
            lazzy_container[ir].clear()

            # Now proceed with the result
            logger.info("Diff return %s", str(rc))
            t.context.diff_history.append_record(
                rc, source_container[ir], rhandler
            )
            try:
                logger.info("Diff result %s", str(rc.result))
            except AttributeError:
                pass
            if not rc:
                try:
                    logger.warning(
                        "Some diff occurred with %s", rhandler.locate()
                    )
                except Exception:
                    logger.warning("Some diff occurred with ???")
                try:
                    rc.result.differences()
                except Exception:
                    pass
                if fatal:
                    logger.critical(
                        "Difference in resource comparison is fatal"
                    )
                    raise ValueError("Fatal diff")
            if t.sh.trace:
                print()
            rlok.append(rc)

    return rlok


def magic(localpath, **kw):
    """
    Return a minimal resource handler build with an unknown resource,
    a file container and an anonymous provider described with its URL.
    """
    kw.update(
        unknown=True,
        magic="magic://localhost/" + localpath,
        filename=localpath,
    )
    rhmagic = rh(**kw)
    rhmagic.get()
    return rhmagic


def archive_refill(*args, **kw):
    """
    Get a ressource in cache and upload it into the archive.

    This will only have effect when working on a multistore.

    The **kw** items are passed directly to the :func:`rload` function in
    order to create the resource's :class:`~vortex.data.handlers.Handler`.
    No "container" description is needed. One will be created by default.

    :return: A list of :class:`vortex.data.handlers.Handler` objects.
    """

    t = sessions.current()

    # First, retrieve arguments of the toolbox command itself
    loglevel = kw.pop("loglevel", None)
    talkative = kw.pop("verbose", active_verbose)

    with _tb_isolate(t, loglevel):
        # Distinguish between section arguments, and resource loader arguments
        opts, kwclean = stripargs_section(**kw)
        fatal = opts.get("fatal", True)

        # Print the user inputs
        if talkative:
            nicedump(
                "Archive Refill Ressource+Provider description", **kwclean
            )

        # Create the resource handlers
        kwclean["container"] = footprints.proxy.container(
            uuid4fly=True, uuid4flydir="archive_refills"
        )
        rl = rload(*args, **kwclean)

        @contextmanager
        def _fatal_wrap(action):
            """Handle errors during the calls to get or put."""
            wrap_rc = dict(rc=True)
            try:
                yield wrap_rc
            except Exception as e:
                logger.error(
                    "Something wrong (action %s): %s. %s",
                    action,
                    str(e),
                    traceback.format_exc(),
                )
                wrap_rc["rc"] = False
                wrap_rc["exc"] = e
            if fatal and not wrap_rc["rc"]:
                logger.critical("Fatal error with action %s.", action)
                raise RuntimeError(
                    "Could not {:s} resource: {!s}".format(
                        action, wrap_rc["rc"]
                    )
                )

        with t.sh.ftppool():
            for ir, rhandler in enumerate(rl):
                if talkative:
                    t.sh.subtitle(
                        "Resource no {:02d}/{:02d}".format(ir + 1, len(rl))
                    )
                    rhandler.quickview(nb=ir + 1, indent=0)
                if not (
                    rhandler.store.use_cache() and rhandler.store.use_archive()
                ):
                    logger.info(
                        "The requested store does not have both the cache and archive capabilities. "
                        + "Skipping this ressource handler."
                    )
                    continue
                with _fatal_wrap("get") as get_status:
                    get_status["rc"] = rhandler.get(
                        incache=True,
                        intent=intent.IN,
                        fmt=rhandler.resource.nativefmt,
                    )
                put_status = dict(rc=False)
                if get_status["rc"]:
                    with _fatal_wrap("put") as put_status:
                        put_status["rc"] = rhandler.put(
                            inarchive=True, fmt=rhandler.resource.nativefmt
                        )
                    rhandler.container.clear()
                if talkative:
                    t.sh.highlight(
                        "Result from get: [{!s}], from put: [{!s}]".format(
                            get_status["rc"], put_status["rc"]
                        )
                    )

    return rl


def stack_archive_refill(*args, **kw):
    """Get a stack ressource in cache and upload it into the archive.

    This will only have effect when working on a multistore.

    The **kw** items are passed directly to the :func:`rload` function in
    order to create the resource's :class:`~vortex.data.handlers.Handler`.

    * No "container" description is needed. One will be created by default.
    * The **block** attribute will be set automaticaly

    :return: A list of :class:`vortex.data.handlers.Handler` objects.
    """
    kw["block"] = "stacks"
    return archive_refill(*args, **kw)


def namespaces(**kw):
    """
    Some kind of interactive help to find out quickly which namespaces are in
    used. By default tracks ``stores`` and ``providers`` but one could give an
    ``only`` argument.
    """
    rematch = re.compile(
        "|".join(kw.get("match", ".").split(",")), re.IGNORECASE
    )
    if "only" in kw:
        usedcat = kw["only"].split(",")
    else:
        usedcat = ("provider", "store")
    nameseen = dict()
    for cat in [footprints.collectors.get(tag=x) for x in usedcat]:
        for cls in cat():
            fp = cls.footprint_retrieve().attr
            netattr = fp.get("namespace", None)
            if not netattr:
                netattr = fp.get("netloc", None)
            if netattr and "values" in netattr:
                for netname in filter(
                    lambda x: rematch.search(x), netattr["values"]
                ):
                    if netname not in nameseen:
                        nameseen[netname] = list()
                    nameseen[netname].append(cls.fullname())
    return nameseen


def print_namespaces(**kw):
    """Formatted print of current namespaces."""
    prefix = kw.pop("prefix", "+ ")
    nd = namespaces(**kw)
    justify = max([len(x) for x in nd.keys()])
    linesep = ",\n" + " " * (justify + len(prefix) + 2)
    for k, v in sorted(nd.items()):
        nice_v = linesep.join(v) if len(v) > 1 else v[0]
        print(prefix + k.ljust(justify), "[" + nice_v + "]")


def clear_promises(
    clear=None, netloc="promise.cache.fr", scheme="vortex", storeoptions=None
):
    """Remove all promises that have been made in the current session.

    :param netloc: Netloc of the promise's cache store to clean up
    :param scheme: Scheme of the promise's cache store to clean up
    :param storeoptions: Option dictionary passed to the store (may be None)
    """
    if clear is None:
        clear = active_clear
    if clear:
        t = sessions.current()
        myctx = t.context
        for ctx in t.subcontexts:
            ctx.activate()
            ctx.clear_promises(netloc, scheme, storeoptions)
        # Switch back to the previous context
        myctx.activate()


def rescue(*files, **opts):
    """Action to be undertaken when things really went bad."""

    t = sessions.current()
    sh = t.sh
    env = t.env

    # Summarise diffs...
    if len(t.context.diff_history):
        sh.header("Summary of automatic toolbox diffs")
        t.context.diff_history.show()

    # Force clearing of all promises
    clear_promises(clear=True)

    sh.header("Rescuing current dir")
    sh.dir(output=False, fatal=False)

    logger.info("Rescue files %s", files)

    if "VORTEX_RESCUE" in env and env.false("VORTEX_RESCUE"):
        logger.warning("Skip rescue <VORTEX_RESCUE=%s>", env.VORTEX_RESCUE)
        return False

    if files:
        items = list(files)
    else:
        items = sh.glob("*")

    rfilter = opts.get("filter", env.VORTEX_RESCUE_FILTER)
    if rfilter is not None:
        logger.warning("Rescue filter <%s>", rfilter)
        select = "|".join(re.split(r"[,;:]+", rfilter))
        items = [x for x in items if re.search(select, x, re.IGNORECASE)]
        logger.info("Rescue filter [%s]", select)

    rdiscard = opts.get("discard", env.VORTEX_RESCUE_DISCARD)
    if rdiscard is not None:
        logger.warning("Rescue discard <%s>", rdiscard)
        select = "|".join(re.split(r"[,;:]+", rdiscard))
        items = [x for x in items if not re.search(select, x, re.IGNORECASE)]
        logger.info("Rescue discard [%s]", select)

    if items:
        bkupdir = opts.get("bkupdir", env.VORTEX_RESCUE_PATH)

        if bkupdir is None:
            logger.error("No rescue directory defined.")
        else:
            logger.info("Backup directory defined by user < %s >", bkupdir)
            items.sort()
            logger.info("Rescue items %s", str(items))
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
        logger.warning("No item to rescue.")

    return bool(items)
