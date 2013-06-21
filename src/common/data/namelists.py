#!/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re
from vortex.autolog import logdefault as logger
from vortex.tools import env
from vortex.tools.fortran import NamelistParser, NamelistBlock
from vortex.tools.date import Time
from vortex.data.outflow import ModelResource, NoDateResource
from vortex.data.contents import AlmostDictContent, IndexedTable
from vortex.syntax.stdattrs import binaries, term
from gco.syntax.stdattrs import GenvKey


class NamelistContent(AlmostDictContent):
    """Fortran namelist including namelist blocks."""

    def __init__(self, **kw):
        kw.setdefault('macros', dict(NBPROC = None))
        kw.setdefault('remove', set())
        kw.setdefault('parser', None)
        kw.setdefault('automkblock', 0)
        super(NamelistContent, self).__init__(**kw)

    def add(self, addlist):
        for nam in filter(lambda x: x.isinstance(NamelistBlock), addlist):
            self._data[nam.name] = nam

    def toremove(self, bname):
        """Add an entry to the list of blocks to be removed."""
        self._remove.add(bname)

    def rmblocks(self):
        """Returns the list of blocks to get rid off."""
        return self._remove

    def newblock(self, name=None):
        """Construct a new block."""
        if name == None:
            self._automkblock += 1
            name = 'AUTOBLOCK{0:03d}'.format(self._automkblock)
        if name not in self._data:
            self._data[name] = NamelistBlock(name=name)
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
                newblock = NamelistBlock(name=namblock.name)
                for dk in namblock.keys():
                    newblock[dk] = namblock[dk]
                self[namblock.name] = newblock
        if rmblocks == None and hasattr(delta, 'rmblocks'):
            rmblocks = delta.rmblocks()
        if rmblocks != None:
            for item in [ x for x in rmblocks if x in self ]:
                del self[item]
        if clblocks != None:
            for item in [ x for x in clblocks if x in self ]:
                self[item].clear()
        if rmkeys != None:
            for item in self:
                self[item].clear(rmkeys)

    def slurp(self, container):
        """Get data from the ``container`` namelist."""
        container.rewind()
        if not self._parser:
            self._parser = NamelistParser(macros=self._macros.keys())
        self._data = self._parser.parse(container.readall())

    def rewrite(self, container):
        """Write the namelist contents in the specified container."""
        container.write(self.dumps())


class Namelist(ModelResource):
    """
    Class for all kinds of namelists
    """
    _footprint = dict(
        info = 'Namelist from binary pack',
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
            model = dict(
                optional = True,
            ),
            binary = dict(
                optional = True,
                values = binaries,
                default = 'arpege',
            ),
            kind = dict(
                values = [ 'namelist' ]
            ),
            clscontents = dict(
                default = NamelistContent
            )
        )
    )

    @property
    def realkind(self):
        return 'namelist'

    def gget_urlquery(self):
        """GGET specific query : ``extract``."""
        return 'extract=' + self.source


class NamUtil(Namelist):
    """
    Class for namelists utilities
    """
    _footprint = dict(
        info = 'Namelist from utilities pack',
        attr = dict(
            gvar = dict(
                values = ['NAMELIST_UTILITIES'],
                default = 'namelist_utilities'
            ),
            binary = dict(
                values = ['utilities', 'odbtools'],
                default = 'utilities',
                optional = True,
            ),
            kind = dict(
                values = [ 'namelist_util', 'namutil' ],
                remap = dict(
                    namelist_util = 'namutil'
                )
            )
        )
    )

    @property
    def realkind(self):
        return 'namutil'


