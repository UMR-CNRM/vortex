#!/usr/bin/env python
# -*- coding:Utf-8 -*-
"""
Hooks for special DAVAI processings.
"""
from __future__ import print_function, absolute_import, unicode_literals, division

import os
import json
import re

from bronx.fancies import loggers

from .util import SummariesStack, DavaiException, send_task_to_DAVAI_server

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


def take_the_DAVAI_train(t, rh,
                         fatal=True):
    """Usual double put of summaries for DAVAI."""
    send_to_DAVAI_server(t, rh, fatal=fatal)
    throw_summary_on_stack(t, rh)


def throw_summary_on_stack(t, rh, reload_trolley=False):
    """
    Put summary on stack (cache directory in which are gathered all summaries).

    :param reload_trolley: if True, reload trolley on-the-fly right afterwards
    """
    stack = SummariesStack(vapp=rh.provider.vapp,
                           vconf=rh.provider.vconf,
                           xpid=rh.provider.experiment)
    stack.throw_on_stack(t, rh, reload_trolley=reload_trolley)


def send_to_DAVAI_server(t, rh, fatal=True):  # @UnusedVariables
    """
    Send JSON summary to DAVAI server.

    :param fatal: if False, catch errors, log but do not raise
    """
    server_syntax = 'http://<host>[:<port>]/<url> (port is optional)'
    try:
        with open(rh.container.localpath(), 'r') as s:
            summary = json.load(s)
        if rh.resource.kind == 'xpinfo':
            jsonData = {rh.resource.kind:summary}
        elif rh.resource.kind == 'taskinfo':
            jsonData = {rh.provider.block:{rh.resource.scope:summary}}
        else:
            raise DavaiException("Only kind=('xpinfo','taskinfo') resources can be sent.")
        davai_server_url = os.environ.get('DAVAI_SERVER')
        if davai_server_url == '':
            raise DavaiException("DAVAI_SERVER must be defined ! Expected syntax: " + server_syntax)
        else:
            if not davai_server_url.endswith('/api/'):
                davai_server_url = os.path.join(davai_server_url, 'api', '')
        if not t.sh.default_target.isnetworknode:
            # Compute node: open tunnel for send to target
            # identify target
            _re_url = re.compile('http://(?P<host>[\w\.]+)(:(?P<port>\d+))?/(?P<url>.+)$')
            davai_server_match = _re_url.match(davai_server_url)
            assert davai_server_match is not None, \
                "DAVAI_SERVER does not match expected syntax: " + server_syntax
            args = davai_server_match.groupdict()
            if args.get('port') is None:
                args['port'] = 80
            # open tunnel
            sshobj = t.sh.ssh('network', virtualnode=True, maxtries=1)
            tunnel = sshobj.tunnel(args['host'], int(args['port']))
            proxies = {'http':'http://127.0.0.1:{}'.format(tunnel.entranceport)}  # 127.0.0.1 == localhost == tunnel entrance
        else:
            tunnel = None
            proxies = {}
        try:
            send_task_to_DAVAI_server(davai_server_url,
                                      rh.provider.experiment,
                                      json.dumps(jsonData),
                                      kind=rh.resource.kind,
                                      fatal=fatal,
                                      proxies=proxies)
        finally:
            if tunnel:
                tunnel.close()
    except Exception as e:
        if fatal:
            raise
        else:
            logger.error(str(e))
