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
    return os.path.join(*os.environ['SMSNAME'].split(os.path.sep)[6:])


def default_experts():
    """Defaults experts for DAVAI Expertise."""
    return [dict(kind='drHookMax'),
            dict(kind='rss',
                 ntasks_per_node=os.environ['VORTEX_SUBMIT_TASKS']),
            ]


class SummariesStack(object):

    summaries_stack_dir = 'summaries_stack'
    trolley = 'trolley.json'  # CLEANME: deprecated
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
    def trolley_abspath(self):  # CLEANME: deprecated
        """Get absolute path of trolley."""
        return os.path.join(self.stackdir_abspath, self.trolley)

    @property
    def trolleytar_abspath(self):
        """Get absolute path of trolley."""
        return os.path.join(self.stackdir_abspath, self.trolleytar)

    def witness_trolley_obsolescence(self, t):  # CLEANME: deprecated
        """Witness trolley obsolescence, by writing explicit message in it."""
        # Note: we use temp file then move to ensure atomicity wrt other tasks or trolley loading
        _fd, tmp = tempfile.mkstemp(dir=os.getcwd())
        t.sh.close(_fd)
        with open(tmp, 'a') as out:
            json.dump({'Error':'A task has been ran AFTER last gathering of summaries ! Re-run gathering...'},
                      out)
        t.sh.mv(tmp, self.trolley_abspath)

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

    def slurp_json_from_stack(self, file_basename):  # CLEANME: deprecated
        """Read json from file in stack."""
        with open(os.path.join(self.stackdir_abspath, file_basename)) as sf:
            summary = json.load(sf)
        return summary

    def load_trolley(self, t):  # CLEANME: deprecated
        """Load summaries on trolley."""
        t.sh.rm(self.trolley_abspath)
        trolley_dict = {}
        # browse files in stack
        for f in t.sh.listdir(self.stackdir_abspath):
            match = self._re_tasksummary.match(f)
            # if a summary, load it in trolley
            if match:
                task = match.group('task').replace(self._task_junction, '/')
                scope = match.group('scope')
                if task not in trolley_dict.keys():
                    trolley_dict[task] = {}
                summary = self.slurp_json_from_stack(f)
                trolley_dict[task][scope] = summary
            elif f == self.xpinfo:
                xpinfo = self.slurp_json_from_stack(f)
                trolley_dict['xpinfo'] = xpinfo
        # write trolley
        with open(self.trolley, 'w') as out:
            json.dump(trolley_dict, out)
        # and move it to stack
        # Note: we use temp file then move to ensure atomicity wrt other tasks
        try:
            os.remove(self.trolley_abspath)  # here we use os and not t.sh.rm, because we need to catch an error
        except Exception as e:
            # trolley should not be present, since we deleted it before gathering
            if 'No such file or directory' not in str(e):
                raise e
        else:
            # in which case, a task has produced new results in between: raise an error !
            raise DavaiException("A task has been updated in between: re-run !")
        t.sh.mv(self.trolley, self.trolley_abspath)
        # and get it back for archiving
        t.sh.cp(self.trolley_abspath, self.trolley)

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
