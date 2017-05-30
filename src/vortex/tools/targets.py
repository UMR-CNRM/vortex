#!/usr/bin/env python
# -*- coding:Utf-8 -*-

"""
This package handles targets computers objects that could in charge of
hosting a specific execution.Target objects use the :mod:`footprints` mechanism.
"""

#: No automatic export
__all__ = []

import re
import platform

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.util.config import GenericConfigParser
from vortex import sessions


class Target(footprints.FootprintBase):
    """Root class for any :class:`Target` subclasses.

    Target classes are used to define specific settings and/or behaviour for a
    given host (*e.g.* your own workstation) or group of hosts (*e.g.* each of
    the nodes of a cluster).

    Through the :meth:`get` method, it gives access to the **Target**'s specific
    configuration file (``target-[hostname].ini`` by default).
    """

    _abstract  = True
    _explicit  = False
    _collector = ('target',)
    _footprint = dict(
        info = 'Default target description',
        attr = dict(
            hostname = dict(
                optional = True,
                default  = platform.node(),
                alias    = ('nodename', 'computer')
            ),
            inetname = dict(
                optional = True,
                default  = platform.node(),
            ),
            sysname = dict(
                optional = True,
                default  = platform.system(),
            ),
            userconfig = dict(
                type     = GenericConfigParser,
                optional = True,
                default  = None,
            ),
            inifile = dict(
                optional = True,
                default  = '@target-[hostname].ini',
            ),
            iniauto = dict(
                type     = bool,
                optional = True,
                default  = True,
            )
        )
    )

    _re_nodes_property = re.compile(r'(\w+)(nodes)$')
    _re_proxies_property = re.compile(r'(\w+)(proxies)$')
    _re_isnode_property = re.compile(r'is(\w+)node$')

    def __init__(self, *args, **kw):
        logger.debug('Abstract target computer init %s', self.__class__)
        super(Target, self).__init__(*args, **kw)
        self._actualconfig = self.userconfig
        self._specialnodes = None
        self._sepcialnodesaliases = None
        self._specialproxies = None
        if self._actualconfig is None:
            self._actualconfig = GenericConfigParser(inifile=self.inifile, mkforce=self.iniauto)

    @property
    def realkind(self):
        return 'target'

    @property
    def config(self):
        return self._actualconfig

    def generic(self):
        """Generic name is inetname by default."""
        return self.inetname

    def get(self, key, default=None):
        """Get the actual value of the specified ``key`` ( ``section:option`` ).

        Sections of the configuration file may be overwritten with sections
        specific to a given user's group (identified by the Glove's realkind
        property).

        :example:

        Let's consider a user with the *opuser* Glove's realkind and
        the following configuration file::

            [sectionname]
            myoption = generic
            [sectionname@opuser]
            myoption = operations

        The :meth:`get` method called whith ``key='sectionname:myoption'`` will
        return 'operations'.
        """
        my_glove_rk = '@' + sessions.current().glove.realkind
        glove_rk_id = re.compile(r'^.*@\w+$')
        if ':' in key:
            section, option = [x.strip() for x in key.split(':', 1)]
            # Check if an override section exists
            sections = [x for x in (section + my_glove_rk, section)
                        if x in self.config.sections()]
        else:
            option = key
            # First look in override sections, then in default one
            sections = ([s for s in self.config.sections() if s.endswith(my_glove_rk)] +
                        [s for s in self.config.sections() if not glove_rk_id.match(s)])
        # Return the first matching section/option
        for section in [x for x in sections if self.config.has_option(x, option)]:
            return self.config.get(section, option)
        return default

    def options(self, key):
        """For a given section, returns the list of available options.

        The results may depends on the current glove (see the :meth:`get` method
        documentation).
        """
        my_glove_rk = '@' + sessions.current().glove.realkind
        sections = [x for x in (key + my_glove_rk, key)
                    if x in self.config.sections()]
        options = set()
        for section in sections:
            options.update(self.config.options(section))
        return list(options)

    @classmethod
    def is_anonymous(cls):
        """Return a boolean either the current footprint define or not a mandatory set of hostname values."""
        fp = cls.footprint_retrieve()
        return not bool(fp.attr['hostname']['values'])

    def spawn_hook(self, sh):
        """Specific target hook before any serious execution."""
        pass

    def _init_supernodes(self, main_re, rangeid='range', baseid='base',):
        """Read the configuration file in order to initialize the specialnodes
        and specialproxies lists.

        To define a node list, the XXXnodes configuration key must be
        specified. It can an hardcoded coma-separated list or the
        *generic_nodes* keyword. In such a case, the node list will be
        auto-generated using the XXXrange and XXXbase configuration keys.
        """
        confsection = 'generic_nodes'
        confoptions = self.options(confsection)
        nodetypes = [(m.group(1), m.group(2))
                     for m in [main_re.match(k) for k in confoptions]
                     if m is not None]
        outdict = dict()
        for nodetype, nodelistid in nodetypes:
            nodelist = self.get(confsection + ':' + nodetype + nodelistid)
            if nodelist == 'no_generic':
                noderanges = self.get(confsection + ':' + nodetype + rangeid, None)
                if noderanges is None:
                    raise ValueError('when {0:s}{1:s} == no_generic, {0:s}{2:s} must be provided'
                                     .format(nodetype, nodelistid, rangeid))
                nodebases = self.get(confsection + ':' + nodetype + baseid,
                                     self.inetname + nodetype + '{:d}')
                outdict[nodetype] = list()
                for (r, b) in zip(noderanges.split('+'), nodebases.split('+')):
                    outdict[nodetype].extend([b.format(int(i)) for i in r.split(',')])
            else:
                outdict[nodetype] = nodelist.split(',')
        return outdict

    @property
    def specialnodesaliases(self):
        """Return the list of known aliases."""
        if self._sepcialnodesaliases is None:
            confsection = 'generic_nodes'
            confoptions = self.options(confsection)
            aliases_re = re.compile(r'(\w+)(aliases)')
            nodetypes = [(m.group(1), m.group(2))
                         for m in [aliases_re.match(k) for k in confoptions]
                         if m is not None]
            rdict = {ntype: self.get(confsection + ':' + ntype + key, '').split(',')
                     for ntype, key in nodetypes}
            self._sepcialnodesaliases = rdict
        return self._sepcialnodesaliases

    @property
    def specialnodes(self):
        """Returns a dictionary that contains the list of nodes for a given
        node-type."""
        if self._specialnodes is None:
            self._specialnodes = self._init_supernodes(self._re_nodes_property)
            for ntype, aliases in self.specialnodesaliases.items():
                for alias in aliases:
                    self._specialnodes[alias] = self._specialnodes[ntype]
        return self._specialnodes

    @property
    def specialproxies(self):
        """Returns a dictionary that contains the proxy-nodes list for a given
        node-type.

        If the proxy-nodes are not defined in the configuration file, it is
        equal to the specialnodes list.
        """
        if self._specialproxies is None:
            self._specialproxies = self._init_supernodes(self._re_proxies_property, 'proxiesrange', 'proxiesbase')
            for nodetype, nodelist in self.specialnodes.items():
                if nodetype not in self._specialproxies:
                    self._specialproxies[nodetype] = nodelist
            for ntype, aliases in self.specialnodesaliases.items():
                for alias in aliases:
                    self._specialproxies[alias] = self._specialproxies[ntype]
        return self._specialproxies

    def __getattr__(self, key):
        """Create attributes on the fly.

        * XXXnodes: returns the list of nodes for a given node-type
            (e.g loginnodes). If the XXX node-type is not defined in the
            configuration file, it returns an empty list.
        * XXXproxies: returns the list of proxy nodes for a given node-type
            (e.g loginproxies). If the XXX node-type is not defined in the
            configuration file, it returns an empty list.
        * isXXXnode: Return True if the current host is of XXX node-type.
            If the XXX node-type is note defined in the configuration file,
            it returns True.

        """
        kmatch = self._re_nodes_property.match(key)
        if kmatch is not None:
            return footprints.stdtypes.FPList(self.specialnodes.get(kmatch.group(1), []))
        kmatch = self._re_proxies_property.match(key)
        if kmatch is not None:
            return footprints.stdtypes.FPList(self.specialproxies.get(kmatch.group(1), []))
        kmatch = self._re_isnode_property.match(key)
        if kmatch is not None:
            return ((kmatch.group(1) not in self.specialnodes) or
                    (self.hostname in self.specialnodes[kmatch.group(1)]))
        raise AttributeError('The "{:s}" does not exists.'.format(key))


class LocalTarget(Target):
    """A very generic class usable for most of the computers."""

    _footprint = dict(
        info = 'Nice local target',
        attr = dict(
            sysname = dict(
                values = [ 'Linux', 'Darwin', 'Local', 'Localhost' ]
            ),
        )
    )

