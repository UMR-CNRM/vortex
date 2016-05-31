#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex import sessions
from vortex.tools import env
from vortex.tools.date import Time, Date
from vortex.data.outflow import ModelResource, NoDateResource
from vortex.data.contents import AlmostDictContent, IndexedTable
from vortex.syntax.stdattrs import binaries, term, cutoff
from gco.syntax.stdattrs import GenvKey


class NamelistContentError(ValueError):
    pass


class NamelistContent(AlmostDictContent):
    """Fortran namelist including namelist blocks."""

    def __init__(self, **kw):
        """
        Initialize default namelist content with optional parameters:
          * macros : pre-defined macros for all namelist blocks
          * remove : elements to remove from the contents
          * parser : a namelist parser object (a default one will be built otherwise)
          * automkblock : give automaticaly a name to new blocks when not provided
          * namblockcls : class for new blocks
        """
        kw.setdefault('macros', dict(
            NPROC     = None,
            NBPROC    = None,
            NBPROC_IO = None,
            NCPROC    = None,
            NDPROC    = None,
            NBPROCIN  = None,
            NBPROCOUT = None,
            IDAT      = None,
            CEXP      = None,
            TIMESTEP  = None,
            FCSTOP    = None,
            NMODVAL   = None,
            NBE       = None,
            SEED      = None,
            MEMBER    = None,
            NUMOD     = None,
        ))
        kw.setdefault('remove', set())
        kw.setdefault('parser', None)
        kw.setdefault('automkblock', 0)
        if 'namblockcls' not in kw:
            import vortex.tools.fortran
            kw['namblockcls'] = vortex.tools.fortran.NamelistBlock
        super(NamelistContent, self).__init__(**kw)

    def add(self, addlist):
        """Add namelist blocks to current contents."""
        for nam in filter(lambda x: x.isinstance(self._namblockcls), addlist):
            self._data[nam.name] = nam

    def toremove(self, bname):
        """Add an entry to the list of blocks to be removed."""
        self._remove.add(bname)

    def rmblocks(self):
        """Returns the list of blocks to get rid off."""
        return self._remove

    def newblock(self, name=None):
        """Construct a new block."""
        if name is None:
            self._automkblock += 1
            name = 'AUTOBLOCK{0:03d}'.format(self._automkblock)
        if name not in self._data:
            self._data[name] = self._namblockcls(name=name)
        return self._data[name]

    def macros(self):
        """Returns the dictionary of macros already registered."""
        return self._macros.copy()

    def setmacro(self, item, value):
        """Set macro value for further substitution."""
        for namblock in filter(lambda x: item in x.macros(), self.values()):
            namblock.addmacro(item, value)
        self._macros[item] = value

    def dumps(self):
        """Returns the namelist contents as a string."""
        return ''.join([ self.get(x).dumps() for x in sorted(self.keys()) ])

    def merge(self, delta, rmkeys=None, rmblocks=None, clblocks=None):
        """Merge of the current namelist content with the set of namelist blocks provided."""
        for namblock in delta.values():
            if namblock.name in self:
                self[namblock.name].merge(namblock)
            else:
                newblock = self._namblockcls(name=namblock.name)
                for dk in namblock.keys():
                    newblock[dk] = namblock[dk]
                self[namblock.name] = newblock
        if rmblocks is None and hasattr(delta, 'rmblocks'):
            rmblocks = delta.rmblocks()
        if rmblocks is not None:
            for item in [ x for x in rmblocks if x in self ]:
                del self[item]
        if clblocks is not None:
            for item in [ x for x in clblocks if x in self ]:
                self[item].clear()
        if rmkeys is not None:
            for item in self:
                self[item].clear(rmkeys)

    def slurp(self, container):
        """Get data from the ``container`` namelist."""
        container.rewind()
        if not self._parser:
            import vortex.tools.fortran
            self._parser = vortex.tools.fortran.NamelistParser(macros=self._macros.keys())
        namset = self._parser.parse(container.read())
        if namset:
            self._data = namset.as_dict()
        else:
            raise NamelistContentError('Could not parse container contents')

    def rewrite(self, container):
        """Write the namelist contents in the specified container."""
        container.close()
        container.write(self.dumps())
        container.close()


