#!/usr/bin/env python
# -*- coding:Utf-8 -*-

#: Automatic export of the online provider Olive
__all__ = ['Olive']

import re

import footprints
logger = footprints.loggers.getLogger(__name__)

from vortex.data.providers import Provider, Remote
from vortex.syntax.stdattrs import namespacefp, member, block, Namespace, a_suite,\
    FmtInt
from vortex.util.config import GenericConfigParser

from common.tools.igastuff import archive_suffix, fuzzyname, arpcourt_vconf, IgakeyFactoryArchive


class Olive(Provider):
    """
    This provider offers accessibility to resources created in the OLIVE framekork
    using the old perl toolbox.
    """

    _footprint = [
        block,
        member,
        namespacefp,
        dict(
            info = 'Olive experiment provider',
            attr = dict(
                experiment = dict(
                    info     = "The experiment's identifier.",
                ),
                namespace = dict(
                    values   = ['olive.cache.fr', 'olive.archive.fr', 'olive.multi.fr', 'multi.olive.fr'],
                    default  = Namespace('olive.cache.fr'),
                    remap    = {
                        'multi.olive.fr': 'olive.multi.fr',
                    }
                ),
                member = dict(
                    type    = FmtInt,
                    args    = dict(fmt = '03'),
                ),
            )
        )
    ]

    @property
    def realkind(self):
        return 'olive'

    def __init__(self, *args, **kw):
        logger.debug('Olive experiment provider init %s', self.__class__)
        super(Olive, self).__init__(*args, **kw)

    def scheme(self, resource):
        """Default scheme is ``olive``."""
        return 'olive'

    def netloc(self, resource):
        """Proxy to actual ``namespace`` value."""
        return self.namespace.netloc

    def nice_member(self):
        """Nice formatting view of the member number, if any."""
        mb = None
        if self.member is not None:
            if re.match(r'pearp', self.vconf):
                mb = 'fc_' + str(self.member) if self.member is not None else ''
            if re.match(r'aearp', self.vconf):
                mb = 'member_' + str(self.member) if self.member is not None else ''
        return mb

    def basename(self, resource):
        """Add block information to resource mailbox... just in case..."""
        resource.mailbox.update(block=self.block)
        bname = super(Olive, self).basename(resource)
        resource.mailbox.clear()
        return bname

    def pathname(self, resource):
        """Build a path according to the existence of a valid date value."""
        rinfo = self.pathinfo(resource)
        rdate = rinfo.get('date', '')
        if rdate:
            rdate = rdate.ymdh
            rdate = re.sub(r'(\d\d)$', r'H\1', rdate)
            rdate = rdate + rinfo.get('cutoff', 'n')[0].upper()
        elts = [self.experiment, rdate, self.block]
        n_member = self.nice_member()
        if n_member is not None:
            elts.insert(2, n_member)
        return '/'.join(elts)


