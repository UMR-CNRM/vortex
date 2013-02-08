#!/bin/env python
# -*- coding: utf-8 -*-

r"""
First version of command line dispatcher.
Mainly for demonstration purpose ?
"""

import logging, re
from vortex import toolbox
from vortex.syntax import footprint
from vortex.utilities import catalogs, dumper, trackers
from vortex.data.geometries import SpectralGeometry, GridGeometry
from vortex import data, algo, tools

#: No automatic export
__all__ = []

class Dispatcher(object):

    def __init__(self, **kw):
        self.__dict__.update(kw)
        logging.debug('Dispatcher init %s', self)

    # Internal tools

    def _objectslist(self, objs):
        return "\n".join(sorted([str(x) for x in objs]))

    # Interactive sessions

    def help(self, t, kw):
        """
        Print documentation for all or specified methods of the current shell dispatcher.
        """
        methods = sorted(filter(lambda x: not x.startswith('_'), self.__class__.__dict__.keys()))
        if kw:
            strdocs = list()
            for fm in sorted(filter(lambda x: x in methods, kw.keys())):
                fdoc = getattr(self, fm).__doc__
                if not fdoc:
                    fdoc = 'Not documented yet.'
                strdocs.append('{0:s}: {1:s}'.format(fm, fdoc))
            return (0, "\n".join(strdocs), strdocs)
        else:
            alldoc = dict()
            for fm in methods:
                alldoc[fm] = True
            return self.help(t, alldoc)

    def functions(self, t, kw):
        """
        Print list of available functions in this current shell dispatcher.
        """
        methods = sorted(filter(lambda x: not x.startswith('_'), self.__class__.__dict__.keys()))
        return (0, ' '.join(methods), methods)

    def default(self, t, kw):
        """
        Print / Return the actual arguments.
        """
        if kw:
            rmsg = str(kw)
        else:
            rmsg = 'Ok'
        return (0, rmsg, kw)

    def id(self, t, kw):
        """
        Print current session identification card.
        Return the id number of the session.
        """
        return (0, t.idcard(), id(t))

    def pwd(self, t, kw):
        """
        Print the current working directory of the daemon.
        Return the same value.
        """
        return (0, t.system().pwd, t.system().pwd)

    def sleep(self, t, kw):
        """
        Print nothing.
        Return the elapsed time.
        """
        ts = int(kw.get('time', 1))
        t.system().sleep(ts)
        return (0, 'Done...', ts)

    def daemons(self, t, kw):
        """
        Print the list of current active vortex dispatchers.
        Return this list.
        """
        system = t.system()
        psall = system.ps(opts=['-u', system.env.LOGNAME], search='python.*vortexd')
        psfmt = '{0:16s} {1:24s} {2:32s}'
        psd = [ psfmt.format('USER', 'FIFOTAG', 'FIFODIR') ]
        psr = []
        bl = re.compile('\s+')
        for ps in psall:
            items = bl.split(ps)
            psr.append((items[0], items[-2], items[-1]))
            psd.append(psfmt.format(items[0], items[-2], items[-1]))
        return (0, "\n".join(psd), psr)

    def session(self, t, kw):
        """
        Print current session tag.
        Return current session.
        """
        return (0, t.tag, t)

    def env(self, t, kw):
        """
        Print environment associated to current session.
        Return current tied environment.
        """
        if 'dump' in kw and kw['dump'] == True:
            info = t.env.mydump()
        else:
            info = [ str(t.env) ]
        return (0, "\n".join(info), t.env)

    def setenv(self, t, kw):
        """
        Print actual value of the environment variable defined.
        Return this value.
        """
        info = list()
        for x in kw:
            if kw[x] == None:
                if x in t.env: del t.env[x]
            else:
                t.env[x] = kw[x]
                x = x.upper()
                info.append(x + '=' + t.env.native(x))
        return (0, "\n".join(info), t.env)

    def echo(self, t, kw):
        """
        Print a string version of the specified elements.
        Return <None>.
        """
        info = map(lambda x: x + ': ' + str(kw[x]), sorted(kw.keys()))
        return (0, "\n".join(info), None)

    def attributes(self, t, kw):
        """
        Print the attributes contents of the specified elements.
        Return <None>.
        """
        info = map(
            lambda x: x + ': ' + str(
                sorted(
                    filter(
                        lambda k: not k.startswith('_'),
                        getattr(kw[x], '_attributes', getattr(kw[x], '__dict__')).keys()
                    )
                )
            ),
            sorted(filter(lambda x: hasattr(kw[x], '_attributes') or hasattr(kw[x], '__dict__'), kw.keys()))
        )
        return (0, "\n".join(info), None)

    def mload(self, t, kw):
        """
        Print / Return the results of the import on the specified modules.
        """
        loaded = list()
        for modname in kw.keys():
            loaded.append(__import__(modname, globals(), locals(), [], 0))
        return (0, str(loaded), loaded)

    # Glove information

    def glove(self, t, kw):
        """
        Display current glove id.
        Return the glove itself.
        """
        return(0, t.glove.idcard(), t.glove)

    def user(self, t, kw):
        """
        Shortcut to glove's username.
        """
        return(0, t.glove.user, t.glove.user)

    def vapp(self, t, kw):
        """
        Print or set current <vapp> value.
        Return actual vapp.
        """
        if 'value' in kw:
            t.glove.setvapp(app=kw['value'])
        return (0, t.glove.vapp, t.glove.vapp)

    def vconf(self, t, kw):
        """
        Print or set current <vconf> value according to <value> argument.
        Return actual vconf.
        """
        if 'value' in kw:
            t.glove.setvconf(conf=kw['value'])
        return (0, t.glove.vconf, t.glove.vconf)

    # Footprint interface

    def envfp(self, t, kw):
        """
        Set and print the current default footprint values.
        Result current <fpenv> object.
        """
        fpenv = footprint.envfp(**kw)
        return (0, str(fpenv()), fpenv)

    def rmfp(self, t, kw):
        """
        Remove from current default footprint the specified keys.
        Return the list of removed keys.
        """
        fpenv = footprint.envfp()
        removed = list()
        for item in kw.keys():
            if item in fpenv:
                del fpenv[item]
                removed.append(item)
        return (0, str(removed), removed)


    # Explicit action on objects

    def apply(self, t, kw):
        """
        Get <attr> or apply <method> on the <with> object.
        Return this value.
        """
        if 'with' in kw:
            obj = kw['with']
            del kw['with']
        else:
            return (1, 'No object specified', None)
        if 'attr' in kw:
            rattr = getattr(obj, kw['attr'], None)
            return (0, str(rattr), rattr)
        if 'method' in kw:
            rattr = getattr(obj, kw['method'], None)
            if callable(rattr):
                args = kw.setdefault('args', False)
                if args:
                    del kw['args']
                    del kw['method']
                    info = rattr(kw)
                else:
                    info = rattr()
                return (0, str(info), info)
            else:
                return (2, kw['method'] + ' is not a callable method', None)

    def item(self, t, kw):
        """
        Extract from an object specified through the <from> argument
        either a <key> or <idx> entry. Return this entry.
        """
        if 'from' in kw:
            obj = kw['from']
            del kw['from']
        else:
            return (1, 'No dict or iterable specified', None)
        if 'idx' in kw:
            return (0, str(obj[int(kw['idx'])]), obj[int(kw['idx'])])
        elif 'key' in kw:
            return (0, str(obj[kw['key']]), obj[kw['key']])
        else:
            return (1, 'No idx or key specified', None)

    def call(self, t, kw):
        """
        Display and return the output of the call on objects provided,
        as long as they are callable.
        """
        if 'from' in kw:
            obj = kw['from']
            del kw['from']
        else:
            obj = None
        if callable(obj):
            info = obj(**kw)
            return (0, str(info), info)
        else:
            return (2, 'Object not callable', None)

    def nice(self, t, kw):
        """
        Data dumper on any key/value.
        Nothing to return.
        """
        strdumps = list()
        for k, v in kw.iteritems():
            strdumps.append('  ' + k + ':')
            strdumps.append(dumper.nicedump(v))
        return (0, "\n".join(strdumps), None)


    # Catalogs

    def catalogs(self, t, kw):
        """
        Return current entries in catalogs table.
        """
        tc = catalogs.table().keys()
        return(0, str(tc), tc)

    def refill(self, t, kw):
        """
        Refill the specified catalogs already in the calatogs table.
        Return the actual number of items.
        """
        refilled = list()
        ctable = catalogs.table()
        select = kw.keys()
        if not select:
            select = catalogs.autocatlist()
        for item in sorted(select):
            if item in ctable:
                refilled.append(item + ': ' + str(catalogs.fromtable(item).refill()))
            else:
                refilled.append(item + ': ' + str(len(catalogs.autocatload(kind=item))))
        return(0, "\n".join(refilled), len(refilled))

    def namespaces(self, t, kw):
        """
        Display the range of names defined as values for ``namespace`` or ``netloc`` attributes.
        Optional arguments are ``only`` and ``match``.
        Return the associated dictionary.
        """
        ns = toolbox.namespaces(**kw)
        strns = list()
        for k,v in ns.iteritems():
            strns.append('  {0:20s} {1:s}'.format(k, str(v)))
        return(0, "\n".join(sorted(strns)), ns)

    def containers(self, t, kw):
        """
        Display containers catalog contents.
        Return the catalog itself.
        """
        cat = data.containers.catalog()
        return (0, self._objectslist(cat()), cat)

    def providers(self, t, kw):
        """
        Display providers catalog contents.
        Return the catalog itself.
        """
        cat = data.providers.catalog()
        return (0, self._objectslist(cat()), cat)

    def resources(self, t, kw):
        """
        Display resources catalog contents.
        Return the catalog itself.
        """
        cat = data.resources.catalog()
        return (0, self._objectslist(cat()), cat)

    def stores(self, t, kw):
        """
        Display stores catalog contents.
        Return the catalog itself.
        """
        cat = data.stores.catalog()
        return (0, self._objectslist(cat()), cat)

    def components(self, t, kw):
        """
        Display algo components catalog contents.
        Return the catalog itself.
        """
        cat = algo.components.catalog()
        return (0, self._objectslist(cat()), cat)

    def mpitools(self, t, kw):
        """
        Display mpitools catalog contents.
        Return the catalog itself.
        """
        cat = algo.mpitools.catalog()
        return (0, self._objectslist(cat()), cat)

    def systems(self, t, kw):
        """
        Display systems catalog contents.
        Return the catalog itself.
        """
        cat = tools.systems.catalog()
        return (0, self._objectslist(cat()), cat)

    def services(self, t, kw):
        """
        Display services catalog contents.
        Return the catalog itself.
        """
        cat = tools.services.catalog()
        return (0, self._objectslist(cat()), cat)

    def trackers(self, t, kw):
        """
        Display the tagged references to internal trackers table.
        Return a shallow copy of the table itself.
        """
        info = trackers.tracktable()
        return (0, str(info), info)

    def trackfp(self, t, kw):
        """
        Display a complete dump of the footprint resolution tracker.
        Return nothing.
        """
        info = trackers.tracker(tag='fpresolve').alldump()
        return (0, str(info), None)


    # shortcuts to load commands

    def container(self, t, kw):
        """
        Load a container object according to description.
        Return the object itself.
        """
        info = data.containers.load(**kw)
        return (0, str(info), info)

    def provider(self, t, kw):
        """
        Load a provider object according to description.
        Return the object itself.
        """
        info = data.providers.load(**kw)
        return (0, str(info), info)

    def resource(self, t, kw):
        """
        Load a resource object according to description.
        Return the object itself.
        """
        info = data.resources.load(**kw)
        return (0, str(info), info)

    def store(self, t, kw):
        """
        Load a store object according to description.
        Return the object itself.
        """
        info = data.stores.load(**kw)
        return (0, str(info), info)

    def component(self, t, kw):
        """
        Load an algo component object according to description.
        Return the object itself.
        """
        info = algo.components.load(**kw)
        return (0, str(info), info)

    def mpitool(self, t, kw):
        """
        Load a mpitool object according to description.
        Return the object itself.
        """
        info = algo.mpitools.load(**kw)
        return (0, str(info), info)

    def system(self, t, kw):
        """
        Load a system object according to description.
        Return the object itself.
        """
        info = tools.systems.load(**kw)
        return (0, str(info), info)

    def service(self, t, kw):
        """
        Load a service object according to description.
        Return the object itself.
        """
        info = tools.services.load(**kw)
        return (0, str(info), info)


    # Direct resources access

    def spectral(self, t, kw):
        """
        Instanciate a SpectralGeometry with specified attributes.
        Return the new object.
        """
        info = SpectralGeometry(**kw)
        return (0, str(info), info)

    def grid(self, t, kw):
        """
        Instanciate a GridGeometry with specified attributes.
        Return the new object.
        """
        info = GridGeometry(**kw)
        return (0, str(info), info)

    def handler(self, t, kw):
        """
        Perform a toolbox.rh call with current attributes.
        Return the resource handler.
        """
        info = toolbox.rh(kw)
        if info:
            return (0, info.idcard(), info)
        else:
            return (1, 'No handler defined', None)

    def locate(self, t, kw):
        """
        Load a resource handler and apply the <locate> method.
        Return this information.
        """
        rh = toolbox.rh(kw)
        if rh:
            info = rh.locate()
            return (0, str(info), info)
        else:
            return (1, 'None', None)

    def get(self, t, kw):
        """
        Perform a toolbox.rget call with current attributes.
        Return the resource handler.
        """
        info = filter(lambda x: x.complete, toolbox.rget(kw))
        return (0, "\n".join(map(lambda x: x.strlast(), info)), info)

    def put(self, t, kw):
        """
        Perform a toolbox.rput call with current attributes.
        Return the resource handler.
        """
        info = filter(lambda x: x.complete, toolbox.rput(kw))
        return (0, "\n".join(map(lambda x: x.strlast(), info)), info)

    def dblput(self, t, kw):
        """
        Perform a "double" put : the first one is a true "physical" put,
        the second one is an hard link to the location given by the <dblp> provider.
        Therefore a valid <dbl> parameter is mandatory.
        Return the resource handler.
        """
        if 'dblp' not in kw:
            return (1, 'No double provider specified', None)
        dblprovider = kw['dblp']
        del kw['dblp']
        if not dblprovider:
            return (1, 'Invalid provider', None)
        info = filter(lambda x: x.complete, toolbox.rload(kw))
        rc = 0
        display = list()
        if info:
            for rh in info:
                if rh.put():
                    actualstorage = rh.locate()
                    logging.info('DBLPUT p1 = %s / loc = %s', rh.provider, actualstorage)
                    actualprovider = rh.provider
                    rh.provider = dblprovider
                    doublestorage = rh.locate()
                    logging.info('DBLPUT p2 = %s / loc = %s', rh.provider, doublestorage)
                    rh.provider = actualprovider
                    if doublestorage:
                        system = t.system()
                        system.remove(doublestorage)
                        system.filecocoon(doublestorage)
                        system.link(actualstorage, doublestorage)
                        display.extend([actualstorage, '  -> ' + doublestorage])
                else:
                    logging.warning('DBLPUT could not store main resource %s', rh)
                    display.extend('Could not put ' + str(rh), rh.idcard())
                    rc = 1
        else:
            display.append('No resource handler matching the description')
            rc = 1
        return (rc, "\n".join(display), info)
