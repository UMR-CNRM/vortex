# -*- coding: utf-8 -*-

"""
Interface to SMS commands.
"""

from __future__ import print_function, absolute_import, unicode_literals, division

import uuid

import tempfile

from bronx.fancies import loggers
import footprints

from vortex.tools.schedulers import EcmwfLikeScheduler

__all__ = []

logger = loggers.getLogger(__name__)


class EctransSMS(EcmwfLikeScheduler):
    """
    Client interface to SMS scheduling and monitoring system.
    """

    _footprint = dict(
        info = 'SMS client service',
        attr = dict(
            kind = dict(
                values   = ['sms'],
            ),
            env_pattern = dict(
                default  = 'SMS',
                optional = True,
            )
        ),
        priority=dict(
            level=footprints.priorities.top.TOOLBOX
        )
    )

    _KNOWN_CMD = ('abort', 'complete', 'event', 'init', 'label', 'meter',
                  'msg', 'variable', 'fix')

    def __init__(self, *args, **kw):
        logger.debug('EctransSMS scheduler client init %s', self)
        super(EctransSMS, self).__init__(*args, **kw)
        self._confcheck = ('ectrans' in self.sh.loaded_addons() and
                           'VORTEX_UPDSERVER_HOST' in self.env and
                           'VORTEX_UPDSERVER_PATH' in self.env)
        if self._confcheck:
            self._remote = self.sh.ectrans_remote_init(storage=self.env.VORTEX_UPDSERVER_HOST)
            self._gateway = self.sh.ectrans_gateway_init()
            self._targetpath = self.env.VORTEX_UPDSERVER_PATH
        else:
            logger.warning('EctransSMS service could not be configured')

    def info(self):
        """Dump current defined variables."""
        super(EctransSMS, self).info()
        print("Extra SMS' Ectrans configuration:")
        if self._confcheck:
            print('  gateway=', self._gateway)
            print('  remote=', self._remote)
            print('  targetpath=', self._targetpath)
        else:
            print('  NO CONFIGURATION !')

    def cmd_rename(self, cmd):
        """Remap command name. Strip any sms prefix."""
        cmd = super(EctransSMS, self).cmd_rename(cmd)
        while cmd.startswith('sms'):
            cmd = cmd[3:]
        return cmd

    def _actual_child(self, cmd, options):
        """Miscellaneous smschild subcommand."""
        if not self._confcheck:
            raise RuntimeError('EctransSMS is not configured properly !')
        args = ['sms' + self.cmd_rename(cmd)]
        args.extend(options)
        with tempfile.NamedTemporaryFile('w', prefix='smscmd_send.') as fhdir:
            fhdir.write(' '.join(args) + "\n")
            for prefix in ('SMS', 'SWAPP_SERVER_ID'):
                fhdir.write(''.join([var + '=' + str(self.env.get(var, '') + '\n')
                                     for var in self.env.keys()
                                     if var.startswith(prefix)]))
            fhdir.flush()
            return self.sh.raw_ectransput(source=fhdir.name,
                                          target=self.sh.path.join(self._targetpath,
                                                                   'smsupd.' + uuid.uuid4().hex),
                                          gateway=self._gateway, remote=self._remote,
                                          priority=99, retryCnt=15, retryFrq=120, sync=True)