class OpArchive(Provider):

    _footprint = [
        member,
        namespacefp,
        dict(
            info = 'Old archive provider',
            attr = dict(
                vconf = dict(
                    outcast  = arpcourt_vconf
                ),
                tube = dict(
                    optional = True,
                    default  = 'op',
                    values   = ['op', 'ftop'],
                    remap    = dict(ftop = 'op'),
                ),
                namespace = dict(
                    default  = '[suite].multi.fr',
                    values   = ['oper.archive.fr', 'dble.archive.fr',
                                'oper.multi.fr', 'dble.multi.fr',
                                'mirr.archive.fr', 'mirr.multi.fr', ],
                ),
                suite = a_suite,
                igakey = dict(
                    type     = IgakeyFactoryArchive,
                    optional = True,
                    default  = '[vapp]/[vconf]'
                ),
                inout = dict(
                    optional = True,
                    default  = 'input',
                    values   = ['in', 'input', 'out', 'output'],
                    remap    = {'in': 'input', 'out': 'output'}
                ),
                block = dict(
                    optional = True,
                    default = '',
                )
            )
        )
    ]

    def __init__(self, *args, **kw):
        logger.debug('Old archive provider init %s', self.__class__)
        super(OpArchive, self).__init__(*args, **kw)

    @property
    def realkind(self):
        return 'archive'

    def scheme(self, resource):
        """Return the actual tube as scheme."""
        return self.tube

    def netloc(self, resource):
        """Proxy to actual ``namespace`` value."""
        return self.namespace.netloc

    def basename(self, resource):
        bname = resource.basename(self.realkind)

        if hasattr(resource, 'model') and resource.model == 'hycom':
            region_map = dict(atl= '_', med='_MED_', oin='_OIN_')
            mode_map = dict(fc= 'pre', an='ana' )
            region = region_map.get(self.vconf[:3], self.vconf[:3])
            mode = mode_map.get(self.vconf[4:][:2], self.vconf[4:][:2])
            config = self.vconf[-3:] + region + mode

        for i in re.findall(r'\(\w+\:\w+\)|\(\w+\)', bname):
            s1 = re.sub(r'\(|\)', '', i)
            mobj = re.match(r'(\w+):(\w+)', s1)
            if mobj:
                entry = mobj.group(1)
                keyattr = mobj.group(2)
                if entry == 'histfix':
                    if self.block == 'coupling_fc' and resource.model == 'arome':
                        fuzzy = self.block
                    elif resource.model == 'hycom':
                        fuzzy = (fuzzyname('prefix', 'historic', 'hycom_gss') +
                                 '.'.join((config, resource.date.ymdh[4:],
                                           fuzzyname('suffix', 'historic', 'hycom_gss'))))
                    else:
                        igakey = getattr(self, keyattr)
                        if igakey in ('pearp', 'arpege', 'arp_court', 'aearp'):
                            keyattr = igakey
                        else:
                            keyattr = resource.model
                        fuzzy = fuzzyname(entry, resource.realkind, keyattr)
                elif entry == 'icmshfix':
                    if keyattr == 'modelkey':
                        if self.block == 'coupling_fc' and resource.model == 'arome':
                            fuzzy = 'guess_'
                        else:
                            fuzzy = 'icmsh'
                            modelkey = resource.model + '_' + self.vapp
                            if modelkey in ('arome_arome', 'surfex_arome', 'aladin_aladin', 'surfex_aladin'):
                                fuzzy = fuzzy.upper()
                elif entry == 'termfix':
                    fuzzy = '+' + resource.term.fmthour
                    if keyattr == 'modelkey' and self.block == 'coupling_fc':
                        fuzzy = ''
                elif entry == 'suffix':
                    if keyattr == 'modelkey':
                        fuzzy = fuzzyname('suffix', resource.realkind, resource.model + '_' + self.igakey, default='')
                        if (self.vapp == 'arpege' and self.vconf == 'aearp' and
                                self.block == 'forecast' and resource.model != 'surfex'):
                            fuzzy += '_noninfl'
                        if (self.vapp == 'arpege' and self.vconf == 'aearp' and
                                self.block == 'forecast_infl' and resource.model == 'surfex'):
                            fuzzy += '_infl'
                elif entry == 'gribfix':
                    rr = archive_suffix(resource.model, resource.cutoff,
                                        resource.date, vconf=self.vconf)
                    if getattr(self, keyattr) == 'pearp':
                        fuzzy = '_'.join(('fc', rr, str(self.member), resource.geometry.area, resource.term.fmthour))
                    elif getattr(self, keyattr) in ('surcotes', 'surcotes_oi'):
                        fuzzy = '.'.join((fuzzyname('prefix', 'gridpoint', 'hycom_grb'), config,
                                          resource.date.ymdh[4:], fuzzyname('suffix', 'gridpoint', 'hycom_grb')))
                    else:
                        t = '{0:03d}'.format(resource.term.hour)
                        fuzzy = fuzzyname('prefix', 'gridpoint', self.suite) + rr + t + resource.geometry.area
                elif entry == 'errgribfix':
                    fuzzy = 'errgribvor'
                    if getattr(self, keyattr) in ('aearp', 'arpege'):
                        fuzzy += fuzzyname('term' + resource.term.fmthour,
                                           resource.realkind,
                                           self.inout)
                    if getattr(self, keyattr) == 'aearp':
                        fuzzy += '.' + fuzzyname('suffix', resource.realkind, self.inout)
                elif entry == 'memberfix':
                    fuzzy = '{:03d}'.format(int(getattr(self, keyattr)))
                else:
                    fuzzy = fuzzyname(entry, resource.realkind, getattr(self, keyattr))
                bname = bname.replace(i, fuzzy)
            else:
                bname = bname.replace(i, str(getattr(self, s1)))

        return bname

    def pathname(self, resource):
        suite_map = dict(dble='dbl', mirr='miroir')
        rinfo = self.pathinfo(resource)
        rdate = rinfo.get('date')
        suite = suite_map.get(self.suite, self.suite)
        yyyy = str(rdate.year)
        mm = '{0:02d}'.format(rdate.month)
        dd = '{0:02d}'.format(rdate.day)
        rr = 'r{0:d}'.format(rdate.hour)
        rdir = rinfo.get('{0.vapp:s}_{0.vconf:s}_directory'.format(self),
                         rinfo.get('directory', ''))

        if self.member is not None:
            run = 'RUN' + "%d" % self.member
            if re.match(r'pearp', self.igakey) and resource.realkind == 'gridpoint':
                    return '/'.join((self.igakey, suite, dd, rr))
            else:
                return '/'.join((self.igakey, suite, rinfo['cutoff'], yyyy, mm, dd, rr, run ))
        else:
            if re.match(r'arpege|arome|aearp', self.igakey):
                return '/'.join((self.igakey, suite, rinfo['cutoff'], yyyy, mm, dd, rr, rdir )).rstrip('/')
            else:
                if re.match(r'testms1|testmp1', self.igakey):
                    return '/'.join((self.igakey, dd, rr ))
                elif re.match(r'mocage', self.igakey):
                    return '/'.join((self.igakey, dd))
                elif re.match(r'surcotes', self.igakey):
                    return '/'.join((self.igakey, suite, dd, rr )).rstrip('/')
                else:
                    return '/'.join((self.igakey, suite, rinfo['cutoff'], yyyy, mm, dd, rr ))