class NamTerm(Namelist):
    """
    Class for all the terms dependent namelists
    """
    _footprint = [
        term,
        dict(
             info = 'Terms dependent namelist',
             attr = dict(
                kind = dict(
                    values = [ 'namterm' ]
                )
            )
        )
    ]

    @property
    def realkind(self):
        return 'namterm'

    def incoming_xxt_fixup(self, attr, key=None, prefix=None):
        """Fix as best as possible the ``xxt.def`` file."""

        regex = re.compile(',(.*)$')
        myenv = env.current()
        suffix = regex.search(myenv.SWAPP_XXT_DEF)
        if suffix:
            fp = suffix.group(1)
        else:
            fp = None

        try:
            with open('xxt.def', 'r') as f:
                lines = f.readlines()
        except IOError:
            logger.error('Could not open file xxt.def')

        select = lines[self.term.hour].split()[2]

        if not re.match('undef', select):
            if fp:
                rgx = re.compile(key + '(.*)$')
                sfx = rgx.search(select)
                if sfx:
                    s = sfx.group(1)
                else:
                    s = ''
                return ''.join((key,'_', fp, s))
            else:
                return select
        else:
            logger.error('Fullpos namelist id not defined for term %s', self.term)

    def incoming_namelist_fixup(self, attr, key=None):
        """Fix as best as possible the namelist term extensions."""

        val = getattr(self, attr)
        r1 = re.compile('^(.*\/)?(' + key + '.*_fp|cpl)$')
        r2 = re.compile('^(.*\/)?(' + key + '.*_fp)(\..*)$')
        r3 = re.compile('^(.*\/)?(' + key + '.*_p)$')

        fixed = 0

        for r in (r1, r2, r3) :
            s = r.search(val)
            if s:
                fixed = 1
                ( dirpath, base ) = (s.group(1), s.group(2))
                if dirpath == None:
                    dirpath = ''
                ext = ''
                if r == r3:
                    if self.term.hour == 0:
                        p = '0'
                    elif self.term.hour % 6 == 0:
                        p = '6'
                    elif self.term.hour % 3 == 0:
                        p = '3'
                    else :
                        p ='1'
                else:
                    if self.term.hour == 0:
                        p = '0'
                    else:
                        p = ''
                    if r == r2:
                        ext = s.group(3)
                        if ext == None:
                            ext = ''


        if fixed:
            return dirpath + base + p + ext
        else:
            return val


class NamSelect(NamTerm):
    """
    Class for the select namelists
    """
    _footprint = [
        dict(
             info = 'Select namelist for fullpos ',
             attr = dict(
                kind = dict(
                    values = [ 'namselect']
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
        if myenv.has_key('SWAPP_XXT_DEF') and myenv.true('SWAPP_XXT_DEF'):
            return 'extract=' + self.incoming_xxt_fixup('source', 'select')
        else:
            return 'extract=' + self.incoming_namelist_fixup('source', 'select')


class Namelistfp(NamTerm):
    """
    Class for the fullpos term dependent namelists
    """
    _footprint = [
        dict(
             info = 'Namelist for offline fullpos ',
             attr = dict(
                kind = dict(
                    values = [ 'namelistfp']
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

    def fmtkey(self, key):
        key = Time(key)
        return key.fmthm

    def xxtpos(self, n, g, x):
        t = g.get('term', x.get('term', None))
        if t == None:
            return None
        else:
            value = None
            tkey = self.get(t.fmthm, self.get(str(t.hour), None))
            if tkey != None:
                try:
                    value = tkey[n]
                except IndexError:
                    return None
            return value

    def xxtnam(self, g, x):
        return self.xxtpos(0, g, x)

    def xxtsrc(self, g, x):
        return self.xxtpos(1, g, x)


class Namselectdef(NoDateResource):
    """
    Class for the xxt file
    """
    _footprint = dict(
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
                default = 'xxt.def'
            ),
            binary = dict(
                optional = True,
                values = binaries,
                default = 'arpege',
            ),
            kind = dict(
                values = [ 'xxtdef', 'namselectdef' ]
            ),
            clscontents = dict(
                default = XXTContent
            )
        ),
        bind = [ 'gvar', 'source' ]
    )

    @property
    def realkind(self):
        return 'namselectdef'

    def gget_urlquery(self):
        """GGET specific query : ``extract``."""
        return 'extract=' + self.source

