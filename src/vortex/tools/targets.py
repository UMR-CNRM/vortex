"""
This package handles targets computers objects that could in charge of
hosting a specific execution. Target objects use the :mod:`footprints` mechanism.
"""

import contextlib
import logging
import re
import platform
import socket

from bronx.fancies import loggers
from bronx.syntax.decorators import secure_getattr
import footprints as fp

from vortex.util.config import GenericConfigParser
from vortex import sessions

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


def default_fqdn():
    """Tries to find the Fully-Qualified Domain Name of the host."""
    try:
        fqdn = socket.getfqdn()
    except OSError:
        fqdn = platform.node()
    return fqdn


class Target(fp.FootprintBase):
    """Root class for any :class:`Target` subclasses.

    Target classes are used to define specific settings and/or behaviour for a
    given host (*e.g.* your own workstation) or group of hosts (*e.g.* each of
    the nodes of a cluster).

    Through the :meth:`get` method, it gives access to the **Target**'s specific
    configuration file (``target-[hostname].ini`` by default).
    """

    _abstract = True
    _explicit = False
    _collector = ("target",)
    _footprint = dict(
        info="Default target description",
        attr=dict(
            hostname=dict(
                optional=True,
                default=platform.node(),
                alias=("nodename", "computer"),
            ),
            inetname=dict(
                optional=True,
                default=platform.node(),
            ),
            fqdn=dict(
                optional=True,
                default=default_fqdn(),
            ),
            sysname=dict(
                optional=True,
                default=platform.system(),
            ),
            userconfig=dict(
                type=GenericConfigParser,
                optional=True,
                default=None,
            ),
            inifile=dict(
                optional=True,
                default="@target-[hostname].ini",
            ),
            defaultinifile=dict(
                optional=True,
                default="target-commons.ini",
            ),
            iniauto=dict(
                type=bool,
                optional=True,
                default=True,
            ),
        ),
    )

    _re_nodes_property = re.compile(r"(\w+)(nodes)$")
    _re_proxies_property = re.compile(r"(\w+)(proxies)$")
    _re_isnode_property = re.compile(r"is(\w+)node$")
    _re_glove_rk_id = re.compile(r"^(.*)@\w+$")

    def __init__(self, *args, **kw):
        logger.debug("Abstract target computer init %s", self.__class__)
        super().__init__(*args, **kw)
        self._actualconfig = self.userconfig
        self._specialnodes = None
        self._sepcialnodesaliases = None
        self._specialproxies = None

    @property
    def realkind(self):
        return "target"

    @property
    def config(self):
        return self._actualconfig

    def generic(self):
        """Generic name is inetname by default."""
        return self.inetname

    def cache_storage_alias(self):
        """The tag used when reading Cache Storage configuration files."""
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
        my_glove_rk = "@" + sessions.current().glove.realkind
        if ":" in key:
            section, option = (x.strip() for x in key.split(":", 1))
            # Check if an override section exists
            sections = [
                x
                for x in (section + my_glove_rk, section)
                if x in self.config.sections()
            ]
        else:
            option = key
            # First look in override sections, then in default one
            sections = [
                s for s in self.config.sections() if s.endswith(my_glove_rk)
            ] + [
                s
                for s in self.config.sections()
                if not self._re_glove_rk_id.match(s)
            ]
        # Return the first matching section/option
        for section in [
            x for x in sections if self.config.has_option(x, option)
        ]:
            return self.config.get(section, option)
        return default

    def getx(
        self, key, default=None, env_key=None, silent=False, aslist=False
    ):
        r"""Return a value from several sources.

        In turn, the following sources are considered:

        - a shell environment variable
        - this configuration handler (key = 'section:option') (see the :meth:`get` method)
        - a default value

        Unless **silent** is set, ``KeyError`` is raised if the value cannot be found.

        **aslist** forces the result into a list (be it with a unique element).
        separators are spaces, commas, carriage returns or antislashes.
        e.g. these notations are equivalent::

            alist = val1 val2 val3 val4 val5
            alist  = val1, val2 val3 \
                     val4,
                     val5

        """
        if env_key is not None:
            env_key = env_key.upper()
            value = sessions.system().env.get(env_key, None)
        else:
            value = None

        if value is None:
            if ":" not in key:
                if silent:
                    return None
                msg = 'Configuration key should be "section:option" not "{}"'.format(
                    key
                )
                raise KeyError(msg)
            value = self.get(key, default)

        if value is None:
            if silent:
                return None
            msg = 'Please define "{}" in "{}"'.format(key, self.config.file)
            if env_key is not None:
                msg += ' or "{}" in the environment.'.format(env_key)
            logger.error(msg)
            raise KeyError(msg)

        if aslist:
            value = (
                value.replace("\n", " ")
                .replace("\\", " ")
                .replace(",", " ")
                .split()
            )

        return value

    def sections(self):
        """Returns the list of sections contained in the config file."""
        my_glove_rk = "@" + sessions.current().glove.realkind
        return sorted(
            {
                self._re_glove_rk_id.sub(r"\1", x)
                for x in self.config.sections()
                if (
                    (not self._re_glove_rk_id.match(x))
                    or x.endswith(my_glove_rk)
                )
            }
        )

    def options(self, key):
        """For a given section, returns the list of available options.

        The result may depend on the current glove (see the :meth:`get`
        method documentation).
        """
        my_glove_rk = "@" + sessions.current().glove.realkind
        sections = [
            x for x in (key, key + my_glove_rk) if x in self.config.sections()
        ]
        options = set()
        for section in sections:
            options.update(self.config.options(section))
        return sorted(options)

    def items(self, key):
        """For a given section, returns a dict that contains all options.

        The result may depend on the current glove (see the :meth:`get`
        method documentation).
        """
        items = dict()
        if key is not None:
            my_glove_rk = "@" + sessions.current().glove.realkind
            sections = [
                x
                for x in (key, key + my_glove_rk)
                if x in self.config.sections()
            ]
            for section in sections:
                items.update(self.config.items(section))
        return items

    @classmethod
    def is_anonymous(cls):
        """Return a boolean either the current footprint define or not a mandatory set of hostname values."""
        fp = cls.footprint_retrieve()
        return not bool(fp.attr["hostname"]["values"])

    def spawn_hook(self, sh):
        """Specific target hook before any serious execution."""
        pass

    @contextlib.contextmanager
    def algo_run_context(self, ticket, *kmappings):
        """Specific target hook before any component run."""
        yield

    def _init_supernodes(
        self,
        main_re,
        rangeid="range",
        baseid="base",
    ):
        """Read the configuration file in order to initialize the specialnodes
        and specialproxies lists.

        To define a node list, the XXXnodes configuration key must be
        specified. It can be an hardcoded coma-separated list, or the
        *generic_nodes* keyword. In such a case, the node list will be
        auto-generated using the XXXrange and XXXbase configuration keys.
        """
        confsection = "generic_nodes"
        confoptions = self.options(confsection)
        nodetypes = [
            (m.group(1), m.group(2))
            for m in [main_re.match(k) for k in confoptions]
            if m is not None
        ]
        outdict = dict()
        for nodetype, nodelistid in nodetypes:
            nodelist = self.get(confsection + ":" + nodetype + nodelistid)
            if nodelist == "no_generic":
                noderanges = self.get(
                    confsection + ":" + nodetype + rangeid, None
                )
                if noderanges is None:
                    raise ValueError(
                        "when {0:s}{1:s} == no_generic, {0:s}{2:s} must be provided".format(
                            nodetype, nodelistid, rangeid
                        )
                    )
                nodebases = self.get(
                    confsection + ":" + nodetype + baseid,
                    self.inetname + nodetype + "{:d}",
                )
                outdict[nodetype] = list()
                for r, b in zip(noderanges.split("+"), nodebases.split("+")):
                    outdict[nodetype].extend(
                        [b.format(int(i)) for i in r.split(",")]
                    )
            else:
                outdict[nodetype] = nodelist.split(",")
        return outdict

    @property
    def specialnodesaliases(self):
        """Return the list of known aliases."""
        if self._sepcialnodesaliases is None:
            confsection = "generic_nodes"
            confoptions = self.options(confsection)
            aliases_re = re.compile(r"(\w+)(aliases)")
            nodetypes = [
                (m.group(1), m.group(2))
                for m in [aliases_re.match(k) for k in confoptions]
                if m is not None
            ]
            rdict = {
                ntype: self.get(confsection + ":" + ntype + key, "").split(",")
                for ntype, key in nodetypes
            }
            self._sepcialnodesaliases = rdict
        return self._sepcialnodesaliases

    @property
    def specialnodes(self):
        """
        Returns a dictionary that contains the list of nodes for a given
        node-type.
        """
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
            self._specialproxies = self._init_supernodes(
                self._re_proxies_property, "proxiesrange", "proxiesbase"
            )
            for nodetype, nodelist in self.specialnodes.items():
                if nodetype not in self._specialproxies:
                    self._specialproxies[nodetype] = nodelist
            for ntype, aliases in self.specialnodesaliases.items():
                for alias in aliases:
                    self._specialproxies[alias] = self._specialproxies[ntype]
        return self._specialproxies

    @secure_getattr
    def __getattr__(self, key):
        """Create attributes on the fly.

        * XXXnodes: returns the list of nodes for a given node-type
            (e.g loginnodes). If the XXX node-type is not defined in the
            configuration file, it returns an empty list.
        * XXXproxies: returns the list of proxy nodes for a given node-type
            (e.g loginproxies). If the XXX node-type is not defined in the
            configuration file, it returns an empty list.
        * isXXXnode: Return True if the current host is of XXX node-type.
            If the XXX node-type is not defined in the configuration file,
            it returns True.

        """
        kmatch = self._re_nodes_property.match(key)
        if kmatch is not None:
            return fp.stdtypes.FPList(
                self.specialnodes.get(kmatch.group(1), [])
            )
        kmatch = self._re_proxies_property.match(key)
        if kmatch is not None:
            return fp.stdtypes.FPList(
                self.specialproxies.get(kmatch.group(1), [])
            )
        kmatch = self._re_isnode_property.match(key)
        if kmatch is not None:
            return (kmatch.group(1) not in self.specialnodes) or any(
                [
                    self.hostname.startswith(s)
                    for s in self.specialnodes[kmatch.group(1)]
                ]
            )
        raise AttributeError('The key "{:s}" does not exist.'.format(key))

    @property
    def ftraw_default(self):
        """The default value for the System object ftraw attribute."""
        return "ftraw" in self.specialnodes and any(
            [self.hostname.startswith(s) for s in self.specialnodes["ftraw"]]
        )


class LocalTarget(Target):
    """A very generic class usable for most computers."""

    _footprint = dict(
        info="Nice local target",
        attr=dict(
            sysname=dict(values=["Linux", "Darwin", "Local", "Localhost"]),
        ),
    )


# Disable priority warnings on the target collector
fcollect = fp.collectors.get(tag="target")
fcollect.non_ambiguous_loglevel = logging.DEBUG
del fcollect
