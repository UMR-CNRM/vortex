#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
This modules defines the base nodes of the logical layout
for any :mod:`vortex` experiment.
"""

from __future__ import print_function, absolute_import, unicode_literals, division
import six

import re
import sys

from bronx.fancies import loggers
from bronx.patterns import getbytag
from bronx.syntax.iterators import izip_pcn
from bronx.system.interrupt import SignalInterruptError
from footprints import proxy as fpx
from vortex import toolbox, VortexForceComplete
from vortex.algo.components import DelayedAlgoComponentError
from vortex.layout.appconf import ConfigSet
from vortex.layout.subjobs import subjob_output_markup
from vortex.syntax.stdattrs import Namespace
from vortex.util.config import GenericConfigParser

logger = loggers.getLogger(__name__)

#: Export real nodes.
__all__ = ['Driver', 'Task', 'Family']


class NiceLayout(object):
    """Some nice method to share between layout items."""

    @property
    def sh(self):
        """Abstract property: have to be defined later on"""
        raise NotImplementedError

    def subtitle(self, *args, **kw):
        """Proxy to :meth:`~vortex.tools.systems.subtitle` method."""
        return self.sh.subtitle(*args, **kw)

    def header(self, *args, **kw):
        """Proxy to :meth:`~vortex.tools.systems.header` method."""
        return self.sh.header(*args, **kw)

    def nicedump(self, msg, titlecallback=None, **kw):
        """Simple dump of the dict contents with ``msg`` as header."""
        titlecallback = titlecallback or self.header
        titlecallback(msg)
        if kw:
            maxlen = max([len(x) for x in kw.keys()])
            for k, v in sorted(six.iteritems(kw)):
                print(' +', k.ljust(maxlen), '=', six.text_type(v))
            print()
        else:
            print(" + ...\n")


class Node(getbytag.GetByTag, NiceLayout):
    """Base class type for any element in the logical layout.

    :param str tag: The node's tag (must be unique !)
    :param Ticket ticket: The session's ticket that will be used
    :param str config_tag: The configuration's file section name that will be used
                           to setup this node (default: ``self.tag``)
    :param active_callback: Some function or lambda that will be called with
                            ``self`` as first argument in order to determine if
                            the current not should be used (default: ``None``.
                            i.e. The node is active).
    :param str special_prefix: The prefix of any environment variable that should
                               be exported into ``self.conf``
    :param str register_cycle_prefix: The callback function used to initialise
                                      Genv's cycles
    :param JobAssistant jobassistant: the jobassistant object that might
                                      be used to find out the **special_prefix**
                                      and **register_cycle_prefix** callback.
    :param dict kw: Any other attributes that will be added to ``self.options``
                    (that will eventually be added to ``self.conf``)
    """

    def __init__(self, kw):
        logger.debug('Node initialisation %s', repr(self))
        self.options = dict()
        self.play = kw.pop('play', False)
        self._ticket = kw.pop('ticket', None)
        if self._ticket is None:
            raise ValueError("The session's ticket must be provided")
        self._configtag = kw.pop('config_tag', self.tag)
        self._active_cb = kw.pop('active_callback', None)
        if self._active_cb is not None and not callable(self._active_cb):
            raise ValueError("If provided, active_callback must be a callable")
        self._locprefix = kw.pop('special_prefix', 'OP_').upper()
        self._subjobok = kw.pop('subjob_allowed', True)
        self._subjobtag = kw.pop('subjob_tag', None)
        self._cycle_cb = kw.pop('register_cycle_prefix', None)
        j_assist = kw.pop('jobassistant', None)
        if j_assist is not None:
            self._locprefix = j_assist.special_prefix.upper()
            self._cycle_cb = j_assist.register_cycle
            self._subjobok = j_assist.subjob_allowed
            self._subjobtag = j_assist.subjob_tag
        self._conf = None
        self._activenode = None
        self._contents = list()
        self._aborted = False

    def _args_loopclone(self, tagsuffix, extras):  # @UnusedVariable
        """All the necessary arguments to build a copy of this object."""
        argsdict = dict(play=self.play,
                        ticket=self.ticket,
                        config_tag=self.config_tag,
                        active_callback=self._active_cb,
                        special_prefix=self._locprefix,
                        register_cycle_prefix=self._cycle_cb,
                        subjob_tag=self._subjobtag,
                        subjob_allowed=self._subjobok)
        argsdict.update(self.options)
        return argsdict

    def loopclone(self, tagsuffix, extras):
        """Create a copy of the present object by adding a suffix to the tag.

        **extras** items can be added to the copy's options.
        """
        kwargs = self._args_loopclone(tagsuffix, extras)
        kwargs.update(**extras)
        return self.__class__(tag=self.tag + tagsuffix, **kwargs)

    @classmethod
    def tag_clean(cls, tag):
        """Lower case, space-free and underscore-free tag."""
        return tag.lower().replace(' ', '')

    @property
    def ticket(self):
        return self._ticket

    @property
    def config_tag(self):
        return self._configtag

    @property
    def aborted(self):
        return self._aborted

    @property
    def conf(self):
        return self._conf

    @property
    def activenode(self):
        if self._activenode is None:
            if self.conf is None:
                raise RuntimeError('Setup the configuration object befoe calling activenode !')
            self._activenode = self._active_cb is None or self._active_cb(self)
        return self._activenode

    @property
    def sh(self):
        return self.ticket.sh

    @property
    def env(self):
        return self.ticket.env

    @property
    def contents(self):
        return self._contents

    def clear(self):
        """Clear actual contents."""
        self._contents[:] = []

    def __iter__(self):
        for node in self.contents:
            yield node

    def build_context(self):
        """Build the context and subcontexts of the current node."""
        if self.activenode:
            oldctx = self.ticket.context
            ctx = self.ticket.context.newcontext(self.tag, focus=True)
            ctx.cocoon()
            self._setup_context(ctx)
            oldctx.activate()

    def _setup_context(self, ctx):
        """Setup the newly created context."""
        pass

    def __enter__(self):
        """
        Enter a :keyword:`with` context, freezing the current env
        and joining a cocoon directory.
        """
        if self.activenode:
            self._oldctx = self.ticket.context
            ctx = self.ticket.context.switch(self.tag)
            ctx.cocoon()
            logger.debug('Node context directory <%s>', self.sh.getcwd())
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """Exit from :keyword:`with` context."""
        if self.activenode:
            logger.debug('Exit context directory <%s>', self.sh.getcwd())
            self._oldctx.activate()
            self.ticket.context.cocoon()

    def setconf(self, conf_local, conf_global):
        """Build a new conf object for the actual node."""

        # The parent conf is the default configuration
        if isinstance(conf_local, ConfigSet):
            self._conf = conf_local.copy()
        else:
            self._conf = ConfigSet()
            self._conf.update(conf_local)
        self._active = None

        # This configuration is updated with any section with the current tag name
        updconf = conf_global.get(self.config_tag, dict())
        self.nicedump(' '.join(('Configuration for', self.realkind, self.tag)), **updconf)
        self.conf.update(updconf)

        # Add exported local variables
        self.local2conf()

        # Add potential options
        if self.options:
            self.nicedump('Update conf with last minute arguments',
                          titlecallback=self.subtitle, **self.options)
            self.conf.update(self.options)

        if self.activenode:
            # Then we broadcast the current configuration to the kids
            for node in self.contents:
                node.setconf(self.conf, conf_global)
        else:
            logger.info('Under present conditions/configuration, this node will not be activated.')

    def localenv(self):
        """Dump the actual env variables."""
        self.header('ENV catalog')
        self.env.mydump()

    def local2conf(self):
        """Set some parameters if defined in environment but not in actual conf."""
        autoconf = dict()
        localstrip = len(self._locprefix)
        for localvar in sorted([x for x in self.env.keys() if x.startswith(self._locprefix)]):
            if (localvar[localstrip:] not in self.conf or
                    (localvar[localstrip:] not in ('rundate', ) and
                     self.env[localvar] != self.conf[localvar[localstrip:]])):
                autoconf[localvar[localstrip:].lower()] = self.env[localvar]
        if autoconf:
            self.nicedump('Populate conf with local variables',
                          titlecallback=self.subtitle, **autoconf)
            self.conf.update(autoconf)

    def conf2io(self):
        """Abstract method."""
        pass

    def xp2conf(self):
        """Set the actual experiment value -- Could be the name of the op suite if any."""
        if 'xpid' not in self.conf:
            self.conf.xpid = self.conf.get('suite', self.env.VORTEX_XPID)
        if self.conf.xpid is None:
            raise ValueError('Could not set a proper experiment id.')

    def register_cycle(self, cyclename):
        """Adds a new cycle to genv if a proper callback is defined."""
        if self._cycle_cb is not None:
            self._cycle_cb(cyclename)
        else:
            raise NotImplementedError()

    def cycles(self):
        """Update and register some configuration cycles."""

        other_cycles = [x for x in self.conf.keys() if x.endswith('_cycle')]
        if 'cycle' in self.conf or other_cycles:
            self.header("Registering cycles")

        # At least, look for the main cycle
        if 'cycle' in self.conf:
            self.register_cycle(self.conf.cycle)

        # Have a look to other cycles
        for other in other_cycles:
            self.register_cycle(self.conf.get(other))

    def geometries(self):
        """Setup geometries according to actual tag."""
        thisgeo = self.tag + '_geometry'
        if thisgeo in self.conf:
            self.conf.geometry = self.conf.get(thisgeo)
        if 'geometry' not in self.conf:
            logger.error('No default geometry defined -- Probably a big mistake !')

    def defaults(self, extras):
        """Set toolbox defaults, extended with actual arguments ``extras``."""
        t = self.ticket
        toolbox.defaults(
            model=t.glove.vapp,
            namespace=self.conf.get('namespace', Namespace('vortex.cache.fr')),
            gnamespace=self.conf.get('gnamespace', Namespace('gco.multi.fr')),
        )

        if 'rundate' in self.conf:
            toolbox.defaults['date'] = self.conf.rundate

        for optk in ('cutoff', 'geometry', 'cycle', 'model',):
            if optk in self.conf:
                toolbox.defaults[optk] = self.conf.get(optk)

        toolbox.defaults(**extras)
        toolbox.defaults.show()

    def setup(self, **kw):
        """A methodic way to build the conf of the node."""
        self.subtitle(self.realkind.upper() + ' setup')
        self.localenv()
        self.local2conf()
        self.conf2io()
        self.xp2conf()
        if kw:
            self.nicedump('Update conf with last minute arguments', **kw)
            self.conf.update(kw)
        self.cycles()
        self.geometries()
        self.header('Toolbox defaults')
        self.defaults(kw.get('defaults', dict()))

    def summary(self):
        """Dump actual parameters of the configuration."""
        self.nicedump('Complete parameters', **self.conf)

    def refill(self, **kw):
        """Populates the vortex cache with expected input flow data.

        The refill method is systematically called when a task is run. However,
        the refill is not always desirable hence the if statement that checks the
        self.steps attribute's content.
        """
        # This method acts as an example: if a refill is actually needed,
        # it should be overwritten.
        if 'refill' in self.steps:
            logger.warning("Refill should takes place here: please overwrite...")

    def process(self):
        """Abstract method: perform the task to do."""
        # This method acts as an example: it should be overwritten.

        if 'early-fetch' in self.steps or 'fetch' in self.steps:
            # In a multi step job (MTOOL, ...), this step will be run on a
            # transfer node. Consequently, data that may be missing from the
            # local cache must be fetched here. (e.g. GCO's genv, data from the
            # mass archive system, ...). Note: most of the data should be
            # retrieved here since the use of transfer node is costless.
            pass

        if 'fetch' in self.steps:
            # In a multi step job (MTOOL, ...), this step will be run, on a
            # compute node, just before the beginning of computations. It is the
            # appropriate place to fetch data produced by a previous task (the
            # so-called previous task will have to use the 'backup' step
            # (see the later explanations) in order to make such data available
            # in the local cache).
            pass

        if 'compute' in self.steps:
            # The actual computations... (usually a call to the run method of an
            # AlgoComponent)
            pass

        if 'backup' in self.steps or 'late-backup' in self.steps:
            # In a multi step job (MTOOL, ...), this step will be run, on a
            # compute node, just after the computations. It is the appropriate
            # place to put data in the local cache in order to make it available
            # to a subsequent step.
            pass

        if 'late-backup' in self.steps:
            # In a multi step job (MTOOL, ...), this step will be run on a
            # transfer node. Consequently, most of the data should be archived
            # here.
            pass

    def complete(self, aborted=False):
        """Some cleaning and completion status."""
        self._aborted = aborted

    def _actual_run(self, nbpass=0, sjob_activated=True):
        """Abstract method: the actual job to do."""
        pass

    def run(self, nbpass=0, sjob_activated=True):
        """Execution driver: setup, run, complete... (if needed)."""
        if self.activenode:
            self._actual_run(nbpass, sjob_activated)

    def filter_execution_error(self, exc):  # @UnusedVariable
        """
        May be overwritten if exceptions generated by the AlgoComponent needs
        to be filtered.

        :param Exception exc: The exception that triggered the call

        :return: Two elements. The first item (boolean) tells whether or not
                 a delayed exception error is to be masked. The second item is a
                 (possibly empty) dictionary that gives some extra information
                 about the warning/error (such information could be used to
                 generate a meaningful alert email).

        :note: Do not re-raised the **exc** exception in this method.
        """
        return False, dict()

    def report_execution_warning(self, exc, **kw_infos):  # @UnusedVariable
        """
        May be overwritten if a report needs to be sent when a filtered
        execution error occurs.

        :param Exception exc: The exception that triggered the call
        :param dict kw_infos: Any kind of extra informations provided by the
            :meth:`filter_execution_error`.

        :note: Do not re-raised the **exc** exception in this method.
        """
        pass

    def report_execution_error(self, exc, **kw_infos):  # @UnusedVariable
        """
        May be overwritten if a report needs to be sent when an un-filtered
        execution error occurs.

        :param Exception exc: The exception that triggered the call
        :param dict kw_infos: Any kind of extra informations provided by the
            :meth:`filter_execution_error`.

        :note: Do not re-raised the **exc** exception in this method.
        """
        pass

    def component_runner(self, tbalgo, tbx=(None,), **kwargs):
        """Run the binaries listed in tbx using the tbalgo algo component.

        This is a helper method that maybe useful (its use is not mandatory).
        """
        # it may be necessary to setup a default value for OpenMP...
        env_update = dict()
        if 'openmp' not in self.conf or not isinstance(self.conf.openmp, (list, tuple)):
            env_update['OMP_NUM_THREADS'] = int(self.conf.get('openmp', 1))

        # If some mpiopts are in the config file, use them...
        mpiopts = kwargs.pop('mpiopts', dict())
        mpiopts_map = dict(nnodes='nn', ntasks='nnp', nprocs='np', proc='np')
        for stuff in [s
                      for s in ('proc', 'nprocs', 'nnodes', 'ntasks', 'openmp',
                                'prefixcommand', 'envelope')
                      if s in mpiopts or s in self.conf]:
            mpiopts[mpiopts_map.get(stuff, stuff)] = mpiopts.pop(stuff, self.conf[stuff])

        # if the prefix command is missing in the configuration file, look in the input sequence
        if 'prefixcommand' not in mpiopts:
            prefixes = self.ticket.context.sequence.effective_inputs(role=re.compile('Prefixcommand'))
            if len(prefixes) > 1:
                raise RuntimeError("Only one prefix command can be used...")
            for sec in prefixes:
                prefixpath = sec.rh.container.actualpath()
                logger.info('The following MPI prefix command will be used: %s', prefixpath)
                mpiopts['prefixcommand'] = prefixpath

        # Ensure that some of the mpiopts are integers
        for stuff in [s for s in ('nn', 'nnp', 'openmp', 'np') if s in mpiopts]:
            if isinstance(mpiopts[stuff], (list, tuple)):
                mpiopts[stuff] = [int(v) for v in mpiopts[stuff]]
            else:
                mpiopts[stuff] = int(mpiopts[stuff])

        # When multiple list of binaries are given (i.e several binaries are launched
        # by the same MPI command).
        if tbx and isinstance(tbx[0], (list, tuple)):
            tbx = zip(*tbx)
        with self.env.delta_context(**env_update):
            with self.sh.default_target.algo_run_context(self.ticket, self.conf):
                for binary in tbx:
                    try:
                        tbalgo.run(binary, mpiopts=mpiopts, **kwargs)
                    except (Exception, SignalInterruptError, KeyboardInterrupt) as e:
                        mask_delayed, f_infos = self.filter_execution_error(e)
                        if isinstance(e, DelayedAlgoComponentError) and mask_delayed:
                            logger.warning("The delayed exception is masked:\n%s", str(f_infos))
                            self.report_execution_warning(e, **f_infos)
                        else:
                            logger.error("Un-filtered execution error:\n%s", str(f_infos))
                            self.report_execution_error(e, **f_infos)
                            raise


class Family(Node):
    """Logical group of :class:`Family` or :class:`Task`.

    Compared to the usual :class:`Node` class, additional attributes are:

    :param nodes: The list of :class:`Family` or :class:`Task` objects that
                  are members of this family
    """

    def __init__(self, **kw):
        logger.debug('Family init %s', repr(self))
        super(Family, self).__init__(kw)
        nodes = kw.pop('nodes', list())
        self.options = kw.copy()

        # Build the nodes sequence
        fcount = 0
        for x in nodes:
            if isinstance(x, Node):
                self._contents.append(x)
            else:
                fcount += 1
                self._contents.append(
                    Family(
                        tag='{0:s}.f{1:02d}'.format(self.tag, fcount),
                        ticket=self.ticket,
                        nodes=x,
                        **kw
                    )
                )

    @property
    def realkind(self):
        return 'family'

    def _args_loopclone(self, tagsuffix, extras):  # @UnusedVariable
        baseargs = super(Family, self)._args_loopclone(tagsuffix, extras)
        baseargs['nodes'] = [node.loopclone(tagsuffix, extras) for node in self._contents]
        return baseargs

    def _setup_context(self, ctx):
        """Build the contexts of all the nodes contained by this family."""
        for node in self.contents:
            node.build_context()

    def localenv(self):
        """No env dump in families (it is enough to dump it in Tasks)."""
        pass

    def summary(self):
        """No parameters dump in families (it is enough to dump it in Tasks)."""
        pass

    @property
    def _parallel_launchtool(self):
        """Create a launchtool for parallel runs (if sensible only)."""
        if self._subjobok and self._subjobtag is None and 'paralleljobs_kind' in self.conf:
            # Subjob are allowed and I'am the main job (because self._subjobtag is None) :
            # => Run the family's content using subjobs

            # Create the subjob launcher
            launcher_opts = {k[len('paralleljobs_'):]: self.conf[k]
                             for k in self.conf if k.startswith('paralleljobs_')}
            launchtool = fpx.subjobslauncher(scriptpath=sys.argv[0],
                                             ** launcher_opts)
            if launchtool is None:
                raise RuntimeError('No subjob launcher could be found: check "paralleljobs_kind".')
            launchtool.ticket = self.ticket
            return launchtool
        else:
            return None

    def _actual_run(self, nbpass=0, sjob_activated=True):
        """Execution driver: setup, run kids, complete."""
        launchtool = self._parallel_launchtool
        if launchtool:
            self.ticket.sh.title(' '.join(('Build', self.realkind, self.tag, '(using subjobs)')))

            def node_recurse(node):
                """Recursively find tags."""
                o_set = set([node.tag, ])
                for snode in node.contents:
                    o_set = o_set | node_recurse(snode)
                return o_set

            # Launch each family's member
            for node in self.contents:
                launchtool(node.tag, node_recurse(node))
            # Wait for everybody to complete
            launchtool.waitall()
        else:
            # No subjobs configured or allowed: run the usual way...
            sjob_activated = sjob_activated or self._subjobtag == self.tag
            with subjob_output_markup(self._subjobtag == self.tag):
                self.ticket.sh.title(' '.join(('Build', self.realkind, self.tag)))
                self.setup()
                self.summary()
                for node in self.contents:
                    with node:
                        node.run(sjob_activated=sjob_activated)
                self.complete()


class LoopFamily(Family):
    """
    Loop on the Family's content according to a variable taken from ``self.conf``.

    Compared to the usual :class:`Family` class, additional attributes are:

    :param str loopconf: The name of the ``self.conf`` entry to loop on
    :param str loopvariable: The name of the loop control variable (that is
                             automatically added to the child's self.conf).
                             By default, **loopconf** without trailing ``s`` is
                             used.
    :param str loopsuffix: The suffix that will be added to the child's tag.
                           By default '+loopvariable{!s}' (where {!s} will be
                           replaced by the loop control variable's value).
    :param bool loopneedprev: Ensure that the previous value is available
    :param bool loopneednext: Ensure that the next value is available
    """

    def __init__(self, **kw):
        logger.debug('LoopFamily init %s', repr(self))
        # On what should we iterate ?
        self._loopconf = kw.pop('loopconf', None)
        if not self._loopconf:
            raise ValueError('The "loopconf" named argument must be given')
        else:
            self._loopconf = self._loopconf.split(',')
        # Find the loop's variable names
        self._loopvariable = kw.pop('_loopvariable', None)
        if self._loopvariable is None:
            self._loopvariable = [s.rstrip('s') for s in self._loopconf]
        else:
            self._loopvariable = self._loopvariable.split(',')
            if len(self._loopvariable) != len(self._loopconf):
                raise ValueError('Inconsistent size between loopconf and loopvariable')
        # Find the loop suffixes
        self._loopsuffix = kw.pop('loopsuffix', None)
        if self._loopsuffix is None:
            self._loopsuffix = '+' + self._loopvariable[0] + '{0!s}'
        # Prev/Next
        self._loopneedprev = kw.pop('loopneedprev', False)
        self._loopneednext = kw.pop('loopneednext', False)
        # Generic init...
        super(LoopFamily, self).__init__(**kw)
        # Initialisation stuff
        self._actual_content = None

    def _args_loopclone(self, tagsuffix, extras):  # @UnusedVariable
        baseargs = super(LoopFamily, self)._args_loopclone(tagsuffix, extras)
        baseargs['loopconf'] = ','.join(self._loopconf)
        baseargs['loopvariable'] = ','.join(self._loopvariable)
        baseargs['loopsuffix'] = self._loopsuffix
        baseargs['loopneedprev'] = self._loopneedprev
        baseargs['loopneednext'] = self._loopneednext
        return baseargs

    @property
    def contents(self):
        if self._actual_content is None:
            self._actual_content = list()
            for pvars, cvars, nvars in izip_pcn(*[self.conf.get(lc) for lc in self._loopconf]):
                if self._loopneedprev and all([v is None for v in pvars]):
                    continue
                if self._loopneednext and all([v is None for v in nvars]):
                    continue
                extras = {v: x for v, x in zip(self._loopvariable, cvars)}
                extras.update({v + '_prev': x for v, x in zip(self._loopvariable, pvars)})
                extras.update({v + '_next': x for v, x in zip(self._loopvariable, nvars)})
                suffix = self._loopsuffix.format(*cvars)
                for node in self._contents:
                    self._actual_content.append(node.loopclone(suffix, extras))
        return self._actual_content


class WorkshareFamily(Family):
    """
    Loop on the Family's content according to a list taken from ``self.conf``.

    The list taken from ``self.conf`` is sliced, and each iteration of the
    loop works on its slice of the list. That's why it's called a workshare...

    Compared to the usual :class:`Family` class, additional attributes are:

    :param str workshareconf: The name of the ``self.conf`` entry to slice
    :param str worksharename: The name of the slice control variable (that is
                              automatically added to the childs' ``self.conf``).
    :param int worksharesize: The minimum number of items in each workshare (default=1)
    :param worksharesize: The maximum number of workshares (it might
                          be an integer or a name referring to an entry
                          ``in self.conf`` (default: None. e.g. no limit)
    """

    def __init__(self, **kw):
        logger.debug('WorkshareFamily init %s', repr(self))
        # On what should we build the workshare ?
        self._workshareconf = kw.pop('workshareconf', None)
        if not self._workshareconf:
            raise ValueError('The "workshareconf" named argument must be given')
        else:
            self._workshareconf = self._workshareconf.split(',')
        # Find the loop's variable names
        self._worksharename = kw.pop('worksharename', None)
        if not self._worksharename:
            raise ValueError('The "worksharename" named argument must be given')
        else:
            self._worksharename = self._worksharename.split(',')
            if len(self._worksharename) != len(self._workshareconf):
                raise ValueError('Inconsistent size between workshareconf and worksharename')
        # Minimum size for a workshare
        self._worksharesize = int(kw.pop('worksharesize', 1))
        # Maximum number of workshares
        self._worksharelimit = kw.pop('worksharelimit', None)
        # Generic init
        super(WorkshareFamily, self).__init__(**kw)
        # Initialisation stuff
        self._actual_content = None

    def _args_loopclone(self, tagsuffix, extras):  # @UnusedVariable
        baseargs = super(WorkshareFamily, self)._args_loopclone(tagsuffix, extras)
        baseargs['workshareconf'] = ','.join(self._workshareconf)
        baseargs['worksharename'] = ','.join(self._worksharename)
        baseargs['worksharesize'] = self._worksharesize
        baseargs['worksharelimit'] = self._worksharelimit
        return baseargs

    @property
    def contents(self):
        if self._actual_content is None:
            # Find the population sizes and workshares size/number
            populations = [self.conf.get(lc) for lc in self._workshareconf]
            n_population = set([len(p) for p in populations])
            if not(len(n_population) == 1):
                raise RuntimeError('Inconsistent sizes in "workshareconf" lists')
            n_population = n_population.pop()
            # Number of workshares if worksharesize alone is considered
            sb_ws_number = n_population // self._worksharesize
            # Workshare limit
            if isinstance(self._worksharelimit, six.string_types):
                lb_ws_number = int(self.conf.get(self._worksharelimit))
            else:
                lb_ws_number = self._worksharelimit or sb_ws_number
            # Final result
            ws_number = min([sb_ws_number, lb_ws_number])
            # Find out the workshares sizes
            floorsize = n_population // ws_number
            ws_sizes = [floorsize, ] * ws_number
            for i in range(n_population - ws_number * floorsize):
                ws_sizes[i] += 1
            # Build de family's content
            self._actual_content = list()
            ws_start = 0
            for i, ws_size in enumerate(ws_sizes):
                ws_slice = slice(ws_start, ws_start + ws_size)
                extras = {v: x[ws_slice] for v, x in zip(self._worksharename, populations)}
                ws_start += ws_size
                ws_suffix = '_ws{:03d}'.format(i + 1)
                for node in self._contents:
                    self._actual_content.append(node.loopclone(ws_suffix, extras))
        return self._actual_content


class Task(Node):
    """Terminal node including a :class:`Sequence`."""

    def __init__(self, **kw):
        logger.debug('Task init %s', repr(self))
        super(Task, self).__init__(kw)
        self.__dict__.update(
            steps=kw.pop('steps', tuple()),
            fetch=kw.pop('fetch', 'fetch'),
            compute=kw.pop('compute', 'compute'),
            backup=kw.pop('backup', 'backup'),
        )
        self.options = kw.copy()
        if isinstance(self.steps, six.string_types):
            self.steps = tuple(self.steps.replace(' ', '').split(','))

    @property
    def realkind(self):
        return 'task'

    def _args_loopclone(self, tagsuffix, extras):  # @UnusedVariable
        baseargs = super(Task, self)._args_loopclone(tagsuffix, extras)
        baseargs['steps'] = self.steps
        baseargs['fetch'] = self.fetch
        baseargs['compute'] = self.compute
        baseargs['backup'] = self.backup
        return baseargs

    @property
    def ctx(self):
        return self.ticket.context

    def build(self):
        """Switch to rundir and check the active steps."""

        t = self.ticket
        t.sh.title(' '.join(('Build', self.realkind, self.tag)))

        # Change actual rundir if specified
        rundir = self.options.get('rundir', None)
        if rundir:
            t.env.RUNDIR = rundir
            t.sh.cd(rundir, create=True)
            t.rundir = t.sh.getcwd()
        print('The current directory is: {}'.format(t.sh.getcwd()))

        # Some attempt to find the current active steps
        if not self.steps:
            if self.env.get(self._locprefix + 'REFILL'):
                self.steps = ('refill',)
            elif self.play:
                self.steps = ('early-{:s}'.format(self.fetch), self.fetch,
                              self.compute,
                              self.backup, 'late-{:s}'.format(self.backup))
            elif int(self.env.get('SLURM_NPROCS', 1)) > 1:
                self.steps = (self.fetch, self.compute)
            else:
                self.steps = (self.fetch,)
        self.header('Active steps: ' + ' '.join(self.steps))

    def conf2io(self):
        """Broadcast IO SERVER configuration values to environment."""
        t = self.ticket
        triggered = any([i in self.conf
                         for i in ('io_nodes', 'io_companions', 'io_incore_tasks',
                                   'io_openmp')])
        if 'io_nodes' in self.conf:
            t.env.default(VORTEX_IOSERVER_NODES=self.conf.io_nodes)
            if 'io_tasks' in self.conf:
                t.env.default(VORTEX_IOSERVER_TASKS=self.conf.io_tasks)
        elif 'io_companions' in self.conf:
            t.env.default(VORTEX_IOSERVER_COMPANION_TASKS=self.conf.io_companions)
        elif 'io_incore_tasks' in self.conf:
            t.env.default(VORTEX_IOSERVER_INCORE_TASKS=self.conf.io_incore_tasks)
            if 'io_incore_fixer' in self.conf:
                t.env.default(VORTEX_IOSERVER_INCORE_FIXER=self.conf.io_incore_fixer)
            if 'io_incore_dist' in self.conf:
                t.env.default(VORTEX_IOSERVER_INCORE_DIST=self.conf.io_incore_dist)
        if 'io_openmp' in self.conf:
            t.env.default(VORTEX_IOSERVER_OPENMP=self.conf.io_openmp)
        if triggered:
            self.nicedump('IOSERVER Environment', **{k: v for k, v in t.env.items()
                                                     if k.startswith('VORTEX_IOSERVER_')})

    def io_poll(self, prefix=None):
        """Complete the polling of data produced by the execution step."""
        sh = self.sh
        if prefix and sh.path.exists('io_poll.todo'):
            for iopr in prefix:
                sh.header('IO poll <' + iopr + '>')
                rc = sh.io_poll(iopr)
                print(rc)
                print(rc.result)
            sh.header('Post-IO Poll directory listing')
            sh.ll(output=False, fatal=False)

    def _actual_run(self, nbpass=0, sjob_activated=True):
        """Execution driver: build, setup, refill, process, complete."""
        sjob_activated = sjob_activated or self._subjobtag == self.tag
        if sjob_activated:
            with subjob_output_markup(self._subjobtag == self.tag):
                try:
                    self.build()
                    self.setup()
                    self.summary()
                    self.refill()
                    self.process()
                except VortexForceComplete:
                    self.sh.title('Force complete')
                finally:
                    self.complete()


class Driver(getbytag.GetByTag, NiceLayout):
    """Iterable object for a simple scheduling of :class:`Application` objects."""

    _tag_default = 'pilot'

    def __init__(self, ticket, nodes=(), rundate=None, iniconf=None,
                 jobname=None, options=None, iniencoding=None):
        """Setup default args value and read config file job."""
        self._ticket = t = ticket
        self._conf = None

        # Set default parameters for the actual job
        self._options = dict() if options is None else options
        self._special_prefix = self._options.get('special_prefix', 'OP_').upper()
        self._subjob_tag = self._options.get('subjob_tag', None)
        j_assist = self._options.get('jobassistant', None)
        if j_assist is not None:
            self._special_prefix = j_assist.special_prefix.upper()
            self._subjob_tag = j_assist.subjob_tag
        self._iniconf = iniconf or t.env.get('{:s}INICONF'.format(self._special_prefix))
        self._iniencoding = iniencoding or t.env.get('{:s}INIENCODING'.format(self._special_prefix), None)
        self._jobname = jobname or t.env.get('{:s}JOBNAME'.format(self._special_prefix)) or 'void'
        self._rundate = rundate or t.env.get('{:s}RUNDATE'.format(self._special_prefix))
        self._nbpass = 0

        # Build the tree to schedule
        self._contents = list()
        fcount = 0
        for x in nodes:
            if isinstance(x, Node):
                self._contents.append(x)
            else:
                fcount += 1
                self._contents.append(
                    Family(
                        tag='{0:s}.f{1:02d}'.format(self.tag, fcount),
                        ticket=self.ticket,
                        nodes=x,
                        ** dict(self._options)
                    )
                )

    @property
    def ticket(self):
        return self._ticket

    @property
    def conf(self):
        return self._conf

    @property
    def sh(self):
        return self.ticket.sh

    @property
    def env(self):
        return self.ticket.env

    @property
    def iniconf(self):
        return self._iniconf

    @property
    def iniencoding(self):
        return self._iniencoding

    @property
    def jobconf(self):
        return self._jobconf

    @property
    def contents(self):
        return self._contents

    @property
    def jobname(self):
        return self._jobname

    @property
    def rundate(self):
        return self._rundate

    @property
    def nbpass(self):
        return self._nbpass

    def read_config(self, inifile=None, iniencoding=None):
        """Read specified ``inifile`` initialisation file."""
        if inifile is None:
            inifile = self.iniconf
        if iniencoding is None:
            iniencoding = self.iniencoding
        try:
            iniparser = GenericConfigParser(inifile, encoding=iniencoding)
            thisconf = iniparser.as_dict(merged=False)
        except Exception:
            logger.critical('Could not read config %s', inifile)
            raise
        return thisconf

    def setup(self, name=None, date=None, verbose=True):
        """Top setup of the current configuration, including at least one name."""

        jobname = name or self.jobname

        rundate = date or self.rundate
        if rundate is None:
            logger.info('No date provided for this run.')

        if verbose:
            if rundate is None:
                self.sh.title(['Starting job', '', jobname, ])
            else:
                self.sh.title(['Starting job', '', jobname, '', 'date ' + rundate.isoformat()])

        # Read once for all the job configuration file
        if self.iniconf is None:
            logger.warning('This driver does not have any configuration file')
            self._jobconf = dict()
        else:
            self._jobconf = self.read_config(self.iniconf, self.iniencoding)

        self._conf = ConfigSet()
        updconf = self.jobconf.get('defaults', dict())
        updconf.update(self.jobconf.get(self.jobname, dict()))
        self.nicedump('Configuration for job ' + self.jobname, **updconf)
        self.conf.update(updconf)

        # Recursively set the configuration tree and contexts
        if rundate is not None:
            self.conf.rundate = rundate
        for node in self.contents:
            node.setconf(self.conf, self.jobconf)
            node.build_context()

    def run(self):
        """Assume recursion of nodes `run` methods."""
        self._nbpass += 1
        for node in self.contents:
            with node:
                node.run(nbpass=self.nbpass, sjob_activated=self._subjob_tag is None)
