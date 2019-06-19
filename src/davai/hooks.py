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

from .util import SummariesStack, DavaiException

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


def take_the_DAVAI_train(t, rh,
                         reload_trolley=False,
                         fatal=True):
    """Usual double put of summaries for DAVAI."""
    send_to_DAVAI_server(t, rh, fatal=fatal)
    throw_summary_on_stack(t, rh, reload_trolley=reload_trolley)


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

    :param fatal: if False, catch any errors and do not raise
    """
    server_syntax = 'http://<host>:<port>/<url>'
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
        assert davai_server_url, \
            "DAVAI_SERVER must be defined ! Expected syntax: " + server_syntax
        if not t.sh.default_target.isnetworknode:
            # Compute node: open tunnel for send to target
            # identify target
            _re_url = re.compile('http://(?P<host>.+):(?P<port>\d+)/(?P<url>.+)$')
            davai_server_match = _re_url.match(davai_server_url)
            assert davai_server_match is not None, \
                "DAVAI_SERVER does not match expected syntax: " + server_syntax
            args = davai_server_match.groupdict()
            # open tunnel
            sshobj = t.sh.ssh('network', virtualnode=True, maxtries=3)
            tunnel = sshobj.tunnel(args['host'], int(args['port']))
            davai_server_url = 'http://{}:{}/{}'.format(
                '127.0.0.1',  # 127.0.0.1 == localhost == tunnel entrance
                tunnel.entranceport,
                args['url'])
        else:
            tunnel = None
        try:
            _send_task_to_DAVAI_server(davai_server_url,
                                       rh.provider.experiment,
                                       json.dumps(jsonData),
                                       kind=rh.resource.kind,
                                       fatal=fatal)
        finally:
            if tunnel:
                tunnel.close()
    except Exception as e:
        if fatal:
            raise
        else:
            logger.error(str(e))


def _send_task_to_DAVAI_server(davai_server_url, xpid, jsonData, kind,
                               fatal=True):
    """
    Send JSON data to DAVAI server.

    :param xpid: experiment identifier
    :param jsonData: data to be sent, formatted as output from json.dumps(...)
    :param kind: kind of data, among 'xpinfo' or 'taskinfo'
    :param fatal: raise errors (or log them and ignore)
    """
    import requests
    # data to be sent to api
    data = {'jsonData':jsonData,
            'xpid':xpid,
            'type':kind}
    # sending post request and saving response as response object
    try:
        r = requests.post(url=davai_server_url, data=data)
    except requests.ConnectionError as e:
        logger.error('Connection with remote server: {} failed: {}'.format(
            davai_server_url,
            str(e)))
        if fatal:
            raise
    # Check returnCode/message
    resultDict = json.loads(r.text)
    # success
    if resultDict.get('returnCode') == 0:
        logger.info(resultDict.get('message'))
    # fail
    else:
        logger.error('The post failed: returnCode is {}'.format(
            resultDict.get('returnCode')))
        if fatal:
            raise DavaiException(resultDict.get('message'))
