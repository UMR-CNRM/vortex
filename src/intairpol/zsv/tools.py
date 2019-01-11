#!/usr/bin/env python
# -*- coding: utf-8 -*-

from __future__ import absolute_import, print_function, division, unicode_literals

"""
TODO: Module documentation
"""

import six
import io

import bronx.fancies.dump
from bronx.fancies import loggers
from bronx.stdtypes import date
import footprints

import vortex
from vortex.syntax.stdattrs import DelayedEnvValue

from intairpol.basics import AirTool


logger = loggers.getLogger(__name__)


class ZSVDriver(AirTool):

    _footprint = dict(
        info = 'Driver for processing ZSV sites data',
        attr = dict(
            kind = dict(
                values   = ['driver'],
            ),
            family = dict(
                values   = ['zsv'],
            ),
            cfgfile = dict(
                default  = '[family]-sites.json',
            ),
            sites = dict(
                optional = True,
                type     = footprints.FPList,
                access   = 'rwx',
                default  = footprints.FPList(),
            ),
            sites_ordered = dict(
                optional = True,
                type     = footprints.FPList,
                access   = 'rwx',
                default  = None,
            ),
            sites_discard = dict(
                optional = True,
                type     = footprints.FPList,
                access   = 'rwx',
                default  = None,
            ),
            date_begin = dict(
                optional = True,
                type     = date.Date,
                access   = 'rwx',
                default  = date.lastround(base=date.utcnow()) - 'PT1H',
            ),
            date_end = dict(
                optional = True,
                type     = date.Date,
                access   = 'rwx',
                default  = date.lastround(base=date.utcnow()),
            ),
            date_period = dict(
                optional = True,
                type     = date.Period,
                default  = date.Period('PT1H'),
            ),
            data_path = dict(
                optional = True,
                default  = DelayedEnvValue('ZSV_DATA_PATH', 'webCMC/zsv'),
            ),
            data_host = dict(
                optional = True,
                default  = DelayedEnvValue('ZSV_DATA_HOST', 'wasabi'),
            ),
            data_user = dict(
                optional = True,
                default  = DelayedEnvValue('ZSV_DATA_USER', 'cmc'),
            ),
            archive_path = dict(
                optional = True,
                default  = DelayedEnvValue('ZSV_ARCHIVE_PATH', '/home/m/mcpr/prodpg/WebCMC/ZSV'),
            ),
            archive_host = dict(
                optional = True,
                default  = DelayedEnvValue('ZSV_ARCHIVE_HOST', 'hendrix'),
            ),
            archive_user = dict(
                optional = True,
                default  = DelayedEnvValue('ZSV_ARCHIVE_USER', vortex.ticket().glove.user),
            ),
        )
    )

    def __init__(self, *args, **kw):
        """Few extra setup for connexions."""
        super(ZSVDriver, self).__init__(*args, **kw)
        self.inline = None
        self.archive = None
        self.setup_done = False

    def close_connexions(self):
        if self.inline:
            self.inline.close()
        if self.archive:
            self.archive.close()

    def setup_dates(self):
        """Check coherency of begin and end dates."""
        self.date_begin = date.lastround(base=self.date_begin)
        self.date_end   = date.lastround(base=self.date_end)

        if date.utcnow() < self.date_end:
            logger.warning('End date is in future <date:%s>', self.date_end.ymdhm)

        if self.date_begin > self.date_end:
            logger.error('Bad chronology <begin:%s> <end:%s>',
                         self.date_begin.ymdhm, self.date_end.ymdhm)

    def setup_config(self):
        """Merge footprints and defaults from configuration file."""

        # load default configuration
        logger.info('Configuration <file:%s>', self.actualcfg)
        self.config = self.sh.json_load(self.actualcfg)
        logger.debug('Configuration defaults: %s', self.config)

        # populate actual options with defaults
        for k, v in six.iteritems(self.config):
            if not hasattr(self, k) or getattr(self, k) is None:
                setattr(self, k, v)

    def setup_sites(self):
        """Check actual list of sites."""
        if self.sites:
            self.sites = [s.upper() for s in self.sites]
            for s in self.sites:
                if s not in self.sites_ordered:
                    logger.warning('Unknown <site:%s>', s)
            self.sites = [ s for s in self.sites_ordered if s in self.sites ]
        elif self.sites_ordered:
            self.sites = self.sites_ordered[:]
        else:
            logger.warning('Could not set a proper site list')

    def setup_summary(self):
        """Nice dump of actual options."""
        logger.info('Actual options: %s', footprints.dump.lightdump(self.footprint_as_dict()))

    def setup_extensions(self):
        pass

    def setup(self, summary=True):
        """Pure setup driver (call to other setup methods)."""
        if self.setup_done:
            logger.warning('Setup already completed')
        else:
            self.setup_dates()
            self.setup_config()
            self.setup_sites()
            self.setup_extensions()
            self.setup_done = True
        if summary:
            self.setup_summary()

    def process(self, site):
        pass

    def complete(self):
        self.close_connexions()

    def run(self):
        self.setup()
        for site in self.sites:
            self.process(site)
        self.complete()


