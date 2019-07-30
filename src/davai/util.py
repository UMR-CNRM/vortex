#!/usr/bin/env python
# -*- coding:Utf-8 -*-
"""
Functions and classes used by other modules from package.
"""
from __future__ import print_function, absolute_import, unicode_literals, division

from footprints import proxy as fpx

import os
import tempfile
import json
import re
import tarfile

from bronx.fancies import loggers

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class DavaiException(Exception):
    pass


def block_from_olive_tree():
    """Get block from the Olive tree."""
    return os.path.join(*os.environ['SMSNAME'].split(os.path.sep)[4:])


def default_experts():
    """Defaults experts for DAVAI Expertise."""
    return [dict(kind='drHookMax'),
            dict(kind='rss',
                 ntasks_per_node=os.environ['VORTEX_SUBMIT_TASKS']),
            ]


def send_task_to_DAVAI_server(davai_server_post_url, xpid, jsonData, kind,
                              fatal=True, **kwargs):
    """
    Send JSON data to DAVAI server.

    :param xpid: experiment identifier
    :param jsonData: data to be sent, formatted as output from json.dumps(...)
    :param kind: kind of data, among 'xpinfo' or 'taskinfo'
    :param fatal: raise errors (or log them and ignore)

    Additional kwargs are passed to requests.post()
    """
    import requests
    # data to be sent to api
    data = {'jsonData':jsonData,
            'xpid':xpid,
            'type':kind}
    # sending post request and saving response as response object
    try:
        r = requests.post(url=davai_server_post_url, data=data, **kwargs)
    except requests.ConnectionError as e:
        logger.error('Connection with remote server: {} failed: {}'.format(
            davai_server_post_url,
            str(e)))
        if fatal:
            raise
    else:
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


class SummariesStack(object):

    summaries_stack_dir = 'summaries_stack'
    trolleytar = 'trolley.tar'
    xpinfo = 'xpinfo.json'
    # syntax: taskinfo.scope.json
    _re_tasksummary = re.compile('(?P<task>.+)\.(?P<scope>' +
                                 '|'.join(('itself', 'consistency', 'continuity')) +
                                 ')\.json$')
    _task_junction = '-'

    def __init__(self, vapp, vconf, xpid):
        self.vapp = vapp
        self.vconf = vconf
        self.xpid = xpid
        self.cache = fpx.cache(kind='mtool')

    @property
    def stackdir_abspath(self):
        """Get absolute path of trolley."""
        path = os.path.join(self.cache.fullpath(''), self.incache_stackdir)
        if not os.path.exists(path):
            os.makedirs(path)
        return path

    @property
    def incache_stackdir(self):
        """Location of stack dir within cache."""
        return os.path.join(self.vapp, self.vconf, self.xpid,
                            self.summaries_stack_dir)

    @property
    def trolleytar_abspath(self):
        """Get absolute path of trolley."""
        return os.path.join(self.stackdir_abspath, self.trolleytar)

    def witness_trolleytar_obsolescence(self, t):
        """Witness trolley obsolescence, by writing explicit message in it."""
        # Note: we use temp file then move to ensure atomicity wrt other tasks or trolley loading
        _fd, tmp = tempfile.mkstemp(dir=os.getcwd())
        t.sh.close(_fd)
        with open(tmp, 'a') as out:
            json.dump({'Error':'A task has been ran AFTER last gathering of summaries ! Re-run gathering...'},
                      out)
        _fd, tmptar = tempfile.mkstemp(dir=os.getcwd(), suffix='.tar')
        t.sh.close(_fd)
        with tarfile.open(tmptar, "w") as tar:
            tar.add(tmp, 'obsolete.json')
        t.sh.mv(tmptar, self.trolleytar_abspath)

    def throw_on_stack(self, t, rh, reload_trolley=False):
        """Put summary on stack"""
        stacked_name = os.path.join(self.incache_stackdir,
                                    '.'.join([rh.provider.block.replace('/', self._task_junction),
                                              rh.resource.scope,
                                              rh.resource.nativefmt])
                                    )
        # put on cache
        self.cache.insert(stacked_name,
                          rh.container.localpath(),
                          intent='in',
                          fmt=rh.resource.nativefmt)
        if reload_trolley:
            self.load_trolleytar(t)
        else:
            # witness trolley obsolescence
            self.witness_trolleytar_obsolescence(t)

    def load_trolleytar(self, t):
        """Load summaries on trolley."""
        # Note: we use temp file then move to ensure atomicity wrt other tasks
        t.sh.rm(self.trolleytar_abspath)  # remove if existing but do not crash if not
        # create trolley tar
        _fd, tmptar = tempfile.mkstemp(dir=os.getcwd(), suffix='.tar')
        t.sh.close(_fd)
        with tarfile.open(tmptar, 'w') as tar:
            # browse files in stack, and add to tar
            for f in t.sh.listdir(self.stackdir_abspath):
                match = self._re_tasksummary.match(f)
                # if a summary or xpinfo, load it in trolley
                if match or f == self.xpinfo:
                    tar.add(os.path.join(self.stackdir_abspath, f), f)
        # ensure no trolley has been created in stack in between
        try:
            os.remove(self.trolleytar_abspath)  # here we use os and not t.sh.rm, because we need to catch an error
        except Exception as e:
            # trolley should not be present, since we deleted it before gathering
            if 'No such file or directory' not in str(e):
                raise e
        else:
            # in which case, a task has produced new results in between: raise an error !
            raise DavaiException("A task has been updated in between: re-run !")
        # move it to stack
        t.sh.mv(tmptar, self.trolleytar_abspath)
