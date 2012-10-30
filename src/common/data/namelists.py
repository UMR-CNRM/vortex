#!/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re, logging

from vortex.tools import env
from vortex.data.outflow import ModelResource, NoDateResource
from vortex.data.contents import AlmostDictContent
from vortex.tools.fortran import NamelistParser, NamelistBlock
from vortex.syntax.stdattrs import binaries, term
from gco.syntax.stdattrs import GenvKey


class NamelistContent(AlmostDictContent):
    """Fortran namelist including namelist blocks."""

    def __init__(self, **kw):
        kw.setdefault('macros', dict(NBPROC = None))
        kw.setdefault('remove', set())
        kw.setdefault('parser', None)
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

    def macros(self):
        """Returns a list of macro names."""
        return self._macros

    def setmacro(self, item, value):
        """Set macro value for further substitution."""
        for namblock in filter(lambda x: item in x.macros(), self.values()):
            namblock.addmacro(item, value)
        self._macros[item] = value

    def dumps(self):
        """Returns the namelist contents as a string."""
        return ''.join(map(lambda x: self.get(x).dumps(), sorted(self.keys())))

    def merge(self, delta):
        """Merge of the current namelist content with the set of namelist blocks provided."""
        for namblock in delta.values:
            if namblock.name in self:
                self[namblock.name].merge(namblock)
            else:
                newblock = NamelistBlock(name=namblock.name)
                for dk in namblock.keys():
                    newblock[dk] = namblock[dk]
                self[namblock.name] = newblock
        for item in delta.rmblocks:
            del self[item]

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

    @classmethod
    def realkind(cls):
        return 'namelist'

    def gget_urlquery(self):
        """GGET specific query : ``extract``."""
        return 'extract=' + self.source

    def iga_pathinfo(self):
        """IGA specific informations to let the provider build the url-path."""
        return dict(
            model = self.model,
            geometry = self.geometry
        )


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
                values = [ 'namelist_util', 'namutil' ]
            )
        )
    )

    @classmethod
    def realkind(cls):
        return 'namelist_uti'


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

    @classmethod
    def realkind(cls):
        return 'namterm'

    def incoming_xxt_fixup(self, attr, key=None, prefix=None):
        """Fix as best as possible the ``xxt.def`` file."""

        regex = re.compile(',(.*)$')
        myenv = env.current()
        suffix = regex.search(myenv.SWAPP_XXT_DEF)
        if suffix:
            fp = suffix.group(1)
        else :
            fp = None

        try:
            f = open('xxt.def', 'r')
            lines = f.readlines()
            f.close
        except IOError:
            logging.error('Could not open file xxt.def')

        select = lines[self.term].split()[2]

        if not re.match('undef', select):
            if fp :
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
            logging.error('Fullpos namelist id not defined for term %s', self.term)

    def incoming_namelist_fixup(self, attr, key=None):
        """Fix as best as possible the namelist term extensions."""

        val = getattr(self, attr)
        r1 = re.compile('^(.*\/)?(' + key + '.*_fp|cpl)$')
        r2 = re.compile('^(.*\/)?(' + key + '.*_fp)(\..*)$')
        r3 = re.compile('^(.*\/)?(' + key + '.*_p)$')

        fixed = 0

        for r in (r1, r2, r3) :
            s = re.search(r, val)
            if s :
                fixed = 1
                ( dir, base ) = (s.group(1), s.group(2))
                if dir == None:
                    dir = ''
                ext = ''
                if r == r1 or r == r2 :
                    if self.term == 0:
                        p = '0'
                    else :
                        p = ''
                    if r == r2:
                        ext = s.group(3)
                        if ext == None:
                            ext = ''
                else :
                    if self.term == 0:
                        p = '0'
                    elif self.term%6 == 0 :
                        p = '6'
                    elif self.term%3 == 0 :
                        p = '3'
                    else :
                        p ='1'

        if fixed:
            return dir + base + p + ext
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

    @classmethod
    def realkind(cls):
        return 'namselect'

    def gget_urlquery(self):
        """GGET specific query : ``extract``."""
        myenv = env.current()
        if myenv.has_key('SWAPP_XXT_DEF') and re.match('1', myenv.SWAPP_XXT_DEF):
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

    @classmethod
    def realkind(cls):
        return 'namelistfp'

    def gget_urlquery(self):
        """GGET specific query : ``extract``."""
        return 'extract=' + self.incoming_namelist_fixup('source', 'namel')


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
            )
        ),
        bind = [ 'gvar', 'source' ]
    )

    @classmethod
    def realkind(cls):
        return 'namselectdef'

    def gget_urlquery(self):
        """GGET specific query : ``extract``."""
        return 'extract=' + self.source

