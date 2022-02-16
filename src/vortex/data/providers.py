# -*- coding: utf-8 -*-

"""
Abstract and generic classes provider for any "Provider". "Provider" objects,
describe where are stored the data.

Of course, the :class:`Vortex` abstract provider is a must see. It has three
declinations depending on the experiment indentifier type.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import collections
import operator
import os.path
import re
from six.moves.urllib import parse as urlparse

from bronx.fancies import loggers
from bronx.syntax.parsing import StringDecoder
import footprints
from footprints import proxy as fpx

from vortex import sessions
from vortex.syntax.stdattrs import xpid, legacy_xpid, free_xpid, opsuites, \
    demosuites, scenario, member, block
from vortex.syntax.stdattrs import LegacyXPid, FreeXPid
from vortex.syntax.stdattrs import namespacefp, Namespace, FmtInt, DelayedEnvValue
from vortex.tools import net, names
from vortex.util.config import GenericConfigParser

#: No automatic export
__all__ = ['Provider']

logger = loggers.getLogger(__name__)


class Provider(footprints.FootprintBase):
    """Abstract class for any Provider."""

    _abstract = True
    _collector = ('provider',)
    _footprint = dict(
        info = 'Abstract root provider',
        attr = dict(
            vapp = dict(
                info        = "The application's identifier.",
                alias       = ('application',),
                optional    = True,
                default     = '[glove::vapp]',
                doc_zorder  = -10
            ),
            vconf = dict(
                info        = "The configuration's identifier.",
                alias       = ('configuration',),
                optional    = True,
                default     = '[glove::vconf]',
                doc_zorder  = -10
            ),
            username = dict(
                info     = "The username that will be used whenever necessary.",
                optional = True,
                default  = None,
                alias    = ('user', 'logname')
            ),
        ),
        fastkeys = set(['namespace', ]),
    )

    def __init__(self, *args, **kw):
        logger.debug('Abstract provider init %s', self.__class__)
        super(Provider, self).__init__(*args, **kw)

    def _str_more(self):
        """Additional information to print representation."""
        try:
            return 'namespace=\'{0:s}\''.format(self.namespace)
        except AttributeError:
            return super(Provider, self)._str_more()

    @property
    def realkind(self):
        return 'provider'

    def scheme(self, resource):
        """Abstract method."""
        pass

    def netloc(self, resource):
        """Abstract method."""
        pass

    def netuser_name(self, resource):  # @UnusedVariable
        """Abstract method."""
        return self.username

    def pathname(self, resource):
        """Abstract method."""
        pass

    def pathinfo(self, resource):
        """Delegates to resource eponym method."""
        return resource.pathinfo(self.realkind)

    def basename(self, resource):
        """Delegates to resource eponym method."""
        return resource.basename(self.realkind)

    def urlquery(self, resource):
        """Delegates to resource eponym method."""
        return resource.urlquery(self.realkind)

    def uri(self, resource):
        """
        Create an uri adapted to a vortex resource so as to allow the element
        in charge of retrieving the real resource to be able to locate and
        retreive it. The method used to achieve this action:

        * obtain the proto information,
        * ask for the netloc,
        * get the pathname,
        * get the basename.

        The different operations of the algorithm can be redefined by subclasses.
        """
        username = self.netuser_name(resource)
        fullnetloc = ('{:s}@{:s}'.format(username, self.netloc(resource)) if username
                      else self.netloc(resource))
        logger.debug(
            'scheme %s netloc %s normpath %s urlquery %s',
            self.scheme(resource),
            fullnetloc,
            os.path.normpath(self.pathname(resource) + '/' + self.basename(resource)),
            self.urlquery(resource)
        )

        return net.uriunparse((
            self.scheme(resource),
            fullnetloc,
            os.path.normpath(self.pathname(resource) + '/' + self.basename(resource)),
            None,
            self.urlquery(resource),
            None
        ))


class Magic(Provider):

    _footprint = [
        xpid,
        dict(
            info = 'Magic provider that always returns the same URI.',
            attr = dict(
                fake = dict(
                    info     = "Enable this magic provider.",
                    alias    = ('nowhere', 'noprovider'),
                    type     = bool,
                    optional = True,
                    default  = True,
                ),
                magic = dict(
                    info     = "The URI returned by this provider."
                ),
                experiment = dict(
                    optional = True,
                    doc_visibility  = footprints.doc.visibility.ADVANCED,
                ),
                vapp = dict(
                    doc_visibility  = footprints.doc.visibility.GURU,
                ),
                vconf = dict(
                    doc_visibility  = footprints.doc.visibility.GURU,
                ),
            ),
            fastkeys = set(['magic', ]),
        )
    ]

    @property
    def realkind(self):
        return 'magic'

    def uri(self, resource):
        """URI is supposed to be the magic value !"""
        return self.magic


class Remote(Provider):

    _footprint = dict(
        info = 'Provider that manipulates data given a real path',
        attr = dict(
            remote = dict(
                info        = 'The path to the data.',
                alias       = ('remfile', 'rempath'),
                doc_zorder  = 50
            ),
            hostname = dict(
                info     = 'The hostname that holds the data.',
                optional = True,
                default  = 'localhost'
            ),
            tube = dict(
                info     = "The protocol used to access the data.",
                optional = True,
                values   = ['scp', 'ftp', 'rcp', 'file', 'symlink'],
                default  = 'file',
            ),
            vapp = dict(
                doc_visibility  = footprints.doc.visibility.GURU,
            ),
            vconf = dict(
                doc_visibility  = footprints.doc.visibility.GURU,
            ),
        ),
        fastkeys = set(['remote', ]),
    )

    def __init__(self, *args, **kw):
        logger.debug('Remote provider init %s', self.__class__)
        super(Remote, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'remote'

    def _str_more(self):
        """Additional information to print representation."""
        return 'path=\'{0:s}\''.format(self.remote)

    def scheme(self, resource):
        """The Remote scheme is its tube."""
        return self.tube

    def netloc(self, resource):
        """Fully qualified network location."""
        return self.hostname

    def pathname(self, resource):
        """OS dirname of the ``remote`` attribute."""
        return os.path.dirname(self.remote)

    def basename(self, resource):
        """OS basename of the ``remote`` attribute."""
        return os.path.basename(self.remote)

    def urlquery(self, resource):
        """Check for relative path or not."""
        if self.remote.startswith('/'):
            return None
        else:
            return 'relative=1'


class Vortex(Provider):
    """Main provider of the toolbox, using a fix-size path and a dedicated name factory."""

    _DEFAULT_NAME_BUILDER = names.VortexNameBuilder()
    _CUSTOM_NAME_BUILDERS = dict()

    _abstract = True
    _footprint = [
        block,
        member,
        scenario,
        namespacefp,
        xpid,
        dict(
            info = 'Vortex provider',
            attr = dict(
                member = dict(
                    type    = FmtInt,
                    args    = dict(fmt = '03'),
                ),
                namespace = dict(
                    values   = [
                        'vortex.cache.fr', 'vortex.archive.fr', 'vortex.multi.fr', 'vortex.stack.fr',
                        'open.cache.fr', 'open.archive.fr', 'open.multi.fr', 'open.stack.fr',
                    ],
                    default  = Namespace('vortex.cache.fr'),
                    remap    = {
                        'open.cache.fr': 'vortex.cache.fr',
                        'open.archive.fr': 'vortex.archive.fr',
                        'open.multi.fr': 'vortex.multi.fr',
                        'open.stack.fr': 'vortex.stack.fr',
                    }
                ),
                namebuild = dict(
                    info           = "The object responsible for building filenames.",
                    optional       = True,
                    doc_visibility = footprints.doc.visibility.ADVANCED,
                ),
                expected = dict(
                    info        = "Is the resource expected ?",
                    alias       = ('promised',),
                    type        = bool,
                    optional    = True,
                    default     = False,
                    doc_zorder  = -5,
                ),
                set_aside = dict(
                    info        = "Do we need to re-archive retrieve data somewhere else?",
                    optional    = True,
                    default     = DelayedEnvValue('VORTEX_PROVIDER_SET_ASIDE',
                                                  default='dict()'),
                    doc_visibility = footprints.doc.visibility.GURU,
                )
            ),
            fastkeys = set(['block', 'experiment']),
        )
    ]

    def __init__(self, *args, **kw):
        logger.debug('Vortex experiment provider init %s', self.__class__)
        super(Vortex, self).__init__(*args, **kw)
        if self.namebuild is not None:
            if self.namebuild not in self._CUSTOM_NAME_BUILDERS:
                builder = fpx.vortexnamebuilder(name=self.namebuild)
                if builder is None:
                    raise ValueError("The << {:s} >> name builder does not exists."
                                     .format(self.namebuild))
                self._CUSTOM_NAME_BUILDERS[self.namebuild] = builder
            self._namebuilder = self._CUSTOM_NAME_BUILDERS[self.namebuild]
        else:
            self._namebuilder = self._DEFAULT_NAME_BUILDER
        self._x_set_aside = None

    @property
    def namebuilder(self):
        return self._namebuilder

    @property
    def realkind(self):
        return 'vortex'

    def actual_experiment(self, resource):
        return self.experiment

    def _str_more(self):
        """Additional information to print representation."""
        try:
            return 'namespace=\'{0:s}\' block=\'{1:s}\''.format(self.namespace, self.block)
        except AttributeError:
            return super(Vortex, self)._str_more()

    def scheme(self, resource):
        """Default: ``vortex``."""
        return 'x' + self.realkind if self.expected else self.realkind

    def netloc(self, resource):
        """Returns the current ``namespace``."""
        return self.namespace.netloc

    def _pathname_info(self, resource):
        """Return all the necessary informations to build a pathname."""
        rinfo = resource.namebuilding_info()
        rinfo.update(
            vapp=self.vapp,
            vconf=self.vconf,
            experiment=self.actual_experiment(resource),
            block=self.block,
            member=self.member,
            scenario=self.scenario,
        )
        return rinfo

    def pathname(self, resource):
        """Constructs pathname of the ``resource`` according to :func:`namebuilding_info`."""
        return self.namebuilder.pack_pathname(self._pathname_info(resource))

    def basename(self, resource):
        """
        Constructs basename according to current ``namebuild`` factory
        and resource :func:`~vortex.data.resources.Resource.namebuilding_info`.
        """
        return self.namebuilder.pack_basename(resource.namebuilding_info())

    def urlquery(self, resource):
        """Construct the urlquery (taking into account stacked storage)."""
        s_urlquery = super(Vortex, self).urlquery(resource)
        if s_urlquery:
            uqs = urlparse.parse_qs(super(Vortex, self).urlquery(resource))
        else:
            uqs = dict()
        # Deal with stacked storage
        stackres, keepmember = resource.stackedstorage_resource()
        if stackres:
            stackpathinfo = self._pathname_info(stackres)
            stackpathinfo['block'] = 'stacks'
            if not keepmember:
                stackpathinfo['member'] = None
            uqs['stackpath'] = [(self.namebuilder.pack_pathname(stackpathinfo) + '/' +
                                 self.basename(stackres)), ]
            uqs['stackfmt'] = [stackres.nativefmt, ]
        # Deal with set_aside
        if self._x_set_aside is None:
            self._x_set_aside = StringDecoder()(self.set_aside)
            if not isinstance(self._x_set_aside, dict):
                logger.warning("setaside should decode as a dictionary (got '%s' that translate into '%s')",
                               self.set_aside, self._x_set_aside)
                self._x_set_aside = dict()
        if self.experiment in self._x_set_aside:
            provider_attrs = self.footprint_as_shallow_dict()
            provider_attrs['experiment'] = self._x_set_aside[self.experiment]
            provider_bis = fpx.provider(** provider_attrs)
            uqs['setaside_n'] = [provider_bis.netloc(resource), ]
            uqs['setaside_p'] = [provider_bis.pathname(resource) + '/' + provider_bis.basename(resource), ]
        return urlparse.urlencode(sorted(uqs.items()), doseq=True)


class VortexStd(Vortex):
    """Standard Vortex provider (any experiment with an Olive id)."""

    _footprint = [
        legacy_xpid,
        dict(
            info = 'Vortex provider for casual experiments with an Olive XPID',
            attr = dict(
                experiment = dict(
                    outcast = opsuites | demosuites,
                ),
            ),
        ),
    ]


class VortexFreeStd(Vortex):
    """Standard Vortex provider (any experiment with an user-defined id)."""

    _footprint = [
        free_xpid,
        dict(
            info = 'Vortex provider for casual experiments with a user-defined XPID',
            attr = dict(
                provider_global_config = dict(
                    info = 'The vortex free store global configuration file',
                    optional = True,
                    default = '@provider-vortex-free.ini',
                    doc_visibility = footprints.doc.visibility.GURU,
                ),
            ),
        ),
    ]

    _datastore_id = 'provider-vortex-free-conf'
    _redirect_section_re = re.compile(r'\s*(?P<xp>\S+)\s*(priority (?P<pri>-?\d+))?\s*$')
    _redirect_filter_re = re.compile(r'\s*(?P<key>\S+)_(?P<op>lt|le|eq|ne|gt|ge|in)\s*$')

    def __init__(self, *kargs, **kwargs):
        super(VortexFreeStd, self).__init__(*kargs, **kwargs)
        self._experiment_conf = None
        self._actual_experiment_cache = dict()

    @staticmethod
    def _get_remote_config(store, url, container):
        """Fetch a configuration file from **url** using **store**."""
        rc = store.get(url, container.iotarget(), dict(fmt='ascii'))
        if rc:
            return GenericConfigParser(inifile=container.iotarget())
        else:
            return None

    @property
    def experiment_conf(self):
        """Some configuration data for this specific experiment."""
        if self._experiment_conf is None:
            t = sessions.current()
            ds = t.datastore
            # Global config
            if ds.check(self._datastore_id, dict(conf_target=self.provider_global_config)):
                global_conf_stack = ds.get(self._datastore_id,
                                           dict(conf_target=self.provider_global_config))
            else:
                # Open the global configuration file
                global_conf = GenericConfigParser(inifile=self.provider_global_config)
                if global_conf.defaults():
                    raise ValueError('Global Defaults are not allowed in {:s}.'
                                     .format(self.provider_global_config))
                # Process it
                global_conf_stack = list()
                for section in global_conf.sections():
                    options = global_conf.options(section)
                    if not ('generic_restrict' in options and
                            'generic_uri' in options):
                        raise ValueError('Both generic_restrict and generic_uri are required in section {:s} of {:s}'
                                         .format(section, self.provider_global_config))
                    try:
                        restrict_re = re.compile(global_conf.get(section, 'generic_restrict'))
                    except re.error as e:
                        logger.error('The regex provided for "%s" does not compile !: "%s" (ignoring...).',
                                     section, str(e))
                        continue
                    uri = global_conf.get(section, 'generic_uri')
                    tg_uri = '{:s}_uri'.format(t.sh.default_target.inetname)
                    if tg_uri in options:
                        uri = global_conf.get(section, tg_uri)
                    global_conf_stack.append((restrict_re, uri))
                ds.insert(self._datastore_id,
                          dict(conf_target=self.provider_global_config),
                          global_conf_stack,
                          readonly=True)
            # Experiment specific configuration
            if ds.check(self._datastore_id, dict(conf_target=self.provider_global_config,
                                                 experiment=self.experiment)):
                self._experiment_conf = ds.get(self._datastore_id, dict(conf_target=self.provider_global_config,
                                                                        experiment=self.experiment))
            else:
                self._experiment_conf = collections.defaultdict(dict)
                conf_data = dict()
                # Is there actually a specific configuration for this experiment ?
                conf_uri = None
                for restrict_re, uri in global_conf_stack:
                    restrict_match = restrict_re.search(self.experiment)
                    if restrict_match:
                        for k, v in restrict_match.groupdict().items():
                            uri = uri.replace('{{' + k + '}}', v)
                        conf_uri = uri
                        break
                if conf_uri:
                    if ds.check(self._datastore_id, dict(conf_uri=conf_uri)):
                        conf_data = ds.get(self._datastore_id, dict(conf_uri=conf_uri))
                    else:
                        logger.info("Reading config file: %s (experiment=%s)", conf_uri, self.experiment)
                        url = net.uriparse(conf_uri)
                        tempstore = footprints.proxy.store(
                            scheme=url['scheme'],
                            netloc=url['netloc'],
                            storetrack=False,
                        )
                        retry = False
                        # First, try with a temporary ShouldFly
                        tempcontainer = footprints.proxy.container(shouldfly=True,
                                                                   incore=False)
                        remotecfg_parser = None
                        try:
                            remotecfg_parser = self._get_remote_config(tempstore, url, tempcontainer)
                        except (OSError, IOError):
                            # This may happen if the user has insufficient rights on
                            # the current directory
                            retry = True
                        finally:
                            t.sh.remove(tempcontainer.filename)
                        # Is retry needed ? This time a completely virtual file is used.
                        if retry:
                            remotecfg_parser = self._get_remote_config(tempstore, url,
                                                                       footprints.proxy.container(shouldfly=True,
                                                                                                  incore=True))
                        if remotecfg_parser is None:
                            raise OSError('The following remote configuration was not found: {!s}'
                                          .format(url))
                        else:
                            conf_data = remotecfg_parser.as_dict()
                # Does the configuration file contains relevant things ?
                section_prefix = self.experiment + ' redirection to '
                for k in conf_data.keys():
                    if k.startswith(self.experiment + ' redirection to '):
                        k_match = self._redirect_section_re.match(k[len(section_prefix):])
                        if k_match:
                            redirection_priority = int(k_match.group('pri')) if k_match.group('pri') else 0
                            redirection_to = None
                            try:
                                redirection_to = LegacyXPid(k_match.group('xp'))
                            except ValueError:
                                try:
                                    redirection_to = FreeXPid(k_match.group('xp'))
                                except ValueError:
                                    logger.error('Invalid experiment ID provided (section "%s" from "%s"). Ignoring',
                                                 k, conf_uri)
                            logger.debug('Valid configuration entry %s -> %s. Priority=%d',
                                         self.experiment, redirection_to, redirection_priority)
                            if redirection_to is not None:
                                self._experiment_conf[redirection_priority][redirection_to] = conf_data[k]
                        else:
                            logger.error('Malformed configuration entry (section: %s)', k)
                # Store the result for next time
                ds.insert(self._datastore_id, dict(conf_target=self.provider_global_config,
                                                   experiment=self.experiment),
                          self._experiment_conf, readonly=True)
        return self._experiment_conf

    def _match_experiment_xinfo(self, resource):
        """Resource/Provider characteristics."""
        rinfo = resource.namebuilding_info()
        rinfo_src = rinfo.get('src', None)
        if rinfo_src is not None:
            rinfo_src = [{'index{:d}'.format(i): v} for i, v in enumerate(rinfo_src)]
        xinfo = dict(
            radical=rinfo.get('radical', None),
            flow=rinfo.get('flow', None),
            src=rinfo_src,
            vapp=self.vapp,
            vconf=self.vconf,
            block=self.block,
            member=self.member,
            scenario=self.scenario,
        )
        return xinfo

    def _match_experiment_filter(self, r_filter, xinfo):
        """
        Compare the filter specified in a configuration section with the
        Resource/Provider characteristics.
        """
        # Actually compare r_filter to xinfo
        outcome = True
        for f_entry, f_value in r_filter.items():
            if not outcome:
                break
            f_entry_m = self._redirect_filter_re.match(f_entry)
            item_path = f_entry_m.group('key').split('@')
            item_path.reverse()
            item_value = xinfo.get(item_path[0], None)
            if len(item_path) > 1:
                for k in item_path[1:]:
                    found = None
                    if isinstance(item_value, dict):
                        found = item_value.get(k, None)
                    elif isinstance(item_value, list):
                        for subitem in item_value:
                            if k in subitem:
                                found = subitem[k]
                                break
                    item_value = found
                    if item_path is None:
                        break
            logger.debug('Item path: %s / Item value: %s / op: %s / expected: %s',
                         item_path, item_value, f_entry_m.group('op'), f_value)
            if item_value is None:
                outcome = False
            else:
                try:
                    if f_entry_m.group('op') == 'in':
                        outcome = outcome and (item_value in
                                               {type(item_value)(i.strip()) for i in f_value.split(',')})
                    else:
                        outcome = outcome and getattr(operator, f_entry_m.group('op'))(item_value,
                                                                                       type(item_value)(f_value))
                except (ValueError, TypeError):
                    outcome = False
        return outcome

    def actual_experiment(self, resource):
        """Remap the experiment id (for "special" experiments)."""
        if self.experiment_conf:
            if resource not in self._actual_experiment_cache:
                logger.debug('Starting actual_experiment lookup for resource: %s', resource)
                xinfo = self._match_experiment_xinfo(resource)
                for priority in sorted(self.experiment_conf.keys(), reverse=True):
                    for target in sorted(self.experiment_conf[priority].keys()):
                        logger.debug('Checking redirection to %s (priority=%d)', target, priority)
                        r_filter = self.experiment_conf[priority][target]
                        if not r_filter or self._match_experiment_filter(r_filter, xinfo):
                            self._actual_experiment_cache[resource] = target
                            break
                    if resource in self._actual_experiment_cache:
                        break
            if resource not in self._actual_experiment_cache:
                # Look up failed
                raise ValueError('Given the resource and provider attributes, no suitable configuration ' +
                                 'could be found.')
            return self._actual_experiment_cache[resource]
        else:
            return self.experiment

    def netloc(self, resource):
        """Find out the appropriate netloc (based on actual_experiment)."""
        actual_xp = self.actual_experiment(resource)
        if isinstance(actual_xp, LegacyXPid):
            return ('vsop.' + self.namespace.domain if actual_xp in opsuites
                    else self.namespace.netloc)
        else:
            return 'vortex-free.' + self.namespace.domain


class VortexOp(Vortex):
    """Standard Vortex provider (any experiment without an op id)."""

    _footprint = [
        legacy_xpid,
        dict(
            info = 'Vortex provider for op experiments',
            attr = dict(
                experiment = dict(
                    alias  = ('suite',),
                    values = opsuites,
                ),
            ),
        ),
    ]

    def netloc(self, resource):
        """Vortex Special OP scheme, aka VSOP !"""
        return 'vsop.' + self.namespace.domain


# Activate the footprint's fasttrack on the resources collector
fcollect = footprints.collectors.get(tag='provider')
fcollect.fasttrack = ('namespace', )
del fcollect
