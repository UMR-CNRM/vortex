#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: Automatic export of the online provider Olive
__all__ = ['Olive']

import re
from vortex.autolog import logdefault as logger
from vortex.data.providers import Provider
from iga.syntax.stdattrs import suites, fuzzyname, archivesuffix


class Olive(Provider):

    _footprint = dict(
        info = 'Olive experiment provider',
        attr = dict(
            experiment = dict(),
            block = dict(),
            member = dict(
                type = int,
                optional = True,
            ),
            namespace = dict(
                optional = True,
                values = [ 'olive.cache.fr', 'olive.archive.fr', 'olive.multi.fr', 'multi.olive.fr' ],
                default = 'olive.cache.fr',
                remap = {
                    'multi.olive.fr' : 'olive.multi.fr',
                }
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Olive experiment provider init %s', self)
        super(Olive, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'olive'

    def scheme(self):
        return 'olive'

    def domain(self):
        return self.namespace

    def pathname(self, resource):
        rinfo = self.pathinfo(resource)
        rdate = rinfo.get('date', '')
        if rdate:
            rdate = rdate.ymdh
            rdate = re.sub(r'(\d\d)$', r'H\1', rdate)
            rdate = rdate + rinfo.get('cutoff', 'n')[0].upper()
        return '/'.join((
            self.experiment,
            rdate,
            self.block
        ))


class OpArchive(Provider):

    _footprint = dict(
        info = 'Old archive provider',
        attr = dict(
            tube = dict(
                optional = True,
                values = [ 'op', 'ftop' ],
                remap = dict( ftop = 'op' ),
                default = 'op'
            ),
            namespace = dict(
                optional = True,
                values= [ 'oper.archive.fr', 'dble.archive.fr', 'oper.multi.fr', 'dble.multi.fr' ],
                default = '[suite].multi.fr'
            ),
            suite = dict(
                values = suites,
                remap = dict(dbl='dble')
            ),
            igakey = dict(
                optional = True,
                default = '[vapp]'
            ),
            member = dict(
                type = int,
                optional = True,
            ),
            inout = dict(
                optional = True,
                default = 'output',
                values =  [ 'in', 'input', 'out', 'output' ],
                remap = { 'in' : 'input', 'out' : 'output' }
            )
        )
    )

    def __init__(self, *args, **kw):
        logger.debug('Old archive provider init %s', self)
        super(OpArchive, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'archive'

    def scheme(self):
        """Return the actual tube as scheme."""
        return self.tube

    def domain(self):
        """Return the actual namespace as domain."""
        return self.namespace

    def basename(self, resource):
        bname = resource.basename(self.realkind)
        sublist = re.findall(r'\(\w+\:\w+\)|\(\w+\)', bname)
        for i in sublist:
            s1 = re.sub(r'\(|\)', '', i)
            mobj = re.match(r'(\w+):(\w+)', s1)
            if mobj:
                entry = mobj.group(1)
                keyattr = mobj.group(2)
                if entry == 'histfix':
                    if getattr(self, keyattr) != 'pearp':
                        keyattr = resource.model
                    else:
                        keyattr = getattr(self, keyattr)
                    fuzzy = fuzzyname(entry, resource.realkind, keyattr)
                elif entry == 'gribfix':
                    rr = archivesuffix(resource.model, resource.cutoff, resource.date)
                    if getattr(self, keyattr) == 'pearp':
                        fuzzy = '_'.join(('fc', rr, str(self.member) , resource.geometry.area, resource.term.fmthour))
                    else:
                        t = '{0:03d}'.format(resource.term.hour)
                        fuzzy = fuzzyname('prefix', 'gridpoint', self.suite) + rr + t + resource.geometry.area
                elif entry == 'errgribfix':
                    fuzzy = 'errgribvor'
                    if getattr(self, keyattr)== 'aearp':
                        fuzzy = 'errgribvor' \
                            + fuzzyname('term' + resource.term.fmthour,resource.realkind, self.inout) + '.' \
                            + fuzzyname('suffix', resource.realkind, self.inout)
                else:
                    fuzzy = fuzzyname(entry, resource.realkind, getattr(self, keyattr))
                bname = bname.replace(i, fuzzy)
            else:
                bname = bname.replace(i, str(getattr(self, s1)))

        return bname  

    def pathname(self, resource):
        rinfo = self.pathinfo(resource)
        rdate = rinfo.get('date','')
        yyyy = str(rdate.year)
        mm = '{0:02d}'.format(rdate.month)
        dd = '{0:02d}'.format(rdate.day)
        rr = 'r{0:d}'.format(rdate.hour)

        if self.member is not None:
            run = 'RUN' + "%d" % self.member
            if re.match(r'pearp', self.igakey) and resource.realkind == 'gridpoint':
                    return '/'.join((self.igakey, self.suite, dd, rr))
            else:
                return '/'.join((self.igakey, self.suite, rinfo['cutoff'], yyyy, mm, dd, rr, run )) 
        else:
            if re.match(r'arpege|arome|aearp', self.igakey):
                return '/'.join((self.igakey, self.suite, rinfo['cutoff'], yyyy, mm, dd, rr ))
            else:
                if re.match(r'testms1|testmp1', self.igakey):
                    return '/'.join((self.igakey, dd, rr ))
                elif re.match(r'mocage', self.igakey):
                    return '/'.join((self.igakey, dd))
                else:
                    return '/'.join((self.igakey, self.suite, rinfo['cutoff'], yyyy, mm, dd, rr ))
