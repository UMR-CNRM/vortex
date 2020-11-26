#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TODO: Module documentation
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import six
import io

from bronx.fancies import loggers
from bronx.stdtypes import date

import vortex
from vortex.syntax.stdattrs import DelayedEnvValue, Latitude, Longitude

from intairpol.basics import AirTool

logger = loggers.getLogger(__name__)

SIMULATION_LEVELS = dict(
    EXERCICE=0,
    ACCIDENT=1,
    TEST=2,
)

EMISSION_TYPES = dict(
    radiologic='radiologique',
    chemical='chimique',
    volcanic='volcanic',
)


class SimulationLevel(six.text_type):
    """TODO: Class documentation."""

    def __new__(cls, value):
        value = six.text_type(value).upper()
        for k in SIMULATION_LEVELS.keys():
            if k.startswith(value):
                value = k
                break
        for i, l in {six.text_type(v): k for k, v in SIMULATION_LEVELS.items()}.items():
            if value == i:
                value = l
                break
        if value not in SIMULATION_LEVELS:
            raise ValueError('Not a valid SimulationLevel: ' + value)
        return six.text_type.__new__(cls, value)

    def __int__(self):
        return SIMULATION_LEVELS[self]


class EmissionType(six.text_type):
    """TODO: Class documentation."""

    def __new__(cls, value):
        value = six.text_type(value).lower()
        for k in EMISSION_TYPES.keys():
            if k.startswith(value):
                value = k
                break
        for i, l in {v: k for k, v in EMISSION_TYPES.items()}.items():
            if value == i:
                value = l
                break
        if value not in EMISSION_TYPES:
            raise ValueError('Not a valid EmissionType: ' + value)
        return six.text_type.__new__(cls, value)

    def french(self):
        return EMISSION_TYPES[self]


class PerleTool(AirTool):
    """TODO: Class documentation."""

    _abstract = True
    _footprint = dict(
        info = 'Generic PERLE tool',
        attr = dict(
            family = dict(
                values = ['perle'],
            ),
        )
    )

    @property
    def realkind(self):
        return 'perletool'


class PerleLauncher(PerleTool):
    """TODO: Class documentation."""

    _abstract = True
    _footprint = dict(
        info = 'Generic PERLE launcher (inline scripts)',
        attr = dict(
            kind = dict(
                values   = ['submit', 'launcher', 'job'],
                remap    = dict(autoremap = 'first'),
            ),
            model = dict(
                values   = ['arp', 'arpege', 'aro', 'arome', 'ifs'],
                remap    = dict(arp = 'arpege', aro = 'arome'),
            ),
            oper_version = dict(
                optional = True,
                alias    = ('op',),
                values   = ['oper', 'dble', 'test', 'dbl'],
                default  = DelayedEnvValue('PERLE_OPER_VERSION', 'oper'),
            ),
            simulation_level = dict(
                optional = True,
                type     = SimulationLevel,
                default  = SimulationLevel(0),
            ),
            target_host = dict(
                optional = True,
                default  = DelayedEnvValue('PERLE_TARGET_HOST', 'beaufix'),
            ),
            target_user = dict(
                optional = True,
                default  = DelayedEnvValue('PERLE_TARGET_USER', vortex.rootenv.USER),
            ),
            target_root = dict(
                optional = True,
                default  = DelayedEnvValue('PERLE_TARGET_ROOT', '/home/mf/dp/menv/sevaulte/perle'),
            ),
            target_path = dict(
                optional = True,
                access   = 'rwx',
                default  = DelayedEnvValue('PERLE_TARGET_PATH', '/scratch/work'),
            ),
            lpdm_path = dict(
                optional = True,
                access   = 'rwx',
                default  = DelayedEnvValue('PERLE_LPDM_PATH'),
            ),
            nolpdm = dict(
                optional = True,
                default  = False,
            ),
            storage = dict(
                optional = True,
                values   = ['archive', 'inline'],
                default  = DelayedEnvValue('PERLE_STORAGE', 'archive'),
            ),
            local_tmp = dict(
                optional = True,
                access   = 'rwx',
                default  = DelayedEnvValue('PERLE_LOCAL_TMP', vortex.rootenv.HOME + '/tmp'),
            ),
        )
    )

    def get_family_tag(self):
        return self.family[:4].lower() + self.model[:3].lower()

    def setup_tables(self, **kw):
        for k, v in kw.items():
            setattr(self, 'table_' + k.lower(), v)

    @property
    def ssh(self):
        if not hasattr(self, '_ssh'):
            self._ssh = self.sh.ssh(self.target_host, self.target_user)
            if self.target_user in self._ssh.execute('ls ' + self.target_path):
                self.target_path = self.sh.path.join(self.target_path, self.target_user)
                logger.info('Change workdir dir to <path:%s>', self.target_path)
        return self._ssh

    def dataput(self, filename):
        """Put the specified file to the remote target path working directory."""
        self.ssh.scpput(filename, self.sh.path.join(self.target_path, self.xtag, filename))

    def setup_controls(self):
        pass


