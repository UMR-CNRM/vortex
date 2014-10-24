#!/usr/bin/env python
# -*- coding: utf-8 -*-

#: No automatic export
__all__ = []

import re, io

from vortex.autolog import logdefault as logger

from vortex.tools import date, odb

from vortex.algo.components import Parallel
from vortex.data.handlers   import Handler
from vortex.util.structs    import Foo
from vortex.syntax.stdattrs import a_date

from common.data.obs import ObsMapContent, ObsMapItem, ObsRefItem

from footprints import dump

class Raw2ODB(Parallel):
    """Coupling for IFS-like LAM Models."""

    _footprint = dict(
        attr = dict(
            kind = dict(
                values = ['raw2odb', 'bufr2odb', 'obsoul2odb'],
                remap  = dict(
                    bufr2odb   = 'raw2odb',
                    obsoul2odb = 'raw2odb',
                )
            ),
            date = a_date,
            npool = dict(
                type = int,
            ),
            ioassign = dict(),
            slots = dict(
                type     = odb.TimeSlots,
                optional = True,
                default  = odb.TimeSlots(7, chunk='PT1H'),
            ),
            virtualdb = dict(
                optional = True,
                default  = 'ecma',
            ),
            iomethod = dict(
                type     = int,
                optional = True,
                default  = 1,
            ),
            ontime = dict(
                type     = bool,
                optional = True,
                default  = True,
            ),
            mapall = dict(
                type     = bool,
                optional = True,
                default  = False,
            ),
            maponly = dict(
                type     = bool,
                optional = True,
                default  = False,
            ),
        )
    )

    def prepare(self, rh, opts):
        """Default pre-link for climatological files"""
        super(Raw2ODB, self).prepare(rh, opts)

        sh = self.system

        # Build IO-Assign table
        iopath = self.target.get('odbtools:rootdir', self.env.TMPDIR)
        iovers = self.target.get('odbtools:odbcycle', 'oper')
        iomake = self.target.get('odbtools:iomake', 'create_ioassign')
        iocmd  = self.env.get('VORTEX_ODB_IOMAKE', '/'.join((iopath, iovers, iomake)))
        sh.chmod(self.ioassign, 0755)
        sh.spawn([iocmd, '-l' + self.virtualdb.upper(), '-n' + str(self.npool)], output=False)

        # Looking for input observations
        obsall = [ x.rh for x in self.context.sequence.effective_inputs(kind = 'observations') ]
        obsall.sort(lambda a, b: cmp(a.resource.part, b.resource.part))

        # Looking for valid raw observations
        sizemin = self.env.VORTEX_OBS_SIZEMIN or 80
        obsok   = list()
        for ro in obsall:
            logger.info('Inspect observation ' + ro.resource.part)
            if ro.resource.nativefmt == 'odb':
                logger.warning('Observations set [%s] is ODB ready', ro.resource.part)
                continue
            if ro.container.totalsize < sizemin:
                logger.warning('Observations set [%s] is far too small: %d', ro.resource.part, ro.container.totalsize)
            else:
                logger.info('Obs size: ' + str(ro.container.totalsize))
                obsok.append(Foo(rh=ro, refdata=list(), mapped=False, discarded=False))

        # Building refdata map for direct access to (fmt, data, instr) entries
        refmap = dict()
        refall = [ x.rh for x in self.context.sequence.effective_inputs(kind = 'refdata') ]
        for rd in refall:
            logger.info('Inspect refdata ' + rd.container.localpath())
            sh.subtitle(rd.role)
            rd.container.cat()
            for item in rd.contents:
                refmap[(item.fmt.lower(), item.data, item.instr)] = (rd, item)

        # Build actual refdata
        for obs in obsok:
            thisdate = obs.rh.resource.date
            thispart = obs.rh.resource.part
            thisfmt  = obs.rh.container.actualfmt.lower()
            logger.info(' '.join(('Building information for [', thisfmt, '/', thispart, ']')))

            # Check date
            if thisdate != self.date:
                logger.error('Run date [%s] is not obs date [%s]', thisdate.isoformat(), self.date.isoformat())

            # Gather equivalent refdata lines
            if not sh.path.exists('norefdata.' + thispart) and (
                not self.env.VORTEX_OBSDB_NOREF or not re.search(thispart, self.env.VORTEX_OBSDB_NOREF, re.IGNORECASE)
            ):
                for k, v in refmap.items():
                    x_fmt, x_data, x_instr = k
                    if x_fmt == thisfmt and x_data == thispart:
                        rd, item = v
                        obs.refdata.append(rd.contents.formatted_data(item))

        # Looking for obs maps
        mapitems = list()
        for om in [ x.rh for x in self.context.sequence.effective_inputs(kind = 'obsmap') ]:
            logger.info(' '.join(('Gathering information from map', om.container.localpath())))
            sh.subtitle(om.role)
            om.container.cat()
            mapitems.extend(om.contents)

        # Building actual map / refdata correspondance
        self.obspack = dict()
        for imap in mapitems:
            logger.info('Inspect ' + str(imap))
            candidates = [
                obs for obs in obsok
                    if obs.rh.resource.part == imap.data and obs.rh.container.actualfmt.lower() == imap.fmt.lower()
            ]
            for obs in candidates:
                obs.mapped = True
                if self.ontime and obs.rh.resource.date != self.date:
                    obs.discarded = True
                    logger.warning(
                        'Observation [%s] discarded [time mismatch: %s / %s]',
                        obs.rh.resource.date.isoformat(),
                        self.date.isoformat()
                    )
            candidates = [ obs for obs in candidates if not obs.discarded ]
            if not candidates:
                errmsg = 'No input obsfile could match [data:{0:s}/fmt:{1:s}]'.format(imap.data, imap.fmt)
                if self.mapall:
                    raise ValueError(errmsg)
                else:
                    logger.warning(errmsg)
                    continue
            self.obspack.setdefault(imap.odb, Foo())
            thismap = self.obspack.get(imap.odb)
            thismap.setdefault('mapping', list())
            thismap.mapping.append(imap)
            thismap.setdefault('refdata', list())
            thismap.setdefault('obsfile', dict())
            thismap.obsfile[imap.fmt.upper() + '.' + imap.data] = candidates[-1]
            thiskey = (imap.fmt.lower(), imap.data, imap.instr)
            if thiskey in refmap:
                rd, item = refmap[thiskey]
                thismap.refdata.append(rd.contents.formatted_data(item))
            else:
                logger.warning('Creating automatic refdata entry for ' + str(thiskey))
                item = ObsRefItem(imap.data, imap.fmt, imap.instr, self.date.ymd, self.date.hh)
                if refall:
                    thismap.refdata.append(refall[0].contents.formatted_data(item))
                else:
                    logger.critical('No way to format data %s', item)
                    raise ValueError('No default refdata contents to produced formatted data')

        for notmap in [ obs for obs in obsok if not obs.mapped ]:
            thispart = notmap.rh.resource.part
            logger.info('Inspect not mapped obs ' + thispart)
            if thispart not in self.obspack:
                thisfmt = notmap.rh.container.actualfmt.upper()
                thismsg = 'standalone obs entry [data:{0:s}/fmt:{1:s}]'.format(thispart, thisfmt)
                if self.maponly:
                    logger.warning('ignore ' + thismsg)
                else:
                    logger.warning('active ' + thismsg)
                    self.obspack.setdefault(thispart, Foo())
                    thismap = self.obspack.get(thispart)
                    thismap.setdefault('mapping', list())
                    thismap.mapping.append(ObsMapItem(thispart, thispart, thisfmt, 'unknown'))
                    thismap.setdefault('refdata', notmap.refdata)
                    thismap.setdefault('obsfile', dict())
                    thismap.obsfile[thisfmt.upper() + '.' + thispart] = notmap

        self.slots.as_file(self.date, 'ficdate')

        odb.setup_env(
            env      = self.env,
            date     = self.date,
            npool    = self.npool,
            nslots   = self.slots.nslots,
            iomethod = self.iomethod,
        )

    def execute(self, rh, opts):
        """Loop on the various initial conditions provided."""

        sh = self.system

        batnam    = [ x.rh for x in self.context.sequence.effective_inputs(role = 'NamelistBatodb') ]
        obsmapout = list()

        for odbset, thispack in self.obspack.items():
            odbname = self.virtualdb.upper() + '.' + odbset
            sh.title('ODB set ' + odbname)

            # Make a soft link when necessary
            linked = list()
            for obsname, obsinfo in thispack.obsfile.items():
                sh.subtitle(obsname)
                if sh.path.islink(obsname):
                    sh.remove(obsname)
                if obsname != obsinfo.rh.container.localpath():
                    sh.softlink(obsinfo.rh.container.localpath(), obsname)
                    linked.append(obsname)

            # Fill the actual refdata according to information gathered in prepare stage
            if thispack.refdata:
                with io.open('refdata', 'w') as fd:
                    for r in thispack.refdata:
                        fd.write(unicode(r + "\n"))
                sh.subtitle('Local refdata')
                sh.cat('refdata', output=False)

            # Give a glance to the actual namelist
            if batnam:
                sh.subtitle('Namelist Raw2ODB')
                batnam[0].container.cat()

            # Standard execution

            self.env.ODB_SRCPATH_ECMA  = sh.path.abspath(odbname)
            self.env.ODB_DATAPATH_ECMA = sh.path.abspath(odbname)
            super(Raw2ODB, self).execute(rh, opts)

            # Some cleaning
            sh.header('Partial cleaning for ' + odbname)
            sh.remove('refdata')
            for obslink in linked:
                sh.remove(obslink)

            # Save a copy of io assign map in the new database
            if sh.path.isdir(odbname):
                sh.cp('IOASSIGN', odbname + '/' + 'IOASSIGN')
                obsmapout.extend(thispack.mapping)
            else:
                logger.warning('DataBase not created: ' + odbname)

        with io.open('batodb_map.out', 'w') as fd:
            for x in sorted(obsmapout):
                fd.write(unicode(ObsMapContent.formatted_data(x) + '\n'))

    def postfix(self, rh, opts):
        """Post coupling cleaning."""
        super(Raw2ODB, self).postfix(rh, opts)