class Namelist(ModelResource):
    """
    Class for all kinds of namelists
    """
    _footprint = dict(
        info = 'Namelist from binary pack',
        attr = dict(
            kind = dict(
                values   = ['namelist']
            ),
            clscontents = dict(
                default  = NamelistContent
            ),
            gvar = dict(
                type = GenvKey,
                optional = True,
                values   = ['NAMELIST_' + x.upper() for x in binaries],
                default  = 'namelist_[binary]'
            ),
            source = dict(
                optional = True,
                default  = 'namel_[binary]',
            ),
            model = dict(
                optional = True,
            ),
            binary = dict(
                optional = True,
                values   = binaries,
                default  = '[model]',
            ),
            date = dict(
                type     = Date,
                optional = True,
            )
        )
    )

    @property
    def realkind(self):
        return 'namelist'

    def _find_source(self):
        sources = self.source.split('|')
        if len(sources) == 1:
            source = sources[0].split(':')[0]
        else:
            # Check that the date argument was provided.:
            if self.date is None:
                raise AttributeError('The date argument should be provided when dealing ' +
                                     'with time based namelist sources.')
            datedSource = {}
            for s in sources:
                dateNsource = s.split(':')
                if dateNsource[0]:
                    if len(dateNsource) == 2:
                        date = Date(dateNsource[1], year = self.date.year)
                    else:
                        date = Date(self.date.year, 1, 1)
                    if date not in datedSource.keys():
                        datedSource[date] = dateNsource[0]
                    else:
                        logger.warning('%s already begins the %s, %s is ignored.',
                                       datedSource[date],
                                       date.strftime('%d of %b.'), dateNsource[0])
            datedSource = sorted(datedSource.iteritems(), reverse=True)
            source = datedSource[0][1]
            for dateNsource in datedSource:
                if self.date >= dateNsource[0]:
                    source = dateNsource[1]
                    break
            logger.info('The consistent source is %s', source)

        return source

    def gget_urlquery(self):
        """GGET specific query : ``extract``."""
        return 'extract=' + self._find_source()


class NamelistUtil(Namelist):
    """
    Class for namelists utilities
    """
    _footprint = dict(
        info = 'Namelist from utilities pack',
        attr = dict(
            kind = dict(
                values   = ['namelist_util', 'namutil'],
                remap    = dict(namelist_util = 'namutil'),
            ),
            gvar = dict(
                values   = ['NAMELIST_UTILITIES'],
                default  = 'namelist_utilities'
            ),
            binary = dict(
                values   = ['batodb', 'utilities', 'odbtools'],
                default  = 'utilities',
                optional = True,
            ),
        )
    )


class NamelistTerm(Namelist):
    """
    Class for all the terms dependent namelists
    """
    _footprint = [
        term,
        dict(
            info = 'Terms dependent namelist',
            attr = dict(
                kind = dict(
                    values = ['namterm']
                )
            )
        )
    ]

    def incoming_xxt_fixup(self, attr, key=None, prefix=None):
        """Fix as best as possible the ``xxt.def`` file."""

        regex = re.compile(r',(.*)$')
        myenv = env.current()
        suffix = regex.search(myenv.VORTEX_XXT_DEF)
        if suffix:
            fp = suffix.group(1)
        else:
            fp = None

        try:
            with open('xxt.def', 'r') as f:
                lines = f.readlines()
        except IOError:
            logger.error('Could not open file xxt.def')
            raise

        select = lines[self.term.hour].split()[2]

        if not re.match(r'undef', select):
            if fp:
                rgx = re.compile(key + r'(.*)$')
                sfx = rgx.search(select)
                if sfx:
                    s = sfx.group(1)
                else:
                    s = ''
                return ''.join((key, '_', fp, s))
            else:
                return select
        else:
            logger.error('Fullpos namelist id not defined for term %s', self.term)

    def incoming_namelist_fixup(self, attr, key=None):
        """Fix as best as possible the namelist term extensions."""

        val = getattr(self, attr)
        r1 = re.compile(r'^(.*\/)?(' + key + r'.*_fp|cpl)$')
        r2 = re.compile(r'^(.*\/)?(' + key + r'.*_fp)(\..*)$')
        r3 = re.compile(r'^(.*\/)?(' + key + r'.*_p)$')

        fixed = 0

        for r in (r1, r2, r3):
            s = r.search(val)
            if s:
                fixed = 1
                ( dirpath, base ) = (s.group(1), s.group(2))
                if dirpath is None:
                    dirpath = ''
                ext = ''
                if r == r3:
                    if self.term.hour == 0:
                        p = '0'
                    elif self.term.hour % 6 == 0:
                        p = '6'
                    elif self.term.hour % 3 == 0:
                        p = '3'
                    else:
                        p = '1'
                else:
                    if self.term.hour == 0:
                        p = '0'
                    else:
                        p = ''
                    if r == r2:
                        ext = s.group(3)
                        if ext is None:
                            ext = ''

        if fixed:
            return dirpath + base + p + ext
        else:
            return val


class NamelistSelect(NamelistTerm):
    """
    Class for the select namelists
    """
    _footprint = [
        dict(
            info = 'Select namelist for fullpos ',
            attr = dict(
                kind = dict(
                    values = [ 'namselect' ]
                )
            )
        )
    ]

    @property
    def realkind(self):
        return 'namselect'

    def gget_urlquery(self):
        """GGET specific query : ``extract``."""
        myenv = env.current()
        if myenv.true('VORTEX_XXT_DEF'):
            return 'extract=' + self.incoming_xxt_fixup('source', 'select')
        else:
            return 'extract=' + self.incoming_namelist_fixup('source', 'select')


