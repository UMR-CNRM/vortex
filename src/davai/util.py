"""
Functions and classes used by other modules from package.
"""

from footprints import proxy as fpx

import errno
import json
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


def default_experts(excepted=[]):
    """Defaults experts for DAVAI Expertise."""
    default = [dict(kind='drHookMax'),
               dict(kind='rss',
                    ntasks_per_node=sessions.current().env['VORTEX_SUBMIT_TASKS']),
               dict(kind='setup', fatal_exceptions=False),
               ]
    return [e for e in default if e['kind'] not in excepted]


def guess_packname(git_ref,
                   compiler_label,
                   packtype,
                   compiler_flag=None,
                   abspath=False,
                   homepack=None,
                   to_bin=False):
    """
    Guess pack name from a number of arguments.

    :param git_ref: Git reference to be exported to pack
    :param compiler_label: gmkpack compiler label
    :param packtype: type of pack, among ('incr', 'main')
    :param compiler_flag: gmkpack compiler flag
    :param abspath: True if the absolute path to pack is requested (instead of basename)
    :param homepack: home of pack
    :param to_bin: True if the path to binaries subdirectory is requested
    """
    from ial_build.pygmkpack import GmkpackTool  # @UnresolvedImport
    return GmkpackTool.guess_pack_name(git_ref,
                                       compiler_label,
                                       compiler_flag,
                                       packtype,
                                       abspath=abspath,
                                       homepack=homepack,
                                       to_bin=to_bin)


def bundle_guess_packname(bundle,
                          compiler_label,
                          packtype,
                          compiler_flag=None,
                          abspath=False,
                          homepack=None,
                          to_bin=False):
    """
    Guess pack name from a number of arguments.

    :param bundle: bundle file (yaml)
    :param compiler_label: gmkpack compiler label
    :param packtype: type of pack, among ('incr', 'main')
    :param compiler_flag: gmkpack compiler flag
    :param abspath: True if the absolute path to pack is requested (instead of basename)
    :param homepack: home of pack
    :param to_bin: True if the path to binaries subdirectory is requested
    """
    from ial_build.algos import bundle_guess_packname  # @UnresolvedImport
    return bundle_guess_packname(bundle,
                                 compiler_label,
                                 packtype,
                                 compiler_flag=compiler_flag,
                                 abspath=abspath,
                                 homepack=homepack,
                                 to_bin=to_bin)


def send_task_to_DAVAI_server(davai_server_post_url, xpid, jsonData, kind,
                              fatal=True, proxies=None, **kwargs):
    """
    Send JSON data to DAVAI server.

    :param xpid: experiment identifier
    :param jsonData: data to be sent, formatted as output from json.dumps(...)
    :param kind: kind of data, among 'xpinfo' or 'taskinfo'/'statictaskinfo'
    :param fatal: raise errors (or log them and ignore)

    Additional kwargs are passed to requests.post()
    """
    # token
    t = sessions.current()
    token = t.env.get('CIBOULAI_TOKEN', '')
    if token == '':
        logger.error("Environment variable CIBOULAI_TOKEN must be set in order to send data to Ciboulai. " +
                     "Please contact your Davai admin to get a valid token.")
        if fatal:
            raise ValueError("Invalid CIBOULAI_TOKEN")
    # data to be sent to api
    data = {'jsonData': jsonData,
            'xpid': xpid,
            'type': kind,
            'token': token}
    # sending post request and saving response as response object
    try:
        rc, status, headers, rdata = http_post_data(url=davai_server_post_url, data=data,
                                                    proxies=proxies, **kwargs)
    except OSError as e:
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


def set_env4git():
    """Configure environment to have git available, from target config."""
    t = sessions.current()
    target = t.sh.target()
    git_installdir = target.config.get('git', 'git_installdir')
    if git_installdir not in ('', None):
        logger.info("Loading git from: '{}'".format(git_installdir))
        t.env.setbinpath(t.sh.path.join(git_installdir, 'bin'), 0)
        t.env['GIT_EXEC_PATH'] = t.sh.path.join(git_installdir,
                                                'libexec',
                                                'git-core')


class SummariesStack:

    summaries_stack_dir = 'summaries_stack'
    unhandled_flag = 'unhandled_items.whitness'
    trolleytar = 'trolley.tar'
    xpinfo = 'xpinfo.json'
    # syntax: taskinfo.scope.json or statictaskinfo.scope.json
    _re_tasksummary = re.compile(r'(?P<task>.+)\.(?P<scope>' +
                                 '|'.join(('itself', 'consistency', 'continuity')) +
                                 r')\.json$')
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
            with open(self.cache.fullpath(item)):
                pass
        except OSError as ioe:
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

    def tasks_status(self, print_it=False):
        """Get summarized tasks status."""
        XP_status = {}
        for f in sorted(self.cache.list('')):
            match = self._re_tasksummary.match(f)
            if match:
                task = match.group('task')
                with open(self.cache.fullpath(f)) as _f:
                    ts = json.load(_f)
                scope = match.group('scope')
                if scope == 'consistency':  # IGNORED for now
                    continue
                else:
                    status = XP_status.get(task, {})
                    if scope == 'itself':
                        status['Status'] = ts['Status']['short']
                    elif scope == 'continuity':
                        status['continuity'] = ts['comparisonStatus']['short']
                    XP_status[task] = status
        if print_it:
            fmt = '{:<60} {:10} {:>10}'
            print("In summaries stack:", self.cache.fullpath(''))
            print("-" * 82)
            print(fmt.format("Task", "Status", "continuity"))
            print("-" * 82)
            for task, status in XP_status.items():
                print(fmt.format(task, status['Status'], status.get('continuity', '-')))
            print("-" * 82)
        return XP_status

    def task_summary_fullpath(self, task):
        """Print fullpath of a task summaries in cache."""
        t = sessions.current()
        kind_desc = {'itself': "Execution summary",
                     'consistency': "Potential comparison to other task of the same XP",
                     'continuity': "Comparison to reference"}
        print("=" * 80)
        print("Task: {}".format(task))
        print("-" * (len(task) + 6) + "\n")
        for k in ['itself', 'consistency', 'continuity']:
            print("* {}:".format(kind_desc[k]))
            print("  " + "-" * len(kind_desc[k]))
            f = '.'.join([task, k, 'json'])
            fp = self.cache.fullpath(f)
            if t.sh.path.exists(fp):
                print("  => {}\n".format(fp))
            else:
                print("  => N/A")
        print("=" * 80)
