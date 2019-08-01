#!/usr/bin/env python
# -*- coding:Utf-8 -*-
"""
Functions and classes used by other modules from package.
"""
from __future__ import print_function, absolute_import, unicode_literals, division

from six.moves.urllib import error as urlerror

from footprints import proxy as fpx

import errno
import io
import re
import tarfile
import tempfile

from bronx.fancies import loggers

from vortex import sessions
from vortex.tools.net import http_post_data

#: No automatic export
__all__ = []

logger = loggers.getLogger(__name__)


class DavaiException(Exception):
    """Any exceptions thrown by DAVAI."""
    pass


def block_from_olive_tree():
    """Get block from the Olive tree."""
    t = sessions.current()
    return t.sh.path.join(* t.env['SMSNAME'].split(t.sh.path.sep)[4:])


def default_experts():
    """Defaults experts for DAVAI Expertise."""
    return [dict(kind='drHookMax'),
            dict(kind='rss',
                 ntasks_per_node=sessions.current().env['VORTEX_SUBMIT_TASKS']),
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
    # data to be sent to api
    data = {'jsonData': jsonData,
            'xpid': xpid,
            'type': kind}
    # sending post request and saving response as response object
    try:
        rc, status, headers, rdata = http_post_data(url=davai_server_post_url, data=data, **kwargs)
    except urlerror.URLError as e:
        logger.error('Connection with remote server: {} failed: {}'.format(
            davai_server_post_url,
            str(e)))
        if fatal:
            raise
    else:
        # success
        if rc:
            logger.info('HTTP Post suceeded: status=%d. data:\n%s',
                        status, rdata)
        # fail
        else:
            logger.error('HTTP post failed: status=%d. header:\n%s data:\n%s.',
                         status, headers, rdata)
            if fatal:
                raise DavaiException('HTTP post failed')


class SummariesStack(object):

    summaries_stack_dir = 'summaries_stack'
    unhandled_flag = 'unhandled_items.whitness'
    trolleytar = 'trolley.tar'
    xpinfo = 'xpinfo.json'
    # syntax: taskinfo.scope.json
    _re_tasksummary = re.compile('(?P<task>.+)\.(?P<scope>' +
                                 '|'.join(('itself', 'consistency', 'continuity')) +
                                 ')\.json$')
    _task_junction = '-'

    def __init__(self, ticket, vapp, vconf, xpid):
        self._sh = ticket.sh
        self.cache = fpx.cache(kind='mtool',
                               headdir=self._sh.path.join('vortex', vapp, vconf, xpid,
                                                          self.summaries_stack_dir))

    def _witness_trolleytar_obsolescence(self):
        """
        Witness trolley obsolescence, by setting the unhandled_flag and
        destroying the trolley.
        """
        # Create an empty file and place it in the cache
        with tempfile.NamedTemporaryFile(dir=self._sh.getcwd()) as tfh:
            self.cache.insert(self.unhandled_flag, tfh.name)
        # Delete the Tar file
        self.cache.delete(self.trolleytar)

    def throw_on_stack(self, rh):
        """Put summary on stack"""
        stacked_name = '.'.join([rh.provider.block.replace('/', self._task_junction),
                                 getattr(rh.resource, 'scope', 'all'),
                                 rh.resource.nativefmt])
        # put on cache
        rc = self.cache.insert(stacked_name, rh.container.localpath(),
                               intent='in', fmt=rh.resource.nativefmt)
        if rc:
            self._witness_trolleytar_obsolescence()
        return rc

    def _item_really_exists(self, item):
        """Check if an item really exists."""
        try:
            # ensure no new files have been dropped in the stack. To do so, check
            # if an unhandled_flag file exists (use open instead of "stat" since
            # "stat" can be affected by caching effects on network filesystems).
            with io.open(self.cache.fullpath(item), 'r'):
                pass
        except IOError as ioe:
            if ioe.errno != errno.ENOENT:
                raise ioe
            return False
        else:
            return True

    def load_trolleytar(self, fetch=False, local=None, intent='in'):
        """Load summaries on trolley."""
        # If the tar is already here, check that it's not too old...
        rc = (self._item_really_exists(self.trolleytar) and
              not self._item_really_exists(self.unhandled_flag))
        # The Tar file is missing or too old
        if not rc:
            self.cache.delete(self.unhandled_flag)
            self.cache.delete(self.trolleytar)
            # create trolley tar in a temporary file
            with tempfile.NamedTemporaryFile(dir=self._sh.getcwd(), suffix='.tar', mode='w+b') as tfh:
                with tarfile.open(fileobj=tfh, mode='w') as tar:
                    # browse files in stack, and add to tar
                    for f in self.cache.list(''):
                        match = self._re_tasksummary.match(f)
                        # if a summary or xpinfo, load it in trolley
                        if match or f == self.xpinfo:
                            tar.add(self.cache.fullpath(f), f)
                tfh.flush()
                if self._item_really_exists(self.unhandled_flag):
                    raise DavaiException("A task has been updated in between: re-run !")
                else:
                    rc = self.cache.insert(self.trolleytar, tfh.name, intent='in', format='tar')
        if fetch:
            return self.get_trolleytar_file(local, intent)
        else:
            return rc

    def get_trolleytar_file(self, local=None, intent='in'):
        """Return an opened filehandle to the trolley tar file."""
        if local is None:
            local = self.trolleytar
        return self.cache.retrieve(self.trolleytar, local, intent=intent, format='tar')