class NamelistFullPos(NamelistTerm):
    """
    Class for the fullpos term dependent namelists
    """
    _footprint = [
        dict(
            info = 'Namelist for offline fullpos ',
            attr = dict(
                kind = dict(
                    values = [ 'namelistfp' ]
                )
            )
        )
    ]

    @property
    def realkind(self):
        return 'namelistfp'

    def gget_urlquery(self):
        """GGET specific query : ``extract``."""
        return 'extract=' + self.incoming_namelist_fixup('source', 'namel')


class XXTContent(IndexedTable):
    """Indexed table of selection namelist used by inlined fullpos forecasts."""

    def __init__(self, *kargs, **kwargs):
        super(XXTContent, self).__init__(*kargs, **kwargs)
        self._cachedomains = None
        self._cachedomains_term = None

    def fmtkey(self, key):
        """Reshape entry keys of the internal dictionary as a :class:`~vortex.tools.date.Time` value."""
        key = Time(key)
        return key.fmthm

    def xxtpos(self, n, g, x):
        """
        Return value in position ``n`` for the ``term`` occurence defined in ``g`` or ``x``.
          * ``g`` stands for a guess dictionary.
          * ``x`` stands for an extra dictionary.

        These naming convention refer to the footprints resolve mechanism.
        """
        t = g.get('term', x.get('term', None))
        if t is None:
            return None
        else:
            value = None
            tkey = self.get(t.fmthm, self.get(str(t.hour), None))
            if tkey is not None:
                try:
                    value = tkey[n]
                except IndexError:
                    return None
            return value

    def xxtnam(self, g, x):
        """Return local namelist filename according to first column."""
        return self.xxtpos(0, g, x)

    def xxtsrc(self, g, x):
        """Return local namelist source in gco set according to second column."""
        return self.xxtpos(1, g, x)

    def mapdomains(self, maxterm=None):
        """Return a map of domains associated for each term in selection namelists."""
        mapdom = dict()
        allterms = sorted([ Time(x) for x in self.keys() ])
        if maxterm is None:
            if allterms:
                maxterm = allterms[-1]
            else:
                maxterm = -1
        maxterm = Time(maxterm)

        if (self._cachedomains is None) or (self._cachedomains_term != maxterm):

            import vortex.tools.fortran

            select_seen = dict()
            for term in [ x for x in allterms if x <= maxterm ]:
                tvalue = self.get(term.fmthm, self.get(str(term.hour), None))
                sh = sessions.system()
                if tvalue[0] is not None and sh.path.exists(tvalue[0]):
                    # Do not waste time on duplicated selects...
                    if tvalue[1] not in select_seen:
                        fortp = vortex.tools.fortran.NamelistParser()
                        with open(tvalue[0], 'r') as fd:
                            xx = fortp.parse(fd.read())
                        domains = set()
                        for nb in xx.values():
                            for domlist in [ y for x, y in nb.iteritems() if x.startswith('CLD') ]:
                                domains = domains | set(domlist.pop().split(':'))
                        select_seen[tvalue[1]] = domains
                    else:
                        domains = select_seen[tvalue[1]]
                    mapdom[term.fmthm] = list(domains)
                    if term.minute == 0:
                        mapdom[str(term.hour)] = list(domains)

            self._cachedomains_term = maxterm
            self._cachedomains = mapdom

        else:
            mapdom = self._cachedomains

        return dict(term=mapdom)


class NamelistSelectDef(NoDateResource):
    """Utility, so-called xxt file."""
    _footprint = [
        cutoff,
        dict(
            info = 'xxt.def file from namelist pack',
            attr = dict(
                gvar = dict(
                    type = GenvKey,
                    optional = True,
                    values = ['NAMELIST_' + x.upper() for x in binaries],
                    default = 'namelist_[binary]'
                ),
                source = dict(
                    optional = True,
                ),
                binary = dict(
                    optional = True,
                    values = binaries,
                    default = '[model]',
                ),
                kind = dict(
                    values = [ 'xxtdef', 'namselectdef' ]
                ),
                clscontents = dict(
                    default = XXTContent
                )
            ),
            bind = ['gvar', 'source']
        )
    ]

    _source_map = dict(assim='xxt.def.assim', )

    @property
    def realkind(self):
        return 'namselectdef'

    def gget_urlquery(self):
        """GGET specific query : ``extract``."""
        if self.source is None:
            thesource = self._source_map.get(self.cutoff, 'xxt.def')
        else:
            thesource = self.source
        return 'extract=' + thesource