class OldPerleLauncher(PerleLauncher):
    """TODO: Class documentation."""

    _footprint = dict(
        info = 'PERLE launcher old style',
        attr = dict(
            date_begin = dict(
                optional = True,
                type     = date.Date,
                default  = date.synop(base=date.utcnow()),
            ),
            date_period = dict(
                optional = True,
                type     = date.Period,
                default  = date.Period('P1D'),
            ),
            emission_latitude = dict(
                alias    = ('latitude',),
                access   = 'rwx',
                optional = True,
                type     = Latitude,
                default  = None,
            ),
            emission_longitude = dict(
                alias    = ('longitude',),
                access   = 'rwx',
                optional = True,
                type     = Longitude,
                default  = None,
            ),
            emission_amount = dict(
                alias    = ('amount',),
                type     = float,
            ),
            emission_unit = dict(
                alias    = ('unit',),
                access   = 'rwx',
                optional = True,
                values   = ['bq', 'g'],
                default  = 'bq',
            ),
            emission_bottom = dict(
                optional = True,
                alias    = ('bottom',),
                type     = int,
                default  = 0,
            ),
            emission_top = dict(
                alias    = ('top',),
                type     = int,
            ),
            emission_site = dict(
                alias    = ('site',),
                access   = 'rwx',
            ),
            emission_type = dict(
                access   = 'rwx',
                optional = True,
                type     = EmissionType,
                default  = EmissionType('radio'),
            ),
            emission_element = dict(
                alias    = ('element',),
            ),
            emission_density = dict(
                alias    = ('density',),
                access   = 'rwx',
                optional = True,
                type     = float,
                default  = None,
            ),
            emission_partsize = dict(
                alias    = ('partsize',),
                access   = 'rwx',
                optional = True,
                type     = float,
                default  = None,
            ),
            emission_deposit_velocity = dict(
                alias    = ('deposit_velocity',),
                access   = 'rwx',
                optional = True,
                type     = float,
                default  = None,
            ),
            emission_scavenging_rate = dict(
                alias    = ('scavenging_rate',),
                access   = 'rwx',
                optional = True,
                type     = float,
                default  = None,
            ),
            emission_halflife = dict(
                alias    = ('halflife',),
                access   = 'rwx',
                optional = True,
                type     = int,
                default  = None,
            ),
        )
    )

    def setup_controls(self):
        """Try to set undefined attributes and check their cohenrency."""

        site = self.table_sites.match(self.emission_site)
        if site is None:
            logger.warning('Unknown <site:%s>', self.emission_site)
        else:
            self.emission_site = site.name
            tr = self.config['sites_map']
            for a in self.footprint_attributes:
                if getattr(self, a) is None and hasattr(site, tr.get(a, a)):
                    setattr(self, a, getattr(site, tr.get(a, a)))

        elmt = self.table_elements.match(self.emission_element)
        if elmt is None:
            logger.warning('Unknown <element:%s>', self.emission_element)
        else:
            tr = self.config['elements_map']
            for a in self.footprint_attributes:
                if getattr(self, a) is None and hasattr(elmt, tr.get(a, a)):
                    setattr(self, a, getattr(elmt, tr.get(a, a)))

        if self.footprint_undefs():
            logger.error('Undefined launcher <attributes:%s>',
                         ','.join(self.footprint_undefs()))
            raise ValueError('Undefined AirTool launcher attributes: ' +
                             ','.join(self.footprint_undefs()))

        if self.emission_top < self.emission_bottom:
            logger.error('Incompatible level values <bottom:%d> <top:%d>',
                         self.emission_bottom, self.emission_top)
            raise ValueError('Incompatible level values ' +
                             six.text_type(self.emission_bottom) + '-' +
                             six.text_type(self.emission_top))

    def dump_void(self, value):
        return six.text_type(value)

    def dump_date_begin(self, value):
        return value.compact()

    def dump_date_period(self, value):
        return value.hmscompact

    def dump_model(self, value):
        return value.upper()

    def dump_emission_type(self, value):
        return value.french().upper()

    def dump_simulation_level(self, value):
        return self.dump_void(int(value))

    def export_cfg(self, filename='PERLE.CFG'):
        """Write raw perle configuration file (old style)."""

        with io.open(filename, 'w') as fd:
            fd.write(six.text_type(''.join([
                x + '\n' for x in [getattr(self, 'dump_' + p, self.dump_void)(getattr(self, p, ''))
                                   for p in self.config['simulation_params']] if len(x) > 0
            ])))

        logger.info('Job config written <file:%s> <size:%d>', filename, self.sh.size(filename))

        self.sh.yaml_dump(dict(simulations_params=[{p: getattr(self, p, '')}
                                                   for p in self.config['simulation_params']
                                                   ]
                               ), 'perle.yml'
                          )

        return filename

    def export_env(self, filename='PERLE.ENV'):
        """Write raw perle configuration file (old style)."""

        with io.open(filename, 'w') as fd:
            fd.write(six.text_type(''.join([
                'PERLE_' + a.upper() + '="' + six.text_type(getattr(self, a)) + '"\n'
                for a in self.footprint_attributes if 'local_' not in a
            ])))
            fd.write(six.text_type('\n'.join([
                'PERLE_VERSION=' + self.get_family_tag(),
                'PERLE_XTAG=' + self.xtag,
                'PERLE_REMOTE_HOST=' + self.sh.hostname,
                'PERLE_REMOTE_USER=' + self.env.USER,
                'PERLE_REMOTE_PATH=' + self.sh.pwd(),
                'PERLE_REMOTE_TMP=' + self.sh.path.abspath(self.local_tmp),
            ])))
            fd.write('\n')

        logger.info('Job config written <file:%s> <size:%d>', filename, self.sh.size(filename))

        return filename

    def submit(self, nosubmit=False):
        """Submit the remote job."""

        # some cocooning...
        if self.sh.path.isdir(self.xtag):
            logger.warning('Submit directory already exists <path:%s>', self.xtag)
        else:
            self.sh.mkdir(self.xtag)
        self.sh.cd(self.xtag)

        # secure the local tmp path
        if self.env.USER in self.sh.ls(self.local_tmp, output=True):
            self.local_tmp = self.sh.path.join(self.local_tmp, self.env.USER)
        self.local_tmp = self.sh.path.join(self.local_tmp, self.xtag)
        self.sh.mkdir(self.local_tmp)

        # dump the standard config file
        driver_cfg = self.export_cfg()
        self.dataput(driver_cfg)

        # dump attributes as env
        driver_env = self.export_env()
        self.dataput(driver_env)

        # launch the remote job
        actualcmd = '; '.join((
            'cd ' + self.sh.path.join(self.target_path, self.xtag),
            self.sh.path.join(
                self.target_root, self.release, self.get_family_tag(),
                'job', 'replay_submit.sh'
            )
        ))
        if nosubmit:
            print('Not submitted:', actualcmd)
        else:
            print('\n'.join(self.ssh.execute(actualcmd)))