class OpArchiveCourt(OpArchive):

    _footprint = dict(
        info = 'Old archive provider for very short cutoff',
        attr = dict(
            vconf = dict(
                values  = arpcourt_vconf,
                outcast = set(),
            ),
        )
    )

    def pathinfo(self, resource):
        """Force cutoff to be ``court``."""
        rinfo = super(OpArchiveCourt, self).pathinfo(resource)
        rinfo['cutoff'] = 'court'
        return rinfo


class RemoteGenericSet(Remote):

    _abstract = True
    _footprint = dict(
        info = 'A set of things in a remote repository',
        attr = dict(
            setcontent = dict(
                info = 'The content of the repository',
            ),
        ),
        priority = dict(
            level = footprints.priorities.top.TOOLBOX
        )
    )

    def pathname(self, resource):
        """OS dirname of the ``remote`` attribute."""
        return self.remote


class RemoteBinset(RemoteGenericSet):

    _footprint = dict(
        info = 'A set of binaries in a remote repository',
        attr = dict(
            setcontent = dict(
                values = ['binaries', 'bin'],
                remap = dict(autoremap='first')
            ),
            binmap = dict(
                info     = 'The style of the mapping between Genv keys and binary names.',
                optional = True,
                default  = 'gco'
            ),
            config = dict(
                type            = GenericConfigParser,
                optional        = True,
                default         = GenericConfigParser('@binset-map-resources.ini'),
                doc_visibility  = footprints.doc.visibility.GURU,
            )
        )
    )

    def basename(self, resource):
        """OS basename of the ``remote`` attribute."""
        gvar = str(resource.basename('genv')).lower()
        if not self.config.has_section(self.binmap):
            raise ValueError("The {:s} binmap do not exists.".format(self.binmap))
        return self.config.get(self.binmap, gvar)


class RemoteExtractSet(RemoteGenericSet):

    _RE_EXTRACT = re.compile(r'extract\=([^&]+)(:?&|$)')

    _footprint = dict(
        info = 'A set of namelists or other things in a remote repository',
        attr = dict(
            setcontent = dict(
                values = ['namelists', 'nam', 'filters'],
                remap = dict(nam='namelists')
            ),
        )
    )

    def basename(self, resource):
        """OS basename of the ``remote`` attribute."""
        extractquery = str(resource.urlquery('gget'))
        source = self._RE_EXTRACT.search(extractquery)
        if source:
            return source.group(1)
        else:
            raise ValueError("The gget_urlquery does not returned anything.")