class ZSVQualityStats(ZSVDriver):

    _footprint = dict(
        info = 'ZSV quality indices statistic computations',
        attr = dict(
            kind = dict(
                values   = ['stats', 'zsv_qstats', 'qstats', 'zsvqstats'],
                remap    = dict(autoremap = 'first'),
            ),
            data_list = dict(
                optional = True,
                default  = DelayedEnvValue('ZSV_DATA_LIST', 'liste_sites.txt'),
            ),
            update = dict(
                optional = True,
                type     = bool,
                default  = False,
            ),
            statsfmt = dict(
                optional = True,
                type     = footprints.FPTuple,
                default  = footprints.FPTuple(('json', 'csv', 'txt')),
            ),
        )
    )

    def __init__(self, *args, **kw):
        """Setup the log level right from the start."""
        super(ZSVQualityStats, self).__init__(*args, **kw)
        self._actual_dates = dict()
        self._stats = dict()
        self._iqs = None

    def setup_data_list(self):
        """Retrieve effective sites list on remote data server."""

        # always remove any existing local file
        self.sh.rm(self.data_list)

        # fetch the list on the remote server
        with self.sh.ftp(self.data_host, logname=self.data_user) as ftp:
            ftp.cd(self.data_path)
            ftp.get(self.data_list, self.data_list)

        if self.sh.size(self.data_list) > 0:
            deflist = self.sh.cat(self.data_list)
            logger.info('Retrieved site list:\n%s', "\n".join(deflist))
            self.sites_map = {
                xs['name']: xs
                for xs in [ dict(zip(self.sites_labels, s.split())) for s in deflist ]
            }
            for xmap in self.sites_map.values():
                xmap['dfirst'] = date.Date(xmap['dfirst'])
                xmap['dlast']  = date.Date(xmap['dlast'])
            logger.debug('Actual sites map: %s', footprints.dump.lightdump(self.sites_map))
            for s in self.sites[:]:
                if s not in self.sites_map:
                    logger.warning('Not in data sites list <site:%s>', s)
                    self.sites.remove(s)
        else:
            logger.critical('Could not fetch sites list <path:%s> <file:%s>',
                            self.data_path, self.data_list, )

    def setup_extensions(self):
        self.setup_data_list()
        self.record_load()

    def record_load(self):
        """Load and set up current record of statistic computations."""

        if self.update:
            self.upfile = self.sh.path.join(self.workdir, 'zsv-record-' + self.label + '.json')
            logger.info('Loading <record:%s>', self.upfile)
            if self.sh.size(self.upfile) > 0:
                self.record = self.sh.json_load(self.upfile)
                for k, v in sorted(self.record.items()):
                    ordered_dates = sorted(v.keys())
                    if ordered_dates:
                        logger.info('Current record <len:%s> <begin:%s> <end:%s> <site:%s>',
                                    len(v), ordered_dates[0], ordered_dates[-1], k)
            else:
                logger.warning('No such file <record:%s>', self.upfile)
                self.record = dict()
        else:
            self.record = dict()

    def record_dump(self):
        """Dump current updated record of statistic computations."""

        if self.update:
            logger.info('Dumping <record:%s>', self.upfile)
            if self.sh.path.exists(self.upfile):
                if self.sh.path.isdir(self.bkup_path):
                    self.sh.mkdir(self.sh.path.join(self.bkup_path, 'bkup_zsv_records'))
                    self.sh.mv(
                        self.upfile,
                        self.sh.path.join(
                            self.bkup_path,
                            'bkup_zsv_records',
                            self.sh.path.basename(self.upfile) + '-' + date.now().compact()
                        )
                    )
                else:
                    self.sh.cp(self.upfile, self.upfile + '.bkup')
        self.sh.json_dump(self.record, self.upfile, indent=4, sort_keys=True)

    def parse_obsreport(self, obsfile):
        """Parse ZSV hourly obs report with a very empiric strategy."""

        logger.info('Obs report <file:%s> <size:%s>', obsfile, self.sh.size(obsfile))
        obsreport = dict(timeline=dict())
        datebloc  = False

        for l in self.sh.cat(obsfile, output=True):
            guess = [ x.strip() for x in l.split(':') ]
            if l.startswith('Valide'):
                data = l.split()
                obsreport['valid_begin'] = date.Date(data[2] + 'T' + data[3])
                obsreport['valid_end']   = date.Date(data[6] + 'T' + data[7])
            elif len(guess) == 1 and guess[0] and datebloc:
                # store real values
                data = guess[0].split()
                obsreport['timeline'][datebloc].append(
                    dict(level=int(data[0]), u=float(data[1]), v=float(data[2]), obsmod=data[3])
                )
            elif len(guess) == 2:
                # bingo, this is very simple
                obsreport[self.obsreport_map.get(guess[0], guess[0]).lower()] = guess[1]
            elif len(guess) == 3 and guess[2].endswith('UTC'):
                # new date bloc
                datebloc = date.Date(l.strip()).compact()
                obsreport['timeline'][datebloc] = list()

        return obsreport

    def actual_dates(self, site):
        """Effective start and stop dates for a specified site."""

        if site not in self._actual_dates:

            # set actual begin and end dates
            info  = self.sites_map[site]
            start = self.date_begin
            stop  = self.date_end

            logger.info('Begin date <actual:%s> <requested:%s>',
                        info['dfirst'].ymdhm, self.date_begin.ymdhm)
            if info['dfirst'] < self.date_begin:
                logger.warning('Begin date gap <couldbe:%s> <begin:%s>',
                               info['dfirst'].ymdhm, self.date_begin.ymdhm)

            logger.info('End date <actual:%s> <requested:%s>',
                        info['dlast'].ymdhm, self.date_end.ymdhm)
            if info['dlast'] > self.date_end:
                logger.warning('End date gap <end:%s> <couldbe:%s>',
                               self.date_end.ymdhm, info['dlast'].ymdhm)

            if self.date_end > info['dlast']:
                logger.warning('Change date <end:%s> <set:%s>',
                               self.date_end.ymdhm, info['dlast'].ymdhm)
                stop = info['dlast']

            if start > stop:
                logger.warning('Change date <begin:%s> <set:%s>', start, stop)
                start = stop

            self._actual_dates[site] = (start, stop)

        return self._actual_dates[site]

    @property
    def iqs(self):
        if self._iqs is None:
            self._iqs = tuple([iq.lower() for iq in sorted(self.obsreport_map.values())
                               if iq.lower().startswith('iq') ])
        return self._iqs

    def extract(self, site):
        """Fetch and parse data from a site."""

        self.sh.mkdir(site)
        start, stop = self.actual_dates(site)
        info = self.sites_map[site]

        # set up connexions
        if stop >= info['dfirst'] and self.inline is None:
            self.inline = self.sh.ftp(self.data_host)
            self.inline.cd(self.data_path)

        if start < info['dfirst'] and self.archive is None:
            self.archive = self.sh.ftp(self.archive_host)
            self.archive.cd(self.archive_path)

        # time loop
        sitedata = self.record.setdefault(site, dict())
        current = start

        while current <= stop:
            logger.debug('Extract <date:%s>', current.ymdhm)
            if current.ymdh in sitedata:
                logger.info('Taken from record <date:%s>', current.ymdh)
            else:
                filename = self.sh.path.join(site, site + '_' + current.ymdhm + '.txt')
                bkupname = self.sh.path.join(self.bkup_path, 'bkup_reports',
                                             'zsv-reports-', current.strftime('%Y%m'), '.tgz')
                if self.sh.size(filename) < 1:
                    if info['dfirst'] <= current <= info['dlast']:
                        logger.info('Inline <fetch:%s>', filename)
                        self.inline.get(filename, filename)
                    elif self.sh.path.exists(bkupname):
                        logger.info('Extract <bkup:%s>', filename)
                        self.sh.untar(bkupname, filename)
                    else:
                        tarfile = 'ZSV_OBS_' + current.strftime('%d%H') + '.tar'
                        tmpfile = 'ZSV_OBS_' + current.ymdh + '.tar'
                        if not self.sh.path.exists(tmpfile):
                            logger.info('Archive <fetch:%s>', tarfile)
                            self.archive.get(tarfile, tmpfile)
                        logger.info('Extract <file:%s>', filename)
                        self.sh.untar(tmpfile, filename)

                # parse obs data
                obsdata = self.parse_obsreport(filename)

                # check internal date and store quality indices
                if 'valid_begin' in obsdata:
                    if obsdata['valid_begin'] == current:
                        logger.info('Quality indices %s',
                                    ' '.join(['<' + iq + ':' + obsdata[iq] + '>' for iq in self.iqs]))
                        sitedata[current.ymdh] = ''.join([obsdata[iq] for iq in self.iqs])
                    else:
                        logger.error('Obs mismatch <file:%s> <date:%s>', filename, obsdata['valid_begin'].ymdhm)
                else:
                    logger.error('No valid date found in <file:%s>', filename)

            # update current date
            current = current + self.date_period

    def stats_add(self, site, stats):
        self._stats[site] = stats

    def stats_keys(self):
        return self._stats.keys()

    def stats_basefile(self):
        return self.sh.path.join(self.workdir, '-'.join((
            'zsv-qstats', self.label, self.date_begin.ymdh, self.date_end.ymdh)))

    @property
    def stats_csvfile(self):
        return self.stats_basefile() + '.csv'

    @property
    def stats_jsonfile(self):
        return self.stats_basefile() + '.json'

    @property
    def stats_txtfile(self):
        return self.stats_basefile() + '.txt'

    def stats_dump_as_json(self):
        logger.info('Dump stats as json <file:%s>', self.stats_jsonfile)
        self.sh.json_dump(self._stats, self.stats_jsonfile, indent=4, sort_keys=True)

    def stats_dump_as_csv(self):
        logger.info('Dump stats as csv <file:%s>', self.stats_csvfile)
        with io.open(self.stats_csvfile, 'w') as fd:
            for n, site in enumerate(self.sites):
                fd.write(u'{0:d},{1:s},{2:s}\n'.
                         format(n + 1, site,
                                ','.join([six.text_type(round(self._stats[site][iq].get('P' + ival, 0), 6))
                                          for iq in self.iqs for ival in ('A', 'B', 'C')])))

    def stats_dump_as_txt(self):
        logger.info('Dump stats as txt <file:%s>', self.stats_txtfile)
        with io.open(self.stats_txtfile, 'w') as fd:
            for n, site in enumerate(self.sites):
                fd.write(u'{0:d};{1:s};{2:s}\n'.
                         format(n + 1, site,
                                ';'.join([six.text_type(round(self._stats[site][iq].get('P' + ival, 0), 6)).replace('.', ',')
                                          for iq in self.iqs for ival in ('A', 'B', 'C')])))

    def stats_dump(self):
        for fmt in self.statsfmt:
            dump_method = 'stats_dump_as_' + fmt
            if hasattr(self, dump_method):
                getattr(self, dump_method)()

    def compute(self, site):
        """Compute ratio for each indices."""

        if site in self.record:
            stats = {iq: dict(ilen=0, A=0, B=0, C=0) for iq in self.iqs}
            start, stop = self.actual_dates(site)
            stats.update(date_begin=start.ymdhm, date_end=stop.ymdhm)
            current = start
            while current <= stop:
                if current.ymdh in self.record[site]:
                    logger.debug('Compute <date:%s>', current.ymdhm)
                    iobs = self.record[site][current.ymdh]
                    while len(iobs) < len(self.iqs):
                        iobs = iobs + 'X'
                    for i, iq in enumerate(self.iqs):
                        if iobs[i] != 'X':
                            stats[iq]['ilen'] = stats[iq]['ilen'] + 1
                            stats[iq][iobs[i]] = stats[iq][iobs[i]] + 1
                else:
                    logger.warning('Skip <date:%s>', current.ymdhm)
                # update current date
                current = current + self.date_period
            # percentage computations
            for iq in self.iqs:
                if stats[iq]['ilen'] == 0:
                    logger.error('No data for stats <site:%s> <iq:%s>', site, iq)
                else:
                    for ival in ('A', 'B', 'C'):
                        stats[iq]['P' + ival] = stats[iq][ival] * 100.0 / stats[iq]['ilen']
            logger.info('Complete stats <site:%s> %s', site, footprints.dump.lightdump(stats))
            self.stats_add(site, stats)
        else:
            logger.critical('No information available <site:%s>', site)

    def process(self, site):
        if self.verbose:
            self.sh.title(site)
        logger.info('Processing <site:%s>', site)
        self.extract(site)
        self.compute(site)

    def complete(self):
        super(ZSVQualityStats, self).complete()
        if self.verbose:
            print(bronx.fancies.dump.fulldump(self.record))
        if self.update:
            self.record_dump()
        if self.stats_keys():
            self.stats_dump()
