#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
TODO module description.
"""

from __future__ import print_function

import os
import pwd
import shutil
import io
import zipfile
import json
import time
from glob import glob
from datetime import datetime, timedelta

from bronx.patterns import getbytag
import footprints


#: No automatic export
__all__ = []

ZIP_ARCHIVE_BASE_PATH = 'archive'


# Module Interface

def get(**kw):
    """Return actual session ticket object matching description."""
    return Deposit(**kw)


def keys():
    """Return the list of current session tickets names collected."""
    return Deposit.tag_keys()


def values():
    """Return the list of current session ticket values collected."""
    return Deposit.tag_values()


def items():
    """Return the items of the session tickets table."""
    return Deposit.tag_items()


def clear_all():
    """Clear internal references to existing deposits."""
    Deposit.tag_clear()


def timestamp():
    """Time stamp with raw precision of a second."""
    return datetime.now().strftime('%Y%m%d%H%M%S')


def logname():
    """Technical wrapper to overcome some strange results of the native os.getlogin function."""
    return pwd.getpwuid(os.getuid())[0]


def duration_to_seconds(value):
    """Convert to seconds a duration given as an int, possibly
    suffixed with 's' for seconds (the default) , 'mn' for minutes,
    'h' for 'hours' or 'd' for days.

    >>> duration_to_seconds(3600)
    3600
    >>> duration_to_seconds('3600s')
    3600
    >>> duration_to_seconds('25mn')
    1500
    >>> duration_to_seconds('25H')
    90000
    >>> duration_to_seconds('3d')
    259200
    >>> duration_to_seconds('3m')
    Traceback (most recent call last):
     ...
    ValueError: invalid literal for int() with base 10: '3m'
    >>> duration_to_seconds('3w')
    Traceback (most recent call last):
     ...
    ValueError: invalid literal for int() with base 10: '3w'
    """
    try:
        value = int(value)
    except ValueError:
        value = str(value).lower().rstrip('s')
        if value.endswith('d'):
            value = value.rstrip('d')
            value = int(value) * 24 * 3600
        elif value.endswith('h'):
            value = value.rstrip('h')
            value = int(value) * 3600
        elif value.endswith('mn'):
            value = value[:-2]
            value = int(value) * 60
        else:
            value = int(value)
    return value


def clean_older_files(logger, path, timelimit, pattern='*'):
    """
    Remove files in this path matching the glob pattern and older than timelimit
    seconds (not recursive).

    See :py:func:`duration_to_seconds` for the timelimit accepted forms.
    """
    seconds = duration_to_seconds(timelimit)
    rightnow = time.time()
    antiques = [f for f in glob(os.path.join(path, pattern))
                if (os.path.isfile(f) and
                    (rightnow - os.path.getmtime(f)) > seconds)]
    logger.debug('Cleaning archived files', path=path, nfiles=len(antiques))
    for antique in antiques:
        os.remove(antique)


def parent_mkdir(path, mode=0o755):
    """Like ``mkdir -p``: creates parent directories if necessary.

    Does not change the mode of existing directories. Return ``True`` if at
    least one directory was created.
    """
    try:
        os.makedirs(path, mode=mode)
        return True
    except OSError:
        pass
    return False


def seconds_to_now(time):
    """Return the time delta in seconds between the current time
    and the parameter `time`.

    :param time: datetime object
    :return: delta in seconds
    """
    return (datetime.now() - time).total_seconds()


class Request(object):
    """
    The basic meta structure of any `ask` to Jeeves.
    """

    def __init__(self, todo='show', user=None, task=None, date=None,
                 opts=None, data=None, jtag=None,
                 mail=tuple(), conf=tuple(), apps=tuple(), info='Nope'):
        self.todo = todo
        self.user = user or logname()
        self.task = task or os.environ.get('JOBNAME') or os.environ.get('SMSNAME')
        self.date = date or timestamp()
        self.opts = dict() if opts is None else dict(opts)
        self.data = data
        self.jtag = jtag
        self.mail = footprints.util.mktuple(mail)
        self.conf = conf
        self.apps = apps
        self.info = str(info)
        self._dumpfiles = list()

    def filename(self, radical='depot/config'):
        """Build a standard json file name for ask requests."""
        subpath, radical = os.path.split(os.path.normpath(self.jtag or radical))
        while '..' in radical:
            radical = radical.replace('..', '.')
        while radical.endswith('.json'):
            radical = radical[:-5]
        while radical.startswith('ask.'):
            radical = radical[4:]
        return os.path.join(
            subpath,
            '.'.join((
                'ask',
                datetime.now().strftime('%Y%m%d%H%M%S.%f'),
                'P{0:06d}'.format(os.getpid()),
                logname(),
                radical,
                'json'
            ))
        )

    def as_dict(self):
        """Return the request as a plain dictionary."""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

    @property
    def last(self):
        return self._dumpfiles[-1] if self._dumpfiles else None

    @property
    def dumpfiles(self):
        return self._dumpfiles[:]

    def dump(self):
        """Dump request as a json file."""
        self._dumpfiles.append(self.filename())
        with io.open(self._dumpfiles[-1] + '.tmp', 'wb' if six.PY2 else 'w') as fd:
            json.dump(self.as_dict(), fd, sort_keys=True, indent=4)
        shutil.move(self._dumpfiles[-1] + '.tmp', self._dumpfiles[-1])
        return True

    def show(self, *args):
        """Display specified attributes values or all of them."""
        if not args:
            args = self.__dict__.keys() + ['last']
        for attr in sorted([x for x in args if not x.startswith('_')]):
            print(' *', attr, '=', getattr(self, attr))


class Deposit(getbytag.GetByTag):
    """Something simple to handle a directory used by Jeeves to process requests.

    - ``cleaning``   : is cleaning active for this pool
    - ``periodclean``: The archiving mechanism is activated every ``periodclean``.
    - ''maxitems''   : an archiving is triggered when more than maxitems are present in the pool
                       (and will be effective is the date condition is also met)
    - ``maxtime``    : same role as maxitems, but for the duration
    - ``keepzip``    : retention time for archived zip files
    - ``minclean``   : items older than this duration will be archived, whatever how few
    - ``tryclean``   : the last date the archiving process was run
    - ``lastclean``  : the last date the archiving was effectively performed
    """

    _tag_default = 'foo'

    def __init__(self, logger=None, path=None, active=False, target=None,
                 cleaning=True, maxitems=128, maxtime='24H', keepzip='10d',
                 periodclean='15mn', minclean='48H'):
        self._logger = logger
        self._target = target
        self._path = self.tag if path is None else path
        self.active = active
        self._cleaning = bool(cleaning)
        self._maxitems = int(maxitems)
        self._maxtime = duration_to_seconds(maxtime)
        self._keepzip = duration_to_seconds(keepzip)
        self._periodclean = duration_to_seconds(periodclean)
        self._tryclean = None
        self._lastclean = None
        self._minclean = duration_to_seconds(minclean)
        self._first_clean()

    @property
    def logger(self):
        return self._logger

    @property
    def cleaning(self):
        return self._cleaning

    @property
    def archivepath(self):
        return os.path.join(ZIP_ARCHIVE_BASE_PATH, self.path)

    def _get_path(self):
        return self._path

    def _set_path(self, value):
        if os.path.isdir(str(value)):
            self._path = str(value)
        else:
            self.logger.critical('Invalid path setting', pool=self.tag, path=value)
            raise ValueError('Invalid pool path setting')

    path = property(_get_path, _set_path)

    def _get_active(self):
        return self._active

    def _set_active(self, value):
        self._active = bool(value)

    active = property(_get_active, _set_active)

    def _get_target(self):
        return self._target

    def _set_target(self, value):
        if value is not None:
            if value in self.tag_keys():
                self._target = value
            else:
                self.logger.critical('Invalid target tag', pool=self.tag, target=value)
                raise ValueError('Invalid pool target setting')

    target = property(_get_target, _set_target)

    @property
    def maxitems(self):
        return self._maxitems

    @property
    def maxtime(self):
        return self._maxtime

    @property
    def keepzip(self):
        return self._keepzip

    @property
    def periodclean(self):
        return self._periodclean

    @property
    def minclean(self):
        return self._minclean

    @property
    def contents(self):
        return sorted([os.path.basename(x) for x in glob(self.path + '/ask.*.json')])

    def clean(self):
        """Try to clean up the current pool."""
        if self.cleaning and seconds_to_now(self._tryclean) >= self.periodclean:
            self._real_clean()

    def _cleaning_condition(self, items):
        """Return a (time, size) criterions pair: we will archive
        items older than the ``time`` criterion, but only if there
        are more of them than the ``size`` criterion.
        """
        if not items:
            return None, None
        elif len(items) > self.maxitems:
            return self.maxtime, self.maxitems
        elif seconds_to_now(self._lastclean) > self.minclean:
            return self.minclean, 0
        else:
            return None, None

    def _first_clean(self):
        """Run at deposit creation: set ``_last_clean``to force cleaning at initialization."""
        if not self.cleaning:
            return
        self._lastclean = datetime.now() - timedelta(hours=1, seconds=self.minclean)
        self._real_clean()

    def _real_clean(self):
        """Do the real cleaning."""
        items = self.contents
        justnow = datetime.now()
        self.logger.debug('status cleaning', path=self.path, len=len(items))
        self.logger.debug('last cleaning     : %s', self._lastclean)
        self.logger.debug('last try cleaning : %s', self._tryclean)
        self._tryclean = justnow

        cleaningtime, cleaningsize = self._cleaning_condition(items)
        if cleaningtime:
            oldfiles = list()
            self.logger.debug('cleaning', path=self.path, len=len(items),
                              len_clean=cleaningsize, maxtime=cleaningtime)
            for askfile in items:
                try:
                    askdate = datetime.strptime(askfile.split('.')[1], '%Y%m%d%H%M%S')
                except ValueError:
                    self.logger.error('Bad request format', item=askfile)
                    os.remove(os.path.join(self.path, askfile))
                else:
                    if seconds_to_now(askdate) > cleaningtime:
                        oldfiles.append(askfile)

            if len(oldfiles) > cleaningsize:
                zipname = os.path.join(
                    self.archivepath,
                    oldfiles[0].split('.')[1] + '-' + oldfiles[-1].split('.')[1] + '.zip'
                )
                self.logger.info('Zip', path=zipname, maxtime=cleaningtime, size=len(oldfiles))
                with zipfile.ZipFile(zipname, 'w') as pzip:
                    for xfile in oldfiles:
                        actualfile = os.path.join(self.path, xfile)
                        pzip.write(actualfile, xfile)
                        os.remove(actualfile)
                self._lastclean = justnow
                self.clean_archive()

    def migrate(self, item, target=None):
        """Migrate the request to the chained pool."""
        rc = None
        if target is None:
            target = self.target
        if item is not None and target is not None and target != self.tag:
            target = Deposit(tag=target)
            os.rename(os.path.join(self.path, item), os.path.join(target.path, item))
            rc = target.tag
        return rc

    def clean_archive(self):
        """Remove old archive files."""
        if self.cleaning:
            clean_older_files(self.logger, self.archivepath, self.keepzip, '*.zip')

    def cocoon(self):
        """Create directories for the pool and for it's zip archives."""
        if parent_mkdir(self.path, 0o755):
            self.logger.warning('Mkdir', pool=self.tag, path=self.path)
        else:
            self.logger.info('Mkdir skipped', pool=self.tag, path=self.path, size=len(self.contents))

        if self.cleaning:
            if parent_mkdir(self.archivepath):
                self.logger.warning('Mkdir', pool=self.tag, archivepath=self.archivepath)
            else:
                self.clean_archive()


if __name__ == '__main__':
    import doctest
    result = doctest.testmod(verbose=False)
    print('{}/{} tests passed.'.format(result.attempted - result.failed, result.attempted))
